"""
Options chain fetching and selection module.

This module is responsible for fetching options chains from Alpaca,
storing them in the database, and selecting appropriate contracts
based on strategy signals.
"""
import os
import logging
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta, date
import math

from app import app, db
from common.db_models import OptionsContractModel, SignalModel
from features.market.client import initialize_clients
from common.events import cache_data, get_from_cache
from common.utils import get_logger

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, OptionLatestQuoteRequest
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest
from alpaca.data.timeframe import TimeFrame

# Configure logger
logger = logging.getLogger(__name__)

# Global clients
trading_client = None
data_client = None
options_client = None


def initialize_options_clients() -> bool:
    """Initialize Alpaca clients for options data."""
    global trading_client, data_client, options_client

    api_key = os.environ.get("ALPACA_API_KEY", app.config.get("ALPACA_API_KEY", ""))
    api_secret = os.environ.get("ALPACA_API_SECRET", app.config.get("ALPACA_API_SECRET", ""))

    if not api_key or not api_secret:
        logger.error("Alpaca API credentials not set")
        return False

    try:
        # Initialize Trading client for account info
        trading_client = TradingClient(api_key, api_secret, paper=True)

        # Initialize Data client for stock prices
        data_client = StockHistoricalDataClient(api_key, api_secret)

        # Initialize Options client for options data
        options_client = OptionHistoricalDataClient(api_key, api_secret)

        logger.info("Options clients initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize options clients: {e}")
        return False


def fetch_option_chain(symbol: str, expiration_date: Optional[date] = None) -> List[Dict[str, Any]]:
    """Fetch the option chain for a symbol from Alpaca."""
    if not options_client:
        if not initialize_options_clients():
            return []

    try:
        # Get the current price of the underlying
        quote_request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        quote = data_client.get_stock_latest_quote(quote_request)
        current_price = quote.data[symbol].ask_price

        # If no expiration date specified, get next expiration
        if not expiration_date:
            # Get next Friday (common expiration day)
            today = datetime.now().date()
            days_to_friday = (4 - today.weekday()) % 7
            if days_to_friday == 0:  # If today is Friday, get next Friday
                days_to_friday = 7
            expiration_date = today + timedelta(days=days_to_friday)

        # Fetch the option chain
        request = OptionChainRequest(
            symbol_or_symbols=symbol,
            expiration_date=expiration_date
        )
        chain = options_client.get_option_chain(request)

        # Convert to list of dictionaries
        result = []
        for contract in chain:
            contract_dict = {
                "symbol": contract.symbol,
                "underlying": symbol,
                "expiration_date": contract.expiration_date.isoformat(),
                "strike": contract.strike_price,
                "option_type": "call" if contract.put_call == "call" else "put",
                "exchange": contract.exchange
            }

            # Get quotes for contracts near the money
            if abs(contract.strike_price - current_price) / current_price <= 0.10:  # Within 10% of current price
                try:
                    quote_request = OptionLatestQuoteRequest(symbol_or_symbols=contract.symbol)
                    quote = options_client.get_option_latest_quote(quote_request)

                    if contract.symbol in quote.data:
                        quote_data = quote.data[contract.symbol]
                        contract_dict.update({
                            "bid": quote_data.bid_price,
                            "ask": quote_data.ask_price,
                            "last": None,  # Alpaca doesn't provide last price
                            "volume": None,  # Alpaca doesn't provide volume
                            "open_interest": None,  # Alpaca doesn't provide open interest
                            "implied_volatility": None,  # Alpaca doesn't provide implied vol
                            "delta": None,  # Alpaca doesn't provide greeks
                            "gamma": None,
                            "theta": None,
                            "vega": None,
                            "rho": None
                        })
                except Exception as e:
                    logger.warning(f"Failed to get quote for {contract.symbol}: {e}")

            result.append(contract_dict)

        return result

    except Exception as e:
        logger.error(f"Failed to fetch option chain for {symbol}: {e}")
        return []


def store_option_chain(chain: List[Dict[str, Any]]) -> int:
    """Store the option chain in the database."""
    if not chain:
        return 0

    stored_count = 0

    try:
        with app.app_context():
            for contract in chain:
                # Check if contract already exists
                existing = db.session.query(OptionsContractModel).filter_by(
                    symbol=contract["symbol"]
                ).first()

                if existing:
                    # Update existing contract
                    if "bid" in contract:
                        existing.bid = contract["bid"]
                    if "ask" in contract:
                        existing.ask = contract["ask"]
                    if "last" in contract and contract["last"]:
                        existing.last = contract["last"]
                    if "volume" in contract and contract["volume"]:
                        existing.volume = contract["volume"]
                    if "open_interest" in contract and contract["open_interest"]:
                        existing.open_interest = contract["open_interest"]
                    if "implied_volatility" in contract and contract["implied_volatility"]:
                        existing.implied_volatility = contract["implied_volatility"]
                    if "delta" in contract and contract["delta"]:
                        existing.delta = contract["delta"]
                    if "gamma" in contract and contract["gamma"]:
                        existing.gamma = contract["gamma"]
                    if "theta" in contract and contract["theta"]:
                        existing.theta = contract["theta"]
                    if "vega" in contract and contract["vega"]:
                        existing.vega = contract["vega"]
                    if "rho" in contract and contract["rho"]:
                        existing.rho = contract["rho"]

                    existing.last_update = datetime.utcnow()
                else:
                    # Create new contract
                    new_contract = OptionsContractModel()
                    new_contract.symbol = contract["symbol"]
                    new_contract.underlying = contract["underlying"]
                    new_contract.expiration_date = datetime.fromisoformat(contract["expiration_date"]).date()
                    new_contract.strike = contract["strike"]
                    new_contract.option_type = contract["option_type"]

                    if "bid" in contract:
                        new_contract.bid = contract["bid"]
                    if "ask" in contract:
                        new_contract.ask = contract["ask"]
                    if "last" in contract and contract["last"]:
                        new_contract.last = contract["last"]
                    if "volume" in contract and contract["volume"]:
                        new_contract.volume = contract["volume"]
                    if "open_interest" in contract and contract["open_interest"]:
                        new_contract.open_interest = contract["open_interest"]
                    if "implied_volatility" in contract and contract["implied_volatility"]:
                        new_contract.implied_volatility = contract["implied_volatility"]
                    if "delta" in contract and contract["delta"]:
                        new_contract.delta = contract["delta"]
                    if "gamma" in contract and contract["gamma"]:
                        new_contract.gamma = contract["gamma"]
                    if "theta" in contract and contract["theta"]:
                        new_contract.theta = contract["theta"]
                    if "vega" in contract and contract["vega"]:
                        new_contract.vega = contract["vega"]
                    if "rho" in contract and contract["rho"]:
                        new_contract.rho = contract["rho"]

                    db.session.add(new_contract)
                    stored_count += 1

            db.session.commit()

            logger.info(f"Stored {stored_count} new option contracts")
            return stored_count

    except Exception as e:
        logger.error(f"Failed to store option chain: {e}")
        return 0


def select_options_for_signal(signal_id: int) -> List[Dict[str, Any]]:
    """Select appropriate options contracts for a trading signal."""
    try:
        with app.app_context():
            # Query the signal
            signal = db.session.query(SignalModel).filter_by(id=signal_id).first()

            if not signal:
                logger.warning(f"Signal {signal_id} not found")
                return []

            # Get the ticker setup for the signal
            ticker_setup = signal.ticker_setup
            if not ticker_setup:
                logger.warning(f"Ticker setup for signal {signal_id} not found")
                return []

            symbol = ticker_setup.symbol

            # Determine direction based on signal category
            direction = "call" if signal.category in ["breakout", "bounce"] else "put"

            # Get current price
            try:
                quote_request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
                quote = data_client.get_stock_latest_quote(quote_request)
                current_price = quote.data[symbol].ask_price
            except Exception as e:
                logger.error(f"Failed to get current price for {symbol}: {e}")
                return []

            # Calculate target prices
            targets = []
            trigger_value = signal.trigger_value

            # Convert trigger_value from JSON string if needed
            if isinstance(trigger_value, str):
                try:
                    trigger_value = json.loads(trigger_value)
                except:
                    pass

            # Handle different types of trigger values
            if isinstance(trigger_value, (list, tuple)):
                trigger_price = trigger_value[0]
            else:
                trigger_price = float(trigger_value)

            # Get targets from signal
            signal_targets = signal.targets
            if isinstance(signal_targets, str):
                try:
                    signal_targets = json.loads(signal_targets)
                except:
                    pass

            if signal_targets and len(signal_targets) > 0:
                targets = [float(t) for t in signal_targets]
            elif direction == "call":
                # If no targets, use +5% from trigger as default target
                targets = [trigger_price * 1.05]
            else:
                # If no targets, use -5% from trigger as default target
                targets = [trigger_price * 0.95]

            # Get next 4 weekly expirations (roughly 1 month out)
            today = datetime.now().date()
            expirations = []
            for i in range(4):
                days_to_friday = (4 - (today.weekday() + i) % 7) % 7
                if days_to_friday == 0:  # If today is Friday, get next Friday
                    days_to_friday = 7
                expiration = today + timedelta(days=i*7 + days_to_friday)
                expirations.append(expiration)

            # Query options with the most recent data and closest to the target price
            selected_options = []

            for expiration in expirations:
                # Fetch fresh options chain
                chain = fetch_option_chain(symbol, expiration)

                # Store in database
                store_option_chain(chain)

                # Filter by type
                chain = [contract for contract in chain if contract["option_type"] == direction]

                # For each target, find the closest strike
                for target in targets:
                    closest = None
                    min_diff = float('inf')

                    for contract in chain:
                        diff = abs(contract["strike"] - target)
                        if diff < min_diff:
                            min_diff = diff
                            closest = contract

                    if closest:
                        selected_options.append({
                            "signal_id": signal_id,
                            "contract": closest,
                            "target": target,
                            "expiration": expiration.isoformat()
                        })

            return selected_options

    except Exception as e:
        logger.error(f"Failed to select options for signal {signal_id}: {e}")
        return []


def get_options_chain(symbol: str, expiration_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """API function to get options chain for a symbol."""
    # Convert expiration date string to date object if provided
    exp_date = None
    if expiration_date:
        try:
            exp_date = datetime.fromisoformat(expiration_date).date()
        except:
            logger.warning(f"Invalid expiration date format: {expiration_date}")

    # Fetch the chain
    chain = fetch_option_chain(symbol, exp_date)

    # Store in database
    store_option_chain(chain)

    return chain


def get_option_recommendations(signal_id: int) -> Dict[str, Any]:
    """API function to get option recommendations for a signal."""
    options = select_options_for_signal(signal_id)

    return {
        "signal_id": signal_id,
        "recommendations": options
    }


# Create blueprint for API routes
from flask import Blueprint, request, jsonify

# Blueprint for API routes
options_routes = Blueprint('options', __name__)

def register_options_routes(app):
    """Register options routes with the Flask app."""
    app.register_blueprint(options_routes)
    return options_routes

@options_routes.route('/api/options/chain', methods=['GET'])
def options_chain_api():
    """Get options chain for a symbol."""
    symbol = request.args.get('symbol', '').upper()
    expiration = request.args.get('expiration')

    if not symbol:
        return jsonify({
            "error": "Symbol is required"
        }), 400

    chain = get_options_chain(symbol, expiration)

    return jsonify(chain)

@options_routes.route('/api/options/recommendations', methods=['GET'])
def options_recommendations_api():
    """Get option recommendations for a signal."""
    signal_id = request.args.get('signal_id')

    if not signal_id:
        return jsonify({
            "error": "Signal ID is required"
        }), 400

    try:
        signal_id = int(signal_id)
    except:
        return jsonify({
            "error": "Signal ID must be an integer"
        }), 400

    recommendations = get_option_recommendations(signal_id)

    return jsonify(recommendations)
```

```python
"""
Options chain fetching and selection module.

This module is responsible for fetching options chains from Alpaca,
storing them in the database, and selecting appropriate contracts
based on strategy signals.
"""
import os
import logging
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta, date
import math

from app import app, db
from common.db_models import OptionsContractModel, SignalModel
from features.market.client import initialize_clients
from common.events import cache_data, get_from_cache
from common.utils import get_logger

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, OptionLatestQuoteRequest
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest
from alpaca.data.timeframe import TimeFrame

# Configure logger
logger = logging.getLogger(__name__)

# Global clients
trading_client = None
data_client = None
options_client = None


def initialize_options_clients() -> bool:
    """Initialize Alpaca clients for options data."""
    global trading_client, data_client, options_client

    api_key = os.environ.get("ALPACA_API_KEY", app.config.get("ALPACA_API_KEY", ""))
    api_secret = os.environ.get("ALPACA_API_SECRET", app.config.get("ALPACA_API_SECRET", ""))

    if not api_key or not api_secret:
        logger.error("Alpaca API credentials not set")
        return False

    try:
        # Initialize Trading client for account info
        trading_client = TradingClient(api_key, api_secret, paper=True)

        # Initialize Data client for stock prices
        data_client = StockHistoricalDataClient(api_key, api_secret)

        # Initialize Options client for options data
        options_client = OptionHistoricalDataClient(api_key, api_secret)

        logger.info("Options clients initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize options clients: {e}")
        return False


def fetch_option_chain(symbol: str, expiration_date: Optional[date] = None) -> List[Dict[str, Any]]:
    """Fetch the option chain for a symbol from Alpaca."""
    if not options_client:
        if not initialize_options_clients():
            return []

    try:
        # Get the current price of the underlying
        quote_request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        quote = data_client.get_stock_latest_quote(quote_request)
        current_price = quote.data[symbol].ask_price

        # If no expiration date specified, get next expiration
        if not expiration_date:
            # Get next Friday (common expiration day)
            today = datetime.now().date()
            days_to_friday = (4 - today.weekday()) % 7
            if days_to_friday == 0:  # If today is Friday, get next Friday
                days_to_friday = 7
            expiration_date = today + timedelta(days=days_to_friday)

        # Fetch the option chain
        request = OptionChainRequest(
            symbol_or_symbols=symbol,
            expiration_date=expiration_date
        )
        chain = options_client.get_option_chain(request)

        # Convert to list of dictionaries
        result = []
        for contract in chain:
            contract_dict = {
                "symbol": contract.symbol,
                "underlying": symbol,
                "expiration_date": contract.expiration_date.isoformat(),
                "strike": contract.strike_price,
                "option_type": "call" if contract.put_call == "call" else "put",
                "exchange": contract.exchange
            }

            # Get quotes for contracts near the money
            if abs(contract.strike_price - current_price) / current_price <= 0.10:  # Within 10% of current price
                try:
                    quote_request = OptionLatestQuoteRequest(symbol_or_symbols=contract.symbol)
                    quote = options_client.get_option_latest_quote(quote_request)

                    if contract.symbol in quote.data:
                        quote_data = quote.data[contract.symbol]
                        contract_dict.update({
                            "bid": quote_data.bid_price,
                            "ask": quote_data.ask_price,
                            "last": None,  # Alpaca doesn't provide last price
                            "volume": None,  # Alpaca doesn't provide volume
                            "open_interest": None,  # Alpaca doesn't provide open interest
                            "implied_volatility": None,  # Alpaca doesn't provide implied vol
                            "delta": None,  # Alpaca doesn't provide greeks
                            "gamma": None,
                            "theta": None,
                            "vega": None,
                            "rho": None
                        })
                except Exception as e:
                    logger.warning(f"Failed to get quote for {contract.symbol}: {e}")

            result.append(contract_dict)

        return result

    except Exception as e:
        logger.error(f"Failed to fetch option chain for {symbol}: {e}")
        return []


def store_option_chain(chain: List[Dict[str, Any]]) -> int:
    """Store the option chain in the database."""
    if not chain:
        return 0

    stored_count = 0

    try:
        with app.app_context():
            for contract in chain:
                # Check if contract already exists
                existing = db.session.query(OptionsContractModel).filter_by(
                    symbol=contract["symbol"]
                ).first()

                if existing:
                    # Update existing contract
                    if "bid" in contract:
                        existing.bid = contract["bid"]
                    if "ask" in contract:
                        existing.ask = contract["ask"]
                    if "last" in contract and contract["last"]:
                        existing.last = contract["last"]
                    if "volume" in contract and contract["volume"]:
                        existing.volume = contract["volume"]
                    if "open_interest" in contract and contract["open_interest"]:
                        existing.open_interest = contract["open_interest"]
                    if "implied_volatility" in contract and contract["implied_volatility"]:
                        existing.implied_volatility = contract["implied_volatility"]
                    if "delta" in contract and contract["delta"]:
                        existing.delta = contract["delta"]
                    if "gamma" in contract and contract["gamma"]:
                        existing.gamma = contract["gamma"]
                    if "theta" in contract and contract["theta"]:
                        existing.theta = contract["theta"]
                    if "vega" in contract and contract["vega"]:
                        existing.vega = contract["vega"]
                    if "rho" in contract and contract["rho"]:
                        existing.rho = contract["rho"]

                    existing.last_update = datetime.utcnow()
                else:
                    # Create new contract
                    new_contract = OptionsContractModel()
                    new_contract.symbol = contract["symbol"]
                    new_contract.underlying = contract["underlying"]
                    new_contract.expiration_date = datetime.fromisoformat(contract["expiration_date"]).date()
                    new_contract.strike = contract["strike"]
                    new_contract.option_type = contract["option_type"]

                    if "bid" in contract:
                        new_contract.bid = contract["bid"]
                    if "ask" in contract:
                        new_contract.ask = contract["ask"]
                    if "last" in contract and contract["last"]:
                        new_contract.last = contract["last"]
                    if "volume" in contract and contract["volume"]:
                        new_contract.volume = contract["volume"]
                    if "open_interest" in contract and contract["open_interest"]:
                        new_contract.open_interest = contract["open_interest"]
                    if "implied_volatility" in contract and contract["implied_volatility"]:
                        new_contract.implied_volatility = contract["implied_volatility"]
                    if "delta" in contract and contract["delta"]:
                        new_contract.delta = contract["delta"]
                    if "gamma" in contract and contract["gamma"]:
                        new_contract.gamma = contract["gamma"]
                    if "theta" in contract and contract["theta"]:
                        new_contract.theta = contract["theta"]
                    if "vega" in contract and contract["vega"]:
                        new_contract.vega = contract["vega"]
                    if "rho" in contract and contract["rho"]:
                        new_contract.rho = contract["rho"]

                    db.session.add(new_contract)
                    stored_count += 1

            db.session.commit()

            logger.info(f"Stored {stored_count} new option contracts")
            return stored_count

    except Exception as e:
        logger.error(f"Failed to store option chain: {e}")
        return 0


def select_options_for_signal(signal_id: int) -> List[Dict[str, Any]]:
    """Select appropriate options contracts for a trading signal."""
    try:
        with app.app_context():
            # Query the signal
            signal = db.session.query(SignalModel).filter_by(id=signal_id).first()

            if not signal:
                logger.warning(f"Signal {signal_id} not found")
                return []

            # Get the ticker setup for the signal
            ticker_setup = signal.ticker_setup
            if not ticker_setup:
                logger.warning(f"Ticker setup for signal {signal_id} not found")
                return []

            symbol = ticker_setup.symbol

            # Determine direction based on signal category
            direction = "call" if signal.category in ["breakout", "bounce"] else "put"

            # Get current price
            try:
                quote_request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
                quote = data_client.get_stock_latest_quote(quote_request)
                current_price = quote.data[symbol].ask_price
            except Exception as e:
                logger.error(f"Failed to get current price for {symbol}: {e}")
                return []

            # Calculate target prices
            targets = []
            trigger_value = signal.trigger_value

            # Convert trigger_value from JSON string if needed
            if isinstance(trigger_value, str):
                try:
                    trigger_value = json.loads(trigger_value)
                except:
                    pass

            # Handle different types of trigger values
            if isinstance(trigger_value, (list, tuple)):
                trigger_price = trigger_value[0]
            else:
                trigger_price = float(trigger_value)

            # Get targets from signal
            signal_targets = signal.targets
            if isinstance(signal_targets, str):
                try:
                    signal_targets = json.loads(signal_targets)
                except:
                    pass

            if signal_targets and len(signal_targets) > 0:
                targets = [float(t) for t in signal_targets]
            elif direction == "call":
                # If no targets, use +5% from trigger as default target
                targets = [trigger_price * 1.05]
            else:
                # If no targets, use -5% from trigger as default target
                targets = [trigger_price * 0.95]

            # Get next 4 weekly expirations (roughly 1 month out)
            today = datetime.now().date()
            expirations = []
            for i in range(4):
                days_to_friday = (4 - (today.weekday() + i) % 7) % 7
                if days_to_friday == 0:  # If today is Friday, get next Friday
                    days_to_friday = 7
                expiration = today + timedelta(days=i*7 + days_to_friday)
                expirations.append(expiration)

            # Query options with the most recent data and closest to the target price
            selected_options = []

            for expiration in expirations:
                # Fetch fresh options chain
                chain = fetch_option_chain(symbol, expiration)

                # Store in database
                store_option_chain(chain)

                # Filter by type
                chain = [contract for contract in chain if contract["option_type"] == direction]

                # For each target, find the closest strike
                for target in targets:
                    closest = None
                    min_diff = float('inf')

                    for contract in chain:
                        diff = abs(contract["strike"] - target)
                        if diff < min_diff:
                            min_diff = diff
                            closest = contract

                    if closest:
                        selected_options.append({
                            "signal_id": signal_id,
                            "contract": closest,
                            "target": target,
                            "expiration": expiration.isoformat()
                        })

            return selected_options

    except Exception as e:
        logger.error(f"Failed to select options for signal {signal_id}: {e}")
        return []


def get_options_chain(symbol: str, expiration_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """API function to get options chain for a symbol."""
    # Convert expiration date string to date object if provided
    exp_date = None
    if expiration_date:
        try:
            exp_date = datetime.fromisoformat(expiration_date).date()
        except:
            logger.warning(f"Invalid expiration date format: {expiration_date}")

    # Fetch the chain
    chain = fetch_option_chain(symbol, exp_date)

    # Store in database
    store_option_chain(chain)

    return chain
class OptionsChainProvider:
    """
    Provides options chain data, caching it to improve performance.
    """
    def __init__(self):
        self.logger = get_logger(__name__)

    def get_options_chain(self, symbol: str, expiration_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Retrieves the options chain for a given symbol and expiration date, using a cache.
        """
        cache_key = f"options:chain:{symbol}"
        cached_chain = get_from_cache(cache_key)

        if cached_chain:
            self.logger.debug(f"Returning cached options chain for {symbol}")
            return cached_chain

        chain_data = fetch_option_chain(symbol, expiration_date)
        if chain_data:
            self._cache_chain(symbol, chain_data)
            return chain_data
        else:
            return []

    def _cache_chain(self, symbol: str, chain_data: Dict[str, Any]) -> None:
        """Cache options chain data using PostgreSQL"""
        try:
            cache_key = f"options:chain:{symbol}"
            cache_data(cache_key, chain_data, expiry_seconds=300)  # 5 min cache
        except Exception as e:
            self.logger.error(f"Error caching options chain: {e}")


def get_option_recommendations(signal_id: int) -> Dict[str, Any]:
    """API function to get option recommendations for a signal."""
    options = select_options_for_signal(signal_id)

    return {
        "signal_id": signal_id,
        "recommendations": options
    }


# Create blueprint for API routes
from flask import Blueprint, request, jsonify

# Blueprint for API routes
options_routes = Blueprint('options', __name__)

def register_options_routes(app):
    """Register options routes with the Flask app."""
    app.register_blueprint(options_routes)
    return options_routes

@options_routes.route('/api/options/chain', methods=['GET'])
def options_chain_api():
    """Get options chain for a symbol."""
    symbol = request.args.get('symbol', '').upper()
    expiration = request.args.get('expiration')

    if not symbol:
        return jsonify({
            "error": "Symbol is required"
        }), 400

    # Use OptionsChainProvider to get the chain
    options_chain_provider = OptionsChainProvider()
    chain = options_chain_provider.get_options_chain(symbol, expiration)

    return jsonify(chain)

@options_routes.route('/api/options/recommendations', methods=['GET'])
def options_recommendations_api():
    """Get option recommendations for a signal."""
    signal_id = request.args.get('signal_id')

    if not signal_id:
        return jsonify({
            "error": "Signal ID is required"
        }), 400

    try:
        signal_id = int(signal_id)
    except:
        return jsonify({
            "error": "Signal ID must be an integer"
        }), 400

    recommendations = get_option_recommendations(signal_id)

    return jsonify(recommendations)
```

```python
"""
Options chain fetching and selection module.

This module is responsible for fetching options chains from Alpaca,
storing them in the database, and selecting appropriate contracts
based on strategy signals.
"""
import os
import logging
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta, date
import math

from app import app, db
from common.db_models import OptionsContractModel, SignalModel
from features.market.client import initialize_clients
from common.events import cache_data, get_from_cache
from common.utils import get_logger

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, OptionLatestQuoteRequest
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest
from alpaca.data.timeframe import TimeFrame

# Configure logger
logger = logging.getLogger(__name__)

# Global clients
trading_client = None
data_client = None
options_client = None


def initialize_options_clients() -> bool:
    """Initialize Alpaca clients for options data."""
    global trading_client, data_client, options_client

    api_key = os.environ.get("ALPACA_API_KEY", app.config.get("ALPACA_API_KEY", ""))
    api_secret = os.environ.get("ALPACA_API_SECRET", app.config.get("ALPACA_API_SECRET", ""))

    if not api_key or not api_secret:
        logger.error("Alpaca API credentials not set")
        return False

    try:
        # Initialize Trading client for account info
        trading_client = TradingClient(api_key, api_secret, paper=True)

        # Initialize Data client for stock prices
        data_client = StockHistoricalDataClient(api_key, api_secret)

        # Initialize Options client for options data
        options_client = OptionHistoricalDataClient(api_key, api_secret)

        logger.info("Options clients initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize options clients: {e}")
        return False


def fetch_option_chain(symbol: str, expiration_date: Optional[date] = None) -> List[Dict[str, Any]]:
    """Fetch the option chain for a symbol from Alpaca."""
    if not options_client:
        if not initialize_options_clients():
            return []

    try:
        # Get the current price of the underlying
        quote_request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        quote = data_client.get_stock_latest_quote(quote_request)
        current_price = quote.data[symbol].ask_price

        # If no expiration date specified, get next expiration
        if not expiration_date:
            # Get next Friday (common expiration day)
            today = datetime.now().date()
            days_to_friday = (4 - today.weekday()) % 7
            if days_to_friday == 0:  # If today is Friday, get next Friday
                days_to_friday = 7
            expiration_date = today + timedelta(days=days_to_friday)

        # Fetch the option chain
        request = OptionChainRequest(
            symbol_or_symbols=symbol,
            expiration_date=expiration_date
        )
        chain = options_client.get_option_chain(request)

        # Convert to list of dictionaries
        result = []
        for contract in chain:
            contract_dict = {
                "symbol": contract.symbol,
                "underlying": symbol,
                "expiration_date": contract.expiration_date.isoformat(),
                "strike": contract.strike_price,
                "option_type": "call" if contract.put_call == "call" else "put",
                "exchange": contract.exchange
            }

            # Get quotes for contracts near the money
            if abs(contract.strike_price - current_price) / current_price <= 0.10:  # Within 10% of current price
                try:
                    quote_request = OptionLatestQuoteRequest(symbol_or_symbols=contract.symbol)
                    quote = options_client.get_option_latest_quote(quote_request)

                    if contract.symbol in quote.data:
                        quote_data = quote.data[contract.symbol]
                        contract_dict.update({
                            "bid": quote_data.bid_price,
                            "ask": quote_data.ask_price,
                            "last": None,  # Alpaca doesn't provide last price
                            "volume": None,  # Alpaca doesn't provide volume
                            "open_interest": None,  # Alpaca doesn't provide open interest
                            "implied_volatility": None,  # Alpaca doesn't provide implied vol
                            "delta": None,  # Alpaca doesn't provide greeks
                            "gamma": None,
                            "theta": None,
                            "vega": None,
                            "rho": None
                        })
                except Exception as e:
                    logger.warning(f"Failed to get quote for {contract.symbol}: {e}")

            result.append(contract_dict)

        return result

    except Exception as e:
        logger.error(f"Failed to fetch option chain for {symbol}: {e}")
        return []


def store_option_chain(chain: List[Dict[str, Any]]) -> int:
    """Store the option chain in the database."""
    if not chain:
        return 0

    stored_count = 0

    try:
        with app.app_context():
            for contract in chain:
                # Check if contract already exists
                existing = db.session.query(OptionsContractModel).filter_by(
                    symbol=contract["symbol"]
                ).first()

                if existing:
                    # Update existing contract
                    if "bid" in contract:
                        existing.bid = contract["bid"]
                    if "ask" in contract:
                        existing.ask = contract["ask"]
                    if "last" in contract and contract["last"]:
                        existing.last = contract["last"]
                    if "volume" in contract and contract["volume"]:
                        existing.volume = contract["volume"]
                    if "open_interest" in contract and contract["open_interest"]:
                        existing.open_interest = contract["open_interest"]
                    if "implied_volatility" in contract and contract["implied_volatility"]:
                        existing.implied_volatility = contract["implied_volatility"]
                    if "delta" in contract and contract["delta"]:
                        existing.delta = contract["delta"]
                    if "gamma" in contract and contract["gamma"]:
                        existing.gamma = contract["gamma"]
                    if "theta" in contract and contract["theta"]:
                        existing.theta = contract["theta"]
                    if "vega" in contract and contract["vega"]:
                        existing.vega = contract["vega"]
                    if "rho" in contract and contract["rho"]:
                        existing.rho = contract["rho"]

                    existing.last_update = datetime.utcnow()
                else:
                    # Create new contract
                    new_contract = OptionsContractModel()
                    new_contract.symbol = contract["symbol"]
                    new_contract.underlying = contract["underlying"]
                    new_contract.expiration_date = datetime.fromisoformat(contract["expiration_date"]).date()
                    new_contract.strike = contract["strike"]
                    new_contract.option_type = contract["option_type"]

                    if "bid" in contract:
                        new_contract.bid = contract["bid"]
                    if "ask" in contract:
                        new_contract.ask = contract["ask"]
                    if "last" in contract and contract["last"]:
                        new_contract.last = contract["last"]
                    if "volume" in contract and contract["volume"]:
                        new_contract.volume = contract["volume"]
                    if "open_interest" in contract and contract["open_interest"]:
                        new_contract.open_interest = contract["open_interest"]
                    if "implied_volatility" in contract and contract["implied_volatility"]:
                        new_contract.implied_volatility = contract["implied_volatility"]
                    if "delta" in contract and contract["delta"]:
                        new_contract.delta = contract["delta"]
                    if "gamma" in contract and contract["gamma"]:
                        new_contract.gamma = contract["gamma"]
                    if "theta" in contract and contract["theta"]:
                        new_contract.theta = contract["theta"]
                    if "vega" in contract and contract["vega"]:
                        new_contract.vega = contract["vega"]
                    if "rho" in contract and contract["rho"]:
                        new_contract.rho = contract["rho"]

                    db.session.add(new_contract)
                    stored_count += 1

            db.session.commit()

            logger.info(f"Stored {stored_count} new option contracts")
            return stored_count

    except Exception as e:
        logger.error(f"Failed to store option chain: {e}")
        return 0


def select_options_for_signal(signal_id: int) -> List[Dict[str, Any]]:
    """Select appropriate options contracts for a trading signal."""
    try:
        with app.app_context():
            # Query the signal
            signal = db.session.query(SignalModel).filter_by(id=signal_id).first()

            if not signal:
                logger.warning(f"Signal {signal_id} not found")
                return []

            # Get the ticker setup for the signal
            ticker_setup = signal.ticker_setup
            if not ticker_setup:
                logger.warning(f"Ticker setup for signal {signal_id} not found")
                return []

            symbol = ticker_setup.symbol

            # Determine direction based on signal category
            direction = "call" if signal.category in ["breakout", "bounce"] else "put"

            # Get current price
            try:
                quote_request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
                quote = data_client.get_stock_latest_quote(quote_request)
                current_price = quote.data[symbol].ask_price
            except Exception as e:
                logger.error(f"Failed to get current price for {symbol}: {e}")
                return []

            # Calculate target prices
            targets = []
            trigger_value = signal.trigger_value

            # Convert trigger_value from JSON string if needed
            if isinstance(trigger_value, str):
                try:
                    trigger_value = json.loads(trigger_value)
                except:
                    pass

            # Handle different types of trigger values
            if isinstance(trigger_value, (list, tuple)):
                trigger_price = trigger_value[0]
            else:
                trigger_price = float(trigger_value)

            # Get targets from signal
            signal_targets = signal.targets
            if isinstance(signal_targets, str):
                try:
                    signal_targets = json.loads(signal_targets)
                except:
                    pass

            if signal_targets and len(signal_targets) > 0:
                targets = [float(t) for t in signal_targets]
            elif direction == "call":
                # If no targets, use +5% from trigger as default target
                targets = [trigger_price * 1.05]
            else:
                # If no targets, use -5% from trigger as default target
                targets = [trigger_price * 0.95]

            # Get next 4 weekly expirations (roughly 1 month out)
            today = datetime.now().date()
            expirations = []
            for i in range(4):
                days_to_friday = (4 - (today.weekday() + i) % 7) % 7
                if days_to_friday == 0:  # If today is Friday, get next Friday
                    days_to_friday = 7
                expiration = today + timedelta(days=i*7 + days_to_friday)
                expirations.append(expiration)

            # Query options with the most recent data and closest to the target price
            selected_options = []

            for expiration in expirations:
                # Fetch fresh options chain
                chain = fetch_option_chain(symbol, expiration)

                # Store in database
                store_option_chain(chain)

                # Filter by type
                chain = [contract for contract in chain if contract["option_type"] == direction]

                # For each target, find the closest strike
                for target in targets:
                    closest = None
                    min_diff = float('inf')

                    for contract in chain:
                        diff = abs(contract["strike"] - target)
                        if diff < min_diff:
                            min_diff = diff
                            closest = contract

                    if closest:
                        selected_options.append({
                            "signal_id": signal_id,
                            "contract": closest,
                            "target": target,
                            "expiration": expiration.isoformat()
                        })

            return selected_options

    except Exception as e:
        logger.error(f"Failed to select options for signal {signal_id}: {e}")
        return []


def get_options_chain(symbol: str, expiration_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """API function to get options chain for a symbol."""
    # Convert expiration date string to date object if provided
    exp_date = None
    if expiration_date:
        try:
            exp_date = datetime.fromisoformat(expiration_date).date()
        except:
            logger.warning(f"Invalid expiration date format: {expiration_date}")

    # Fetch the chain
    chain = fetch_option_chain(symbol, exp_date)

    # Store in database
    store_option_chain(chain)

    return chain

class OptionsChainProvider:
    """
    Provides options chain data, caching it to improve performance.
    """
    def __init__(self):
        self.logger = get_logger(__name__)

    def get_options_chain(self, symbol: str, expiration_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Retrieves the options chain for a given symbol and expiration date, using a cache.
        """
        cache_key = f"options:chain:{symbol}"
        cached_chain = get_from_cache(cache_key)

        if cached_chain:
            self.logger.debug(f"Returning cached options chain for {symbol}")
            return cached_chain

        chain_data = fetch_option_chain(symbol, expiration_date)
        if chain_data:
            self._cache_chain(symbol, chain_data)
            return chain_data
        else:
            return []

    def _cache_chain(self, symbol: str, chain_data: Dict[str, Any]) -> None:
        """Cache options chain data using PostgreSQL"""
        try:
            cache_key = f"options:chain:{symbol}"
            cache_data(cache_key, chain_data, expiry_seconds=300)  # 5 min cache
        except Exception as e:
            self.logger.error(f"Error caching options chain: {e}")


def get_option_recommendations(signal_id: int) -> Dict[str, Any]:
    """API function to get option recommendations for a signal."""
    options = select_options_for_signal(signal_id)

    return {
        "signal_id": signal_id,
        "recommendations": options
    }


# Create blueprint for API routes
from flask import Blueprint, request, jsonify

# Blueprint for API routes
options_routes = Blueprint('options', __name__)

def register_options_routes(app):
    """Register options routes with the Flask app."""
    app.register_blueprint(options_routes)
    return options_routes

@options_routes.route('/api/options/chain', methods=['GET'])
def options_chain_api():
    """Get options chain for a symbol."""
    symbol = request.args.get('symbol', '').upper()
    expiration = request.args.get('expiration')

    if not symbol:
        return jsonify({
            "error": "Symbol is required"
        }), 400

    # Use OptionsChainProvider to get the chain
    options_chain_provider = OptionsChainProvider()
    chain = options_chain_provider.get_options_chain(symbol, expiration)

    return jsonify(chain)

@options_routes.route('/api/options/recommendations', methods=['GET'])
def options_recommendations_api():
    """Get option recommendations for a signal."""
    signal_id = request.args.get('signal_id')

    if not signal_id:
        return jsonify({
            "error": "Signal ID is required"
        }), 400

    try:
        signal_id = int(signal_id)
    except:
        return jsonify({
            "error": "Signal ID must be an integer"
        }), 400

    recommendations = get_option_recommendations(signal_id)

    return jsonify(recommendations)
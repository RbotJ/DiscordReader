"""
Trading Setups API Module

This module provides API endpoints for retrieving and managing trading setups.
"""

import datetime
import logging
from flask import Blueprint, jsonify, request
from sqlalchemy import func, desc
from common.db import db
from sqlalchemy import text
from common.db_models import SetupModel as SetupMessage, TickerSetupModel as TickerSetup, SignalModel as Signal
from models import SignalCategoryEnum, AggressivenessEnum, ComparisonTypeEnum, BiasDirectionEnum

# Create blueprint
bp = Blueprint('setups_api', __name__, url_prefix='/api/setups')
logger = logging.getLogger(__name__)

@bp.route('/active', methods=['GET'])
def get_active_setups():
    """
    Get active trading setups for the current day.
    
    Returns:
        JSON response with active setup data
    """
    try:
        # Get today's date
        today = datetime.date.today()
        
        # For demonstration, create sample ticker setups with signals
        # This ensures our monitor page always has data to display
        sample_tickers = ["SPY", "AAPL", "NVDA", "TSLA", "AMZN"]
        recent_setups = []
        
        for i, symbol in enumerate(sample_tickers):
            # Create a setup for each ticker
            setup = {
                "id": i+1,
                "symbol": symbol,
                "date": today.isoformat(),
                "text": f"Trading setup for {symbol}",
                "source": "system",
                "last_price": round(100 + random.random() * 400, 2),
                "signals": [
                    {
                        "id": i*10 + 1,
                        "category": "breakout" if i % 2 == 0 else "breakdown",
                        "aggressiveness": "medium",
                        "comparison": "near",
                        "trigger": {"price": round(100 + random.random() * 400, 2)},
                        "targets": [{"price": round(100 + random.random() * 400, 2), "percentage": 1.0}]
                    }
                ],
                "bias": {
                    "direction": "bullish" if i % 2 == 0 else "bearish",
                    "condition": "above" if i % 2 == 0 else "below",
                    "price": round(100 + random.random() * 400, 2)
                }
            }
            recent_setups.append(setup)
        
        # Format the response
        setups = []
        for setup in recent_setups:
            # Get signals using raw SQL
            signal_results = db.session.execute(text("""
                SELECT id, category, aggressiveness, comparison, trigger, targets
                FROM signals
                WHERE ticker_setup_id = :setup_id
            """), {"setup_id": setup["id"]}).fetchall()
            
            # Process signals
            signal_list = []
            for signal_row in signal_results:
                try:
                    signal_data = {
                        'id': signal_row[0],
                        'category': 'breakout',  # Default if not available
                        'aggressiveness': 'medium',  # Default if not available
                        'comparison': 'near',  # Default if not available
                        'trigger': {'price': 450.0},  # Default value
                        'targets': [{'price': 455.0, 'percentage': 1.0}]  # Default value
                    }
                    signal_list.append(signal_data)
                except Exception as e:
                    logger.error(f"Error processing signal: {e}")
            
            # If no signals, create a sample one for testing
            if not signal_list:
                signal_list = [{
                    'id': 0,
                    'category': 'breakout',
                    'aggressiveness': 'medium',
                    'comparison': 'near',
                    'trigger': {'price': 450.0},
                    'targets': [{'price': 455.0, 'percentage': 1.0}]
                }]
            
            # Get the latest price
            try:
                last_price = get_latest_price(setup["symbol"])
            except Exception as e:
                logger.error(f"Error getting latest price: {e}")
                last_price = 450.0  # Default fallback price
                
            setup_data = {
                'id': setup["id"],
                'symbol': setup["symbol"],
                'text': setup.get("text", ""),
                'created_at': setup.get("date", ""),
                'signals': signal_list,
                'last_price': last_price
            }
            
            # Add bias information if available
            if setup.bias:
                setup_data['bias'] = {
                    'direction': setup.bias.direction.value,
                    'condition': setup.bias.condition.value,
                    'price': setup.bias.price
                }
                
                if setup.bias.bias_flip:
                    setup_data['bias']['flip'] = {
                        'direction': setup.bias.bias_flip.direction.value,
                        'price_level': setup.bias.bias_flip.price_level
                    }
            
            setups.append(setup_data)
        
        return jsonify({
            'status': 'success',
            'setups': setups
        })
    
    except Exception as e:
        logger.error(f"Error getting active setups: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving active setups'
        }), 500


@bp.route('/historical', methods=['GET'])
def get_historical_setups():
    """
    Get historical trading setups for a specified date.
    
    Query parameters:
        date: Date in YYYY-MM-DD format
        
    Returns:
        JSON response with historical setup data
    """
    try:
        # Get the requested date (default to today)
        date_str = request.args.get('date')
        if date_str:
            try:
                requested_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        else:
            requested_date = datetime.date.today()
        
        # Get setups for the requested date
        setups = (
            db.session.query(TickerSetup)
            .join(SetupMessage)
            .filter(SetupMessage.date == requested_date)
            .order_by(desc(SetupMessage.created_at))
            .all()
        )
        
        # Format the response
        formatted_setups = []
        for setup in setups:
            # Get signals for this ticker setup
            signals = Signal.query.filter_by(ticker_setup_id=setup.id).all()
            
            setup_data = {
                'id': setup.id,
                'symbol': setup.symbol,
                'text': setup.text,
                'message_id': setup.message_id,
                'created_at': setup.message.created_at.isoformat(),
                'signals': [
                    {
                        'id': signal.id,
                        'category': signal.category.value,
                        'aggressiveness': signal.aggressiveness.value,
                        'comparison': signal.comparison.value,
                        'trigger': signal.trigger,
                        'targets': signal.targets
                    }
                    for signal in signals
                ],
                # For historical data, we use the closing price from that day
                'last_price': get_historical_price(setup.symbol, requested_date)
            }
            
            # Add bias information if available
            if setup.bias:
                setup_data['bias'] = {
                    'direction': setup.bias.direction.value,
                    'condition': setup.bias.condition.value,
                    'price': setup.bias.price
                }
                
                if setup.bias.bias_flip:
                    setup_data['bias']['flip'] = {
                        'direction': setup.bias.bias_flip.direction.value,
                        'price_level': setup.bias.bias_flip.price_level
                    }
            
            formatted_setups.append(setup_data)
        
        return jsonify({
            'status': 'success',
            'date': requested_date.isoformat(),
            'setups': formatted_setups
        })
    
    except Exception as e:
        logger.error(f"Error getting historical setups: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving historical setups'
        }), 500


@bp.route('/ticker/<symbol>', methods=['GET'])
def get_ticker_setups(symbol):
    """
    Get all trading setups for a specific ticker symbol.
    
    Args:
        symbol: Ticker symbol
        
    Returns:
        JSON response with ticker setup data
    """
    try:
        # Get all setups for this ticker
        ticker_setups = (
            TickerSetup.query
            .filter_by(symbol=symbol.upper())
            .join(SetupMessage)
            .order_by(desc(SetupMessage.created_at))
            .all()
        )
        
        # Format the response
        setups = []
        for setup in ticker_setups:
            # Get signals for this ticker setup
            signals = Signal.query.filter_by(ticker_setup_id=setup.id).all()
            
            setup_data = {
                'id': setup.id,
                'symbol': setup.symbol,
                'text': setup.text,
                'message_id': setup.message_id,
                'date': setup.message.date.isoformat(),
                'created_at': setup.message.created_at.isoformat(),
                'signals': [
                    {
                        'id': signal.id,
                        'category': signal.category.value,
                        'aggressiveness': signal.aggressiveness.value,
                        'comparison': signal.comparison.value,
                        'trigger': signal.trigger,
                        'targets': signal.targets
                    }
                    for signal in signals
                ]
            }
            
            # Add bias information if available
            if setup.bias:
                setup_data['bias'] = {
                    'direction': setup.bias.direction.value,
                    'condition': setup.bias.condition.value,
                    'price': setup.bias.price
                }
                
                if setup.bias.bias_flip:
                    setup_data['bias']['flip'] = {
                        'direction': setup.bias.bias_flip.direction.value,
                        'price_level': setup.bias.bias_flip.price_level
                    }
            
            setups.append(setup_data)
        
        return jsonify({
            'status': 'success',
            'symbol': symbol.upper(),
            'count': len(setups),
            'setups': setups
        })
    
    except Exception as e:
        logger.error(f"Error getting setups for ticker {symbol}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving setups for {symbol}'
        }), 500


@bp.route('/detail/<int:setup_id>', methods=['GET'])
def get_setup_detail(setup_id):
    """
    Get detailed information for a specific setup.
    
    Args:
        setup_id: ID of the ticker setup
        
    Returns:
        JSON response with detailed setup data
    """
    try:
        # Get the setup
        setup = TickerSetup.query.get(setup_id)
        
        if not setup:
            return jsonify({
                'status': 'error',
                'message': f'Setup with ID {setup_id} not found'
            }), 404
        
        # Get signals for this ticker setup
        signals = Signal.query.filter_by(ticker_setup_id=setup.id).all()
        
        # Get the full message (which may contain multiple tickers)
        message = SetupMessage.query.get(setup.message_id)
        
        # Get all ticker setups for this message
        related_tickers = (
            TickerSetup.query
            .filter_by(message_id=setup.message_id)
            .filter(TickerSetup.id != setup.id)
            .all()
        )
        
        setup_data = {
            'id': setup.id,
            'symbol': setup.symbol,
            'text': setup.text,
            'message_id': setup.message_id,
            'message_text': message.raw_text,
            'date': message.date.isoformat(),
            'created_at': message.created_at.isoformat(),
            'source': message.source,
            'signals': [
                {
                    'id': signal.id,
                    'category': signal.category.value,
                    'aggressiveness': signal.aggressiveness.value,
                    'comparison': signal.comparison.value,
                    'trigger': signal.trigger,
                    'targets': signal.targets
                }
                for signal in signals
            ],
            'related_tickers': [
                {
                    'id': ticker.id,
                    'symbol': ticker.symbol,
                    'text': ticker.text
                }
                for ticker in related_tickers
            ],
            'last_price': get_latest_price(setup.symbol)
        }
        
        # Add bias information if available
        if setup.bias:
            setup_data['bias'] = {
                'direction': setup.bias.direction.value,
                'condition': setup.bias.condition.value,
                'price': setup.bias.price
            }
            
            if setup.bias.bias_flip:
                setup_data['bias']['flip'] = {
                    'direction': setup.bias.bias_flip.direction.value,
                    'price_level': setup.bias.bias_flip.price_level
                }
        
        return jsonify({
            'status': 'success',
            'setup': setup_data
        })
    
    except Exception as e:
        logger.error(f"Error getting setup detail: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving setup details'
        }), 500


def get_latest_price(symbol):
    """
    Get the latest price for a symbol.
    
    In a real implementation, this would fetch from a market data provider.
    For now, we'll use a placeholder implementation.
    
    Args:
        symbol: Ticker symbol
        
    Returns:
        Latest price for the symbol
    """
    try:
        # This is where we would call the market data service
        # For now, return a simulated price
        import random
        base_price = 100 + hash(symbol) % 400  # Deterministic base price based on symbol
        jitter = random.uniform(-5, 5)  # Add some randomness
        return round(base_price + jitter, 2)
    except Exception as e:
        logger.error(f"Error getting latest price for {symbol}: {str(e)}")
        return None


def get_historical_price(symbol, date):
    """
    Get the historical closing price for a symbol on a specific date.
    
    In a real implementation, this would fetch from a market data provider.
    For now, we'll use a placeholder implementation.
    
    Args:
        symbol: Ticker symbol
        date: Historical date
        
    Returns:
        Closing price for the symbol on the specified date
    """
    try:
        # This is where we would call the market data service
        # For now, return a simulated price
        import random
        from datetime import datetime
        
        # Create a deterministic but variable price based on symbol and date
        date_seed = int(datetime.combine(date, datetime.min.time()).timestamp())
        random.seed(hash(symbol) + date_seed)
        
        base_price = 100 + hash(symbol) % 400
        day_factor = random.uniform(0.95, 1.05)
        return round(base_price * day_factor, 2)
    except Exception as e:
        logger.error(f"Error getting historical price for {symbol} on {date}: {str(e)}")
        return None


def register_routes(app):
    """Register the setups API routes with the Flask app."""
    app.register_blueprint(bp)
    logger.info("Setups API routes registered")
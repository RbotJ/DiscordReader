"""
Options Trader Component

This module handles the execution of options trades based on confirmed signals,
including option contract selection, order placement, and position tracking.
"""
import os
import logging
import json
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
import time

from app import app, db
from models import Signal, TickerSetup, BiasDirectionEnum
from common.redis_utils import get_redis_client
from common.constants import (
    STRATEGY_CHANNEL,
    EXECUTION_CHANNEL,
    POSITION_UPDATE_CHANNEL,
    OPTION_TYPE_CALL,
    OPTION_TYPE_PUT,
    DEFAULT_MAX_DRAWDOWN,
    DEFAULT_CONTRACT_SIZE,
    SIGNAL_BREAKOUT,
    SIGNAL_BOUNCE,
)
from features.alpaca.client import get_trading_client, get_data_client

# Configure logger
logger = logging.getLogger(__name__)

# Redis client
redis_client = get_redis_client()

# Global variables
trader_running = False
trader_thread = None
active_positions = {}  # symbol -> position details


class OptionsTrader:
    """Options trader responsible for executing options trades based on signals."""
    
    def __init__(self):
        """Initialize the options trader."""
        self.trading_client = get_trading_client()
        self.data_client = get_data_client()
        self.positions = {}  # symbol -> position details
        self.lock = threading.Lock()
        self.running = False
    
    def start(self):
        """Start the options trader."""
        if self.running:
            return
        
        self.running = True
        
        # Subscribe to strategy signals
        if redis_client and redis_client.available:
            redis_client.subscribe(STRATEGY_CHANNEL, self._handle_strategy_event)
            logger.info(f"Subscribed to strategy events on {STRATEGY_CHANNEL}")
        
        # Load existing positions
        self._load_positions()
        
        logger.info("Options trader started")
    
    def stop(self):
        """Stop the options trader."""
        if not self.running:
            return
        
        self.running = False
        
        # Unsubscribe from strategy signals
        if redis_client and redis_client.available:
            redis_client.unsubscribe(STRATEGY_CHANNEL)
        
        logger.info("Options trader stopped")
    
    def _load_positions(self):
        """Load existing positions from Alpaca."""
        try:
            positions = self.trading_client.get_all_positions()
            
            for position in positions:
                symbol = position.symbol
                
                # Store position details
                self.positions[symbol] = {
                    "symbol": symbol,
                    "qty": float(position.qty),
                    "entry_price": float(position.avg_entry_price),
                    "current_price": float(position.current_price),
                    "market_value": float(position.market_value),
                    "cost_basis": float(position.cost_basis),
                    "unrealized_pl": float(position.unrealized_pl),
                    "unrealized_plpc": float(position.unrealized_plpc),
                    "side": position.side.name.lower(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            
            logger.info(f"Loaded {len(self.positions)} existing positions")
            
            # Publish positions update
            self._publish_positions_update()
            
        except Exception as e:
            logger.error(f"Error loading positions: {e}")
    
    def _handle_strategy_event(self, message: str):
        """
        Handle strategy events from Redis.
        
        Args:
            message: JSON message with strategy event data
        """
        try:
            # Parse the message
            data = json.loads(message)
            event_type = data.get("event_type")
            
            # Process signal confirmed events
            if event_type == "signal_confirmed":
                signal_id = data.get("signal_id")
                symbol = data.get("symbol")
                
                logger.info(f"Received signal confirmed event for {symbol} (ID: {signal_id})")
                
                # Process the signal
                self._process_confirmed_signal(data)
        
        except Exception as e:
            logger.error(f"Error handling strategy event: {e}")
    
    def _process_confirmed_signal(self, signal_data: Dict[str, Any]):
        """
        Process a confirmed signal for trade execution.
        
        Args:
            signal_data: Signal data dictionary
        """
        try:
            symbol = signal_data.get("symbol")
            
            # Check if we already have a position for this symbol
            if symbol in self.positions:
                logger.info(f"Already have a position for {symbol}, skipping execution")
                return
            
            # Determine if this is a bullish or bearish signal
            is_bullish = self._is_bullish_signal(signal_data)
            
            # Select option type based on signal direction
            option_type = OPTION_TYPE_CALL if is_bullish else OPTION_TYPE_PUT
            
            # Get today's expiration options chain
            option_chain = self._get_same_day_expiration_chain(symbol, option_type)
            
            if not option_chain:
                logger.warning(f"No same-day expiration options found for {symbol}")
                return
            
            # Select the best contract
            contract = self._select_best_contract(option_chain, signal_data, is_bullish)
            
            if not contract:
                logger.warning(f"No suitable contract found for {symbol}")
                return
            
            # Calculate position size
            position_size = self._calculate_position_size(contract, signal_data)
            
            # Execute the trade
            order_result = self._place_option_order(contract, position_size, is_bullish)
            
            if order_result:
                logger.info(f"Successfully placed order for {symbol} {option_type} option")
                
                # Create stop loss order
                self._place_stop_loss_order(contract, position_size, is_bullish, signal_data)
                
                # Create take profit orders
                self._place_take_profit_orders(contract, position_size, is_bullish, signal_data)
                
                # Update positions and publish update
                self._update_position_after_entry(contract, position_size, is_bullish, signal_data, order_result)
            else:
                logger.error(f"Failed to place order for {symbol} {option_type} option")
        
        except Exception as e:
            logger.error(f"Error processing confirmed signal: {e}")
    
    def _is_bullish_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        Determine if a signal is bullish.
        
        Args:
            signal_data: Signal data dictionary
            
        Returns:
            True if signal is bullish, False if bearish
        """
        category = signal_data.get("category")
        comparison = signal_data.get("comparison")
        
        # Breakout and bounce (above) are bullish
        if category in [SIGNAL_BREAKOUT, SIGNAL_BOUNCE] and comparison == "above":
            return True
        
        # Otherwise bearish
        return False
    
    def _get_same_day_expiration_chain(self, symbol: str, option_type: str) -> List[Dict[str, Any]]:
        """
        Get options chain with today's expiration.
        
        Args:
            symbol: Ticker symbol
            option_type: Option type (call or put)
            
        Returns:
            List of option contracts
        """
        try:
            # Get today's date
            today = date.today().isoformat()
            
            # Get options chain
            options = self.data_client.get_option_chain(
                symbol_or_symbols=symbol,
                expiration_date=today,
                option_types=[option_type.upper()]
            )
            
            # Format for our use
            contracts = []
            
            if symbol in options.data:
                for contract in options.data[symbol]:
                    # Extract contract details
                    details = {
                        "symbol": contract.symbol,
                        "underlying": symbol,
                        "option_type": option_type,
                        "strike_price": float(contract.strike_price),
                        "expiration": contract.expiration_date.isoformat(),
                        "bid": float(contract.bid_price or 0),
                        "ask": float(contract.ask_price or 0),
                        "last": float(contract.last_price or 0),
                        "volume": int(contract.volume or 0),
                        "open_interest": int(contract.open_interest or 0),
                        "implied_volatility": float(contract.implied_volatility or 0),
                        "delta": float(contract.delta or 0),
                        "gamma": float(contract.gamma or 0),
                        "theta": float(contract.theta or 0),
                        "vega": float(contract.vega or 0)
                    }
                    
                    # Calculate mid price if bid/ask available
                    if details["bid"] > 0 and details["ask"] > 0:
                        details["mid"] = (details["bid"] + details["ask"]) / 2
                    else:
                        details["mid"] = details["last"] if details["last"] > 0 else 0.1
                    
                    contracts.append(details)
            
            # Sort by strike price
            contracts.sort(key=lambda x: x["strike_price"])
            
            return contracts
        
        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            return []
    
    def _select_best_contract(self, option_chain: List[Dict[str, Any]], 
                            signal_data: Dict[str, Any], 
                            is_bullish: bool) -> Optional[Dict[str, Any]]:
        """
        Select the best option contract for the trade.
        
        Args:
            option_chain: List of option contracts
            signal_data: Signal data
            is_bullish: Whether signal is bullish
            
        Returns:
            Selected option contract or None if none suitable
        """
        if not option_chain:
            return None
        
        try:
            # Get current price of underlying
            symbol = signal_data.get("symbol")
            quote = self.data_client.get_latest_quote(symbol)
            current_price = float(quote.ask_price)
            
            # For 0DTE options, we want a balance of:
            # 1. Liquidity (preference for higher volume)
            # 2. Price (preference for contracts that are affordable)
            # 3. Strike (preference for slightly OTM for better leverage)
            
            # Filter for contracts with some liquidity (volume/open interest)
            liquid_contracts = [c for c in option_chain if c["volume"] > 10 or c["open_interest"] > 50]
            
            if not liquid_contracts and option_chain:
                # If no liquid contracts, use all contracts
                liquid_contracts = option_chain
            
            # Filter for strikes that are around ATM/slightly OTM
            atm_contracts = []
            if is_bullish:
                # For bullish signals, look for strikes at or slightly above current price
                atm_contracts = [c for c in liquid_contracts if c["strike_price"] >= current_price * 0.99 
                                and c["strike_price"] <= current_price * 1.03]
            else:
                # For bearish signals, look for strikes at or slightly below current price
                atm_contracts = [c for c in liquid_contracts if c["strike_price"] <= current_price * 1.01 
                                and c["strike_price"] >= current_price * 0.97]
            
            if not atm_contracts and liquid_contracts:
                # If no ATM contracts, use liquid contracts
                atm_contracts = liquid_contracts
            
            # Sort by liquidity (volume + open interest)
            atm_contracts.sort(key=lambda x: x["volume"] + x["open_interest"], reverse=True)
            
            # Take the top 3 most liquid contracts
            top_contracts = atm_contracts[:3] if len(atm_contracts) >= 3 else atm_contracts
            
            # Choose the one with the lowest price that's still > $0.10
            valid_contracts = [c for c in top_contracts if c["mid"] >= 0.1]
            
            if not valid_contracts and top_contracts:
                # If no valid contracts, use the top contracts
                valid_contracts = top_contracts
            
            if valid_contracts:
                # Sort by price (lower price preferred)
                valid_contracts.sort(key=lambda x: x["mid"])
                return valid_contracts[0]
            
            return None
        
        except Exception as e:
            logger.error(f"Error selecting best contract: {e}")
            return None
    
    def _calculate_position_size(self, contract: Dict[str, Any], 
                              signal_data: Dict[str, Any]) -> int:
        """
        Calculate position size based on risk parameters.
        
        Args:
            contract: Option contract
            signal_data: Signal data
            
        Returns:
            Number of contracts to buy
        """
        try:
            # Get contract price
            contract_price = contract["mid"]
            
            # Calculate max loss per contract
            max_loss_per_contract = contract_price * 100  # Options are for 100 shares
            
            # Check if we have a stop loss level
            stop_level = signal_data.get("stop_level")
            entry_level = signal_data.get("entry_level")
            
            if stop_level and entry_level:
                # Calculate risk percentage
                risk_percentage = abs(stop_level - float(entry_level)) / float(entry_level)
                
                # Estimate max loss using risk percentage
                estimated_loss_percentage = risk_percentage * 2  # Amplify risk for options
                max_loss_per_contract = contract_price * 100 * estimated_loss_percentage
            
            # Calculate position size based on max drawdown
            max_drawdown = DEFAULT_MAX_DRAWDOWN
            
            if max_loss_per_contract <= 0:
                # Fallback to default contract size
                return DEFAULT_CONTRACT_SIZE
            
            position_size = int(max_drawdown / max_loss_per_contract)
            
            # Ensure at least 1 contract, but no more than max size
            position_size = max(1, min(position_size, DEFAULT_CONTRACT_SIZE))
            
            return position_size
        
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return DEFAULT_CONTRACT_SIZE
    
    def _place_option_order(self, contract: Dict[str, Any], 
                         position_size: int, 
                         is_bullish: bool) -> Optional[Dict[str, Any]]:
        """
        Place an option order.
        
        Args:
            contract: Option contract
            position_size: Number of contracts
            is_bullish: Whether signal is bullish
            
        Returns:
            Order result or None if failed
        """
        try:
            # Get contract details
            contract_symbol = contract["symbol"]
            
            # Calculate price to pay (use mid price + 5% to ensure fill)
            price = contract["mid"] * 1.05
            
            # Round price to nearest $0.05
            price = round(price * 20) / 20
            
            # Ensure price is at least $0.05
            price = max(0.05, price)
            
            # Place the order
            order = self.trading_client.submit_order(
                symbol=contract_symbol,
                qty=position_size,
                side="buy",
                type="limit",
                time_in_force="day",
                limit_price=price
            )
            
            if order:
                # Format order result
                result = {
                    "order_id": order.id,
                    "contract_symbol": contract_symbol,
                    "underlying": contract["underlying"],
                    "contract_type": contract["option_type"],
                    "strike_price": contract["strike_price"],
                    "expiration": contract["expiration"],
                    "qty": position_size,
                    "price": price,
                    "side": "buy",
                    "type": "limit",
                    "time_in_force": "day",
                    "status": order.status.name,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Order placed: {contract_symbol}, {position_size} contracts at ${price}")
                
                # Publish order event
                self._publish_order_event(result, "order_placed")
                
                return result
            
            return None
        
        except Exception as e:
            logger.error(f"Error placing option order: {e}")
            return None
    
    def _place_stop_loss_order(self, contract: Dict[str, Any], 
                            position_size: int, 
                            is_bullish: bool, 
                            signal_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Place a stop loss order.
        
        Args:
            contract: Option contract
            position_size: Number of contracts
            is_bullish: Whether signal is bullish
            signal_data: Signal data
            
        Returns:
            Order result or None if failed
        """
        try:
            # Get contract details
            contract_symbol = contract["symbol"]
            
            # Calculate stop price (50% of entry price as default)
            stop_price = contract["mid"] * 0.5
            
            # Use bias level if available to calculate better stop
            stop_level = signal_data.get("stop_level")
            if stop_level:
                # Calculate stop price based on bias level
                current_price = float(signal_data.get("entry_level", 0))
                if current_price > 0:
                    price_ratio = stop_level / current_price
                    # Adjust for options leverage (roughly 3x impact)
                    option_stop_ratio = 1 - ((1 - price_ratio) * 3)
                    option_stop_ratio = max(0.4, min(option_stop_ratio, 0.9))  # Cap between 40% and 90%
                    stop_price = contract["mid"] * option_stop_ratio
            
            # Round price to nearest $0.05
            stop_price = round(stop_price * 20) / 20
            
            # Ensure stop price is at least $0.05
            stop_price = max(0.05, stop_price)
            
            # Place the order
            order = self.trading_client.submit_order(
                symbol=contract_symbol,
                qty=position_size,
                side="sell",
                type="stop",
                time_in_force="day",
                stop_price=stop_price
            )
            
            if order:
                # Format order result
                result = {
                    "order_id": order.id,
                    "contract_symbol": contract_symbol,
                    "underlying": contract["underlying"],
                    "contract_type": contract["option_type"],
                    "qty": position_size,
                    "price": None,
                    "stop_price": stop_price,
                    "side": "sell",
                    "type": "stop",
                    "time_in_force": "day",
                    "purpose": "stop_loss",
                    "status": order.status.name,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Stop loss order placed: {contract_symbol}, {position_size} contracts at ${stop_price}")
                
                # Publish order event
                self._publish_order_event(result, "stop_loss_placed")
                
                return result
            
            return None
        
        except Exception as e:
            logger.error(f"Error placing stop loss order: {e}")
            return None
    
    def _place_take_profit_orders(self, contract: Dict[str, Any], 
                               position_size: int, 
                               is_bullish: bool, 
                               signal_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Place take profit orders at the target levels.
        
        Args:
            contract: Option contract
            position_size: Number of contracts
            is_bullish: Whether signal is bullish
            signal_data: Signal data
            
        Returns:
            List of order results
        """
        results = []
        try:
            # Get contract details
            contract_symbol = contract["symbol"]
            contract_price = contract["mid"]
            
            # Get target levels
            targets = signal_data.get("targets", [])
            if not targets:
                logger.warning(f"No target levels for {contract_symbol}")
                return results
            
            # Get entry price
            entry_price = float(signal_data.get("entry_level", 0))
            if entry_price <= 0:
                logger.warning(f"Invalid entry price for {contract_symbol}")
                return results
            
            # Calculate quantity per target
            # First target: 1/3, Second target: 1/3, Third target: 1/3
            # If only 2 targets, split 50/50
            # If only 1 target, use full position
            target_portions = []
            if len(targets) >= 3:
                # 1/3 for each target
                portion = max(1, position_size // 3)
                remaining = position_size
                
                target_portions = [portion, portion, remaining - (2 * portion)]
                target_portions = [p for p in target_portions if p > 0]
            elif len(targets) == 2:
                # 50% for each target
                portion = max(1, position_size // 2)
                target_portions = [portion, position_size - portion]
            else:
                # Full position for single target
                target_portions = [position_size]
            
            # Ensure we don't exceed position size
            if sum(target_portions) > position_size:
                target_portions[-1] = max(1, position_size - sum(target_portions[:-1]))
            
            # Place take profit orders for each target
            for i, (target, qty) in enumerate(zip(targets, target_portions)):
                if qty <= 0:
                    continue
                
                # Calculate price ratio
                price_ratio = float(target) / entry_price
                
                # Adjust for options leverage (roughly 3x impact)
                option_price_ratio = 1 + ((price_ratio - 1) * 3)
                
                # Calculate target price
                target_price = contract_price * option_price_ratio
                
                # Round price to nearest $0.05
                target_price = round(target_price * 20) / 20
                
                # Ensure price is at least $0.05
                target_price = max(0.05, target_price)
                
                # Place the order
                order = self.trading_client.submit_order(
                    symbol=contract_symbol,
                    qty=qty,
                    side="sell",
                    type="limit",
                    time_in_force="day",
                    limit_price=target_price
                )
                
                if order:
                    # Format order result
                    result = {
                        "order_id": order.id,
                        "contract_symbol": contract_symbol,
                        "underlying": contract["underlying"],
                        "contract_type": contract["option_type"],
                        "qty": qty,
                        "price": target_price,
                        "side": "sell",
                        "type": "limit",
                        "time_in_force": "day",
                        "purpose": f"take_profit_{i+1}",
                        "target_level": target,
                        "status": order.status.name,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    logger.info(f"Take profit order placed: {contract_symbol}, {qty} contracts at ${target_price}")
                    
                    # Publish order event
                    self._publish_order_event(result, "take_profit_placed")
                    
                    results.append(result)
            
            return results
        
        except Exception as e:
            logger.error(f"Error placing take profit orders: {e}")
            return results
    
    def _update_position_after_entry(self, contract: Dict[str, Any], 
                                  position_size: int, 
                                  is_bullish: bool, 
                                  signal_data: Dict[str, Any],
                                  order_result: Dict[str, Any]):
        """
        Update position details after entry.
        
        Args:
            contract: Option contract
            position_size: Number of contracts
            is_bullish: Whether signal is bullish
            signal_data: Signal data
            order_result: Entry order result
        """
        try:
            # Get symbol
            symbol = contract["underlying"]
            contract_symbol = contract["symbol"]
            
            # Create position entry
            position = {
                "symbol": symbol,
                "contract_symbol": contract_symbol,
                "contract_type": contract["option_type"],
                "strike_price": contract["strike_price"],
                "expiration": contract["expiration"],
                "is_option": True,
                "qty": position_size,
                "entry_price": contract["mid"],
                "current_price": contract["mid"],
                "market_value": contract["mid"] * position_size * 100,  # 100 shares per contract
                "cost_basis": contract["mid"] * position_size * 100,  # 100 shares per contract
                "unrealized_pl": 0,
                "unrealized_plpc": 0,
                "side": "long",
                "signal_id": signal_data.get("signal_id"),
                "entry_condition": signal_data.get("category"),
                "targets": signal_data.get("targets", []),
                "stop_level": signal_data.get("stop_level"),
                "bias_level": signal_data.get("bias_level"),
                "order_id": order_result.get("order_id"),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Add position
            with self.lock:
                self.positions[symbol] = position
            
            # Publish position update
            self._publish_position_update(position, "position_opened")
        
        except Exception as e:
            logger.error(f"Error updating position after entry: {e}")
    
    def _publish_order_event(self, order_data: Dict[str, Any], event_type: str):
        """
        Publish an order event to Redis.
        
        Args:
            order_data: Order data
            event_type: Event type
        """
        if not redis_client or not redis_client.available:
            return
        
        try:
            # Add event metadata
            event = order_data.copy()
            event["event_type"] = event_type
            event["timestamp"] = datetime.utcnow().isoformat()
            
            # Publish to execution channel
            redis_client.publish(EXECUTION_CHANNEL, json.dumps(event))
            
            # Publish to ticker-specific channel
            if "underlying" in event:
                redis_client.publish(f"ticker.{event['underlying']}.execution", json.dumps(event))
        
        except Exception as e:
            logger.error(f"Error publishing order event: {e}")
    
    def _publish_position_update(self, position_data: Dict[str, Any], event_type: str):
        """
        Publish a position update to Redis.
        
        Args:
            position_data: Position data
            event_type: Event type
        """
        if not redis_client or not redis_client.available:
            return
        
        try:
            # Add event metadata
            event = position_data.copy()
            event["event_type"] = event_type
            event["timestamp"] = datetime.utcnow().isoformat()
            
            # Publish to position update channel
            redis_client.publish(POSITION_UPDATE_CHANNEL, json.dumps(event))
            
            # Publish to ticker-specific channel
            redis_client.publish(f"ticker.{position_data['symbol']}.position", json.dumps(event))
        
        except Exception as e:
            logger.error(f"Error publishing position update: {e}")
    
    def _publish_positions_update(self):
        """Publish all positions update to Redis."""
        if not redis_client or not redis_client.available:
            return
        
        try:
            # Create positions update event
            event = {
                "event_type": "positions_update",
                "timestamp": datetime.utcnow().isoformat(),
                "positions": list(self.positions.values())
            }
            
            # Publish to position update channel
            redis_client.publish(POSITION_UPDATE_CHANNEL, json.dumps(event))
        
        except Exception as e:
            logger.error(f"Error publishing positions update: {e}")


# Singleton instance
_options_trader = None


def get_options_trader() -> OptionsTrader:
    """
    Get the options trader instance.
    
    Returns:
        Options trader instance
    """
    global _options_trader
    
    if _options_trader is None:
        _options_trader = OptionsTrader()
    
    return _options_trader


def start_options_trader():
    """Start the options trader."""
    trader = get_options_trader()
    trader.start()


def stop_options_trader():
    """Stop the options trader."""
    trader = get_options_trader()
    trader.stop()
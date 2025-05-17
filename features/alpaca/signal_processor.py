"""
Signal Processor Module

This module processes trading signals and executes appropriate actions
via the Alpaca API.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any

from features.alpaca.client import (
    initialize_clients, get_latest_quote, submit_market_order, 
    submit_limit_order, get_positions, get_account_info
)
from models import (
    Signal, TickerSetup, SignalCategoryEnum, ComparisonTypeEnum, BiasDirectionEnum
)
from sqlalchemy import desc
from app import db

# Configure logger
logger = logging.getLogger(__name__)

# Signal execution configuration
DEFAULT_EQUITY_PER_TRADE = 1000.0  # Default dollar amount for each trade
DEFAULT_MAX_SHARES = 100  # Default maximum shares per trade
MAX_RISK_PERCENT = 2.0  # Maximum percentage of portfolio to risk per trade
STOP_LOSS_BUFFER_PERCENT = 1.0  # Default buffer percentage for stop loss

class SignalProcessor:
    """Process trading signals and execute appropriate actions."""
    
    def __init__(self):
        """Initialize the signal processor."""
        self.initialized = initialize_clients()
        self.account_info = get_account_info() if self.initialized else {}
        
    def process_new_signal(self, signal_id: int, test_mode: bool = True) -> Dict:
        """
        Process a new trading signal.
        
        Args:
            signal_id: ID of the signal to process
            test_mode: Whether to run in test mode (don't execute trades) (default: True)
            
        Returns:
            Dictionary with processing results
        """
        if not self.initialized:
            return {'status': 'error', 'message': 'Alpaca client not initialized'}
            
        # Refresh account info
        self.account_info = get_account_info()
        if not self.account_info:
            return {'status': 'error', 'message': 'Could not get account information'}
        
        try:
            # Get the signal and associated ticker setup
            signal = Signal.query.get(signal_id)
            if not signal:
                return {'status': 'error', 'message': f'Signal not found: {signal_id}'}
            
            ticker_setup = signal.ticker_setup
            symbol = ticker_setup.symbol
            
            # Get current market data
            quote = get_latest_quote(symbol)
            if not quote:
                return {'status': 'error', 'message': f'Could not get quote for {symbol}'}
            
            # Determine trade direction based on signal category and comparison
            trade_side, entry_price = self._determine_trade_direction(signal, quote, ticker_setup)
            if not trade_side:
                return {'status': 'warning', 'message': 'Signal does not indicate a valid trade direction'}
            
            # Calculate position size based on account equity and risk parameters
            qty, stop_price = self._calculate_position_size(
                symbol, trade_side, entry_price, signal
            )
            
            if qty <= 0:
                return {'status': 'warning', 'message': 'Calculated quantity is zero or negative'}
            
            # Execute or log the trade based on test mode
            if test_mode:
                logger.info(f"TEST MODE: Would execute {trade_side} {qty} shares of {symbol} at ~${entry_price:.2f}")
                order_result = {
                    'status': 'success',
                    'test_mode': True,
                    'message': f'Would execute {trade_side} {qty} shares of {symbol}',
                    'symbol': symbol,
                    'side': trade_side,
                    'qty': qty,
                    'entry_price': entry_price,
                    'stop_price': stop_price
                }
            else:
                # Execute the actual trade
                order_result = self._execute_trade(symbol, qty, trade_side, entry_price, stop_price)
            
            # Record the execution in our database
            self._record_signal_execution(signal_id, order_result)
            
            return order_result
        
        except Exception as e:
            logger.error(f"Error processing signal {signal_id}: {e}")
            return {'status': 'error', 'message': f'Error processing signal: {str(e)}'}
    
    def _parse_trigger(self, trigger_raw) -> float:
        """
        Normalize trigger formats to a single float value.
        
        Args:
            trigger_raw: Raw trigger value in various formats
            
        Returns:
            float: Normalized trigger value or 0 if invalid
        """
        try:
            if not trigger_raw:
                return 0
                
            if isinstance(trigger_raw, (int, float)):
                return float(trigger_raw)
                
            if isinstance(trigger_raw, str):
                return float(trigger_raw)
                
            if isinstance(trigger_raw, dict):
                if 'type' in trigger_raw:
                    if trigger_raw['type'] == 'single':
                        return float(trigger_raw.get('value', 0))
                    elif trigger_raw['type'] == 'range':
                        low = float(trigger_raw.get('low', 0))
                        high = float(trigger_raw.get('high', 0))
                        return (low + high) / 2
                return float(next(iter(trigger_raw.values())))
                
            if hasattr(trigger_raw, '__iter__') and not isinstance(trigger_raw, str):
                return float(next(iter(trigger_raw)))
                
            return 0
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing trigger value: {e}")
            return 0
            
    def _determine_trade_direction(self, signal: Signal, quote: Dict, ticker_setup: TickerSetup) -> Tuple[Optional[str], float]:
        """
        Determine the trade direction (buy/sell) based on the signal.
        
        Args:
            signal: The signal to process
            quote: Current market quote
            ticker_setup: The ticker setup associated with the signal
            
        Returns:
            Tuple of (trade_side, entry_price) or (None, 0) if no valid direction
        """
        # Extract quote data
        bid_price = quote.get('bid_price', 0)
        ask_price = quote.get('ask_price', 0)
        
        # Get mid-price if both bid and ask are available
        mid_price = (bid_price + ask_price) / 2 if bid_price and ask_price else (bid_price or ask_price)
        if not mid_price:
            logger.warning(f"Could not determine price for {quote.get('symbol')}")
            return None, 0
        
        # Get trigger value from signal
        try:
            # Extract trigger based on how it's stored in the database
            if hasattr(signal, 'trigger') and signal.trigger:
                # Handle different storage formats
                if isinstance(signal.trigger, dict):
                    # Dictionary format - common in newer schemas
                    if 'type' in signal.trigger and signal.trigger['type'] == 'single':
                        trigger_value = float(signal.trigger.get('value', 0))
                    elif 'type' in signal.trigger and signal.trigger['type'] == 'range':
                        # For range type, use midpoint
                        low = float(signal.trigger.get('low', 0))
                        high = float(signal.trigger.get('high', 0))
                        trigger_value = (low + high) / 2
                    else:
                        # Generic dict handling
                        trigger_value = float(next(iter(signal.trigger.values())))
                elif isinstance(signal.trigger, (int, float)):
                    # Direct numeric value
                    trigger_value = float(signal.trigger)
                elif isinstance(signal.trigger, str):
                    # String value that needs conversion
                    trigger_value = float(signal.trigger)
                else:
                    # Array or other format
                    if hasattr(signal.trigger, '__iter__') and not isinstance(signal.trigger, str):
                        # It's some kind of iterable, use first value
                        trigger_value = float(next(iter(signal.trigger)))
                    else:
                        # Unknown format
                        logger.warning(f"Unknown trigger format: {type(signal.trigger)}")
                        trigger_value = 0
            else:
                logger.warning("No trigger attribute found on signal")
                trigger_value = 0
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing trigger value: {e}")
            trigger_value = 0
        
        if not trigger_value:
            logger.warning(f"Could not determine valid trigger value")
            return None, 0
        
        # Determine trade direction based on signal category and comparison
        trade_side = None
        entry_price = 0
        
        # Convert enum values to strings if needed
        category = signal.category
        if hasattr(category, 'value'):  # If it's an enum
            category = category.value
            
        comparison = signal.comparison
        if hasattr(comparison, 'value'):  # If it's an enum
            comparison = comparison.value
        
        # Process based on category and comparison
        if category == SignalCategoryEnum.BREAKOUT or category == 'breakout':
            if comparison == ComparisonTypeEnum.ABOVE or comparison == 'above':
                # Breakout above - BUY if price is above trigger
                if mid_price > trigger_value:
                    trade_side = 'buy'
                    entry_price = ask_price or mid_price  # Use ask price for buys if available
        
        elif category == SignalCategoryEnum.BREAKDOWN or category == 'breakdown':
            if comparison == ComparisonTypeEnum.BELOW or comparison == 'below':
                # Breakdown below - SELL if price is below trigger
                if mid_price < trigger_value:
                    trade_side = 'sell'
                    entry_price = bid_price or mid_price  # Use bid price for sells if available
        
        elif category == SignalCategoryEnum.REJECTION or category == 'rejection':
            if comparison == ComparisonTypeEnum.NEAR or comparison == 'near':
                # Rejection near - SELL if price is near or testing trigger
                if 0.98 * trigger_value <= mid_price <= 1.02 * trigger_value:
                    trade_side = 'sell'
                    entry_price = bid_price or mid_price
        
        elif category == SignalCategoryEnum.BOUNCE or category == 'bounce':
            if comparison == ComparisonTypeEnum.ABOVE or comparison == 'above':
                # Bounce above - BUY if price is bouncing above support
                if 0.98 * trigger_value <= mid_price <= 1.03 * trigger_value:
                    trade_side = 'buy'
                    entry_price = ask_price or mid_price
        
        # Consider bias if available
        if hasattr(ticker_setup, 'bias') and ticker_setup.bias:
            bias = ticker_setup.bias
            bias_direction = bias.direction
            if hasattr(bias_direction, 'value'):  # If it's an enum
                bias_direction = bias_direction.value
                
            # If bias conflicts with signal, don't trade
            if ((bias_direction == BiasDirectionEnum.BULLISH or bias_direction == 'bullish') and 
                trade_side == 'sell' and mid_price > bias.price):
                trade_side = None
            elif ((bias_direction == BiasDirectionEnum.BEARISH or bias_direction == 'bearish') and 
                  trade_side == 'buy' and mid_price < bias.price):
                trade_side = None
        
        return trade_side, entry_price
    
    def _calculate_position_size(
        self, symbol: str, trade_side: str, entry_price: float, signal: Signal
    ) -> Tuple[int, float]:
        """
        Calculate position size based on account equity and risk parameters.
        
        Args:
            symbol: Ticker symbol
            trade_side: Trade direction ('buy' or 'sell')
            entry_price: Entry price
            signal: Signal object
            
        Returns:
            Tuple of (quantity, stop_price)
        """
        # Get account equity
        equity = float(self.account_info.get('equity', 0))
        if not equity:
            # Fall back to default trade size
            logger.warning("Could not determine account equity, using default size")
            equity = DEFAULT_EQUITY_PER_TRADE * 10  # Assume 10x the default trade size
        
        # Calculate trade size (default to 1% of portfolio)
        trade_size = min(DEFAULT_EQUITY_PER_TRADE, equity * 0.01)
        
        # Calculate stop loss price
        stop_price = 0
        
        if trade_side == 'buy':
            # For buys, stop is below the entry
            stop_buffer = entry_price * (STOP_LOSS_BUFFER_PERCENT / 100)
            stop_price = entry_price - stop_buffer
        else:  # sell
            # For sells, stop is above the entry
            stop_buffer = entry_price * (STOP_LOSS_BUFFER_PERCENT / 100)
            stop_price = entry_price + stop_buffer
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_price)
        if risk_per_share < 0.01:
            # Minimum risk per share
            risk_per_share = 0.01
        
        # Calculate max risk amount (as a percentage of equity)
        max_risk_amount = equity * (MAX_RISK_PERCENT / 100)
        
        # Calculate quantity based on risk
        calc_qty = max_risk_amount / risk_per_share
        
        # Round down to whole shares
        qty = int(min(calc_qty, DEFAULT_MAX_SHARES))
        
        # Ensure minimum quantity
        if qty < 1:
            qty = 1
        
        return qty, stop_price
    
    def _execute_trade(
        self, symbol: str, qty: int, side: str, entry_price: float, stop_price: float
    ) -> Dict:
        """
        Execute a trade based on the calculated parameters using typed OrderRequest classes.
        
        Args:
            symbol: Ticker symbol
            qty: Quantity of shares
            side: Trade direction ('buy' or 'sell')
            entry_price: Entry price
            stop_price: Stop loss price
            
        Returns:
            Order result dictionary
        """
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
            
            # Create market order request
            mkt_req = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                client_order_id=f"signal_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            
            # Submit market order
            entry_order = self.trading_client.submit_order(order_data=mkt_req)
            if not entry_order:
                return {
                    'status': 'error',
                    'message': f'Failed to submit {side} order for {symbol}'
                }
            
            result = {
                'status': 'success',
                'message': f'Executed {side} {qty} shares of {symbol}',
                'symbol': symbol,
                'side': side,
                'qty': qty,
                'entry_price': entry_price,
                'entry_order_id': entry_order.id
            }
            
            # Create stop loss order if specified
            if stop_price > 0:
                stop_req = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=OrderSide.SELL if side == "buy" else OrderSide.BUY,
                    time_in_force=TimeInForce.GTC,
                    limit_price=stop_price,
                    client_order_id=f"stop_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                )
                
                stop_order = self.trading_client.submit_order(order_data=stop_req)
                if stop_order:
                    result.update({
                        'stop_price': stop_price,
                        'stop_order_id': stop_order.id
                    })
            
            return result
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {
                'status': 'error',
                'message': f'Error executing trade: {str(e)}'
            }
    
    def _record_signal_execution(self, signal_id: int, execution_result: Dict) -> None:
        """
        Record the signal execution in the database.
        
        Args:
            signal_id: Signal ID
            execution_result: Execution result dictionary
        """
        try:
            signal = Signal.query.get(signal_id)
            if not signal:
                logger.warning(f"Signal not found for recording execution: {signal_id}")
                return
            
            # Update signal with execution details
            signal.active = False
            signal.triggered_at = datetime.utcnow()
            
            # Create order record if needed
            # This would require an additional Order model that we might implement
            
            # Commit changes
            db.session.commit()
            
            logger.info(f"Recorded execution for signal {signal_id}")
        except Exception as e:
            logger.error(f"Error recording signal execution: {e}")
            db.session.rollback()

# Singleton instance
signal_processor = None

def get_signal_processor() -> SignalProcessor:
    """Get or create the signal processor instance."""
    global signal_processor
    if signal_processor is None:
        signal_processor = SignalProcessor()
    return signal_processor

def process_signal(signal_id: int, test_mode: bool = True) -> Dict:
    """
    Process a trading signal.
    
    Args:
        signal_id: ID of the signal to process
        test_mode: Whether to run in test mode (don't execute trades) (default: True)
        
    Returns:
        Dictionary with processing results
    """
    processor = get_signal_processor()
    return processor.process_new_signal(signal_id, test_mode)
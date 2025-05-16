"""
Signal Processor Module

This module processes trading signals and executes appropriate actions
via the Alpaca API.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from features.alpaca.client import (
    initialize_clients, get_latest_quote, submit_market_order, 
    submit_limit_order, get_positions, get_account_info
)
from features.setups.models import (
    SetupMessage, TickerSetup, Signal,
    SignalCategoryEnum, ComparisonTypeEnum, BiasDirectionEnum
)
from common.db import db

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
            trade_side, entry_price = self._determine_trade_direction(signal, quote)
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
    
    def _determine_trade_direction(self, signal: Signal, quote: Dict) -> Tuple[Optional[str], float]:
        """
        Determine the trade direction (buy/sell) based on the signal.
        
        Args:
            signal: The signal to process
            quote: Current market quote
            
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
        
        # Get trigger value (could be float or dict with range)
        trigger = signal.trigger
        trigger_value = 0
        
        # Parse trigger value based on format
        if isinstance(trigger, dict):
            if trigger.get('type') == 'single':
                trigger_value = float(trigger.get('value', 0))
            elif trigger.get('type') == 'range':
                # For a range, use midpoint of the range
                low = float(trigger.get('low', 0))
                high = float(trigger.get('high', 0))
                trigger_value = (low + high) / 2
        elif isinstance(trigger, (int, float, str)):
            trigger_value = float(trigger)
        
        if not trigger_value:
            logger.warning(f"Could not determine trigger value from {trigger}")
            return None, 0
        
        # Determine trade direction based on signal category and comparison
        trade_side = None
        entry_price = 0
        
        if signal.category == SignalCategoryEnum.BREAKOUT:
            if signal.comparison == ComparisonTypeEnum.ABOVE:
                # Breakout above - BUY if price is above trigger
                if mid_price > trigger_value:
                    trade_side = 'buy'
                    entry_price = ask_price or mid_price  # Use ask price for buys if available
        
        elif signal.category == SignalCategoryEnum.BREAKDOWN:
            if signal.comparison == ComparisonTypeEnum.BELOW:
                # Breakdown below - SELL if price is below trigger
                if mid_price < trigger_value:
                    trade_side = 'sell'
                    entry_price = bid_price or mid_price  # Use bid price for sells if available
        
        elif signal.category == SignalCategoryEnum.REJECTION:
            if signal.comparison == ComparisonTypeEnum.NEAR:
                # Rejection near - SELL if price is near or testing trigger
                if 0.98 * trigger_value <= mid_price <= 1.02 * trigger_value:
                    trade_side = 'sell'
                    entry_price = bid_price or mid_price
        
        elif signal.category == SignalCategoryEnum.BOUNCE:
            if signal.comparison == ComparisonTypeEnum.ABOVE:
                # Bounce above - BUY if price is bouncing above support
                if 0.98 * trigger_value <= mid_price <= 1.03 * trigger_value:
                    trade_side = 'buy'
                    entry_price = ask_price or mid_price
        
        # Consider bias if available
        bias = ticker_setup.bias if hasattr(signal.ticker_setup, 'bias') else None
        if bias and bias.direction and bias.price:
            # If bias conflicts with signal, don't trade
            if (bias.direction == BiasDirectionEnum.BULLISH and trade_side == 'sell' and 
                mid_price > bias.price):
                trade_side = None
            elif (bias.direction == BiasDirectionEnum.BEARISH and trade_side == 'buy' and 
                  mid_price < bias.price):
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
        Execute a trade based on the calculated parameters.
        
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
            # Submit market order
            order = submit_market_order(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force='day',
                client_order_id=f"signal_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            
            if not order:
                return {
                    'status': 'error',
                    'message': f'Failed to submit {side} order for {symbol}'
                }
            
            # Create a stop loss order for risk management
            if stop_price > 0:
                stop_side = 'sell' if side == 'buy' else 'buy'
                stop_order = submit_limit_order(
                    symbol=symbol,
                    qty=qty,
                    side=stop_side,
                    limit_price=stop_price,
                    time_in_force='gtc',
                    client_order_id=f"stop_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                )
                
                return {
                    'status': 'success',
                    'message': f'Executed {side} {qty} shares of {symbol}',
                    'symbol': symbol,
                    'side': side,
                    'qty': qty,
                    'entry_price': entry_price,
                    'entry_order_id': order.get('id'),
                    'stop_price': stop_price,
                    'stop_order_id': stop_order.get('id') if stop_order else None
                }
            else:
                return {
                    'status': 'success',
                    'message': f'Executed {side} {qty} shares of {symbol}',
                    'symbol': symbol,
                    'side': side,
                    'qty': qty,
                    'entry_price': entry_price,
                    'entry_order_id': order.get('id')
                }
                
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
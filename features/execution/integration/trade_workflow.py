"""
Trade Workflow Integration Module

This module connects the Discord message parser with the options trader and monitoring systems
to create an end-to-end workflow for trading based on Discord signals.
"""
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime

from features.discord.message_parser import parse_message, validate_setup
from features.execution.options_trader import (
    execute_signal_trade,
    manage_position,
    get_active_positions,
    get_closed_positions
)
from features.market.feed import subscribe_to_ticker, get_latest_price
from features.market.history import get_recent_candles
from features.options.selector import select_best_option_contract

from common.events import publish_event
from common.events.constants import EventChannels

# Configure logger
logger = logging.getLogger(__name__)

# Global state
_active_setups = {}  # Tracks setups that haven't been traded yet
_active_trades = {}  # Tracks trades that have been executed
_closed_trades = {}  # Tracks trades that have been completed
_enabled = False     # Whether auto-trading is enabled

def initialize_trade_workflow() -> bool:
    """
    Initialize the trade workflow integration.

    Returns:
        Success status
    """
    global _enabled

    try:
        logger.info("Initializing trade workflow integration...")
        _enabled = True
        return True
    except Exception as e:
        logger.error(f"Error initializing trade workflow: {e}")
        return False

def shutdown_trade_workflow() -> bool:
    """
    Shutdown the trade workflow integration.

    Returns:
        Success status
    """
    global _enabled

    try:
        logger.info("Shutting down trade workflow integration...")
        _enabled = False
        return True
    except Exception as e:
        logger.error(f"Error shutting down trade workflow: {e}")
        return False

def process_discord_message(message: str) -> Optional[Dict]:
    """
    Process a Discord message for trading signals.

    Args:
        message: Raw Discord message text

    Returns:
        Parsed setup data if a valid trading setup was found, None otherwise
    """
    try:
        # Parse the message
        setup_data = parse_message(message)

        # Validate if it's a tradable setup
        if not validate_setup(setup_data):
            logger.info("Message doesn't contain a valid trading setup")
            return None

        # Get primary ticker
        ticker = setup_data.get('primary_ticker')
        if not ticker:
            logger.warning("No primary ticker found in the message")
            return None

        # Log the setup
        logger.info(f"Found trading setup for {ticker}: {setup_data.get('signal_type')} - {setup_data.get('bias')}")

        # Store the setup
        setup_id = f"{ticker}_{int(time.time())}"
        setup_data['setup_id'] = setup_id
        setup_data['timestamp'] = datetime.now().isoformat()
        setup_data['status'] = 'pending'  # pending, active, completed, invalid

        _active_setups[setup_id] = setup_data

        # Subscribe to price updates for this ticker
        subscribe_to_ticker(ticker)

        return setup_data

    except Exception as e:
        logger.error(f"Error processing Discord message: {e}")
        return None

def evaluate_setups() -> List[Dict]:
    """
    Evaluate all active setups to check if any should be traded.

    Returns:
        List of setups that were processed for trading
    """
    if not _enabled:
        logger.info("Trade workflow is disabled, skipping setup evaluation")
        return []

    processed = []

    try:
        # Check each active setup
        for setup_id, setup in list(_active_setups.items()):
            if setup['status'] != 'pending':
                continue

            ticker = setup['primary_ticker']
            signal_type = setup.get('signal_type')
            bias = setup.get('bias')

            if not ticker or not (signal_type or bias):
                setup['status'] = 'invalid'
                logger.warning(f"Setup {setup_id} missing critical information")
                continue

            # Get current price
            current_price = get_latest_price(ticker)
            if not current_price:
                logger.warning(f"Could not get price for {ticker}, skipping setup {setup_id}")
                continue

            # Determine if we should enter a trade based on price levels
            should_trade = False
            trade_price = None

            # Entry criteria depends on signal type and price levels
            if signal_type == 'breakout' or (bias == 'bullish' and not signal_type):
                # For breakouts, we enter when price breaks above resistance
                resistance_levels = setup.get('resistance_levels', [])
                if resistance_levels:
                    # Sort resistance levels
                    resistance_levels.sort()
                    # Check if price is above any resistance level
                    for level in resistance_levels:
                        if current_price > level * 1.002:  # 0.2% confirmation buffer
                            should_trade = True
                            trade_price = level
                            break

            elif signal_type == 'breakdown' or (bias == 'bearish' and not signal_type):
                # For breakdowns, we enter when price breaks below support
                support_levels = setup.get('support_levels', [])
                if support_levels:
                    # Sort support levels
                    support_levels.sort(reverse=True)
                    # Check if price is below any support level
                    for level in support_levels:
                        if current_price < level * 0.998:  # 0.2% confirmation buffer
                            should_trade = True
                            trade_price = level
                            break

            elif signal_type == 'bounce' or signal_type == 'support':
                # For bounces, we enter when price bounces off support
                support_levels = setup.get('support_levels', [])
                if support_levels:
                    # Sort support levels
                    support_levels.sort()
                    # Check if price is above any support level
                    for level in support_levels:
                        if current_price > level and current_price < level * 1.01:  # 1% buffer
                            should_trade = True
                            trade_price = level
                            break

            elif signal_type == 'rejection' or signal_type == 'resistance':
                # For rejections, we enter when price is rejected at resistance
                resistance_levels = setup.get('resistance_levels', [])
                if resistance_levels:
                    # Sort resistance levels
                    resistance_levels.sort(reverse=True)
                    # Check if price is below any resistance level
                    for level in resistance_levels:
                        if current_price < level and current_price > level * 0.99:  # 1% buffer
                            should_trade = True
                            trade_price = level
                            break

            # If we have explicit entry levels, prioritize those
            entry_levels = setup.get('entry_levels', [])
            if entry_levels:
                # If we're bullish, look for price above entry
                if bias == 'bullish' or signal_type in ['breakout', 'bounce', 'support']:
                    for level in sorted(entry_levels):
                        if current_price > level:
                            should_trade = True
                            trade_price = level
                            break
                # If we're bearish, look for price below entry
                elif bias == 'bearish' or signal_type in ['breakdown', 'rejection', 'resistance']:
                    for level in sorted(entry_levels, reverse=True):
                        if current_price < level:
                            should_trade = True
                            trade_price = level
                            break

            # If we should trade and haven't done so already
            if should_trade and setup_id not in _active_trades:
                # Execute the trade
                result = execute_trade(setup, trade_price)

                if result:
                    setup['status'] = 'active'
                    setup['trade_data'] = result
                    _active_trades[setup_id] = setup
                    logger.info(f"Executed trade for setup {setup_id}")
                    processed.append(setup)
                else:
                    logger.warning(f"Failed to execute trade for setup {setup_id}")

        return processed

    except Exception as e:
        logger.error(f"Error evaluating setups: {e}")
        return []

def execute_trade(setup: Dict, price_target: Optional[float] = None) -> Optional[Dict]:
    """
    Execute a trade based on a setup.

    Args:
        setup: Setup data dictionary
        price_target: Target price for the trade (optional)

    Returns:
        Trade data if successful, None otherwise
    """
    try:
        ticker = setup['primary_ticker']
        signal_type = setup.get('signal_type')
        bias = setup.get('bias')

        # Set risk amount (default $500)
        risk_amount = 500.0

        # Determine the final signal type based on bias if not explicitly set
        if not signal_type and bias:
            if bias == 'bullish':
                signal_type = 'breakout'
            elif bias == 'bearish':
                signal_type = 'breakdown'
            else:
                signal_type = 'breakout'  # Default

        # Use the provided price target or the current price
        if not price_target:
            price_target = get_latest_price(ticker)
            if not price_target:
                logger.warning(f"Could not get price for {ticker}")
                return None

        # Execute the trade
        trade_result = execute_signal_trade(
            symbol=ticker,
            signal_type=signal_type,
            price_target=price_target,
            risk_amount=risk_amount
        )

        if not trade_result:
            logger.warning(f"Failed to execute trade for {ticker}")
            return None

        # Create trade record
        trade_data = {
            'setup_id': setup['setup_id'],
            'ticker': ticker,
            'signal_type': signal_type,
            'entry_price': trade_result.get('entry_price'),
            'quantity': trade_result.get('quantity'),
            'order_id': trade_result.get('order_id'),
            'timestamp': datetime.now().isoformat(),
            'status': 'open',
            'profit_loss': 0.0
        }

        return trade_data

    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        return None

def monitor_active_trades() -> List[Dict]:
    """
    Monitor all active trades and manage positions.

    Returns:
        List of trades that were updated
    """
    if not _enabled:
        logger.info("Trade workflow is disabled, skipping trade monitoring")
        return []

    updated = []

    try:
        # Get positions from options trader
        active_positions = get_active_positions()
        closed_positions = get_closed_positions()

        # Check each active trade
        for setup_id, setup in list(_active_trades.items()):
            if setup['status'] != 'active':
                continue

            ticker = setup['primary_ticker']

            # Get current price
            current_price = get_latest_price(ticker)
            if not current_price:
                logger.warning(f"Could not get price for {ticker}, skipping trade {setup_id}")
                continue

            # Check if the position is still active
            if setup_id in active_positions:
                # Update the trade with current position info
                position_info = active_positions[setup_id]
                setup['trade_data']['current_price'] = current_price
                setup['trade_data']['profit_loss'] = position_info.get('profit_pct', 0.0)

                # Manage the position
                updated_info = manage_position(ticker, current_price)
                if updated_info:
                    setup['trade_data']['status'] = updated_info.get('status', 'open')

                    # If the position is closed, move it to closed trades
                    if updated_info.get('status') != 'open':
                        setup['status'] = 'completed'
                        setup['trade_data']['exit_price'] = updated_info.get('exit_price')
                        setup['trade_data']['profit_loss'] = updated_info.get('profit_pct', 0.0)
                        _closed_trades[setup_id] = setup
                        del _active_trades[setup_id]
                        logger.info(f"Trade {setup_id} completed with P/L: {setup['trade_data']['profit_loss']:.2f}%")

                updated.append(setup)

            # Check if the position is in the closed positions
            elif setup_id in closed_positions:
                position_info = closed_positions[setup_id]
                setup['status'] = 'completed'
                setup['trade_data']['status'] = position_info.get('status', 'closed_unknown')
                setup['trade_data']['exit_price'] = position_info.get('exit_price')
                setup['trade_data']['profit_loss'] = position_info.get('profit_pct', 0.0)
                _closed_trades[setup_id] = setup
                del _active_trades[setup_id]
                logger.info(f"Trade {setup_id} completed with P/L: {setup['trade_data']['profit_loss']:.2f}%")
                updated.append(setup)

            # If the position is not found, assume it's been closed
            else:
                setup['status'] = 'completed'
                setup['trade_data']['status'] = 'closed_unknown'
                _closed_trades[setup_id] = setup
                del _active_trades[setup_id]
                logger.info(f"Trade {setup_id} not found in positions, assuming closed")
                updated.append(setup)

        return updated

    except Exception as e:
        logger.error(f"Error monitoring trades: {e}")
        return []

def get_active_setups() -> Dict:
    """
    Get all active trading setups.

    Returns:
        Dictionary of active setups by ID
    """
    return _active_setups

def get_active_trades() -> Dict:
    """
    Get all active trades.

    Returns:
        Dictionary of active trades by setup ID
    """
    return _active_trades

def get_trade_history() -> Dict:
    """
    Get all completed trades.

    Returns:
        Dictionary of completed trades by setup ID
    """
    return _closed_trades

def generate_performance_report() -> Dict:
    """
    Generate a performance report for all trades.

    Returns:
        Dictionary containing performance metrics
    """
    try:
        # Get all trades
        all_trades = list(_closed_trades.values())

        # Calculate statistics
        total_trades = len(all_trades)
        winning_trades = sum(1 for t in all_trades if t.get('trade_data', {}).get('profit_loss', 0) > 0)
        losing_trades = sum(1 for t in all_trades if t.get('trade_data', {}).get('profit_loss', 0) < 0)

        # Calculate win rate
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # Calculate profit/loss
        total_profit_loss = sum(t.get('trade_data', {}).get('profit_loss', 0) for t in all_trades)

        # Average P/L per trade
        avg_profit_loss = total_profit_loss / total_trades if total_trades > 0 else 0

        # Average P/L for winning and losing trades
        winning_pl = [t.get('trade_data', {}).get('profit_loss', 0) for t in all_trades if t.get('trade_data', {}).get('profit_loss', 0) > 0]
        losing_pl = [t.get('trade_data', {}).get('profit_loss', 0) for t in all_trades if t.get('trade_data', {}).get('profit_loss', 0) < 0]

        avg_win = sum(winning_pl) / len(winning_pl) if winning_pl else 0
        avg_loss = sum(losing_pl) / len(losing_pl) if losing_pl else 0

        # Track performance by ticker
        ticker_performance = {}
        for trade in all_trades:
            ticker = trade.get('primary_ticker')
            if ticker:
                if ticker not in ticker_performance:
                    ticker_performance[ticker] = {
                        'trades': 0,
                        'winning': 0,
                        'losing': 0,
                        'total_pl': 0
                    }

                ticker_performance[ticker]['trades'] += 1
                profit_loss = trade.get('trade_data', {}).get('profit_loss', 0)
                ticker_performance[ticker]['total_pl'] += profit_loss

                if profit_loss > 0:
                    ticker_performance[ticker]['winning'] += 1
                elif profit_loss < 0:
                    ticker_performance[ticker]['losing'] += 1

        # Best and worst tickers
        best_ticker = max(ticker_performance.items(), key=lambda x: x[1]['total_pl']) if ticker_performance else (None, None)
        worst_ticker = min(ticker_performance.items(), key=lambda x: x[1]['total_pl']) if ticker_performance else (None, None)

        # Create the report
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit_loss': total_profit_loss,
            'avg_profit_loss': avg_profit_loss,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'ticker_performance': ticker_performance,
            'best_ticker': best_ticker[0] if best_ticker[0] else None,
            'worst_ticker': worst_ticker[0] if worst_ticker[0] else None,
            'trades': all_trades
        }

        return report

    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'total_trades': 0
        }

def handle_trade_signal(signal_data):
    publish_event(EventChannels.TRADE_EXECUTED, signal_data)
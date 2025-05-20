"""
Complete Trading Workflow Demo

This script demonstrates the complete trading workflow:
1. Parse Discord messages
2. Extract ticker symbols, signal types, and price levels
3. Create trading setups
4. Monitor price action
5. Execute trades when conditions are met
6. Manage positions with stop-loss and take-profit
"""
import json
import logging
import sys
import time
from datetime import datetime
from pprint import pformat

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import necessary components
try:
    from features.discord.message_parser import parse_message
    from features.integration.trade_workflow import (
        initialize_trade_workflow,
        process_discord_message,
        evaluate_setups,
        monitor_active_trades,
        get_active_setups,
        get_active_trades
    )
    from features.market.feed import get_current_price, subscribe_to_ticker
    from features.market.historical_data import get_recent_bars
    from features.options.pricing import get_option_chain
    from features.execution.options_trader import place_option_order, get_position_details
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

def demonstrate_workflow():
    """
    Demonstrate the complete trading workflow from Discord message to trade execution.
    """
    logger.info("="*80)
    logger.info("TRADING WORKFLOW DEMONSTRATION")
    logger.info("="*80)
    
    # Step 1: Initialize the trade workflow components
    logger.info("\nStep 1: Initializing trade workflow components...")
    if not initialize_trade_workflow():
        logger.error("Failed to initialize workflow components")
        return False
    logger.info("✓ Trade workflow components initialized")
    
    # Step 2: Process a Discord message to extract trading setups
    logger.info("\nStep 2: Processing Discord message...")
    message = """
    A+ Trade Setups - Thursday May 20
    
    $SPY Rejection Near 586
    Bias: Bearish
    
    $AAPL Breaking Support
    Support at $182
    Target: $178
    Stop: $185
    
    $NVDA Bounce at $920
    Looks strong heading into earnings next week
    """
    logger.info(f"Message to process:\n{message}")
    
    # Parse the message
    parsed_result = parse_message(message)
    logger.info(f"Parsed message:\n{pformat(parsed_result)}")
    
    # Process the message to create setup
    setup = process_discord_message(message)
    if not setup:
        logger.error("Failed to process message into a trading setup")
        return False
    
    setup_id = setup.get('setup_id')
    logger.info(f"✓ Created setup with ID: {setup_id}")
    
    # Step 3: Get active setups
    logger.info("\nStep 3: Retrieving active trading setups...")
    active_setups = get_active_setups()
    logger.info(f"Active Setups: {len(active_setups)}")
    
    for setup_id, setup_data in active_setups.items():
        logger.info(f"  Setup ID: {setup_id}")
        logger.info(f"  Primary Ticker: {setup_data.get('primary_ticker')}")
        logger.info(f"  Signal Type: {setup_data.get('signal_type')}")
        logger.info(f"  Bias: {setup_data.get('bias')}")
        
        # Display ticker-specific data
        ticker = setup_data.get('primary_ticker')
        if ticker and 'ticker_specific_data' in setup_data and ticker in setup_data['ticker_specific_data']:
            ticker_data = setup_data['ticker_specific_data'][ticker]
            logger.info(f"  Price Levels for {ticker}:")
            
            # Support levels
            if ticker_data.get('support_levels'):
                logger.info(f"    Support: {ticker_data['support_levels']}")
            
            # Resistance levels
            if ticker_data.get('resistance_levels'):
                logger.info(f"    Resistance: {ticker_data['resistance_levels']}")
            
            # Target levels
            if ticker_data.get('target_levels'):
                logger.info(f"    Targets: {ticker_data['target_levels']}")
            
            # Stop levels
            if ticker_data.get('stop_levels'):
                logger.info(f"    Stops: {ticker_data['stop_levels']}")
    
    # Step 4: Get market data for the tickers
    logger.info("\nStep 4: Getting market data for tickers...")
    
    # Get current prices for tickers
    for ticker in parsed_result['tickers']:
        if ticker == 'A':  # Skip ticker 'A' as it's likely not a real ticker in this context
            continue
            
        # Subscribe to ticker updates
        subscribe_to_ticker(ticker)
        
        # Try to get current price
        try:
            current_price = get_current_price(ticker)
            if current_price:
                logger.info(f"  Current price for {ticker}: ${current_price:.2f}")
            else:
                logger.info(f"  Current price for {ticker} not available")
        except Exception as e:
            logger.error(f"  Error getting current price for {ticker}: {e}")
    
    # Step 5: Evaluate setups to check for trade entry conditions
    logger.info("\nStep 5: Evaluating trading setups...")
    
    # Evaluate setups
    evaluated_setups = evaluate_setups()
    logger.info(f"Evaluated Setups: {len(evaluated_setups)}")
    
    for setup_id in evaluated_setups:
        logger.info(f"  Updated setup: {setup_id}")
    
    # Step 6: Get active trades
    logger.info("\nStep 6: Getting active trades...")
    
    # Monitor trades
    active_trades = get_active_trades()
    logger.info(f"Active Trades: {len(active_trades)}")
    
    for trade_id, trade_data in active_trades.items():
        logger.info(f"  Trade ID: {trade_id}")
        logger.info(f"  Ticker: {trade_data.get('primary_ticker')}")
        logger.info(f"  Signal: {trade_data.get('signal_type')}")
        logger.info(f"  Status: {trade_data.get('status')}")
        
        # Get trade details
        trade_details = trade_data.get('trade_data', {})
        if trade_details:
            logger.info(f"  Entry Price: {trade_details.get('entry_price')}")
            logger.info(f"  Current Price: {trade_details.get('current_price')}")
            logger.info(f"  Profit/Loss: {trade_details.get('profit_loss')}%")
    
    # Step 7: Option Contract Selection (Mock)
    logger.info("\nStep 7: Option Contract Selection...")
    
    # Select ticker for option chain example
    example_ticker = 'AAPL'
    
    try:
        # Get option chain for the ticker
        option_chain = get_option_chain(example_ticker)
        
        if option_chain:
            logger.info(f"  Retrieved option chain for {example_ticker}")
            logger.info(f"  Available expirations: {option_chain.get('expirations', [])}")
            logger.info(f"  Available strikes: {len(option_chain.get('strikes', []))} strikes")
            
            # Select a contract (hypothetical)
            logger.info("  Selected contract: AAPL 180 Put 5/21 (Example)")
        else:
            logger.info(f"  Option chain for {example_ticker} not available")
    except Exception as e:
        logger.error(f"  Error getting option chain: {e}")
    
    # Step 8: Position Management (Mock)
    logger.info("\nStep 8: Position Management...")
    
    # Monitor active trades
    updated_trades = monitor_active_trades()
    logger.info(f"Updated {len(updated_trades)} trades")
    
    # Summary
    logger.info("\nWorkflow demonstration complete!")
    logger.info("="*80)
    
if __name__ == "__main__":
    demonstrate_workflow()
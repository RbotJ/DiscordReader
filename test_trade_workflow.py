"""
Test script for demonstrating the trade workflow integration.
This script simulates receiving a Discord message and processes it through the entire trade workflow.
"""
import logging
import sys
import json
import time
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    # Import workflow components
    from features.integration.trade_workflow import (
        initialize_trade_workflow,
        process_discord_message,
        evaluate_setups,
        monitor_active_trades,
        get_active_setups,
        get_active_trades
    )
    from features.discord.message_parser import parse_message
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

def test_process_message(message_text):
    """
    Test processing a Discord message through the trade workflow.
    
    Args:
        message_text: The Discord message text to process
    """
    logger.info("Initializing trade workflow...")
    if not initialize_trade_workflow():
        logger.error("Failed to initialize trade workflow")
        return

    logger.info(f"Processing message: {message_text}")
    
    # Step 1: Parse the message
    logger.info("Step 1: Parsing message...")
    parsed_result = parse_message(message_text)
    if parsed_result:
        logger.info(f"Parsed result: {json.dumps(parsed_result, indent=2)}")
    else:
        logger.error("Failed to parse message")
        return
    
    # Step 2: Process through the workflow
    logger.info("Step 2: Processing through workflow...")
    setup = process_discord_message(message_text)
    if setup:
        logger.info(f"Setup created: {json.dumps(setup, indent=2)}")
        setup_id = setup.get('setup_id')
        logger.info(f"Setup ID: {setup_id}")
    else:
        logger.error("Failed to process message into a setup")
        return

    # Step 3: Get active setups
    logger.info("Step 3: Getting active setups...")
    active_setups = get_active_setups()
    logger.info(f"Active setups: {len(active_setups)}")
    for setup_id, setup_data in active_setups.items():
        logger.info(f"  - {setup_id}: {setup_data.get('primary_ticker')} {setup_data.get('signal_type')} ({setup_data.get('status')})")
    
    # Step 4: Evaluate setups
    logger.info("Step 4: Evaluating setups...")
    processed = evaluate_setups()
    logger.info(f"Processed setups: {len(processed)}")
    
    # Step 5: Get active trades
    logger.info("Step 5: Getting active trades...")
    active_trades = get_active_trades()
    logger.info(f"Active trades: {len(active_trades)}")
    for setup_id, trade_data in active_trades.items():
        logger.info(f"  - {setup_id}: {trade_data.get('primary_ticker')} {trade_data.get('signal_type')} ({trade_data.get('status')})")
    
    # Step 6: Monitor trades
    logger.info("Step 6: Monitoring trades...")
    updated = monitor_active_trades()
    logger.info(f"Updated trades: {len(updated)}")
    
    logger.info("Workflow demonstration complete!")

if __name__ == "__main__":
    # Sample Discord message with a trading setup
    sample_message = """
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
    
    test_process_message(sample_message)
"""
Test script for the enhanced Discord message parser.
This script verifies that our parser correctly associates price levels with specific tickers.
"""
import json
import logging
from features.discord.message_parser import parse_message

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Test the enhanced message parser with a multi-ticker setup message."""
    # Sample message with multiple tickers and distinct price levels
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
    
    logger.info("Parsing message...")
    result = parse_message(message)
    
    # Print the full result for debugging
    logger.info(f"Parsed message result: {json.dumps(result, indent=2)}")
    
    # Verify ticker-specific data
    logger.info("\nTicker-specific data validation:")
    for ticker, data in result.get('ticker_specific_data', {}).items():
        logger.info(f"\n{ticker} specific data:")
        logger.info(f"  Signal type: {data.get('signal_type')}")
        logger.info(f"  Bias: {data.get('bias')}")
        logger.info(f"  Detected prices: {data.get('detected_prices')}")
        logger.info(f"  Support levels: {data.get('support_levels')}")
        logger.info(f"  Resistance levels: {data.get('resistance_levels')}")
        logger.info(f"  Target levels: {data.get('target_levels')}")
        logger.info(f"  Stop levels: {data.get('stop_levels')}")
        
    # Validate that price levels are correctly assigned to tickers
    if 'AAPL' in result.get('ticker_specific_data', {}):
        apple_data = result['ticker_specific_data']['AAPL']
        if 182 in apple_data.get('support_levels', []):
            logger.info("\nSuccess: AAPL's support level at $182 was correctly identified.")
        else:
            logger.warning("\nWarning: AAPL's support level was not correctly identified.")
        
        if 178 in apple_data.get('target_levels', []):
            logger.info("Success: AAPL's target level at $178 was correctly identified.")
        else:
            logger.warning("Warning: AAPL's target level was not correctly identified.")
            
        if 185 in apple_data.get('stop_levels', []):
            logger.info("Success: AAPL's stop level at $185 was correctly identified.")
        else:
            logger.warning("Warning: AAPL's stop level was not correctly identified.")
    
    if 'NVDA' in result.get('ticker_specific_data', {}):
        nvda_data = result['ticker_specific_data']['NVDA']
        if 920 in nvda_data.get('detected_prices', []):
            logger.info("Success: NVDA's price level at $920 was correctly identified.")
        else:
            logger.warning("Warning: NVDA's price level was not correctly identified.")
    
    if 'SPY' in result.get('ticker_specific_data', {}):
        spy_data = result['ticker_specific_data']['SPY']
        if spy_data.get('signal_type') == 'rejection':
            logger.info("Success: SPY's signal type 'rejection' was correctly identified.")
        else:
            logger.warning(f"Warning: SPY's signal type was incorrect: {spy_data.get('signal_type')}")
        
        if spy_data.get('bias') == 'bearish':
            logger.info("Success: SPY's bearish bias was correctly identified.")
        else:
            logger.warning(f"Warning: SPY's bias was incorrect: {spy_data.get('bias')}")

if __name__ == "__main__":
    main()
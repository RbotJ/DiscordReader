"""
Test Message Parser

This script tests the Discord message parser with sample trading setup messages.
"""
import json
import logging
from pprint import pprint

from features.discord.message_parser import parse_message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample messages
SAMPLE_MESSAGES = [
    """
    A+ Setups - Thursday, May 15
    
    SPY - Rejection Near 586
    
    Looking at the 15-minute chart, SPY is showing a clear rejection at the $586 resistance level. 
    The RSI is showing overbought conditions, and we have bearish divergence on the MACD.
    
    Possible short opportunity with:
    - Entry: $585.50
    - Stop: $587.25
    - Target 1: $584.00 (25%)
    - Target 2: $582.50 (50%)
    - Target 3: $580.00 (25%)
    
    EXPIRY: 0d (same-day) - May 15 puts
    """,
    
    """
    TSLA - Breakout Setup
    
    TSLA looking strong for a breakout above $180 resistance.
    Volume increasing with bullish momentum.
    
    Entry: Above $180.50
    Stop: $178.75
    Targets: $183, $185, $187
    
    Looking at May 17 calls, slightly OTM.
    """,
    
    """
    AAPL Support Play
    
    Apple holding strong support at $182. Seeing good bounce with volume confirmation.
    
    Long bias with entry at $183.25
    SL: $181.80
    Targets: $185, $187
    """,
    
    """
    QQQ - Triangle Pattern
    
    QQQ forming a nice symmetrical triangle on the 15-min chart.
    Resistance at $474, support at $470.
    
    Watch for breakout/breakdown:
    - If breaks above $474: Long with targets at $476, $478
    - If breaks below $470: Short with targets at $468, $466
    
    Use tight stops 1% from entry.
    """,
    
    """
    NVDA - Pre-Earnings Setup
    
    Strong bullish momentum heading into earnings next week.
    Resistance at $950, support at $920.
    
    If breaks above $950 with volume: 
    - Entry: $952
    - Stop: $945
    - Targets: $960, $975, $1000
    
    Consider 1DTE call options with partial profit taking.
    """
]

def test_parser():
    """Test the message parser with sample messages."""
    logger.info("Testing Discord message parser...")
    
    results = []
    
    for i, message in enumerate(SAMPLE_MESSAGES):
        logger.info(f"Parsing message {i+1}...")
        parsed = parse_message(message)
        results.append(parsed)
        
        # Print the parsed results
        print(f"\nMessage {i+1} Results:")
        print("-------------------------------")
        print(f"Tickers: {parsed.get('tickers')}")
        print(f"Primary Ticker: {parsed.get('primary_ticker', 'Not detected')}")
        print(f"Signal Type: {parsed.get('signal_type', 'Not detected')}")
        print(f"Bias: {parsed.get('bias', 'Not detected')}")
        print(f"Price Levels:")
        print(f"  - Support: {parsed.get('support_levels', [])}")
        print(f"  - Resistance: {parsed.get('resistance_levels', [])}")
        print(f"  - Entry: {parsed.get('entry_levels', [])}")
        print(f"  - Stop: {parsed.get('stop_levels', [])}")
        print(f"  - Targets: {parsed.get('target_levels', [])}")
        print(f"Confidence: {parsed.get('confidence', 0):.2f}")
        print("-------------------------------")
    
    # Save results to a file
    with open("parsed_setups.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Parsed {len(results)} messages and saved to parsed_setups.json")

if __name__ == "__main__":
    test_parser()
#!/usr/bin/env python3
"""
Test Message Format Extraction

This script tests the extraction of trading signals from various message formats
to ensure our parser can handle different styles of A+ setup messages.
"""
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Sample message formats to test
TEST_FORMATS = {
    "standard_format": """A+ Trade Setups (Thu, May 16)

1) SPY: Rejection Near 500.5
   - Resistance: 500.5
   - Target: 495
   - Bearish bias below 500.5""",

    "no_comma_format": """A+ Trade Setups (Thu May 16)

1) SPY: Rejection Near 500.5
   - Resistance: 500.5
   - Target: 495
   - Bearish bias below 500.5""",

    "alternative_format": """A+ Trade Setups (May 16)

SPY
🔻 Breakdown Below 500.5
Resistance: 500.5
Target 1: 495
⚠️ Bearish bias below 500.5""",

    "multiple_tickers": """A+ Trade Setups (Thu, May 16)

1) SPY: Rejection Near 500.5
   - Resistance: 500.5
   - Target: 495
   - Bearish bias below 500.5

2) AAPL: Breakout Above 180
   - Support: 180
   - Target 1: 185
   - Target 2: 190
   - Bullish bias above 180""",

    "numbered_with_period": """A+ Trade Setups (Thu, May 16)

1. SPY: Breakdown Below 500.5
   - Resistance: 500.5
   - Target 1: 495
   - Bearish bias below 500.5

2. AAPL: Breakout Above 180
   - Support: 180
   - Target 1: 185
   - Bullish bias above 180"""
}

def test_message_formats():
    """Test extraction of signals from different message formats."""
    # Import directly with a relative import to avoid database dependencies
    from datetime import datetime
    
    # Import core parser functions
    import sys
    sys.path.append('.')
    from features.setups.parser import parse_setup_message, extract_tickers
    
    # Define a simple date extraction function that mimics the real one
    def simple_extract_date(text):
        import re
        date_pattern = r"A\+\s+(?:Trade\s+)?Setups\s+\((?:[A-Za-z]+,?\s+)?([A-Za-z]+)\s+(\d{1,2})(?:,\s+\d{4})?\)"
        match = re.search(date_pattern, text)
        if match:
            month_name = match.group(1)
            day = int(match.group(2))
            current_year = datetime.now().year
            try:
                date_str = f"{day} {month_name} {current_year}"
                return datetime.strptime(date_str, "%d %b %Y").date()
            except:
                return datetime.now().date()
        return datetime.now().date()

    # Test each format
    for format_name, message_text in TEST_FORMATS.items():
        logger.info(f"Testing format: {format_name}")
        logger.info("-" * 50)
        logger.info(message_text)
        logger.info("-" * 50)
        
        # Extract tickers directly
        tickers = extract_tickers(message_text)
        logger.info(f"Extracted tickers: {tickers}")
        
        # Test simple date extraction
        setup_date = simple_extract_date(message_text)
        logger.info(f"Extracted date: {setup_date}")
        
        # Check if relevant for today (always true in test)
        logger.info(f"Testing as if relevant for today's market")
        
        # Parse the message
        setup_message = parse_setup_message(message_text, source="test")
        
        # Log the results
        logger.info(f"Parsed message date: {setup_message.date}")
        logger.info(f"Found {len(setup_message.setups)} ticker setups")
        
        # Validate ticker extraction matches parsing
        parsed_tickers = [setup.symbol for setup in setup_message.setups]
        logger.info(f"Parsed tickers: {parsed_tickers}")
        
        if set(tickers) != set(parsed_tickers):
            logger.warning(f"Ticker mismatch: extracted {tickers}, parsed {parsed_tickers}")
        
        # Log details for each ticker setup
        for i, setup in enumerate(setup_message.setups, 1):
            logger.info(f"Ticker {i}: {setup.symbol}")
            logger.info(f"  Signals: {len(setup.signals)}")
            for j, signal in enumerate(setup.signals, 1):
                logger.info(f"    Signal {j}: {signal.category} {signal.comparison} {signal.trigger}")
                logger.info(f"      Targets: {signal.targets}")
            
            if setup.bias:
                logger.info(f"  Bias: {setup.bias.direction} {setup.bias.condition} {setup.bias.price}")
                if setup.bias.flip:
                    logger.info(f"    Flips {setup.bias.flip.direction} at {setup.bias.flip.price_level}")
            else:
                logger.info("  No bias information found")
        
        logger.info("")  # Empty line for readability
    
    return True

def main():
    """Main function."""
    try:
        # Set environment variable to disable Redis
        os.environ["DISABLE_REDIS"] = "true"
        
        # Import directly
        import sys
        sys.path.append(".")
        
        logger.info("Testing message format extraction - direct mode")
        result = test_message_formats()
        
        if result:
            logger.info("Message format tests completed successfully")
            return 0
        else:
            logger.error("Message format tests failed")
            return 1
    except Exception as e:
        logger.exception(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
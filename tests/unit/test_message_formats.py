"""
Test Message Format Extraction

This module tests the extraction of trading signals from various message formats
to ensure our parser can handle different styles of A+ setup messages.
"""
import os
import sys
import unittest
import logging
from datetime import datetime, timezone
from common.utils import utc_now

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

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


class TestMessageFormatExtraction(unittest.TestCase):
    """Test the extraction of signals from different message formats."""
    
    def setUp(self):
        """Set up test environment."""
        # Set environment variable to disable Redis
        os.environ["DISABLE_REDIS"] = "true"
        
        # Import required modules
        from features.setups.parser import parse_setup_message, extract_tickers
        self.parse_setup_message = parse_setup_message
        self.extract_tickers = extract_tickers
    
    def simple_extract_date(self, text):
        """
        Simple date extraction function that mimics the real one.
        
        Args:
            text (str): The text to extract date from
            
        Returns:
            datetime.date: The extracted date or today's date
        """
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
    
    def test_standard_format(self):
        """Test the standard message format."""
        message_text = TEST_FORMATS["standard_format"]
        self._test_format("standard_format", message_text)
    
    def test_no_comma_format(self):
        """Test the format without commas in the date."""
        message_text = TEST_FORMATS["no_comma_format"]
        self._test_format("no_comma_format", message_text)
    
    def test_alternative_format(self):
        """Test the alternative message format."""
        message_text = TEST_FORMATS["alternative_format"]
        self._test_format("alternative_format", message_text)
    
    def test_multiple_tickers(self):
        """Test a message with multiple tickers."""
        message_text = TEST_FORMATS["multiple_tickers"]
        self._test_format("multiple_tickers", message_text)
    
    def test_numbered_with_period(self):
        """Test a message with numbered tickers using periods."""
        message_text = TEST_FORMATS["numbered_with_period"]
        self._test_format("numbered_with_period", message_text)
    
    def _test_format(self, format_name, message_text):
        """
        Test a specific message format.
        
        Args:
            format_name (str): Name of the format being tested
            message_text (str): The message text to test
        """
        logger.info(f"Testing format: {format_name}")
        logger.info("-" * 50)
        logger.info(message_text)
        logger.info("-" * 50)

        # Extract tickers directly
        tickers = self.extract_tickers(message_text)
        logger.info(f"Extracted tickers: {tickers}")
        self.assertTrue(len(tickers) > 0, f"No tickers found in {format_name}")

        # Test simple date extraction
        setup_date = self.simple_extract_date(message_text)
        logger.info(f"Extracted date: {setup_date}")
        self.assertIsNotNone(setup_date, f"Failed to extract date from {format_name}")

        # Parse the message
        setup_message = self.parse_setup_message(message_text, source="test")
        self.assertIsNotNone(setup_message, f"Failed to parse message for {format_name}")

        # Log the results
        logger.info(f"Parsed message date: {setup_message.date}")
        logger.info(f"Found {len(setup_message.setups)} ticker setups")
        self.assertTrue(len(setup_message.setups) > 0, f"No ticker setups found in {format_name}")

        # Validate ticker extraction matches parsing
        parsed_tickers = [setup.symbol for setup in setup_message.setups]
        logger.info(f"Parsed tickers: {parsed_tickers}")
        
        # Handle expected differences in some formats, otherwise check for exact match
        if format_name in ["alternative_format"]:
            # Some formats might have slightly different parsing behavior
            self.assertTrue(set(tickers).issubset(set(parsed_tickers)) or 
                          set(parsed_tickers).issubset(set(tickers)),
                          f"Ticker mismatch in {format_name}: extracted {tickers}, parsed {parsed_tickers}")
        else:
            # Standard formats should have exact matches
            self.assertEqual(set(tickers), set(parsed_tickers),
                           f"Ticker mismatch in {format_name}: extracted {tickers}, parsed {parsed_tickers}")

        # Check ticker setups have appropriate signals and biases
        for setup in setup_message.setups:
            self.assertIsNotNone(setup.symbol, f"Ticker setup has no symbol in {format_name}")
            self.assertTrue(len(setup.signals) > 0, f"No signals found for {setup.symbol} in {format_name}")
            
            # At least one signal should have targets
            has_targets = any(len(signal.targets) > 0 for signal in setup.signals)
            self.assertTrue(has_targets, f"No signal targets found for {setup.symbol} in {format_name}")


if __name__ == '__main__':
    unittest.main()
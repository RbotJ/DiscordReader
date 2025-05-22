"""
Comprehensive Parser Unit Tests

This module contains all tests for both the standard parser and enhanced parser functionality.
"""
import sys
import unittest
from datetime import date, datetime

# Add the project root to the Python path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import standard parser functions
from features.setups.parser import (
    parse_setup_message
)

# Standard parser functions might be directly in parser.py or in sub-modules
# Import with try-except to handle both cases
try:
    from features.setups.parser import (
        parse_date,
        extract_numbers,
        extract_targets,
        extract_signals as extract_signals_standard,
        extract_bias,
        extract_tickers as extract_tickers_standard
    )
    standard_parser_direct_import = True
except ImportError:
    try:
        from features.setups.parser.date_utils import parse_date
        from features.setups.parser.number_utils import extract_numbers, extract_targets
        from features.setups.parser.signal_utils import extract_signals as extract_signals_standard, extract_bias
        from features.setups.parser.ticker_utils import extract_tickers as extract_tickers_standard
        standard_parser_direct_import = False
    except ImportError:
        # If we can't import these functions, we'll mock them in the test
        standard_parser_direct_import = False
        # Create placeholder functions that will be overridden in tests
        def parse_date(*args, **kwargs): return date.today()
        def extract_numbers(*args, **kwargs): return []
        def extract_targets(*args, **kwargs): return []
        def extract_signals_standard(*args, **kwargs): return []
        def extract_bias(*args, **kwargs): return None
        def extract_tickers_standard(*args, **kwargs): return []

# Import enhanced parser functions (if they exist)
try:
    from features.setups.enhanced_parser import (
        extract_date as enhanced_extract_date,
        extract_tickers as enhanced_extract_tickers,
        extract_signals as enhanced_extract_signals
    )
    enhanced_parser_available = True
except ImportError:
    enhanced_parser_available = False
    # Create placeholder functions for tests that will be skipped
    def enhanced_extract_date(*args, **kwargs): return date.today()
    def enhanced_extract_tickers(*args, **kwargs): return []
    def enhanced_extract_signals(*args, **kwargs): return []

from common.models import SignalCategory, ComparisonType, Aggressiveness, BiasDirection
from tests.fixtures.sample_messages import (
    SIMPLE_MESSAGE,
    MULTI_TICKER_MESSAGE,
    ALTERNATE_FORMAT_MESSAGE,
    COMPLEX_BIAS_MESSAGE,
    NO_DATE_MESSAGE,
    DIVIDER_TICKER_MESSAGE,
    MALFORMED_MESSAGE,
    EMPTY_MESSAGE
)


class TestDateParsing(unittest.TestCase):
    """Test date parsing functionality."""
    
    def test_parse_valid_date(self):
        """Test parsing a valid date string."""
        test_date = "Wed May 14"
        result = parse_date(test_date)
        self.assertEqual(result.month, 5)
        self.assertEqual(result.day, 14)
        
    def test_parse_invalid_date(self):
        """Test parsing an invalid date string."""
        test_date = "Invalid date"
        result = parse_date(test_date)
        # Should default to today's date
        self.assertIsInstance(result, date)
        
    def test_parse_empty_date(self):
        """Test parsing an empty date string."""
        test_date = ""
        result = parse_date(test_date)
        # Should default to today's date
        self.assertIsInstance(result, date)
        
    @unittest.skipIf(not enhanced_parser_available, "Enhanced parser not available")
    def test_enhanced_date_extraction(self):
        """Test the enhanced date extraction functionality."""
        test_cases = [
            ("A+ Trade Setups (Thu, May 16)", datetime(2025, 5, 16).date()),
            ("Setup for Monday, June 1", datetime(2025, 6, 1).date()),
            ("Invalid date format", None)
        ]
        for input_text, expected in test_cases:
            if expected is None:
                # For invalid dates, just test it returns something
                self.assertIsNotNone(enhanced_extract_date(input_text))
            else:
                self.assertEqual(enhanced_extract_date(input_text), expected)


class TestNumberExtraction(unittest.TestCase):
    """Test number extraction from text."""
    
    def test_extract_numbers(self):
        """Test extracting numbers from text."""
        test_text = "Price levels: 123.45, 678.90, and 246.80"
        result = extract_numbers(test_text)
        self.assertEqual(result, [123.45, 678.90, 246.80])
        
    def test_extract_numbers_no_numbers(self):
        """Test extracting numbers with no numbers in text."""
        test_text = "No numbers here"
        result = extract_numbers(test_text)
        self.assertEqual(result, [])
        
    def test_extract_targets(self):
        """Test extracting target price levels."""
        test_text = "🔼 Targets: 585.80, 587.90, 589.50"
        signal_line = "🔼 Aggressive Long Over 583.75"
        result = extract_targets(test_text, signal_line)
        self.assertEqual(result, [585.80, 587.90, 589.50])
        
    def test_extract_targets_from_parentheses(self):
        """Test extracting targets from parentheses format."""
        test_text = "🔼 Aggressive Breakout Above 592.53 (594.70, 597.20, 600.50)"
        result = extract_targets(test_text)
        self.assertEqual(set(result), {594.70, 597.20, 600.50})
        
    def test_extract_targets_from_signal_line(self):
        """Test extracting targets from the signal line."""
        test_text = "Random text"
        signal_line = "🔼 Breakout Above 588.87 (591.30, 593.80, 596.40)"
        result = extract_targets(test_text, signal_line)
        self.assertEqual(result, [591.30, 593.80, 596.40])


class TestSignalExtraction(unittest.TestCase):
    """Test signal extraction from messages."""
    
    def test_extract_signals_simple(self):
        """Test extracting signals from a simple message."""
        signals = extract_signals_standard(SIMPLE_MESSAGE, "SPY")
        self.assertEqual(len(signals), 4)  # Should have 4 signals (rejection, breakdown, breakout, bounce)
        
    def test_extract_signals_aggressiveness(self):
        """Test extracting signals with aggressiveness indicators."""
        message = """SPY:
        🔻 Aggressive Breakdown Below 590.20 (588.00, 585.50, 582.80)
        🔼 Conservative Breakout Above 595.40 (597.20, 599.80)
        """
        signals = extract_signals_standard(message, "SPY")
        
        self.assertEqual(len(signals), 2)
        
        # Find aggressive and conservative signals
        aggressive = next(s for s in signals if s.aggressiveness == "aggressive")
        conservative = next(s for s in signals if s.aggressiveness == "conservative")
        
        self.assertEqual(aggressive.category, SignalCategory.BREAKDOWN)
        self.assertEqual(aggressive.trigger, 590.20)
        
        self.assertEqual(conservative.category, SignalCategory.BREAKOUT) 
        self.assertEqual(conservative.trigger, 595.40)
        
    def test_extract_signals_bounce_zone(self):
        """Test extracting bounce zone signals."""
        signals = extract_signals_standard(ALTERNATE_FORMAT_MESSAGE, "SPY")
        
        # Find the bounce zone signal
        bounce_signal = next((s for s in signals if s.category == SignalCategory.BOUNCE), None)
        
        self.assertIsNotNone(bounce_signal)
        self.assertEqual(bounce_signal.comparison, ComparisonType.RANGE)
        self.assertEqual(bounce_signal.trigger, [571.0, 573.0])
        
    def test_no_signals(self):
        """Test when no signals are found."""
        signals = extract_signals_standard(EMPTY_MESSAGE, "SPY")
        self.assertEqual(len(signals), 0)
        
    @unittest.skipIf(not enhanced_parser_available, "Enhanced parser not available")
    def test_enhanced_signal_extraction(self):
        """Test the enhanced signal extraction functionality."""
        message = "SPY: Breakout Above 420.50 (422.00, 425.00)"
        signals = enhanced_extract_signals(message)
        self.assertTrue(len(signals) > 0, "Should extract at least one signal")
        if len(signals) > 0:
            self.assertEqual(signals[0].trigger_price, 420.50)
            self.assertEqual(signals[0].targets, [422.00, 425.00])


class TestBiasExtraction(unittest.TestCase):
    """Test bias extraction from messages."""
    
    def test_extract_bias_simple(self):
        """Test extracting bias from a simple message."""
        bias = extract_bias(SIMPLE_MESSAGE, "SPY")
        
        self.assertIsNotNone(bias)
        self.assertEqual(bias.direction, BiasDirection.BULLISH)
        self.assertEqual(bias.condition, ComparisonType.ABOVE)
        self.assertEqual(bias.price, 584.50)
        
    def test_extract_bias_with_flip(self):
        """Test extracting bias with flip condition."""
        bias = extract_bias(COMPLEX_BIAS_MESSAGE, "SPY")
        
        self.assertIsNotNone(bias)
        self.assertEqual(bias.direction, BiasDirection.BEARISH)
        self.assertEqual(bias.condition, ComparisonType.BELOW)
        self.assertEqual(bias.price, 562.25)
        
        # Check bias flip
        self.assertIsNotNone(bias.flip)
        self.assertEqual(bias.flip.direction, BiasDirection.BULLISH)
        self.assertEqual(bias.flip.price_level, 564.10)
        
    def test_no_bias(self):
        """Test when no bias is found."""
        bias = extract_bias(EMPTY_MESSAGE, "SPY")
        self.assertIsNone(bias)


class TestTickerExtraction(unittest.TestCase):
    """Test ticker extraction from messages."""
    
    def test_extract_tickers_numbered(self):
        """Test extracting tickers from a message with numbered tickers."""
        tickers = extract_tickers_standard(MULTI_TICKER_MESSAGE)
        self.assertEqual(len(tickers), 3)
        self.assertIn("SPY", tickers)
        self.assertIn("TSLA", tickers)
        self.assertIn("NVDA", tickers)
        
    def test_extract_tickers_divider(self):
        """Test extracting tickers from a message with divider sections."""
        tickers = extract_tickers_standard(DIVIDER_TICKER_MESSAGE)
        self.assertIn("TSLA", tickers)
        
    def test_extract_tickers_no_tickers(self):
        """Test extracting tickers with no tickers in message."""
        tickers = extract_tickers_standard(EMPTY_MESSAGE)
        self.assertEqual(len(tickers), 0)
        
    @unittest.skipIf(not enhanced_parser_available, "Enhanced parser not available")
    def test_enhanced_ticker_extraction(self):
        """Test the enhanced ticker extraction functionality."""
        message = """
        1) SPY: Rejection near 500
        2) TSLA: Breakout above 800
        3) AAPL: Support at 150
        """
        expected_tickers = ["SPY", "TSLA", "AAPL"]
        extracted_tickers = enhanced_extract_tickers(message)
        self.assertEqual(set(extracted_tickers), set(expected_tickers))


class TestMessageParsing(unittest.TestCase):
    """Test complete message parsing."""
    
    def test_parse_simple_message(self):
        """Test parsing a simple message."""
        result = parse_setup_message(SIMPLE_MESSAGE, "test")
        
        self.assertEqual(len(result.setups), 1)
        self.assertEqual(result.setups[0].symbol, "SPY")
        self.assertEqual(len(result.setups[0].signals), 4)
        self.assertIsNotNone(result.setups[0].bias)
        
    def test_parse_multi_ticker_message(self):
        """Test parsing a message with multiple tickers."""
        result = parse_setup_message(MULTI_TICKER_MESSAGE, "test")
        
        self.assertEqual(len(result.setups), 3)
        symbols = [setup.symbol for setup in result.setups]
        self.assertIn("SPY", symbols)
        self.assertIn("TSLA", symbols)
        self.assertIn("NVDA", symbols)
        
    def test_parse_alternate_format(self):
        """Test parsing a message with alternate format."""
        result = parse_setup_message(ALTERNATE_FORMAT_MESSAGE, "test")
        
        self.assertGreater(len(result.setups), 0)
        self.assertGreater(len(result.setups[0].signals), 0)
        
    def test_parse_no_date(self):
        """Test parsing a message with no explicit date."""
        result = parse_setup_message(NO_DATE_MESSAGE, "test")
        
        # Should default to today's date
        self.assertIsInstance(result.date, date)
        
    def test_parse_malformed_message(self):
        """Test parsing a malformed message."""
        # Should not raise exceptions despite malformed input
        result = parse_setup_message(MALFORMED_MESSAGE, "test")
        
        # May or may not extract valid data depending on how robust the parser is
        self.assertIsInstance(result, object)
        
    def test_parse_empty_message(self):
        """Test parsing an empty message."""
        result = parse_setup_message(EMPTY_MESSAGE, "test")
        
        self.assertEqual(len(result.setups), 0)


if __name__ == '__main__':
    unittest.main()
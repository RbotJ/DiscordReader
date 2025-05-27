"""
Unit tests for the trade setup parser module.
"""
import unittest
from datetime import date

from features.parsing.parser import MessageParser
from common.parser_utils import (
    normalize_text,
    extract_ticker_sections,
    _extract_price_levels
)
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
        signals = extract_signals(SIMPLE_MESSAGE, "SPY")
        self.assertEqual(len(signals), 4)  # Should have 4 signals (rejection, breakdown, breakout, bounce)
        
    def test_extract_signals_aggressiveness(self):
        """Test extracting signals with aggressiveness indicators."""
        message = """SPY:
        🔻 Aggressive Breakdown Below 590.20 (588.00, 585.50, 582.80)
        🔼 Conservative Breakout Above 595.40 (597.20, 599.80)
        """
        signals = extract_signals(message, "SPY")
        
        self.assertEqual(len(signals), 2)
        
        # Find aggressive and conservative signals
        aggressive = next(s for s in signals if s.aggressiveness == "aggressive")
        conservative = next(s for s in signals if s.aggressiveness == "conservative")
        
        self.assertEqual(aggressive.category, SignalCategory.BREAKDOWN)
        self.assertEqual(aggressive.trigger, 590.20)
        
        self.assertEqual(conservative.category, SignalCategory.BREAKOUT) 
        self.assertEqual(conservative.trigger, 595.40)
        
        # Check the extracted signals
        categories = [signal.category for signal in signals]
        self.assertIn(SignalCategory.REJECTION, categories)
        self.assertIn(SignalCategory.BREAKDOWN, categories)
        self.assertIn(SignalCategory.BREAKOUT, categories)
        self.assertIn(SignalCategory.BOUNCE, categories)
        
        # Check specific signal details
        breakout_signal = next(s for s in signals if s.category == SignalCategory.BREAKOUT)
        self.assertEqual(breakout_signal.comparison, ComparisonType.ABOVE)
        self.assertEqual(breakout_signal.trigger, 588.87)
        self.assertEqual(len(breakout_signal.targets), 3)
        
    def test_extract_signals_aggressive(self):
        """Test extracting signals with aggressiveness indicators."""
        signals = extract_signals(ALTERNATE_FORMAT_MESSAGE, "SPY")
        
        # Find the aggressive and conservative signals
        aggressive_signal = next((s for s in signals if s.aggressiveness == Aggressiveness.AGGRESSIVE), None)
        conservative_signal = next((s for s in signals if s.aggressiveness == Aggressiveness.CONSERVATIVE), None)
        
        self.assertIsNotNone(aggressive_signal)
        self.assertIsNotNone(conservative_signal)
        
        # Check their values
        self.assertEqual(aggressive_signal.trigger, 583.75)
        self.assertEqual(conservative_signal.trigger, 585.80)
        
    def test_extract_signals_bounce_zone(self):
        """Test extracting bounce zone signals."""
        signals = extract_signals(ALTERNATE_FORMAT_MESSAGE, "SPY")
        
        # Find the bounce zone signal
        bounce_signal = next((s for s in signals if s.category == SignalCategory.BOUNCE), None)
        
        self.assertIsNotNone(bounce_signal)
        self.assertEqual(bounce_signal.comparison, ComparisonType.RANGE)
        self.assertEqual(bounce_signal.trigger, [571.0, 573.0])
        
    def test_no_signals(self):
        """Test when no signals are found."""
        signals = extract_signals(EMPTY_MESSAGE, "SPY")
        self.assertEqual(len(signals), 0)


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
        tickers = extract_tickers(MULTI_TICKER_MESSAGE)
        self.assertEqual(len(tickers), 3)
        self.assertIn("SPY", tickers)
        self.assertIn("TSLA", tickers)
        self.assertIn("NVDA", tickers)
        
    def test_extract_tickers_divider(self):
        """Test extracting tickers from a message with divider sections."""
        tickers = extract_tickers(DIVIDER_TICKER_MESSAGE)
        self.assertIn("TSLA", tickers)
        
    def test_extract_tickers_no_tickers(self):
        """Test extracting tickers with no tickers in message."""
        tickers = extract_tickers(EMPTY_MESSAGE)
        self.assertEqual(len(tickers), 0)


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
from common.utils import extract_all_levels
from common.models import TickerSetupDTO, Signal, Bias, BiasFlip
from common.models import SignalCategory, ComparisonType, BiasDirection, Aggressiveness

def test_extract_all_levels():
    """Test extracting all price levels from ticker setups."""
    # Create test data with overlapping values
    signal1 = Signal(
        category=SignalCategory.BREAKOUT,
        comparison=ComparisonType.ABOVE,
        trigger=590.20,  # Duplicate with bias price
        targets={588.00, 585.50, 582.80},
        aggressiveness=Aggressiveness.AGGRESSIVE
    )
    
    signal2 = Signal(
        category=SignalCategory.REJECTION,
        comparison=ComparisonType.NEAR,
        trigger=585.50,  # Duplicate with signal1 target
        targets={580.00, 575.00},
        aggressiveness=Aggressiveness.NONE
    )
    
    bias = Bias(
        direction=BiasDirection.BULLISH,
        condition=ComparisonType.ABOVE,
        price=590.20,  # Duplicate with signal1 trigger
        flip=BiasFlip(
            direction=BiasDirection.BEARISH,
            price_level=575.00  # Duplicate with signal2 target
        )
    )
    
    setup = TickerSetupDTO(
        symbol="SPY",
        signals=[signal1, signal2],
        bias=bias
    )
    
    # Extract levels
    levels = extract_all_levels([setup])
    
    # Verify unique levels
    expected = {590.20, 588.00, 585.50, 582.80, 580.00, 575.00}
    assert levels == expected

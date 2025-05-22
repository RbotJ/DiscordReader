
import unittest
from features.setups.enhanced_parser import extract_date, extract_tickers, extract_signals
from datetime import datetime

class TestEnhancedParser(unittest.TestCase):
    def test_date_extraction(self):
        test_cases = [
            ("A+ Trade Setups (Thu, May 16)", datetime(2025, 5, 16).date()),
            ("Setup for Monday, June 1", datetime(2025, 6, 1).date()),
            ("Invalid date format", None)
        ]
        for input_text, expected in test_cases:
            self.assertEqual(extract_date(input_text), expected)

    def test_ticker_extraction(self):
        message = """
        1) SPY: Rejection near 500
        2) TSLA: Breakout above 800
        3) AAPL: Support at 150
        """
        expected_tickers = ["SPY", "TSLA", "AAPL"]
        self.assertEqual(extract_tickers(message), expected_tickers)

    def test_signal_extraction(self):
        message = "SPY: Breakout Above 420.50 (422.00, 425.00)"
        signals = extract_signals(message)
        self.assertEqual(signals[0].trigger_price, 420.50)
        self.assertEqual(signals[0].targets, [422.00, 425.00])

if __name__ == '__main__':
    unittest.main()

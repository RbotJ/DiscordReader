"""
Tests for the strategy monitor module.

This tests the breakout confirmation logic and event publishing.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from features.strategy.monitor import (
    Candle,
    is_confirmed_breakout,
    calculate_average_volume,
    is_market_hours,
    monitor_setups,
    clear_confirmed_setups
)


class TestStrategyMonitor(unittest.TestCase):
    """Test cases for the strategy monitor module."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear confirmed setups tracking before each test
        clear_confirmed_setups()
        
        # Create some test candles
        self.bullish_candle = Candle({
            't': '2025-05-21T10:30:00Z',
            'o': 100.0,
            'h': 105.0,
            'l': 99.5,
            'c': 104.0,
            'v': 15000
        })
        
        self.bearish_candle = Candle({
            't': '2025-05-21T10:35:00Z',
            'o': 104.0,
            'h': 104.5,
            'l': 101.0,
            'c': 101.5,
            'v': 12000
        })
        
        self.doji_candle = Candle({
            't': '2025-05-21T10:40:00Z',
            'o': 101.5,
            'h': 102.0,
            'l': 101.0,
            'c': 101.6,
            'v': 5000
        })
        
        self.breakout_candle = Candle({
            't': '2025-05-21T10:45:00Z',
            'o': 101.6,
            'h': 106.0,
            'l': 101.5,
            'c': 105.5,
            'v': 25000
        })
        
        # Previous candles for volume average
        self.previous_candles = [
            Candle({'t': '2025-05-21T10:25:00Z', 'o': 99.0, 'h': 100.5, 'l': 98.5, 'c': 100.0, 'v': 10000}),
            Candle({'t': '2025-05-21T10:30:00Z', 'o': 100.0, 'h': 101.0, 'l': 99.8, 'c': 100.8, 'v': 8000}),
            Candle({'t': '2025-05-21T10:35:00Z', 'o': 100.8, 'h': 101.2, 'l': 100.5, 'c': 101.0, 'v': 7000}),
            Candle({'t': '2025-05-21T10:40:00Z', 'o': 101.0, 'h': 101.5, 'l': 100.8, 'c': 101.2, 'v': 9000}),
            Candle({'t': '2025-05-21T10:45:00Z', 'o': 101.2, 'h': 102.0, 'l': 101.0, 'c': 101.8, 'v': 11000})
        ]

    def test_candle_properties(self):
        """Test the Candle class properties."""
        # Test bullish candle
        self.assertTrue(self.bullish_candle.is_bullish)
        self.assertEqual(self.bullish_candle.body_size, 4.0)
        self.assertEqual(self.bullish_candle.body_percent, 4.0)
        self.assertEqual(self.bullish_candle.range, 5.5)
        
        # Test bearish candle
        self.assertFalse(self.bearish_candle.is_bullish)
        self.assertEqual(self.bearish_candle.body_size, 2.5)
        self.assertAlmostEqual(self.bearish_candle.body_percent, 2.4038, places=4)
        self.assertEqual(self.bearish_candle.range, 3.5)

    def test_is_market_hours(self):
        """Test market hours checking."""
        # Market hours (10:30 AM)
        market_time = datetime(2025, 5, 21, 10, 30, tzinfo=timezone.utc)
        self.assertTrue(is_market_hours(market_time))
        
        # Before market (9:00 AM)
        pre_market = datetime(2025, 5, 21, 9, 0, tzinfo=timezone.utc)
        self.assertFalse(is_market_hours(pre_market))
        
        # After market (16:30 / 4:30 PM)
        after_market = datetime(2025, 5, 21, 16, 30, tzinfo=timezone.utc)
        self.assertFalse(is_market_hours(after_market))

    def test_calculate_average_volume(self):
        """Test average volume calculation."""
        avg_volume = calculate_average_volume(self.previous_candles)
        expected_avg = (10000 + 8000 + 7000 + 9000 + 11000) / 5
        self.assertEqual(avg_volume, expected_avg)
        
        # Test with fewer candles than requested periods
        avg_volume_2 = calculate_average_volume(self.previous_candles[:2], periods=5)
        expected_avg_2 = (10000 + 8000) / 2
        self.assertEqual(avg_volume_2, expected_avg_2)
        
        # Test with empty list
        self.assertEqual(calculate_average_volume([]), 0)

    def test_is_confirmed_breakout(self):
        """Test breakout confirmation logic."""
        # Test successful breakout confirmation
        breakout_level = 103.0
        avg_volume = 9000  # Average volume of previous candles
        
        # Breakout candle should confirm
        self.assertTrue(is_confirmed_breakout(
            candle=self.breakout_candle,
            level=breakout_level,
            avg_volume=avg_volume,
            check_market_hours=False  # Disable for testing
        ))
        
        # Bullish candle below level should not confirm
        self.assertFalse(is_confirmed_breakout(
            candle=self.bullish_candle,
            level=105.0,  # Above the close
            avg_volume=avg_volume,
            check_market_hours=False
        ))
        
        # Bearish candle should not confirm
        self.assertFalse(is_confirmed_breakout(
            candle=self.bearish_candle,
            level=breakout_level,
            avg_volume=avg_volume,
            check_market_hours=False
        ))
        
        # Doji candle (small body) should not confirm
        self.assertFalse(is_confirmed_breakout(
            candle=self.doji_candle,
            level=101.0,  # Below the close
            avg_volume=avg_volume,
            check_market_hours=False
        ))
        
        # Test with insufficient volume
        self.assertFalse(is_confirmed_breakout(
            candle=self.breakout_candle,
            level=breakout_level,
            avg_volume=avg_volume,
            volume_multiplier=3.0,  # Require 3x average volume
            check_market_hours=False
        ))
        
        # Test with previous candles instead of pre-computed average
        self.assertTrue(is_confirmed_breakout(
            candle=self.breakout_candle,
            level=breakout_level,
            previous_candles=self.previous_candles,
            check_market_hours=False
        ))

    @patch('features.strategy.monitor.publish_event')
    async def test_monitor_setups(self, mock_publish_event):
        """Test the monitor_setups function."""
        # Mock the publish event function
        mock_publish_event.return_value = True
        
        # Create test setups
        setups = [
            {
                'id': 1,
                'ticker': 'SPY',
                'level': 102.0,
                'type': 'Aggressive Breakout Above',
                'targets': [105.0, 107.0]
            },
            {
                'id': 2,
                'ticker': 'SPY',
                'level': 106.0,  # Above our test candles
                'type': 'Conservative Breakout Above',
                'targets': [110.0]
            },
            {
                'id': 3,
                'ticker': 'AAPL',  # Different ticker
                'level': 100.0,
                'type': 'Aggressive Breakout Above',
                'targets': [105.0]
            }
        ]
        
        # Create an async generator for candle data
        async def mock_candle_stream():
            # First yield previous candles to build volume average
            for candle in self.previous_candles:
                yield {
                    'ticker': 'SPY',
                    't': candle.timestamp,
                    'o': candle.open,
                    'h': candle.high,
                    'l': candle.low,
                    'c': candle.close,
                    'v': candle.volume
                }
            
            # Then yield the breakout candle
            yield {
                'ticker': 'SPY',
                't': self.breakout_candle.timestamp,
                'o': self.breakout_candle.open,
                'h': self.breakout_candle.high,
                'l': self.breakout_candle.low,
                'c': self.breakout_candle.close,
                'v': self.breakout_candle.volume
            }
        
        # Run the monitor
        await monitor_setups(setups, mock_candle_stream())
        
        # Check that publish_event was called once for the confirmed breakout
        self.assertEqual(mock_publish_event.call_count, 1)
        
        # Check the event data
        args, kwargs = mock_publish_event.call_args
        channel, event_data = args
        
        self.assertEqual(event_data['ticker'], 'SPY')
        self.assertEqual(event_data['setup_id'], 1)
        self.assertEqual(event_data['level'], 102.0)
        self.assertAlmostEqual(event_data['confirmation']['price'], 105.5)


if __name__ == '__main__':
    unittest.main()
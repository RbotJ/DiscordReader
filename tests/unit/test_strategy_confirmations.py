"""
Tests for trade setup confirmation logic.

This module contains tests for confirming breakout trade setups from candle data.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from features.strategy.breakout_monitor import (
    Candle,
    is_confirmed_breakout,
    calculate_average_volume,
    monitor_signals,
    clear_confirmed_signals
)
from features.setups.enhanced_parser import Signal

class TestBreakoutConfirmations(unittest.TestCase):
    """Test cases for the breakout confirmation logic."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear confirmed signals tracking before each test
        clear_confirmed_signals()
        
        # Create signal for testing
        self.breakout_signal = Signal(
            id=1,
            setup_id="SPY-12345",
            type="breakout",
            direction="up",
            aggressiveness="aggressive",
            trigger=592.53,
            targets=[594.70, 597.20, 600.50]
        )
        
        # Create test candles
        self.bullish_above_level = Candle({
            't': '2025-05-21T10:30:00Z',
            'o': 592.70,
            'h': 594.50,
            'l': 592.40,
            'c': 594.20,
            'v': 15000
        })
        
        self.bullish_below_level = Candle({
            't': '2025-05-21T10:30:00Z',
            'o': 590.50,
            'h': 592.30, 
            'l': 590.40,
            'c': 592.20,
            'v': 15000
        })
        
        self.bearish_candle = Candle({
            't': '2025-05-21T10:35:00Z',
            'o': 593.80,
            'h': 594.50,
            'l': 591.00,
            'c': 591.50,
            'v': 12000
        })
        
        self.small_body_candle = Candle({
            't': '2025-05-21T10:40:00Z',
            'o': 592.60,
            'h': 593.00,
            'l': 592.40,
            'c': 592.70,
            'v': 5000
        })
        
        self.low_volume_candle = Candle({
            't': '2025-05-21T10:45:00Z',
            'o': 592.60,
            'h': 594.00,
            'l': 592.50,
            'c': 593.80,
            'v': 3000
        })
        
        # Previous candles for volume average
        self.previous_candles = [
            Candle({'t': '2025-05-21T10:05:00Z', 'o': 589.0, 'h': 589.5, 'l': 588.5, 'c': 589.0, 'v': 10000}),
            Candle({'t': '2025-05-21T10:10:00Z', 'o': 589.0, 'h': 590.0, 'l': 588.8, 'c': 589.8, 'v': 8000}),
            Candle({'t': '2025-05-21T10:15:00Z', 'o': 589.8, 'h': 590.2, 'l': 589.5, 'c': 590.0, 'v': 7000}),
            Candle({'t': '2025-05-21T10:20:00Z', 'o': 590.0, 'h': 591.5, 'l': 589.8, 'c': 591.2, 'v': 9000}),
            Candle({'t': '2025-05-21T10:25:00Z', 'o': 591.2, 'h': 592.0, 'l': 591.0, 'c': 591.8, 'v': 11000})
        ]

    def test_candle_properties(self):
        """Test the Candle class properties."""
        candle = self.bullish_above_level
        self.assertTrue(candle.is_bullish)
        self.assertEqual(candle.body_size, 1.5)
        self.assertAlmostEqual(candle.body_percent, (1.5/592.70)*100, places=2)
        self.assertEqual(candle.range, 2.1)
        
        candle = self.bearish_candle
        self.assertFalse(candle.is_bullish)

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
        avg_volume = 9000  # Average volume of previous candles
        
        # Valid breakout - bullish candle above level with good volume
        self.assertTrue(is_confirmed_breakout(
            candle=self.bullish_above_level,
            signal=self.breakout_signal,
            avg_volume=avg_volume,
            check_market_hours=False  # Disable for testing
        ))
        
        # Invalid - candle below trigger level
        self.assertFalse(is_confirmed_breakout(
            candle=self.bullish_below_level,
            signal=self.breakout_signal,
            avg_volume=avg_volume,
            check_market_hours=False
        ))
        
        # Invalid - bearish candle
        self.assertFalse(is_confirmed_breakout(
            candle=self.bearish_candle,
            signal=self.breakout_signal,
            avg_volume=avg_volume,
            check_market_hours=False
        ))
        
        # Invalid - small body candle
        self.assertFalse(is_confirmed_breakout(
            candle=self.small_body_candle,
            signal=self.breakout_signal,
            avg_volume=avg_volume,
            min_body_percent=0.5,  # Require larger body than this candle has
            check_market_hours=False
        ))
        
        # Invalid - low volume candle
        self.assertFalse(is_confirmed_breakout(
            candle=self.low_volume_candle,
            signal=self.breakout_signal,
            avg_volume=avg_volume,
            volume_multiplier=2.0,  # Require higher volume
            check_market_hours=False
        ))
        
        # Test with previous candles instead of pre-computed average
        self.assertTrue(is_confirmed_breakout(
            candle=self.bullish_above_level,
            signal=self.breakout_signal,
            previous_candles=self.previous_candles,
            check_market_hours=False
        ))

    @patch('features.strategy.breakout_monitor.publish_event')
    async def test_monitor_signals(self, mock_publish_event):
        """Test the monitor_signals function with a simulated candle stream."""
        mock_publish_event.return_value = True
        
        # Create test signals
        signals = [self.breakout_signal]
        
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
            
            # Then yield a breakout candle
            yield {
                'ticker': 'SPY',
                't': self.bullish_above_level.timestamp,
                'o': self.bullish_above_level.open,
                'h': self.bullish_above_level.high,
                'l': self.bullish_above_level.low,
                'c': self.bullish_above_level.close,
                'v': self.bullish_above_level.volume
            }
        
        # Run the monitor
        await monitor_signals(
            mock_candle_stream(),
            signals,
            check_market_hours=False  # Disable for testing
        )
        
        # Check that the signal was confirmed
        self.assertTrue(signals[0].confirmed)
        self.assertIsNotNone(signals[0].confirmed_at)
        self.assertIsNotNone(signals[0].confirmation_details)
        
        # Check that publish_event was called
        mock_publish_event.assert_called_once()
        
        # Check the event data
        args, kwargs = mock_publish_event.call_args
        channel, event_data = args
        
        self.assertEqual(event_data['ticker'], 'SPY')
        self.assertEqual(event_data['signal_id'], self.breakout_signal.id)
        self.assertEqual(event_data['level'], self.breakout_signal.trigger)
        self.assertAlmostEqual(event_data['confirmation']['price'], self.bullish_above_level.close)


if __name__ == '__main__':
    unittest.main()
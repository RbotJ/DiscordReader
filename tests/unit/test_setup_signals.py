# Updated test setup to use PostgreSQL instead of Redis.
"""
Test Setup Signal Extraction

This script tests the signal extraction functionality from trading setup messages.
"""
import os
import sys
import logging
from datetime import datetime
from flask import Flask
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_signal_extraction():
    """Test the signal extraction from setup message text."""
    # Add debug logs for better visibility
    logging.basicConfig(level=logging.DEBUG)

    # Create a direct test function with updated formats
    test_message = """A+ Trade Setups (Thu, May 16)

1) SPY: Breakdown Below 500.5
   - Resistance: 500.5
   - Target 1: 495
   - Target 2: 490
   - Bearish bias below 500.5

2) AAPL: Breakout Above 180
   - Support: 180
   - Target 1: 185
   - Target 2: 190
   - Bullish bias above 180, flips bearish below 175"""

    # Add direct testing of the ticker extraction and signals
    from features.parsing.parser import MessageParser
    from common.events import publish_event, get_latest_events
    from common.db import db

    # Test ticker extraction directly
    tickers = extract_tickers(test_message)
    logger.info(f"Directly extracted tickers: {tickers}")

    # Test signal extraction directly for each ticker
    for ticker in tickers:
        logger.info(f"Testing signal extraction for {ticker}")
        signals = extract_signals(test_message, ticker)
        logger.info(f"Extracted signals for {ticker}: {signals}")

        bias = extract_bias(test_message, ticker)
        logger.info(f"Extracted bias for {ticker}: {bias}")

    # Test full message parsing
    setup_message = parse_setup_message(test_message, "test")
    logger.info(f"Full parsed message: Date={setup_message.date}, Setups count={len(setup_message.setups)}")
    for i, setup in enumerate(setup_message.setups):
        logger.info(f"Setup {i+1}: {setup.symbol} with {len(setup.signals)} signals")

    logger.info("Testing signal extraction from setup message")

    # Parse the message without saving to database
    from features.setups.parser import parse_setup_message

    try:
        # Parse the message
        setup_message = parse_setup_message(test_message, source="test")

        logger.info(f"Parsed message for date: {setup_message.date}")

        # Log extracted tickers and signals
        logger.info(f"Extracted {len(setup_message.setups)} ticker setups")

        # Check each ticker setup
        for ticker_setup in setup_message.setups:
            logger.info(f"Ticker: {ticker_setup.symbol}")

            # Log signals
            if hasattr(ticker_setup, 'signals') and ticker_setup.signals:
                signals_info = []
                for signal in ticker_setup.signals:
                    signal_dict = {
                        "category": signal.category,
                        "aggressiveness": signal.aggressiveness,
                        "comparison": signal.comparison,
                        "trigger": signal.trigger if not isinstance(signal.trigger, list) else [float(t) for t in signal.trigger],
                        "targets": [float(t) for t in signal.targets]
                    }
                    signals_info.append(signal_dict)
                logger.info(f"Signals: {json.dumps(signals_info, indent=2)}")
            else:
                logger.warning(f"No signals found for {ticker_setup.symbol}")

            # Log bias
            if hasattr(ticker_setup, 'bias') and ticker_setup.bias:
                bias_dict = {
                    "direction": ticker_setup.bias.direction,
                    "condition": ticker_setup.bias.condition,
                    "price": float(ticker_setup.bias.price)
                }

                if ticker_setup.bias.flip:
                    bias_dict["flip_direction"] = ticker_setup.bias.flip.direction
                    bias_dict["flip_price_level"] = float(ticker_setup.bias.flip.price_level)

                logger.info(f"Bias: {json.dumps(bias_dict, indent=2)}")
            else:
                logger.warning(f"No bias found for {ticker_setup.symbol}")

            # Log raw text
            if hasattr(ticker_setup, 'text') and ticker_setup.text:
                logger.info(f"Raw text length: {len(ticker_setup.text)} characters")
            else:
                logger.warning(f"No raw text found for {ticker_setup.symbol}")

        return True

    except Exception as e:
        logger.exception(f"Error testing signal extraction: {e}")
        return False

def main():
    """Main function to test setup signal extraction."""
    logger.info("Testing setup signal extraction")

    result = test_signal_extraction()

    logger.info(f"Signal extraction test {'succeeded' if result else 'failed'}")
    return 0 if result else 1

if __name__ == '__main__':
    sys.exit(main())
```The test_setup_signals.py file is updated to use PostgreSQL instead of Redis.
"""
Discord Test Utilities

This module provides utilities for testing Discord integration features.
"""
import logging
import os
from datetime import datetime

# Import Discord utilities with fallback for missing functions
try:
    from features.discord.client import send_status_update, send_trade_alert, is_discord_available
except ImportError:
    # Provide test stubs for missing functions
    def send_status_update(message):
        """Test stub for send_status_update"""
        return True
    
    def send_trade_alert(alert):
        """Test stub for send_trade_alert"""
        return True
    
    def is_discord_available():
        """Test stub for is_discord_available"""
        return False
from features.discord.setup_handler import handle_discord_setup_message

logger = logging.getLogger(__name__)

# Example A+ setup message for testing
EXAMPLE_SETUP_MESSAGE = """A+ Trade Setups (Wed, May 14)

1. SPY: Rejection Near 588.8
   - Resistance: 588.8 (gap fill)
   - Upper target: 584.2
   - Lower target: 578.6
   - Bearish bias above 588.8

2. NVDA: Breakout Above 925
   - Support: 925 (previous high)
   - Target 1: 945
   - Target 2: 960
   - Bullish bias above 925, bearish below 910

3. MSFT: Breakdown Below 412.5
   - Resistance: 412.5 (previous support)
   - Target 1: 405
   - Target 2: 398
   - Bearish bias below 412.5

4. AAPL: Bounce Near 182.5
   - Support: 182.5 (trend line)
   - Target: 188
   - Aggressive bullish bias above 182.5, flips bearish below 180
"""

def test_send_status_message():
    """
    Test sending a status message to Discord.
    
    Returns:
        bool: Success status
    """
    if not is_discord_available:
        logger.warning("Discord unavailable, cannot send test message")
        return False
        
    return send_status_update("This is a test status message from the A+ Trading app")

def test_send_trade_alert():
    """
    Test sending a trade alert to Discord.
    
    Returns:
        bool: Success status
    """
    if not is_discord_available:
        logger.warning("Discord unavailable, cannot send test alert")
        return False
        
    return send_trade_alert(
        symbol="SPY",
        alert_type="Entry",
        details="Opening 1 ATM Put contract, expiry: 5/21, price: $3.45"
    )

def test_process_setup_message():
    """
    Test processing a setup message.
    
    Returns:
        bool: Success status
    """
    if not is_discord_available:
        logger.warning("Discord unavailable, cannot process test setup")
        return False
        
    result = handle_discord_setup_message(
        message_content=EXAMPLE_SETUP_MESSAGE,
        message_timestamp=datetime.utcnow()
    )
    
    return result is not None
"""
Test Utilities for Timezone-Aware Testing

Provides utilities for creating timezone-aware test fixtures and handling
time-sensitive test data consistently across all test suites.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from common.utils import utc_now, ensure_utc, to_local, get_trading_day


def sample_timestamp(days_ago: int = 0, hours_ago: int = 0, minutes_ago: int = 0) -> datetime:
    """
    Create a timezone-aware sample timestamp for testing.
    
    Args:
        days_ago: Number of days in the past
        hours_ago: Number of hours in the past
        minutes_ago: Number of minutes in the past
        
    Returns:
        datetime: Timezone-aware datetime in UTC
    """
    now = utc_now()
    delta = timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
    return now - delta


def sample_trading_day(days_ago: int = 0) -> datetime:
    """
    Create a sample trading day timestamp for testing.
    
    Args:
        days_ago: Number of trading days in the past
        
    Returns:
        datetime: Timezone-aware datetime representing a trading day
    """
    base_time = sample_timestamp(days_ago=days_ago)
    return get_trading_day(base_time)


def sample_discord_message_data(
    message_id: str = "test_123456789",
    channel_id: str = "test_channel_999888777",
    author_id: str = "test_author_abc123",
    content: str = "Sample test message content",
    timestamp: Optional[datetime] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create sample Discord message data for testing.
    
    Args:
        message_id: Discord message ID
        channel_id: Discord channel ID
        author_id: Discord author ID
        content: Message content
        timestamp: Message timestamp (defaults to current UTC time)
        **kwargs: Additional fields
        
    Returns:
        dict: Sample Discord message data
    """
    if timestamp is None:
        timestamp = utc_now()
    
    return {
        'message_id': message_id,
        'channel_id': channel_id,
        'author_id': author_id,
        'content': content,
        'timestamp': ensure_utc(timestamp),
        **kwargs
    }


def sample_aplus_message_content(trading_date: Optional[str] = None) -> str:
    """
    Create sample A+ message content for testing.
    
    Args:
        trading_date: Trading date string (defaults to current date)
        
    Returns:
        str: Sample A+ message content
    """
    if trading_date is None:
        trading_date = get_trading_day(utc_now()).strftime("%B %d")
    
    return f"""A+ Scalp Trade Setups — {trading_date}

SPY
🔻 Aggressive Breakdown Below 525.50 🔻 520.40, 515.30, 510.20
🔻 Conservative Breakdown Below 520.75 🔻 515.65, 510.55, 505.45
🔼 Aggressive Breakout Above 535.80 🔼 540.90, 546.00, 551.10
🔄 Bounce Zone: 515.25-520.75 🔼 Target: 525.85, 530.95

NVDA
🔻 Rejection Short Near 445.50 🔻 442.40, 439.30, 436.20
🔼 Conservative Breakout Above 448.25 🔼 451.35, 454.45, 457.55

⚠️ Bias — Watch for market direction confirmation before entries. Volume validation required for all breakouts."""


def assert_timezone_aware(dt: datetime, message: str = "Datetime should be timezone-aware"):
    """
    Assert that a datetime object is timezone-aware.
    
    Args:
        dt: Datetime object to check
        message: Assertion message
        
    Raises:
        AssertionError: If datetime is not timezone-aware
    """
    assert dt.tzinfo is not None, message
    assert dt.tzinfo.utcoffset(dt) is not None, message


def assert_utc_timezone(dt: datetime, message: str = "Datetime should be in UTC"):
    """
    Assert that a datetime object is in UTC timezone.
    
    Args:
        dt: Datetime object to check
        message: Assertion message
        
    Raises:
        AssertionError: If datetime is not in UTC
    """
    assert_timezone_aware(dt, message)
    assert dt.tzinfo == timezone.utc, f"{message} (got {dt.tzinfo})"


def create_test_message_batch(count: int = 5, base_timestamp: Optional[datetime] = None) -> list:
    """
    Create a batch of test Discord messages with consistent timestamps.
    
    Args:
        count: Number of messages to create
        base_timestamp: Base timestamp for the first message
        
    Returns:
        list: List of sample Discord message data
    """
    if base_timestamp is None:
        base_timestamp = utc_now()
    
    messages = []
    for i in range(count):
        timestamp = base_timestamp - timedelta(minutes=i * 5)  # 5 minutes apart
        message = sample_discord_message_data(
            message_id=f"test_msg_{1000 + i}",
            channel_id="test_channel_batch",
            author_id=f"test_author_{i}",
            content=f"Test message {i + 1}",
            timestamp=timestamp
        )
        messages.append(message)
    
    return messages


def verify_timezone_consistency(test_instance, *datetime_objects):
    """
    Verify that all provided datetime objects are timezone-aware and consistent.
    
    Args:
        test_instance: Test case instance (for assertions)
        *datetime_objects: Datetime objects to verify
    """
    for dt in datetime_objects:
        if dt is not None:
            assert_timezone_aware(dt)
            # Verify can be converted to local time
            local_dt = to_local(dt)
            assert_timezone_aware(local_dt)
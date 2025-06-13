"""
Common Utilities Module

Centralized utilities for timezone handling, data formatting, and other shared functionality.
Provides consistent timezone normalization and display formatting across all features.
"""

import json
from datetime import datetime, date, timezone as dt_timezone
from typing import Any, Dict, Optional, Union
import pytz
from pytz import timezone, UTC

# Standard timezone definitions
CENTRAL = timezone("America/Chicago")
EASTERN = timezone("US/Eastern")
UTC_TZ = UTC


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure datetime is timezone-aware in UTC.
    
    Args:
        dt: Input datetime object (may be naive or timezone-aware)
        
    Returns:
        datetime: Timezone-aware datetime in UTC
    """
    if dt is None:
        return None
        
    if dt.tzinfo is None:
        # Assume naive datetime is already in UTC
        return dt.replace(tzinfo=UTC)
    
    # Convert timezone-aware datetime to UTC
    return dt.astimezone(UTC)


def to_local(dt: Optional[datetime], tz_name: str = "America/Chicago") -> Optional[datetime]:
    """
    Convert UTC datetime to local timezone.
    
    Args:
        dt: UTC datetime object
        tz_name: Target timezone name (default: America/Chicago)
        
    Returns:
        datetime: Datetime converted to local timezone
    """
    if dt is None:
        return None
        
    utc_dt = ensure_utc(dt)
    if utc_dt is None:
        return None
    local_tz = timezone(tz_name)
    return utc_dt.astimezone(local_tz)


def get_trading_day(ts: Optional[datetime], tz_name: str = "America/Chicago") -> Optional[date]:
    """
    Get the trading day for a given timestamp.
    
    Args:
        ts: Input timestamp
        tz_name: Trading timezone (default: America/Chicago for Central Time)
        
    Returns:
        date: Trading day in the specified timezone
    """
    if ts is None:
        return None
        
    local_dt = to_local(ts, tz_name)
    if local_dt is None:
        return None
    return local_dt.date()


def format_timestamp_local(dt: Optional[datetime], tz_name: str = "America/Chicago", 
                          include_seconds: bool = False) -> str:
    """
    Format datetime for local display.
    
    Args:
        dt: UTC datetime object
        tz_name: Target timezone name
        include_seconds: Whether to include seconds in output
        
    Returns:
        str: Formatted timestamp string
    """
    if dt is None:
        return "N/A"
        
    local_dt = to_local(dt, tz_name)
    if local_dt is None:
        return "N/A"
    
    if include_seconds:
        return local_dt.strftime('%b %d, %Y %I:%M:%S %p %Z')
    else:
        return local_dt.strftime('%b %d, %Y %I:%M %p %Z')


def safe_json_serialize(data: Any) -> str:
    """
    Safely serialize data to JSON, handling datetime objects.
    
    Args:
        data: Data to serialize
        
    Returns:
        str: JSON string
    """
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    return json.dumps(data, default=json_serializer)


def utc_now() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.
    
    Returns:
        datetime: Current time in UTC with timezone info
    """
    return datetime.now(tz=dt_timezone.utc)


def parse_discord_timestamp(timestamp_str: str) -> datetime:
    """
    Parse Discord timestamp string into timezone-aware UTC datetime.
    
    Args:
        timestamp_str: Discord timestamp string
        
    Returns:
        datetime: Parsed datetime in UTC
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",      # 2025-06-11T13:53:25.075000Z
        "%Y-%m-%dT%H:%M:%SZ",         # 2025-06-11T13:53:25Z
        "%Y-%m-%dT%H:%M:%S.%f%z",     # 2025-06-11T13:53:25.075000+00:00
        "%Y-%m-%dT%H:%M:%S%z"         # 2025-06-11T13:53:25+00:00
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp_str, fmt)
            # Ensure the result is timezone-aware in UTC
            return ensure_utc(dt)
        except ValueError:
            continue
    
    # Fallback: try fromisoformat
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return ensure_utc(dt)
    except ValueError:
        # Last resort: return current UTC time
        return utc_now()
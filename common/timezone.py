"""
Timezone Utilities for Trading Day Logic

All trading-day logic should align with US/Central timezone (America/Chicago) 
regardless of where the server runs (UTC or otherwise).
"""
from datetime import datetime, date
import pytz
from typing import Optional


def get_central_trading_day(dt: Optional[datetime] = None) -> date:
    """
    Return the current trading day in Central Time.
    
    Args:
        dt: Optional datetime to convert. If None, uses current UTC time.
        
    Returns:
        date: The trading day in Central Time
    """
    central = pytz.timezone("America/Chicago")
    if dt is None:
        dt = datetime.now(tz=pytz.UTC)
    elif dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = pytz.UTC.localize(dt)
    
    return dt.astimezone(central).date()


def is_trading_day(dt: Optional[datetime] = None) -> bool:
    """
    Check if the given datetime falls on a trading day (Monday-Friday in Central Time).
    
    Args:
        dt: Optional datetime to check. If None, uses current UTC time.
        
    Returns:
        bool: True if it's a trading day (weekday), False if weekend
    """
    day = get_central_trading_day(dt).weekday()
    return day < 5  # Monday=0, Sunday=6


def get_central_datetime(dt: Optional[datetime] = None) -> datetime:
    """
    Convert datetime to Central Time.
    
    Args:
        dt: Optional datetime to convert. If None, uses current UTC time.
        
    Returns:
        datetime: The datetime in Central Time
    """
    central = pytz.timezone("America/Chicago")
    if dt is None:
        dt = datetime.now(tz=pytz.UTC)
    elif dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = pytz.UTC.localize(dt)
    
    return dt.astimezone(central)
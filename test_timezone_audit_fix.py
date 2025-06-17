#!/usr/bin/env python3
"""
Test script to verify timezone fixes for weekend setup detection.
This script will show the difference between UTC and Central Time parsing.
"""

import logging
from datetime import datetime, date
import pytz
from features.parsing.store import get_parsing_store
from common.timezone import get_central_trading_day

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_timezone_audit():
    """Test the timezone audit logic with real data."""
    
    store = get_parsing_store()
    
    # Get some sample setups to test
    from features.parsing.models import TradeSetup
    sample_setups = store.session.query(TradeSetup).filter_by(active=True).limit(10).all()
    
    print("Testing timezone-aware weekend detection:")
    print("=" * 60)
    
    weekend_count_old = 0
    weekend_count_new = 0
    
    for setup in sample_setups:
        print(f"\nSetup: {setup.ticker} on {setup.trading_day}")
        
        # Old logic (what was stored)
        old_weekday = setup.trading_day.weekday()
        is_weekend_old = old_weekday >= 5
        if is_weekend_old:
            weekend_count_old += 1
            
        print(f"  Stored trading_day: {setup.trading_day} (weekday: {old_weekday})")
        print(f"  Old logic weekend: {is_weekend_old}")
        
        # Try to simulate what the new logic would produce
        # (We can't recreate the original timestamp easily, so this is approximate)
        print(f"  Central Time today: {get_central_trading_day()}")
    
    print(f"\nSummary:")
    print(f"Weekend setups found with old logic: {weekend_count_old}")
    
    # Test the actual audit function
    audit_data = store.get_audit_anomalies()
    print(f"Current audit weekend count: {audit_data.get('weekend_setup_count', 0)}")
    print(f"Audit weekend setups: {len(audit_data.get('weekend_setups', []))}")
    
    # Show some audit details
    if audit_data.get('weekend_setups'):
        print("\nWeekend setups found:")
        for setup in audit_data['weekend_setups'][:3]:
            print(f"  {setup['ticker']} on {setup['trading_day']} ({setup['weekday']})")

def test_central_time_conversion():
    """Test Central Time conversion with sample timestamps."""
    
    print("\nTesting Central Time conversion:")
    print("=" * 40)
    
    # Test various UTC timestamps
    test_timestamps = [
        "2025-06-15T10:00:00Z",  # Sunday morning UTC
        "2025-06-15T23:00:00Z",  # Sunday evening UTC
        "2025-06-16T05:00:00Z",  # Monday early morning UTC
    ]
    
    central = pytz.timezone("America/Chicago")
    
    for timestamp_str in test_timestamps:
        utc_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        central_dt = utc_dt.astimezone(central)
        central_date = get_central_trading_day(utc_dt)
        
        print(f"UTC: {utc_dt} -> Central: {central_dt}")
        print(f"  Trading day: {central_date} (weekday: {central_date.weekday()})")
        print(f"  Is weekend: {central_date.weekday() >= 5}")
        print()

if __name__ == "__main__":
    print("Testing timezone fixes for audit detection...")
    test_central_time_conversion()
    test_timezone_audit()
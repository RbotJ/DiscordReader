"""
Test script to verify the timezone fix for trading day logic.
"""
import logging
from datetime import datetime, date
import pytz
from common.timezone import get_central_trading_day, is_trading_day, get_central_datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_timezone_utilities():
    """Test the timezone utility functions."""
    print("=== Testing Timezone Utilities ===")
    
    # Test current time
    utc_now = datetime.now(pytz.UTC)
    central_now = get_central_datetime()
    central_date = get_central_trading_day()
    
    print(f"UTC Time: {utc_now}")
    print(f"Central Time: {central_now}")
    print(f"Central Trading Day: {central_date}")
    print(f"Is Trading Day: {is_trading_day()}")
    
    # Test specific edge case: UTC 2025-06-12T01:30:00Z should map to June 11 trading day
    test_utc = datetime(2025, 6, 12, 1, 30, 0, tzinfo=pytz.UTC)
    test_central_date = get_central_trading_day(test_utc)
    test_central_datetime = get_central_datetime(test_utc)
    
    print(f"\nEdge Case Test:")
    print(f"UTC: {test_utc}")
    print(f"Central DateTime: {test_central_datetime}")
    print(f"Central Trading Day: {test_central_date}")
    print(f"Expected: 2025-06-11")
    print(f"Correct: {test_central_date == date(2025, 6, 11)}")
    
    return central_date

def test_audit_logic():
    """Test the audit logic with Central Time."""
    print("\n=== Testing Audit Logic ===")
    
    try:
        from features.parsing.store import get_parsing_store
        store = get_parsing_store()
        
        # Test parsing statistics
        stats = store.get_parsing_statistics()
        print(f"Today's setups (Central Time): {stats.get('today_setups', 0)}")
        print(f"Today's active setups: {stats.get('today_active_setups', 0)}")
        
        # Test audit anomalies
        audit_data = store.get_audit_anomalies()
        print(f"Today's setups count (audit): {audit_data.get('today_setups_count', 0)}")
        print(f"Weekend setups: {audit_data.get('weekend_count', 0)}")
        print(f"Audit timestamp: {audit_data.get('audit_timestamp')}")
        
        return stats, audit_data
        
    except Exception as e:
        logger.error(f"Error testing audit logic: {e}")
        return None, None

def analyze_database_timezone_consistency():
    """Analyze database records for timezone consistency."""
    print("\n=== Analyzing Database Timezone Consistency ===")
    
    try:
        from features.parsing.store import get_parsing_store
        from features.parsing.models import TradeSetup
        
        store = get_parsing_store()
        
        # Get recent setups to analyze
        recent_setups = store.session.query(TradeSetup).filter(
            TradeSetup.active == True
        ).order_by(TradeSetup.created_at.desc()).limit(10).all()
        
        print(f"Analyzing {len(recent_setups)} recent setups:")
        
        for setup in recent_setups:
            if setup.created_at and setup.trading_day:
                # Convert UTC timestamp to Central date
                central_date_from_timestamp = get_central_trading_day(setup.created_at)
                
                print(f"Setup {setup.id}:")
                print(f"  Created (UTC): {setup.created_at}")
                print(f"  Trading Day (stored): {setup.trading_day}")
                print(f"  Central Date from timestamp: {central_date_from_timestamp}")
                print(f"  Consistent: {setup.trading_day == central_date_from_timestamp}")
                print()
        
        return recent_setups
        
    except Exception as e:
        logger.error(f"Error analyzing database consistency: {e}")
        return []

def main():
    """Run all tests."""
    print("Testing Central Time Trading Day Logic Fix")
    print("=" * 50)
    
    # Test timezone utilities
    central_date = test_timezone_utilities()
    
    # Test audit logic
    stats, audit_data = test_audit_logic()
    
    # Analyze database consistency
    recent_setups = analyze_database_timezone_consistency()
    
    print("\n=== Summary ===")
    print(f"Central Trading Date: {central_date}")
    if stats:
        print(f"Today's Setup Count: {stats.get('today_setups', 0)}")
    if audit_data:
        print(f"Audit Today's Count: {audit_data.get('today_setups_count', 0)}")
    
    print("\nTimezone fix implementation complete!")

if __name__ == "__main__":
    main()
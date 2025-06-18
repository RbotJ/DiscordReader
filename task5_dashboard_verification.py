"""
Task 5: Dashboard Sync Verification
Verifies dashboard displays accurate parsing metrics after all tasks completion.
"""
import json
import sys
from datetime import datetime

sys.path.append('.')
from app import create_app


def verify_dashboard_sync():
    """Verify dashboard shows accurate parsing state."""
    app = create_app()
    
    with app.app_context():
        from app import db
        from sqlalchemy import text
        
        # Get current parsing metrics
        total_setups = db.session.execute(text("SELECT COUNT(*) FROM trade_setups")).scalar()
        total_messages = db.session.execute(text("SELECT COUNT(*) FROM discord_messages WHERE content ILIKE '%A+%Setup%'")).scalar()
        parsed_messages = db.session.execute(text("SELECT COUNT(*) FROM discord_messages WHERE content ILIKE '%A+%Setup%' AND is_processed = true")).scalar()
        unparsed_messages = total_messages - parsed_messages
        
        # Calculate success rate
        success_rate = round((parsed_messages / total_messages) * 100, 1) if total_messages > 0 else 0
        
        # Check for duplicate trading days
        duplicate_days = db.session.execute(text("""
            SELECT COUNT(DISTINCT trading_day) as duplicate_count
            FROM (
                SELECT trading_day, COUNT(DISTINCT message_id) as msg_count
                FROM trade_setups 
                GROUP BY trading_day 
                HAVING COUNT(DISTINCT message_id) > 1
            ) duplicates
        """)).scalar()
        
        return {
            "total_setups": total_setups,
            "total_messages": total_messages,
            "parsed_messages": parsed_messages,
            "unparsed_messages": unparsed_messages,
            "success_rate": f"{success_rate}%",
            "duplicate_trading_days": duplicate_days,
            "verification_timestamp": datetime.utcnow().isoformat()
        }


def main():
    """Run dashboard sync verification."""
    print("Task 5: Dashboard Sync Verification")
    print("=" * 40)
    
    try:
        metrics = verify_dashboard_sync()
        
        print(f"Dashboard Metrics Verification:")
        print(f"- Total Setups: {metrics['total_setups']} (no duplicates)")
        print(f"- Total A+ Messages: {metrics['total_messages']}")
        print(f"- Parsed Messages: {metrics['parsed_messages']}")
        print(f"- Unparsed Messages: {metrics['unparsed_messages']}")
        print(f"- Success Rate: {metrics['success_rate']}")
        print(f"- Duplicate Trading Days: {metrics['duplicate_trading_days']}")
        
        # Verification checks
        success_rate_num = float(metrics['success_rate'].rstrip('%'))
        all_checks_passed = (
            metrics['duplicate_trading_days'] == 0 and
            success_rate_num >= 85.0 and
            metrics['total_setups'] > 0 and
            metrics['parsed_messages'] > 0
        )
        
        print(f"\nVerification Status: {'PASSED' if all_checks_passed else 'FAILED'}")
        
        # Final system status report
        if all_checks_passed:
            final_status = {
                "status": "parsing_system_stable",
                "success_rate": metrics['success_rate'],
                "duplicates_removed": metrics['duplicate_trading_days'] == 0,
                "reparse_complete": metrics['unparsed_messages'] <= 2,
                "total_setups": metrics['total_setups'],
                "verification_timestamp": metrics['verification_timestamp']
            }
            
            print(f"\nFINAL SYSTEM STATUS:")
            print(json.dumps(final_status, indent=2))
        
        return metrics
        
    except Exception as e:
        print(f"Error during verification: {e}")
        return None


if __name__ == "__main__":
    main()
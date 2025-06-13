#!/usr/bin/env python3
"""
Parsing Duplicate Cleanup Script

This script provides tools to analyze and clean up duplicate trade setups
that may have been created due to re-processing of Discord messages.
"""

import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from features.parsing.store import ParsingStore

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_duplicates():
    """Analyze duplicate trade setups without making changes."""
    app = create_app()
    
    with app.app_context():
        store = ParsingStore()
        
        logger.info("Analyzing duplicate trade setups...")
        
        # Get comprehensive statistics
        stats = store.get_parsing_statistics()
        
        print("\n" + "="*60)
        print("PARSING EFFECTIVENESS ANALYSIS")
        print("="*60)
        
        print(f"Total Discord Messages: {stats.get('total_discord_messages', 0)}")
        print(f"Messages with Setups: {stats.get('unique_parsed_messages', 0)}")
        print(f"Processing Rate: {stats.get('processing_rate', 0)}%")
        
        print(f"\nTotal Trade Setups: {stats.get('total_setups', 0)}")
        print(f"Active Setups: {stats.get('active_setups', 0)}")
        print(f"Duplicate Groups: {stats.get('duplicate_count', 0)}")
        
        if stats.get('duplicate_count', 0) > 0:
            print(f"\n⚠️  Duplicates detected: {stats['duplicate_count']} groups")
        else:
            print(f"\n✅ No duplicates found")
        
        print("\nTrading Day Distribution:")
        for day_info in stats.get('trading_day_distribution', []):
            print(f"  {day_info['trading_day']}: {day_info['setup_count']} setups")
        
        # Analyze duplicates in detail
        cleanup_preview = store.cleanup_duplicate_setups(dry_run=True)
        
        if cleanup_preview.get('duplicate_groups_found', 0) > 0:
            print(f"\n" + "="*60)
            print("DUPLICATE ANALYSIS")
            print("="*60)
            print(f"Duplicate Groups Found: {cleanup_preview['duplicate_groups_found']}")
            print(f"Total Duplicates to Remove: {cleanup_preview['total_duplicates_to_remove']}")
            
            print("\nTop Duplicate Groups:")
            for i, group in enumerate(cleanup_preview.get('groups', [])[:5]):
                print(f"  {i+1}. Message {group['message_id'][:12]}... | {group['ticker']} | {group['trading_day']} | {group['duplicate_count']} copies")
        
        return cleanup_preview


def cleanup_duplicates(confirm=False):
    """Clean up duplicate trade setups."""
    if not confirm:
        print("This will permanently delete duplicate trade setups.")
        print("Run with --confirm to proceed.")
        return False
    
    store = ParsingStore()
    
    logger.info("Starting duplicate cleanup...")
    
    # Perform cleanup
    result = store.cleanup_duplicate_setups(dry_run=False)
    
    if result.get('success', False):
        print(f"\n✅ Cleanup completed successfully!")
        print(f"   Groups processed: {result['duplicate_groups_processed']}")
        print(f"   Setups removed: {result['setups_removed']}")
        
        # Show updated stats
        print("\nUpdated statistics:")
        stats = store.get_parsing_statistics()
        print(f"   Total setups: {stats.get('total_setups', 0)}")
        print(f"   Duplicate groups: {stats.get('duplicate_count', 0)}")
        
    else:
        print(f"\n❌ Cleanup failed: {result.get('error', 'Unknown error')}")
        return False
    
    return True


def add_database_constraints():
    """Add database constraints to prevent future duplicates."""
    try:
        from common.db import db
        
        # Check if constraint already exists
        constraint_check = db.session.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'trade_setups' 
            AND constraint_type = 'UNIQUE'
            AND constraint_name LIKE '%unique%'
        """).fetchall()
        
        if constraint_check:
            print("✅ Unique constraints already exist on trade_setups table")
            return True
        
        # Add partial unique index for non-null trading_day values
        db.session.execute("""
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_setup_message_ticker_day 
            ON trade_setups (message_id, ticker, trading_day, profile_name) 
            WHERE trading_day IS NOT NULL AND profile_name IS NOT NULL
        """)
        
        # Add simpler constraint for cases without profile_name
        db.session.execute("""
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_setup_message_ticker_day_simple
            ON trade_setups (message_id, ticker, trading_day, setup_type) 
            WHERE trading_day IS NOT NULL AND profile_name IS NULL
        """)
        
        db.session.commit()
        print("✅ Added database constraints to prevent future duplicates")
        return True
        
    except Exception as e:
        logger.error(f"Error adding database constraints: {e}")
        db.session.rollback()
        return False


def main():
    """Main script execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage parsing duplicate cleanup')
    parser.add_argument('action', choices=['analyze', 'cleanup', 'constraints'], 
                       help='Action to perform')
    parser.add_argument('--confirm', action='store_true',
                       help='Confirm destructive operations')
    
    args = parser.parse_args()
    
    try:
        if args.action == 'analyze':
            analyze_duplicates()
            
        elif args.action == 'cleanup':
            cleanup_duplicates(confirm=args.confirm)
            
        elif args.action == 'constraints':
            add_database_constraints()
            
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
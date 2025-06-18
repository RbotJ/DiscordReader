"""
Clean Existing Duplicate Setups

Removes duplicate trade setups from the database, keeping only the most recent 
created_at for each (ticker, trigger_level) pair as specified in Task 2.
"""

import logging
from datetime import datetime
from features.parsing.models import TradeSetup
from features.parsing.store import get_parsing_store
from app import create_app

def clean_duplicate_setups():
    """
    Clean existing duplicates from trade_setups table.
    Keep the most recent created_at for each (ticker, trigger_level) pair.
    """
    
    app = create_app()
    with app.app_context():
        store = get_parsing_store()
        
        print("🧹 Starting duplicate setup cleanup...")
        
        # Get all setups grouped by (ticker, trigger_level)
        from sqlalchemy import text
        from app import db
        
        # Find duplicates using SQL query
        duplicate_query = text("""
            SELECT ticker, trigger_level, COUNT(*) as count
            FROM trade_setups 
            GROUP BY ticker, trigger_level 
            HAVING COUNT(*) > 1
            ORDER BY ticker, trigger_level
        """)
        
        duplicate_groups = db.session.execute(duplicate_query).fetchall()
        
        print(f"Found {len(duplicate_groups)} duplicate groups:")
        
        total_deleted = 0
        
        for group in duplicate_groups:
            ticker = group.ticker
            trigger_level = float(group.trigger_level)
            count = group.count
            
            print(f"  Processing {ticker} @ {trigger_level} ({count} duplicates)")
            
            # Get all setups for this ticker/trigger_level, ordered by created_at DESC
            setups = db.session.query(TradeSetup).filter(
                TradeSetup.ticker == ticker,
                TradeSetup.trigger_level == trigger_level
            ).order_by(TradeSetup.created_at.desc()).all()
            
            if len(setups) > 1:
                # Keep the first (most recent), delete the rest
                keep_setup = setups[0]
                delete_setups = setups[1:]
                
                print(f"    Keeping: ID {keep_setup.id} (created: {keep_setup.created_at})")
                
                for setup_to_delete in delete_setups:
                    print(f"    Deleting: ID {setup_to_delete.id} (created: {setup_to_delete.created_at})")
                    db.session.delete(setup_to_delete)
                    total_deleted += 1
        
        # Commit all deletions
        if total_deleted > 0:
            db.session.commit()
            print(f"\n✅ Cleanup complete: {total_deleted} duplicate setups removed")
            
            # Log the cleanup action
            logging.info(f'{{"action": "duplicate_cleanup_completed", "total_deleted": {total_deleted}, "timestamp": "{datetime.utcnow().isoformat()}"}}')
        else:
            print("\n✅ No duplicates found to clean")
        
        # Verify cleanup by checking for remaining duplicates
        remaining_duplicates = db.session.execute(duplicate_query).fetchall()
        if remaining_duplicates:
            print(f"⚠️ Warning: {len(remaining_duplicates)} duplicate groups still remain")
            for group in remaining_duplicates:
                print(f"  {group.ticker} @ {group.trigger_level} ({group.count} duplicates)")
        else:
            print("✅ Verification: No duplicate groups remaining")

def analyze_current_duplicates():
    """Analyze current duplicate patterns in the database."""
    
    app = create_app()
    with app.app_context():
        from sqlalchemy import text
        from app import db
        
        print("📊 Analyzing current duplicate patterns...")
        
        # Get duplicate statistics
        stats_query = text("""
            SELECT 
                COUNT(*) as total_setups,
                COUNT(DISTINCT CONCAT(ticker, '|', trigger_level)) as unique_combinations,
                COUNT(*) - COUNT(DISTINCT CONCAT(ticker, '|', trigger_level)) as total_duplicates
            FROM trade_setups
        """)
        
        stats = db.session.execute(stats_query).fetchone()
        
        print(f"Total setups: {stats.total_setups}")
        print(f"Unique (ticker, trigger_level) combinations: {stats.unique_combinations}")
        print(f"Total duplicates: {stats.total_duplicates}")
        
        # Get top duplicate patterns
        top_duplicates_query = text("""
            SELECT ticker, trigger_level, COUNT(*) as count, 
                   MIN(created_at) as first_created, 
                   MAX(created_at) as last_created
            FROM trade_setups 
            GROUP BY ticker, trigger_level 
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC, ticker
            LIMIT 10
        """)
        
        top_duplicates = db.session.execute(top_duplicates_query).fetchall()
        
        if top_duplicates:
            print(f"\nTop {len(top_duplicates)} duplicate patterns:")
            for dup in top_duplicates:
                print(f"  {dup.ticker} @ {dup.trigger_level}: {dup.count} copies")
                print(f"    First: {dup.first_created}, Last: {dup.last_created}")

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # First analyze the current state
    analyze_current_duplicates()
    
    print("\n" + "="*60)
    
    # Perform cleanup
    clean_duplicate_setups()
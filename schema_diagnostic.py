#!/usr/bin/env python3
"""
ParsedLevel Creation and Schema Consistency Diagnostic
"""

import os
import sys
from sqlalchemy import inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from common.db import db
from features.parsing.models import ParsedLevel, TradeSetup

def run_schema_diagnostic():
    """Run ParsedLevel schema and creation diagnostic."""
    
    with app.app_context():
        print("=== ParsedLevel Table Diagnostic ===")

        # Check if critical columns exist
        inspector = inspect(db.session.bind)
        columns = [col['name'] for col in inspector.get_columns('parsed_levels')]
        expected = ['id', 'setup_id', 'price', 'level_type', 'active', 'triggered', 'confidence_score']

        missing = [col for col in expected if col not in columns]
        print(f"Missing columns: {missing if missing else 'None — All columns present'}")
        print(f"Existing columns: {columns}")

        # Count parsed levels
        level_count = db.session.query(ParsedLevel).count()
        print(f"Parsed Levels Count: {level_count}")

        # Count trade setups
        setup_count = db.session.query(TradeSetup).count()
        print(f"Trade Setups Count: {setup_count}")

        # Cross-check setups without levels
        try:
            orphan_setups = db.session.query(TradeSetup).outerjoin(
                ParsedLevel, TradeSetup.id == ParsedLevel.setup_id
            ).filter(ParsedLevel.id == None).count()
            print(f"Setups without levels: {orphan_setups}")
        except Exception as e:
            print(f"Error checking orphan setups: {e}")

        # Example: Show recent setup-level pairs
        try:
            from sqlalchemy import text
            recent_pairs = db.session.execute(text("""
                SELECT ts.id AS setup_id, ts.label, pl.level_type, COALESCE(pl.trigger_price, pl.target_1) as price
                FROM trade_setups ts
                LEFT JOIN parsed_levels pl ON ts.id = pl.setup_id
                ORDER BY ts.created_at DESC
                LIMIT 10
            """)).fetchall()
            
            print("\nRecent setup/level pairs:")
            for row in recent_pairs:
                print(f"  Setup {row[0]}: {row[1]} | Level: {row[2]} | Price: {row[3]}")
                
        except Exception as e:
            print(f"Error querying setup/level pairs: {e}")

        # Check model field expectations vs reality
        print("\n=== Model vs Database Schema Analysis ===")
        try:
            # Get the ParsedLevel model's expected columns
            model_columns = [column.name for column in ParsedLevel.__table__.columns]
            print(f"Model expects: {model_columns}")
            print(f"Database has: {columns}")
            
            schema_mismatch = set(model_columns) - set(columns)
            extra_in_db = set(columns) - set(model_columns)
            
            print(f"Missing in DB: {list(schema_mismatch) if schema_mismatch else 'None'}")
            print(f"Extra in DB: {list(extra_in_db) if extra_in_db else 'None'}")
            
        except Exception as e:
            print(f"Error analyzing model schema: {e}")

if __name__ == "__main__":
    run_schema_diagnostic()
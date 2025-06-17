#!/usr/bin/env python3
"""
Parsing Service Dashboard UI Assessment
Diagnostic script to check each UI element's data source, verify correctness, and identify disconnects.
"""

import os
import sys
from datetime import date
from sqlalchemy import func, text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from features.parsing.service import get_parsing_service
from common.db import db
from features.ingestion.models import DiscordMessageModel
from features.parsing.models import TradeSetup, ParsedLevel

def run_diagnostic():
    """Run comprehensive diagnostic of parsing dashboard metrics."""
    
    with app.app_context():
        print("=== UI Diagnostic for Parsing Service Dashboard ===")
        print()

        # 1. Messages Processed
        try:
            processed_messages = db.session.query(DiscordMessageModel).filter_by(is_processed=True).count()
            print(f"Messages Processed: {processed_messages}")
        except Exception as e:
            print(f"Messages Processed: ERROR - {e}")

        # 2. Active Setups
        try:
            active_setups = db.session.query(TradeSetup).filter_by(active=True).count()
            print(f"Active Setups: {active_setups}")
        except Exception as e:
            print(f"Active Setups: ERROR - {e}")

        # 3. Total Levels
        try:
            total_levels = db.session.query(ParsedLevel).count()
            print(f"Total Levels: {total_levels}")
        except Exception as e:
            print(f"Total Levels: ERROR - {e}")

        # 4. Weekend Setups
        try:
            weekend_setups = db.session.query(TradeSetup).filter(
                func.extract('dow', TradeSetup.trading_day).in_([0, 6])
            ).count()
            print(f"Weekend Setups (Sat/Sun): {weekend_setups}")
        except Exception as e:
            print(f"Weekend Setups: ERROR - {e}")

        # 5. Today's Date Setups
        try:
            today = date.today()
            todays_setups = db.session.query(TradeSetup).filter_by(trading_day=today).count()
            print(f"Today's Date Setups ({today}): {todays_setups}")
        except Exception as e:
            print(f"Today's Date Setups: ERROR - {e}")

        # 6. High Volume Messages
        try:
            high_volume_msg_ids = db.session.query(TradeSetup.message_id).group_by(
                TradeSetup.message_id
            ).having(func.count() > 20).all()
            print(f"High Volume Messages (>20 setups): {len(high_volume_msg_ids)}")
        except Exception as e:
            print(f"High Volume Messages: ERROR - {e}")

        # 7. Distinct Trading Days
        try:
            distinct_days = db.session.query(func.count(func.distinct(TradeSetup.trading_day))).scalar()
            print(f"Distinct Trading Days: {distinct_days}")
        except Exception as e:
            print(f"Distinct Trading Days: ERROR - {e}")

        print()
        print("=== Service-Level Metrics ===")
        
        # 8. Cross-check Audit Metrics
        try:
            parsing_service = get_parsing_service()
            service_stats = parsing_service.get_service_stats()
            
            print(f"Service Status: {service_stats.get('service_status', 'unknown')}")
            
            if 'parsing_stats' in service_stats:
                parsing_stats = service_stats['parsing_stats']
                print(f"Service Total Setups: {parsing_stats.get('total_setups', 'N/A')}")
                print(f"Service Active Setups: {parsing_stats.get('active_setups', 'N/A')}")
                print(f"Service Total Levels: {parsing_stats.get('total_levels', 'N/A')}")
                print(f"Service Processing Rate: {parsing_stats.get('processing_rate', 'N/A')}%")
                print(f"Service Today Setups: {parsing_stats.get('today_setups', 'N/A')}")
                print(f"Service Today Active: {parsing_stats.get('today_active_setups', 'N/A')}")
            else:
                print("Service parsing_stats: NOT AVAILABLE")
                
        except Exception as e:
            print(f"Service Stats: ERROR - {e}")

        print()
        print("=== Database Table Status ===")
        
        # Check table existence and row counts
        try:
            discord_msg_count = db.session.query(DiscordMessageModel).count()
            print(f"Discord Messages Total: {discord_msg_count}")
        except Exception as e:
            print(f"Discord Messages Total: ERROR - {e}")
            
        try:
            trade_setup_count = db.session.query(TradeSetup).count()
            print(f"Trade Setups Total: {trade_setup_count}")
        except Exception as e:
            print(f"Trade Setups Total: ERROR - {e}")
            
        try:
            parsed_level_count = db.session.query(ParsedLevel).count()
            print(f"Parsed Levels Total: {parsed_level_count}")
        except Exception as e:
            print(f"Parsed Levels Total: ERROR - {e}")

        print()
        print("=== Audit Anomalies Check ===")
        
        # Check audit anomalies
        try:
            from features.parsing.store import get_parsing_store
            store = get_parsing_store()
            audit_data = store.get_audit_anomalies()
            
            print(f"Weekend Setup Count: {audit_data.get('weekend_setup_count', 'N/A')}")
            print(f"Today Setup Count: {audit_data.get('today_setup_count', 'N/A')}")
            print(f"Suspicious Messages: {len(audit_data.get('suspicious_messages', []))}")
            
            if audit_data.get('weekend_setups'):
                print("Weekend Setup Details:")
                for setup in audit_data['weekend_setups'][:3]:  # Show first 3
                    print(f"  - {setup['ticker']} on {setup['trading_day']} ({setup['weekday']})")
                    
        except Exception as e:
            print(f"Audit Anomalies: ERROR - {e}")

        print()
        print("=== Raw Database Queries ===")
        
        # Raw queries for verification
        try:
            # Messages with is_processed flag
            processed_count = db.session.execute(text(
                "SELECT COUNT(*) FROM discord_messages WHERE is_processed = true"
            )).scalar()
            print(f"DB: Messages with is_processed=true: {processed_count}")
            
            unprocessed_count = db.session.execute(text(
                "SELECT COUNT(*) FROM discord_messages WHERE is_processed = false OR is_processed IS NULL"
            )).scalar()
            print(f"DB: Messages with is_processed=false/null: {unprocessed_count}")
            
        except Exception as e:
            print(f"Raw DB queries: ERROR - {e}")

        print()
        print("✅ UI Diagnostic Complete")
        print("Use this data to confirm dashboard metrics match the underlying data.")

if __name__ == "__main__":
    run_diagnostic()
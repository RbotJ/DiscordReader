#!/usr/bin/env python3
"""
Simple Gap Investigation

Direct database queries to understand the parsing gap.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from common.db import db
from app import app
from sqlalchemy import text

def investigate_parsing_gap():
    """Investigate the parsing gap with direct database queries."""
    print("Direct Database Investigation")
    print("=" * 50)
    
    with app.app_context():
        # Query Discord messages directly
        discord_result = db.session.execute(text("""
            SELECT COUNT(*) as total_messages,
                   COUNT(CASE WHEN content LIKE '%A+ %Setup%' THEN 1 END) as aplus_messages
            FROM discord_messages
        """)).fetchone()
        
        print(f"Total Discord messages: {discord_result.total_messages}")
        print(f"A+ messages (rough): {discord_result.aplus_messages}")
        
        # Query parsed setups
        setup_result = db.session.execute(text("""
            SELECT COUNT(DISTINCT message_id) as unique_messages,
                   COUNT(*) as total_setups,
                   COUNT(DISTINCT trading_day) as unique_days
            FROM trade_setups
        """)).fetchone()
        
        print(f"Unique parsed messages: {setup_result.unique_messages}")
        print(f"Total trade setups: {setup_result.total_setups}")
        print(f"Unique trading days: {setup_result.unique_days}")
        
        # Show gap
        gap = discord_result.total_messages - setup_result.unique_messages
        print(f"\nGap: {gap} messages not parsed")
        
        # Check specific A+ messages
        aplus_messages = db.session.execute(text("""
            SELECT id, LEFT(content, 50) as preview, 
                   CASE WHEN id IN (SELECT DISTINCT message_id FROM trade_setups) 
                        THEN 'PARSED' ELSE 'UNPARSED' END as status
            FROM discord_messages 
            WHERE content LIKE '%A+%Setup%'
            ORDER BY timestamp DESC
            LIMIT 15
        """)).fetchall()
        
        print(f"\nA+ Messages Status:")
        parsed_count = 0
        unparsed_count = 0
        
        for msg in aplus_messages:
            print(f"  {msg.status}: {msg.id} - {msg.preview}...")
            if msg.status == 'PARSED':
                parsed_count += 1
            else:
                unparsed_count += 1
        
        print(f"\nSummary: {parsed_count} parsed, {unparsed_count} unparsed")
        
        # Check if backlog processing works
        print(f"\nTesting backlog processing...")
        try:
            from features.parsing.service import get_parsing_service
            service = get_parsing_service()
            
            # Try processing one unparsed message
            unparsed_messages = [msg for msg in aplus_messages if msg.status == 'UNPARSED']
            if unparsed_messages:
                test_msg_id = unparsed_messages[0].id
                print(f"Attempting to process message: {test_msg_id}")
                
                # Get the full message content
                full_msg = db.session.execute(text("""
                    SELECT id, content, timestamp FROM discord_messages WHERE id = :msg_id
                """), {"msg_id": test_msg_id}).fetchone()
                
                if full_msg:
                    message_data = {
                        'id': full_msg.id,
                        'content': full_msg.content,
                        'timestamp': full_msg.timestamp.isoformat() if full_msg.timestamp else None
                    }
                    
                    result = service.parse_message(message_data)
                    print(f"Parse result: {result.get('success', False)}")
                    if result.get('success'):
                        print(f"Setups created: {len(result.get('setups', []))}")
                    else:
                        print(f"Error: {result.get('error', 'Unknown')}")
            
        except Exception as e:
            print(f"Backlog test failed: {e}")

if __name__ == "__main__":
    investigate_parsing_gap()
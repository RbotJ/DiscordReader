#!/usr/bin/env python3
"""
Debug Parsing Gap Investigation

Systematic investigation of why only 11/22 messages are being parsed.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from features.parsing.store import get_parsing_store
from features.parsing.service import get_parsing_service
from features.parsing.aplus_parser import get_aplus_parser
from common.db import db
from app import app

def debug_unparsed_messages():
    """Check what unparsed messages are available."""
    print("=" * 60)
    print("DEBUGGING UNPARSED MESSAGES")
    print("=" * 60)
    
    with app.app_context():
        store = get_parsing_store()
        
        # Get unparsed messages
        print("1. Checking unparsed messages...")
        unparsed = store.get_unparsed_messages(limit=30)
        print(f"Found {len(unparsed)} unparsed messages:")
        
        for i, msg in enumerate(unparsed[:10], 1):  # Show first 10
            msg_id = msg.get('message_id', 'unknown')
            content_preview = (msg.get('content', '')[:50] + '...') if msg.get('content') else 'No content'
            print(f"  {i}. {msg_id}: {content_preview}")
        
        if len(unparsed) > 10:
            print(f"  ... and {len(unparsed) - 10} more")
        
        return unparsed

def debug_validation_check():
    """Check validation behavior on unparsed messages."""
    print("\n2. Checking validation behavior...")
    
    with app.app_context():
        store = get_parsing_store()
        parser = get_aplus_parser()
        
        unparsed = store.get_unparsed_messages(limit=5)  # Check first 5
        
        valid_count = 0
        for msg in unparsed:
            content = msg.get('content', '')
            if content:
                is_valid = parser.validate_message(content)
                status = "✅" if is_valid else "❌"
                print(f"  {status} {msg.get('message_id', 'unknown')}: {is_valid}")
                if is_valid:
                    valid_count += 1
        
        print(f"Validation rate: {valid_count}/{len(unparsed)} = {valid_count/len(unparsed)*100:.1f}%")
        return valid_count

def debug_parsing_process():
    """Check the parsing process for valid messages."""
    print("\n3. Checking parsing process...")
    
    with app.app_context():
        store = get_parsing_store()
        parser = get_aplus_parser()
        
        unparsed = store.get_unparsed_messages(limit=3)  # Test first 3
        
        for msg in unparsed:
            msg_id = msg.get('message_id', 'unknown')
            content = msg.get('content', '')
            
            if not content:
                print(f"  ❌ {msg_id}: No content")
                continue
                
            if not parser.validate_message(content):
                print(f"  ❌ {msg_id}: Failed validation")
                continue
            
            # Try parsing
            try:
                result = parser.parse_message(content, msg_id)
                setups = result.get('setups', [])
                print(f"  ✅ {msg_id}: Parsed {len(setups)} setups")
                
                if len(setups) == 0:
                    print(f"     ⚠️  No setups extracted despite validation pass")
                    print(f"     Content preview: {content[:100]}...")
                    
            except Exception as e:
                print(f"  ❌ {msg_id}: Parsing error - {e}")

def debug_database_state():
    """Check current database state."""
    print("\n4. Checking database state...")
    
    with app.app_context():
        store = get_parsing_store()
        
        # Check total messages vs parsed
        total_messages = store.get_total_discord_messages()
        parsed_messages = store.get_unique_parsed_messages()
        
        print(f"  Total Discord messages: {total_messages}")
        print(f"  Unique parsed messages: {parsed_messages}")
        print(f"  Gap: {total_messages - parsed_messages} messages")
        
        # Check trading days
        trading_days = store.get_available_trading_days()
        print(f"  Available trading days: {len(trading_days)}")
        for day in trading_days[:5]:  # Show first 5
            print(f"    - {day}")

def debug_duplicate_detection():
    """Check if duplicate detection is interfering."""
    print("\n5. Checking duplicate detection impact...")
    
    with app.app_context():
        try:
            from features.parsing.duplicate_detector import get_duplicate_detector
            detector = get_duplicate_detector()
            
            with db.session() as session:
                stats = detector.get_duplicate_statistics(session)
                print(f"  Duplicate policy: {stats.get('current_policy', 'unknown')}")
                print(f"  Duplicate trading days: {stats.get('duplicate_trading_days', 0)}")
                
                duplicate_days = stats.get('duplicate_days_list', [])
                if duplicate_days:
                    print(f"  Duplicate days sample: {duplicate_days[:3]}")
                    
        except Exception as e:
            print(f"  ❌ Duplicate detection check failed: {e}")

def main():
    """Run comprehensive debugging."""
    print("Starting comprehensive parsing gap investigation...")
    
    try:
        unparsed = debug_unparsed_messages()
        if len(unparsed) == 0:
            print("\n🎉 No unparsed messages found - gap may be resolved!")
            return
            
        valid_count = debug_validation_check()
        if valid_count == 0:
            print("\n⚠️  No messages pass validation - validation logic issue")
            return
            
        debug_parsing_process()
        debug_database_state() 
        debug_duplicate_detection()
        
        print("\n" + "=" * 60)
        print("INVESTIGATION COMPLETE")
        print("=" * 60)
        print("Next steps based on findings above:")
        print("- Check validation logic if many messages fail validation")
        print("- Check parsing logic if validation passes but no setups extracted")
        print("- Check duplicate detection if policy is too aggressive")
        
    except Exception as e:
        print(f"\n❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
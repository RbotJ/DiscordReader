#!/usr/bin/env python3
"""
Process Remaining Unparsed Messages

Direct processing of the 11 unparsed A+ messages to close the parsing gap.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from features.parsing.store import get_parsing_store
from features.parsing.service import get_parsing_service
from app import app

def process_unparsed_messages():
    """Process all unparsed messages directly."""
    print("Processing Remaining Unparsed Messages")
    print("=" * 50)
    
    with app.app_context():
        store = get_parsing_store()
        service = get_parsing_service()
        
        # Get unparsed messages
        unparsed = store.get_unparsed_messages(limit=20)
        print(f"Found {len(unparsed)} unparsed messages")
        
        if len(unparsed) == 0:
            print("✅ No unparsed messages found - gap already resolved!")
            return
        
        successful = 0
        failed = 0
        
        for i, msg in enumerate(unparsed, 1):
            msg_id = msg.get('message_id', 'unknown')
            content = msg.get('content', '')
            
            print(f"\n{i}/{len(unparsed)}: Processing {msg_id}")
            
            if not content:
                print(f"  ❌ No content")
                failed += 1
                continue
            
            try:
                # Create message data structure
                message_data = {
                    'id': msg_id,
                    'content': content,
                    'timestamp': msg.get('timestamp'),
                    'channel_id': msg.get('channel_id'),
                    'author_id': msg.get('author_id')
                }
                
                # Process through service
                result = service.parse_message(message_data)
                
                if result and result.get('success'):
                    setups_count = len(result.get('setups', []))
                    print(f"  ✅ Success: {setups_count} setups created")
                    successful += 1
                else:
                    error = result.get('error', 'Unknown error') if result else 'Service returned None'
                    print(f"  ❌ Failed: {error}")
                    failed += 1
                    
            except Exception as e:
                print(f"  ❌ Exception: {e}")
                failed += 1
        
        print(f"\n" + "=" * 50)
        print(f"PROCESSING COMPLETE")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total processed: {successful + failed}")
        
        if successful > 0:
            print(f"\n✅ Successfully processed {successful} messages!")
            print("The parsing gap should now be resolved.")
        
        if failed > 0:
            print(f"\n⚠️  {failed} messages failed to process.")
            print("These may need manual investigation.")

if __name__ == "__main__":
    process_unparsed_messages()
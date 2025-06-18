"""
Force Re-Parse of Remaining Valid Messages

Reprocesses unparsed A+ messages and ensures proper tracking of processing status.
Only marks is_processed = true when at least one valid TradeSetup is created.
Stores failure reasons in failure_tracker for failed parsing attempts.
"""

import logging
from datetime import datetime
from features.parsing.aplus_parser import get_aplus_parser
from features.parsing.service import ParsingService
from features.parsing.store import get_parsing_store
from features.parsing.failure_tracker import record_parsing_failure, FailureReason
from features.parsing.models import TradeSetup
from app import create_app

def query_unparsed_aplus_messages():
    """Query discord_messages for unparsed A+ messages."""
    
    from app import db
    from sqlalchemy import text
    
    # Query for unparsed A+ messages
    query = text("""
        SELECT id, content, timestamp, channel_id, is_processed
        FROM discord_messages 
        WHERE content ILIKE '%A+%Setup%' 
        AND is_processed = false
        ORDER BY timestamp DESC
    """)
    
    results = db.session.execute(query).fetchall()
    return results

def force_reparse_message(message_id, content, timestamp, channel_id, parser, service, store):
    """
    Force re-parse a single message with comprehensive logging and status tracking.
    
    Returns:
        dict: Results of the parsing attempt with status and metrics
    """
    
    print(f"  Processing message {message_id}")
    print(f"    Timestamp: {timestamp}")
    print(f"    Content preview: {content[:100]}...")
    
    # Validate message first
    if not parser.validate_message(content, message_id):
        failure_reason = "validation_failed"
        print(f"    ❌ Validation failed")
        
        # Store failure reason
        record_parsing_failure(message_id, FailureReason.HEADER_INVALID, content, "Message failed A+ validation")
        
        return {
            'success': False,
            'message_id': message_id,
            'failure_reason': failure_reason,
            'setups_created': 0
        }
    
    # Parse the message
    try:
        parse_result = parser.parse_message(content, message_id, timestamp)
        
        if not parse_result['success']:
            failure_reason = parse_result.get('error', 'unknown_parse_error')
            print(f"    ❌ Parsing failed: {failure_reason}")
            
            # Store failure reason
            record_parsing_failure(message_id, FailureReason.UNKNOWN_ERROR, content, f"Parse error: {failure_reason}")
            
            return {
                'success': False,
                'message_id': message_id,
                'failure_reason': failure_reason,
                'setups_created': 0
            }
        
        # Extract setups for storage
        setups = parse_result.get('setups', [])
        trading_date = parse_result.get('trading_date')
        
        if not setups:
            failure_reason = "no_setups_extracted"
            print(f"    ⚠️  No setups extracted from message")
            
            # Store failure reason
            record_parsing_failure(message_id, FailureReason.NO_TICKER_SECTIONS, content, "No trade setups found in parsed content")
            
            return {
                'success': False,
                'message_id': message_id,
                'failure_reason': failure_reason,
                'setups_created': 0
            }
        
        # Store setups using the store's correct method
        try:
            created_setups, created_levels = store.store_parsed_message(
                message_id=message_id,
                parsed_setups=setups,  # TradeSetup dataclass instances
                trading_day=trading_date,
                ticker_bias_notes=parse_result.get('ticker_bias_notes', {})
            )
            storage_result = {
                'success': True,
                'setups_stored': len(created_setups),
                'levels_created': len(created_levels)
            }
        except Exception as store_error:
            storage_result = {
                'success': False,
                'error': str(store_error)
            }
        
        if storage_result['success']:
            setups_created = storage_result.get('setups_stored', len(setups))
            
            # Mark message as processed only when setups are successfully created
            from app import db
            from sqlalchemy import text
            db.session.execute(
                text("UPDATE discord_messages SET is_processed = true WHERE id = :message_id"),
                {"message_id": message_id}
            )
            db.session.commit()
            
            print(f"    ✅ Success: {setups_created} setups created, message marked as processed")
            
            return {
                'success': True,
                'message_id': message_id,
                'setups_created': setups_created,
                'duplicates_skipped': parse_result.get('duplicates_skipped', 0),
                'trading_date': str(trading_date)
            }
        else:
            failure_reason = storage_result.get('error', 'storage_failed')
            print(f"    ❌ Storage failed: {failure_reason}")
            
            # Store failure reason
            record_parsing_failure(message_id, FailureReason.UNKNOWN_ERROR, content, f"Storage error: {failure_reason}")
            
            return {
                'success': False,
                'message_id': message_id,
                'failure_reason': failure_reason,
                'setups_created': 0
            }
    
    except Exception as e:
        failure_reason = f"exception_during_parsing"
        error_msg = str(e)
        print(f"    ❌ Exception during parsing: {error_msg}")
        
        # Store failure reason
        record_parsing_failure(message_id, FailureReason.UNKNOWN_ERROR, content, f"Exception: {error_msg}")
        
        return {
            'success': False,
            'message_id': message_id,
            'failure_reason': failure_reason,
            'error': error_msg,
            'setups_created': 0
        }

def main():
    """Main function to force re-parse remaining valid A+ messages."""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    app = create_app()
    with app.app_context():
        from app import db
        from sqlalchemy import text
        
        print("🔄 Force Re-Parse of Remaining Valid A+ Messages")
        print("=" * 60)
        
        # Query unparsed A+ messages
        unparsed_messages = query_unparsed_aplus_messages()
        
        print(f"Found {len(unparsed_messages)} unparsed A+ messages")
        
        if not unparsed_messages:
            print("✅ No unparsed A+ messages found - all messages have been processed")
            return
        
        # Initialize components
        parser = get_aplus_parser()
        service = ParsingService()
        store = get_parsing_store()
        
        # Process each message
        results = {
            'successful': [],
            'failed': [],
            'total_setups_created': 0,
            'total_duplicates_skipped': 0
        }
        
        print(f"\nProcessing {len(unparsed_messages)} messages:")
        
        for i, message in enumerate(unparsed_messages, 1):
            message_id = message.id
            content = message.content
            timestamp = message.timestamp
            channel_id = message.channel_id
            
            print(f"\n[{i}/{len(unparsed_messages)}] Message {message_id}")
            
            result = force_reparse_message(
                message_id, content, timestamp, channel_id,
                parser, service, store
            )
            
            if result['success']:
                results['successful'].append(result)
                results['total_setups_created'] += result['setups_created']
                results['total_duplicates_skipped'] += result.get('duplicates_skipped', 0)
            else:
                results['failed'].append(result)
        
        # Summary
        print(f"\n📊 Force Re-Parse Summary:")
        print(f"  Total messages processed: {len(unparsed_messages)}")
        print(f"  Successful: {len(results['successful'])}")
        print(f"  Failed: {len(results['failed'])}")
        print(f"  Total setups created: {results['total_setups_created']}")
        print(f"  Total duplicates skipped: {results['total_duplicates_skipped']}")
        
        if results['successful']:
            print(f"\n✅ Successfully processed messages:")
            for result in results['successful']:
                print(f"    {result['message_id']}: {result['setups_created']} setups")
        
        if results['failed']:
            print(f"\n❌ Failed messages with reasons:")
            for result in results['failed']:
                reason = result.get('failure_reason', 'unknown')
                print(f"    {result['message_id']}: {reason}")
        
        # Verify final state
        remaining_unparsed = query_unparsed_aplus_messages()
        print(f"\n🔍 Verification: {len(remaining_unparsed)} unparsed A+ messages remaining")
        
        # Log completion
        logger.info(f'{{"action": "force_reparse_completed", "total_processed": {len(unparsed_messages)}, "successful": {len(results["successful"])}, "failed": {len(results["failed"])}, "setups_created": {results["total_setups_created"]}, "timestamp": "{datetime.utcnow().isoformat()}"}}')

if __name__ == "__main__":
    main()
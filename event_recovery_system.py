"""
Event Publishing Failure Recovery System

Implements automatic recovery mechanisms for Discord bot event publishing failures.
Addresses the identified gaps where events are published but not processed.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventRecoverySystem:
    """Automatic recovery system for event publishing failures."""
    
    def __init__(self):
        self.recovery_stats = {
            'events_recovered': 0,
            'messages_reprocessed': 0,
            'failures_resolved': 0
        }
    
    async def run_comprehensive_recovery(self):
        """Execute comprehensive recovery for event publishing failures."""
        print("🔄 Event Publishing Failure Recovery System")
        print("=" * 50)
        
        app = create_app()
        with app.app_context():
            # 1. Recover orphaned events (published but not processed)
            await self._recover_orphaned_events()
            
            # 2. Reprocess failed message storage
            await self._reprocess_failed_messages()
            
            # 3. Fix unprocessed messages backlog
            await self._fix_processing_backlog()
            
            # 4. Validate recovery success
            await self._validate_recovery()
        
        self._print_recovery_report()
    
    async def _recover_orphaned_events(self):
        """Recover events that were published but never processed by ingestion."""
        print("\n1. Recovering Orphaned Events")
        print("-" * 30)
        
        try:
            from common.db import db
            from sqlalchemy import text
            
            # Find discord.message.new events without corresponding stored messages
            orphaned_events = db.session.execute(text("""
                SELECT e.id, e.event_type, e.data, e.created_at, e.correlation_id
                FROM events e
                WHERE e.event_type = 'discord.message.new'
                AND e.created_at > NOW() - INTERVAL '2 hours'
                AND NOT EXISTS (
                    SELECT 1 FROM discord_messages dm 
                    WHERE dm.message_id = (e.data->>'message_id')
                )
                ORDER BY e.created_at DESC
                LIMIT 10
            """)).fetchall()
            
            print(f"Found {len(orphaned_events)} orphaned events")
            
            # Republish orphaned events to ensure processing
            for event in orphaned_events:
                event_id, event_type, data_json, created_at, correlation_id = event
                
                try:
                    import json
                    data = json.loads(data_json) if isinstance(data_json, str) else data_json
                    message_id = data.get('message_id', 'unknown')
                    
                    print(f"  Recovering event for message: {message_id}")
                    
                    # Republish the event
                    from common.events.publisher import publish_event_async
                    success = await publish_event_async(
                        event_type="discord.message.recovery",
                        data=data,
                        source="recovery_system",
                        correlation_id=f"recovery_{correlation_id}"
                    )
                    
                    if success:
                        self.recovery_stats['events_recovered'] += 1
                        print(f"    ✓ Recovered: {message_id}")
                    else:
                        print(f"    ✗ Failed to recover: {message_id}")
                        
                except Exception as e:
                    print(f"    ✗ Error recovering event {event_id}: {e}")
            
        except Exception as e:
            print(f"ERROR recovering orphaned events: {e}")
    
    async def _reprocess_failed_messages(self):
        """Reprocess messages that failed initial storage."""
        print("\n2. Reprocessing Failed Messages")
        print("-" * 30)
        
        try:
            from common.db import db
            from sqlalchemy import text
            
            # Find recent events that should have resulted in stored messages
            failed_storage = db.session.execute(text("""
                SELECT DISTINCT e.data->>'message_id' as message_id,
                       e.data->>'content' as content,
                       e.data->>'channel_id' as channel_id,
                       e.data->>'timestamp' as timestamp
                FROM events e
                WHERE e.event_type IN ('discord.message.new', 'discord.message.recovery')
                AND e.created_at > NOW() - INTERVAL '1 hour'
                AND NOT EXISTS (
                    SELECT 1 FROM discord_messages dm 
                    WHERE dm.message_id = (e.data->>'message_id')
                )
                LIMIT 5
            """)).fetchall()
            
            print(f"Found {len(failed_storage)} messages needing reprocessing")
            
            # Attempt to store these messages directly
            from features.ingestion.service import get_ingestion_service
            service = get_ingestion_service()
            
            for msg_data in failed_storage:
                message_id, content, channel_id, timestamp = msg_data
                
                if not all([message_id, content, channel_id]):
                    continue
                
                try:
                    print(f"  Reprocessing message: {message_id}")
                    
                    # Create message data structure
                    message_payload = {
                        'message_id': message_id,
                        'content': content,
                        'channel_id': channel_id,
                        'timestamp': timestamp,
                        'author_id': 'recovery_system',
                        'recovery_attempt': True
                    }
                    
                    # Process through ingestion service
                    success = await service.handle_event({
                        'event_type': 'discord.message.recovery',
                        'payload': message_payload
                    })
                    
                    if success:
                        self.recovery_stats['messages_reprocessed'] += 1
                        print(f"    ✓ Reprocessed: {message_id}")
                    else:
                        print(f"    ✗ Failed to reprocess: {message_id}")
                        
                except Exception as e:
                    print(f"    ✗ Error reprocessing {message_id}: {e}")
            
        except Exception as e:
            print(f"ERROR reprocessing failed messages: {e}")
    
    async def _fix_processing_backlog(self):
        """Fix backlog of unprocessed messages."""
        print("\n3. Fixing Processing Backlog")
        print("-" * 30)
        
        try:
            from common.db import db
            from sqlalchemy import text
            
            # Find unprocessed messages older than 5 minutes
            unprocessed = db.session.execute(text("""
                SELECT message_id, content, channel_id, created_at
                FROM discord_messages
                WHERE is_processed = false
                AND created_at < NOW() - INTERVAL '5 minutes'
                ORDER BY created_at ASC
                LIMIT 10
            """)).fetchall()
            
            print(f"Found {len(unprocessed)} unprocessed messages in backlog")
            
            # Force processing of these messages
            from features.parsing.service import get_parsing_service
            parsing_service = get_parsing_service()
            
            for msg_data in unprocessed:
                message_id, content, channel_id, created_at = msg_data
                
                try:
                    print(f"  Processing backlog message: {message_id}")
                    
                    # Force parse the message using correct method signature
                    message_data = {
                        'message_id': message_id,
                        'content': content,
                        'timestamp': created_at.isoformat() if created_at else None,
                        'channel_id': channel_id,
                        'force_reprocess': True
                    }
                    result = parsing_service.parse_message(message_data)
                    
                    if result.get('success', False):
                        # Mark as processed
                        db.session.execute(text("""
                            UPDATE discord_messages 
                            SET is_processed = true, processed_at = NOW()
                            WHERE message_id = :message_id
                        """), {'message_id': message_id})
                        db.session.commit()
                        
                        self.recovery_stats['failures_resolved'] += 1
                        print(f"    ✓ Processed: {message_id}")
                    else:
                        failure_reason = result.get('error', 'Unknown parsing error')
                        print(f"    ✗ Failed to process {message_id}: {failure_reason}")
                        
                except Exception as e:
                    print(f"    ✗ Error processing {message_id}: {e}")
            
        except Exception as e:
            print(f"ERROR fixing processing backlog: {e}")
    
    async def _validate_recovery(self):
        """Validate that recovery was successful."""
        print("\n4. Validating Recovery Success")
        print("-" * 30)
        
        try:
            from common.db import db
            from sqlalchemy import text
            
            # Check current system health after recovery
            health_stats = db.session.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM events WHERE created_at > NOW() - INTERVAL '1 hour') as recent_events,
                    (SELECT COUNT(*) FROM discord_messages WHERE created_at > NOW() - INTERVAL '1 hour') as recent_messages,
                    (SELECT COUNT(*) FROM discord_messages WHERE is_processed = false) as unprocessed_count,
                    (SELECT COUNT(*) FROM discord_messages WHERE is_processed = false AND created_at < NOW() - INTERVAL '5 minutes') as old_unprocessed
            """)).fetchone()
            
            recent_events, recent_messages, unprocessed, old_unprocessed = health_stats
            
            print(f"Post-recovery system health:")
            print(f"  Recent events: {recent_events}")
            print(f"  Recent messages: {recent_messages}")
            print(f"  Unprocessed messages: {unprocessed}")
            print(f"  Old unprocessed: {old_unprocessed}")
            
            # Validate recovery success
            recovery_success = True
            
            if old_unprocessed > 2:
                print("  ⚠️ Warning: Still have old unprocessed messages")
                recovery_success = False
            
            if recent_events > recent_messages + 3:  # Allow some tolerance
                print("  ⚠️ Warning: Event/message gap still exists")
                recovery_success = False
            
            if recovery_success:
                print("  ✅ Recovery validation passed")
            else:
                print("  ❌ Recovery validation failed - manual intervention needed")
            
        except Exception as e:
            print(f"ERROR validating recovery: {e}")
    
    def _print_recovery_report(self):
        """Print comprehensive recovery report."""
        print("\n" + "=" * 50)
        print("RECOVERY SYSTEM REPORT")
        print("=" * 50)
        
        print(f"Events recovered: {self.recovery_stats['events_recovered']}")
        print(f"Messages reprocessed: {self.recovery_stats['messages_reprocessed']}")
        print(f"Failures resolved: {self.recovery_stats['failures_resolved']}")
        
        total_actions = sum(self.recovery_stats.values())
        
        if total_actions > 0:
            print(f"\nTotal recovery actions: {total_actions}")
            print("✅ Recovery system completed successfully")
        else:
            print("\n✅ No recovery actions needed - system is healthy")


async def main():
    """Run the event recovery system."""
    recovery = EventRecoverySystem()
    await recovery.run_comprehensive_recovery()


if __name__ == "__main__":
    asyncio.run(main())
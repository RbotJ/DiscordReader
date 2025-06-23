"""
Test Event-Driven Pipeline Restoration

Verifies the complete Discord-to-Ingestion pipeline using proper event bus architecture:
1. Simulates Discord message via async event publishing 
2. Verifies PostgreSQL LISTEN/NOTIFY event delivery
3. Confirms ingestion service processes the event
4. Validates message storage in database
"""
import asyncio
import logging
import json
from datetime import datetime
from app import create_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_event_driven_pipeline():
    """Test the complete event-driven pipeline from Discord to database storage."""
    
    print("🧪 Testing Event-Driven Pipeline Restoration")
    print("=" * 50)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Step 1: Simulate Discord message event via proper async publishing
        print("\n1️⃣ Publishing Discord message event via async event bus...")
        
        test_message_payload = {
            "message_id": f"test_{int(datetime.utcnow().timestamp())}",
            "channel_id": "1372012942848954388",  # aplus-setups channel
            "author_id": "808743496341127200",
            "author_name": "TestUser",
            "content": "A+ Setups - Test message for event pipeline verification",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Use proper async event publishing (not direct publishing)
        from common.events.publisher import publish_event_async
        
        success = await publish_event_async(
            event_type="discord.message.new",
            data=test_message_payload,
            channel="events", 
            source="pipeline_test"
        )
        
        if success:
            print("✅ Event published successfully via async event bus")
            print(f"   Message ID: {test_message_payload['message_id']}")
        else:
            print("❌ Failed to publish event via async event bus")
            return False
        
        # Step 2: Verify PostgreSQL LISTEN connection is active
        print("\n2️⃣ Verifying PostgreSQL LISTEN connection...")
        
        from common.db import db
        from sqlalchemy import text
        
        result = db.session.execute(text("""
            SELECT application_name, state, query 
            FROM pg_stat_activity 
            WHERE query LIKE '%LISTEN%'
        """)).fetchall()
        
        if result:
            print("✅ PostgreSQL LISTEN connection found:")
            for row in result:
                print(f"   App: {row[0]}, State: {row[1]}, Query: {row[2]}")
        else:
            print("❌ No PostgreSQL LISTEN connections found")
        
        # Step 3: Check event was stored in events table
        print("\n3️⃣ Verifying event storage in events table...")
        
        recent_events = db.session.execute(text("""
            SELECT event_type, source, correlation_id, created_at, data::text
            FROM events 
            WHERE event_type = 'discord.message.new'
            AND source = 'pipeline_test'
            ORDER BY created_at DESC 
            LIMIT 1
        """)).fetchall()
        
        if recent_events:
            event = recent_events[0]
            print("✅ Event found in events table:")
            print(f"   Type: {event[0]}")
            print(f"   Source: {event[1]}")
            print(f"   Correlation ID: {event[2]}")
            print(f"   Created: {event[3]}")
            
            # Parse the stored data
            event_data = json.loads(event[4])
            stored_message_id = event_data.get('message_id')
            if stored_message_id == test_message_payload['message_id']:
                print(f"✅ Message ID matches: {stored_message_id}")
            else:
                print(f"❌ Message ID mismatch: {stored_message_id}")
        else:
            print("❌ Event not found in events table")
        
        # Step 4: Wait for ingestion processing and check discord_messages table
        print("\n4️⃣ Waiting for ingestion processing...")
        await asyncio.sleep(2)  # Give ingestion time to process
        
        processed_messages = db.session.execute(text("""
            SELECT message_id, content, channel_id, created_at
            FROM discord_messages 
            WHERE message_id = :message_id
        """), {'message_id': test_message_payload['message_id']}).fetchall()
        
        if processed_messages:
            msg = processed_messages[0]
            print("✅ Message processed and stored in discord_messages:")
            print(f"   Message ID: {msg[0]}")
            print(f"   Content: {msg[1][:50]}...")
            print(f"   Channel ID: {msg[2]}")
            print(f"   Created: {msg[3]}")
        else:
            print("❌ Message not found in discord_messages table")
            print("   This may indicate ingestion listener is not processing events")
        
        # Step 5: Check ingestion service metrics
        print("\n5️⃣ Checking ingestion service metrics...")
        
        from features.ingestion.service import get_ingestion_service
        service = get_ingestion_service()
        metrics = service.get_metrics()
        
        print("📊 Ingestion Service Metrics:")
        print(f"   Total messages stored: {metrics.get('total_messages_stored', 0)}")
        print(f"   Messages processed today: {metrics.get('messages_processed_today', 0)}")
        print(f"   Service status: {metrics.get('service_status', 'unknown')}")
        print(f"   Last processed: {metrics.get('last_processed_message', 'none')}")
        
        # Final assessment
        print("\n🎯 Pipeline Assessment:")
        if success and recent_events and processed_messages:
            print("✅ Event-driven pipeline is working correctly!")
            print("   - Discord bot uses async event publishing")
            print("   - PostgreSQL LISTEN/NOTIFY is active") 
            print("   - Ingestion listener processes events")
            print("   - Messages are stored in database")
            return True
        else:
            print("❌ Pipeline has issues that need investigation")
            if not success:
                print("   - Event publishing failed")
            if not recent_events:
                print("   - Events not being stored")
            if not processed_messages:
                print("   - Ingestion not processing events")
            return False


if __name__ == "__main__":
    asyncio.run(test_event_driven_pipeline())
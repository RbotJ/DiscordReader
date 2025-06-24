#!/usr/bin/env python3
"""
Comprehensive Pipeline Test Suite

Simulates various Discord message scenarios to test the complete event-driven pipeline:
- Valid messages with different formats
- Malformed payloads
- Duplicate message IDs
- Delayed/offline messages
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from uuid import uuid4

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PipelineTestSuite:
    def __init__(self):
        self.test_results = []
        self.test_message_ids = []
        
    async def test_valid_messages(self):
        """Test 3 valid Discord messages with different A+ formats."""
        logger.info("📝 Testing valid A+ messages...")
        
        valid_messages = [
            {
                "message_id": f"test_valid_1_{int(time.time())}",
                "channel_id": "1372012942848954388",
                "author_id": "808743496341127200",
                "author_name": "TestUser",
                "content": "A+ Setups - Jun 24\n\nSPY\n🔼 Aggressive Breakout 450.00 🔼 452.50, 455.00",
                "timestamp": datetime.now().isoformat()
            },
            {
                "message_id": f"test_valid_2_{int(time.time())}",
                "channel_id": "1372012942848954388", 
                "author_id": "808743496341127200",
                "author_name": "TestUser",
                "content": "A+ Scalp Trade Setups — Jun 24\n\nTSLA\n🔻 Conservative Breakdown 320.00 🔻 315.00, 310.00",
                "timestamp": datetime.now().isoformat()
            },
            {
                "message_id": f"test_valid_3_{int(time.time())}",
                "channel_id": "1372012942848954388",
                "author_id": "808743496341127200", 
                "author_name": "TestUser",
                "content": "A+ Setups – Trading Day Update\n\nNVDA\n🔄 Bounce 140.00–142.00 🔼 145.00, 148.00",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        for i, message in enumerate(valid_messages, 1):
            try:
                import sys
                sys.path.append('/home/runner/workspace')
                from common.events.direct_publisher import publish_event_direct
                
                event_id = publish_event_direct(
                    event_type="discord.message.new",
                    channel="events", 
                    payload=message,
                    source="pipeline_test"
                )
                
                self.test_message_ids.append(message["message_id"])
                self.test_results.append({
                    "test": f"valid_message_{i}",
                    "status": "published",
                    "event_id": event_id,
                    "message_id": message["message_id"]
                })
                
                logger.info(f"✅ Published valid message {i}: {message['message_id']}")
                await asyncio.sleep(2)  # Allow processing time
                
            except Exception as e:
                logger.error(f"❌ Failed to publish valid message {i}: {e}")
                self.test_results.append({
                    "test": f"valid_message_{i}",
                    "status": "failed",
                    "error": str(e)
                })
    
    async def test_malformed_payload(self):
        """Test malformed payload handling."""
        logger.info("⚠️ Testing malformed payload...")
        
        try:
            # Missing required fields
            malformed_payload = {
                "message_id": f"test_malformed_{int(time.time())}",
                # Missing channel_id, author_id, content, timestamp
                "invalid_field": "should_be_rejected"
            }
            
            from common.events.direct_publisher import publish_event_direct
            
            event_id = publish_event_direct(
                event_type="discord.message.new",
                channel="events",
                payload=malformed_payload,
                source="pipeline_test"
            )
            
            self.test_results.append({
                "test": "malformed_payload",
                "status": "published",
                "event_id": event_id,
                "note": "Should be rejected during processing"
            })
            
            logger.info("✅ Published malformed payload (should be rejected during processing)")
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.info(f"✅ Malformed payload correctly rejected at publish: {e}")
            self.test_results.append({
                "test": "malformed_payload", 
                "status": "rejected_at_publish",
                "error": str(e)
            })
    
    async def test_duplicate_message(self):
        """Test duplicate message ID handling."""
        logger.info("♻️ Testing duplicate message handling...")
        
        try:
            duplicate_id = f"test_duplicate_{int(time.time())}"
            
            duplicate_message = {
                "message_id": duplicate_id,
                "channel_id": "1372012942848954388",
                "author_id": "808743496341127200",
                "author_name": "TestUser", 
                "content": "A+ Setups - Duplicate Test Message",
                "timestamp": datetime.now().isoformat()
            }
            
            from common.events.direct_publisher import publish_event_direct
            
            # Publish first instance
            event_id_1 = publish_event_direct(
                event_type="discord.message.new",
                channel="events",
                payload=duplicate_message,
                source="pipeline_test"
            )
            
            await asyncio.sleep(2)
            
            # Publish duplicate 
            event_id_2 = publish_event_direct(
                event_type="discord.message.new", 
                channel="events",
                payload=duplicate_message,
                source="pipeline_test"
            )
            
            self.test_message_ids.append(duplicate_id)
            self.test_results.extend([
                {
                    "test": "duplicate_first",
                    "status": "published",
                    "event_id": event_id_1,
                    "message_id": duplicate_id
                },
                {
                    "test": "duplicate_second", 
                    "status": "published",
                    "event_id": event_id_2,
                    "message_id": duplicate_id,
                    "note": "Should be handled as duplicate during processing"
                }
            ])
            
            logger.info(f"✅ Published duplicate messages: {duplicate_id}")
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Failed to test duplicates: {e}")
            self.test_results.append({
                "test": "duplicate_handling",
                "status": "failed", 
                "error": str(e)
            })
    
    async def test_delayed_message(self):
        """Test delayed/offline message handling."""
        logger.info("⏳ Testing delayed message...")
        
        try:
            # Message with timestamp from 5 minutes ago (simulating delayed processing)
            delayed_timestamp = (datetime.now() - timedelta(minutes=5)).isoformat()
            
            delayed_message = {
                "message_id": f"test_delayed_{int(time.time())}",
                "channel_id": "1372012942848954388",
                "author_id": "808743496341127200",
                "author_name": "TestUser",
                "content": "A+ Setups - Delayed Message Test\n\nAAPL\n🔼 Breakout 180.00 🔼 182.50, 185.00",
                "timestamp": delayed_timestamp
            }
            
            from common.events.direct_publisher import publish_event_direct
            
            event_id = publish_event_direct(
                event_type="discord.message.new",
                channel="events",
                payload=delayed_message,
                source="pipeline_test"
            )
            
            self.test_message_ids.append(delayed_message["message_id"])
            self.test_results.append({
                "test": "delayed_message",
                "status": "published",
                "event_id": event_id,
                "message_id": delayed_message["message_id"],
                "delay_minutes": 5
            })
            
            logger.info(f"✅ Published delayed message: {delayed_message['message_id']}")
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Failed to test delayed message: {e}")
            self.test_results.append({
                "test": "delayed_message",
                "status": "failed",
                "error": str(e)
            })
    
    async def verify_processing(self):
        """Verify that test messages were processed correctly."""
        logger.info("🔍 Verifying message processing...")
        
        try:
            import psycopg2
            import os
            
            DATABASE_URL = os.getenv("DATABASE_URL")
            
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    # Check how many test messages were stored
                    message_ids_str = "', '".join(self.test_message_ids)
                    
                    cur.execute(f"""
                        SELECT message_id, content, created_at 
                        FROM discord_messages 
                        WHERE message_id IN ('{message_ids_str}')
                        ORDER BY created_at DESC
                    """)
                    
                    stored_messages = cur.fetchall()
                    
                    logger.info(f"📊 Processing Results:")
                    logger.info(f"   Test messages published: {len(self.test_message_ids)}")
                    logger.info(f"   Messages stored in DB: {len(stored_messages)}")
                    
                    for msg in stored_messages:
                        logger.info(f"   ✅ Stored: {msg[0]} at {msg[2]}")
                    
                    # Check recent events
                    cur.execute("""
                        SELECT event_type, correlation_id, source, created_at
                        FROM events
                        WHERE source = 'pipeline_test' AND created_at > now() - interval '10 minutes'
                        ORDER BY created_at DESC
                    """)
                    
                    test_events = cur.fetchall()
                    logger.info(f"   Test events in DB: {len(test_events)}")
                    
                    return {
                        "messages_published": len(self.test_message_ids),
                        "messages_stored": len(stored_messages),
                        "events_created": len(test_events),
                        "success_rate": len(stored_messages) / len(self.test_message_ids) * 100 if self.test_message_ids else 0
                    }
                    
        except Exception as e:
            logger.error(f"Failed to verify processing: {e}")
            return {"error": str(e)}
    
    async def run_all_tests(self):
        """Run the complete test suite."""
        logger.info("🚀 Starting Pipeline Test Suite")
        
        start_time = time.time()
        
        await self.test_valid_messages()
        await self.test_malformed_payload() 
        await self.test_duplicate_message()
        await self.test_delayed_message()
        
        # Wait for processing to complete
        logger.info("⏳ Waiting for processing to complete...")
        await asyncio.sleep(10)
        
        # Verify results
        verification = await self.verify_processing()
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info("📋 Test Suite Summary:")
        logger.info(f"   Duration: {duration:.1f}s")
        logger.info(f"   Tests executed: {len(self.test_results)}")
        logger.info(f"   Messages published: {verification.get('messages_published', 0)}")
        logger.info(f"   Messages stored: {verification.get('messages_stored', 0)}")
        logger.info(f"   Success rate: {verification.get('success_rate', 0):.1f}%")
        
        return {
            "test_results": self.test_results,
            "verification": verification,
            "duration": duration
        }

if __name__ == "__main__":
    async def main():
        test_suite = PipelineTestSuite()
        results = await test_suite.run_all_tests()
        
        print("\n" + "="*50)
        print("PIPELINE TEST RESULTS")
        print("="*50)
        print(json.dumps(results, indent=2, default=str))
    
    asyncio.run(main())
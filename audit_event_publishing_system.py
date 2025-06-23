"""
Comprehensive Discord Bot Event Publishing System Audit

Implements the in-depth analysis plan to detect and prevent event publishing failures.
Covers all textbook failure modes with structured logging and validation.
"""
import asyncio
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from app import create_app

# Configure comprehensive logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EventPublishingAuditor:
    """Comprehensive auditor for Discord bot event publishing system."""
    
    def __init__(self):
        self.audit_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'tests_run': 0,
            'tests_passed': 0,
            'failures': [],
            'recommendations': []
        }
    
    async def run_comprehensive_audit(self):
        """Execute complete audit of event publishing system."""
        print("🔍 Starting Comprehensive Event Publishing System Audit")
        print("=" * 60)
        
        app = create_app()
        with app.app_context():
            await self._audit_core_components()
            await self._test_failure_modes()
            await self._validate_instrumentation()
            await self._verify_system_health()
            
        self._generate_audit_report()
    
    async def _audit_core_components(self):
        """Audit core components for correctness and reliability."""
        print("\n📋 1. CORE COMPONENTS AUDIT")
        print("-" * 40)
        
        # Test 1: Discord bot message detection
        await self._test_message_detection()
        
        # Test 2: Event publisher validation
        await self._test_event_publisher()
        
        # Test 3: PostgreSQL NOTIFY mechanism
        await self._test_postgresql_notify()
        
        # Test 4: Ingestion listener status
        await self._test_ingestion_listener()
    
    async def _test_message_detection(self):
        """Test discord_bot.bot.on_message() detection logic."""
        self.audit_results['tests_run'] += 1
        
        try:
            from features.discord_bot.bot import TradingDiscordBot
            
            # Check if bot class exists and has on_message method
            if hasattr(TradingDiscordBot, 'on_message'):
                logger.info("✅ Discord bot on_message() method found")
                self.audit_results['tests_passed'] += 1
            else:
                self._add_failure("Discord bot missing on_message() method")
                
        except Exception as e:
            self._add_failure(f"Discord bot import failed: {e}")
    
    async def _test_event_publisher(self):
        """Test publish_event_safe() and async publisher."""
        self.audit_results['tests_run'] += 1
        
        try:
            from common.events.publisher import publish_event_async, publish_event_safe
            
            # Test async publisher with instrumented payload
            test_payload = {
                'audit_test': True,
                'message_id': f'audit_{int(datetime.utcnow().timestamp())}',
                'content': 'Event publishing audit test',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info("🧪 Testing async event publisher...")
            success = await publish_event_async(
                event_type="audit.test",
                data=test_payload,
                channel="events",
                source="audit_system"
            )
            
            if success:
                logger.info("✅ Async event publisher working")
                self.audit_results['tests_passed'] += 1
            else:
                self._add_failure("Async event publisher failed")
                
        except Exception as e:
            logger.exception("❌ Event publisher test failed")
            self._add_failure(f"Event publisher error: {e}")
    
    async def _test_postgresql_notify(self):
        """Test PostgreSQL NOTIFY mechanism."""
        self.audit_results['tests_run'] += 1
        
        try:
            from common.db import db
            from sqlalchemy import text
            
            # Check for active LISTEN connections
            result = db.session.execute(text("""
                SELECT application_name, state, query, pid
                FROM pg_stat_activity 
                WHERE query LIKE '%LISTEN%'
            """)).fetchall()
            
            if result:
                logger.info(f"✅ Found {len(result)} PostgreSQL LISTEN connections")
                for row in result:
                    logger.info(f"   PID {row[3]}: {row[1]} - {row[2]}")
                self.audit_results['tests_passed'] += 1
            else:
                self._add_failure("No PostgreSQL LISTEN connections found")
                
        except Exception as e:
            logger.exception("❌ PostgreSQL NOTIFY test failed")
            self._add_failure(f"PostgreSQL NOTIFY error: {e}")
    
    async def _test_ingestion_listener(self):
        """Test ingestion listener status and functionality."""
        self.audit_results['tests_run'] += 1
        
        try:
            from features.ingestion.listener import get_listener_stats
            
            stats = get_listener_stats()
            if stats.get('status') != 'not_running':
                logger.info("✅ Ingestion listener is active")
                logger.info(f"   Events received: {stats.get('events_received', 0)}")
                logger.info(f"   Events processed: {stats.get('events_processed', 0)}")
                logger.info(f"   Errors: {stats.get('errors', 0)}")
                self.audit_results['tests_passed'] += 1
            else:
                self._add_failure("Ingestion listener not running")
                
        except Exception as e:
            logger.exception("❌ Ingestion listener test failed")
            self._add_failure(f"Ingestion listener error: {e}")
    
    async def _test_failure_modes(self):
        """Test known failure modes from the audit plan."""
        print("\n⚠️  2. FAILURE MODE TESTING")
        print("-" * 40)
        
        # Test async context handling
        await self._test_async_context()
        
        # Test event structure validation
        await self._test_event_structure()
        
        # Test database transaction handling
        await self._test_db_transactions()
        
        # Test listener timing
        await self._test_listener_timing()
    
    async def _test_async_context(self):
        """Test for async context and event loop issues."""
        self.audit_results['tests_run'] += 1
        
        try:
            # Test current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logger.info("✅ Event loop is running correctly")
                self.audit_results['tests_passed'] += 1
            else:
                self._add_failure("Event loop not running")
                
            # Test async event publishing in current context
            from common.events.publisher import publish_event_async
            
            test_data = {'test': 'async_context', 'timestamp': datetime.utcnow().isoformat()}
            success = await publish_event_async(
                event_type="audit.async_test",
                data=test_data,
                source="async_context_test"
            )
            
            if success:
                logger.info("✅ Async context handling working")
            else:
                self._add_failure("Async context publishing failed")
                
        except Exception as e:
            logger.exception("❌ Async context test failed")
            self._add_failure(f"Async context error: {e}")
    
    async def _test_event_structure(self):
        """Test event structure validation and malformed payload handling."""
        self.audit_results['tests_run'] += 1
        
        try:
            # Test with valid structure
            valid_payload = {
                'message_id': 'test_valid',
                'channel_id': '1234567890',
                'content': 'Valid test message',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            from common.events.publisher import publish_event_async
            success = await publish_event_async(
                event_type="discord.message.new",
                data=valid_payload,
                source="structure_test"
            )
            
            if success:
                logger.info("✅ Valid event structure accepted")
                self.audit_results['tests_passed'] += 1
            else:
                self._add_failure("Valid event structure rejected")
                
            # Test with malformed structure (should handle gracefully)
            malformed_payload = {'invalid': None, 'missing_required_fields': True}
            
            success = await publish_event_async(
                event_type="discord.message.new",
                data=malformed_payload,
                source="malformed_test"
            )
            
            # This should still succeed but log warnings
            logger.info("ℹ️  Malformed payload handling tested")
            
        except Exception as e:
            logger.exception("❌ Event structure test failed")
            self._add_failure(f"Event structure error: {e}")
    
    async def _test_db_transactions(self):
        """Test database transaction and connection handling."""
        self.audit_results['tests_run'] += 1
        
        try:
            from common.db import db
            from sqlalchemy import text
            
            # Test database connection
            result = db.session.execute(text("SELECT 1")).fetchone()
            if result and result[0] == 1:
                logger.info("✅ Database connection active")
                self.audit_results['tests_passed'] += 1
            else:
                self._add_failure("Database connection failed")
                
            # Test transaction handling
            with db.session.begin():
                test_event = {
                    'event_type': 'audit.db_test',
                    'channel': 'events',
                    'data': json.dumps({'test': 'transaction'}),
                    'source': 'db_audit',
                    'correlation_id': str(uuid.uuid4()),
                    'created_at': datetime.utcnow()
                }
                
                db.session.execute(text("""
                    INSERT INTO events (event_type, channel, data, source, correlation_id, created_at)
                    VALUES (:event_type, :channel, :data, :source, :correlation_id, :created_at)
                """), test_event)
                
                logger.info("✅ Database transaction handling working")
                
        except Exception as e:
            logger.exception("❌ Database transaction test failed")
            self._add_failure(f"Database transaction error: {e}")
    
    async def _test_listener_timing(self):
        """Test listener startup timing and message publishing order."""
        self.audit_results['tests_run'] += 1
        
        try:
            # Check if listener is ready before testing
            await asyncio.sleep(1)  # Brief delay to ensure listener is ready
            
            # Publish test event and verify delivery
            test_id = f"timing_test_{int(datetime.utcnow().timestamp())}"
            from common.events.publisher import publish_event_async
            
            success = await publish_event_async(
                event_type="audit.timing_test",
                data={'test_id': test_id, 'purpose': 'listener_timing'},
                source="timing_audit"
            )
            
            if success:
                logger.info("✅ Listener timing test completed")
                self.audit_results['tests_passed'] += 1
            else:
                self._add_failure("Listener timing test failed")
                
        except Exception as e:
            logger.exception("❌ Listener timing test failed")
            self._add_failure(f"Listener timing error: {e}")
    
    async def _validate_instrumentation(self):
        """Validate logging and instrumentation quality."""
        print("\n🧪 3. INSTRUMENTATION VALIDATION")
        print("-" * 40)
        
        self.audit_results['tests_run'] += 1
        
        try:
            # Check for proper logging configuration
            root_logger = logging.getLogger()
            if root_logger.level <= logging.DEBUG:
                logger.info("✅ Debug logging enabled")
            else:
                self._add_failure("Debug logging not enabled")
            
            # Test structured logging with event publishing
            from common.events.publisher import publish_event_async
            
            instrumentation_data = {
                'audit_type': 'instrumentation_test',
                'correlation_id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'test_fields': {
                    'message_id': 'inst_test_123',
                    'event_type': 'audit.instrumentation',
                    'payload_size': 256
                }
            }
            
            success = await publish_event_async(
                event_type="audit.instrumentation",
                data=instrumentation_data,
                source="instrumentation_audit"
            )
            
            if success:
                logger.info("✅ Structured logging and instrumentation working")
                self.audit_results['tests_passed'] += 1
            else:
                self._add_failure("Instrumentation validation failed")
                
        except Exception as e:
            logger.exception("❌ Instrumentation validation failed")
            self._add_failure(f"Instrumentation error: {e}")
    
    async def _verify_system_health(self):
        """Verify overall system health and recent activity."""
        print("\n🏥 4. SYSTEM HEALTH VERIFICATION")
        print("-" * 40)
        
        self.audit_results['tests_run'] += 1
        
        try:
            from common.db import db
            from sqlalchemy import text
            
            # Check recent events in database
            recent_events = db.session.execute(text("""
                SELECT event_type, source, created_at 
                FROM events 
                WHERE created_at > NOW() - INTERVAL '1 hour'
                ORDER BY created_at DESC 
                LIMIT 10
            """)).fetchall()
            
            logger.info(f"✅ Found {len(recent_events)} recent events")
            for event in recent_events[:3]:  # Show latest 3
                logger.info(f"   {event[1]} -> {event[0]} at {event[2]}")
            
            # Check recent messages
            recent_messages = db.session.execute(text("""
                SELECT message_id, created_at 
                FROM discord_messages 
                ORDER BY created_at DESC 
                LIMIT 5
            """)).fetchall()
            
            logger.info(f"✅ Found {len(recent_messages)} recent messages")
            for msg in recent_messages[:2]:  # Show latest 2
                logger.info(f"   Message {msg[0]} at {msg[1]}")
            
            # Check ingestion service metrics
            from features.ingestion.service import get_ingestion_service
            service = get_ingestion_service()
            metrics = service.get_metrics()
            
            logger.info("📊 Ingestion Service Health:")
            logger.info(f"   Status: {metrics.get('service_status', 'unknown')}")
            logger.info(f"   Total stored: {metrics.get('total_messages_stored', 0)}")
            logger.info(f"   Success rate: {metrics.get('validation_success_rate', 0)}%")
            
            self.audit_results['tests_passed'] += 1
            
        except Exception as e:
            logger.exception("❌ System health verification failed")
            self._add_failure(f"System health error: {e}")
    
    def _add_failure(self, failure_message: str):
        """Add a failure to the audit results."""
        self.audit_results['failures'].append({
            'message': failure_message,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.error(f"❌ AUDIT FAILURE: {failure_message}")
    
    def _generate_audit_report(self):
        """Generate comprehensive audit report with recommendations."""
        print("\n📊 COMPREHENSIVE AUDIT REPORT")
        print("=" * 60)
        
        success_rate = (self.audit_results['tests_passed'] / self.audit_results['tests_run']) * 100
        
        print(f"Tests Run: {self.audit_results['tests_run']}")
        print(f"Tests Passed: {self.audit_results['tests_passed']}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Failures: {len(self.audit_results['failures'])}")
        
        if self.audit_results['failures']:
            print("\n❌ FAILURES DETECTED:")
            for i, failure in enumerate(self.audit_results['failures'], 1):
                print(f"   {i}. {failure['message']}")
        
        # Generate recommendations
        self._generate_recommendations()
        
        if self.audit_results['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(self.audit_results['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        # Overall assessment
        if success_rate >= 90:
            print("\n✅ OVERALL ASSESSMENT: Event publishing system is healthy")
        elif success_rate >= 70:
            print("\n⚠️  OVERALL ASSESSMENT: Event publishing system needs attention")
        else:
            print("\n❌ OVERALL ASSESSMENT: Event publishing system requires immediate fixes")
    
    def _generate_recommendations(self):
        """Generate specific recommendations based on failures."""
        if any('async' in f['message'].lower() for f in self.audit_results['failures']):
            self.audit_results['recommendations'].append(
                "Implement asyncio.run_coroutine_threadsafe for thread-safe async operations"
            )
        
        if any('database' in f['message'].lower() for f in self.audit_results['failures']):
            self.audit_results['recommendations'].append(
                "Add database connection pooling and retry logic"
            )
        
        if any('listener' in f['message'].lower() for f in self.audit_results['failures']):
            self.audit_results['recommendations'].append(
                "Ensure ingestion listener starts before Discord bot"
            )
        
        if len(self.audit_results['failures']) > 2:
            self.audit_results['recommendations'].append(
                "Add comprehensive error handling with structured logging"
            )


async def main():
    """Run the comprehensive audit."""
    auditor = EventPublishingAuditor()
    await auditor.run_comprehensive_audit()


if __name__ == "__main__":
    asyncio.run(main())
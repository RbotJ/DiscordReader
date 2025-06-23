"""
Quick Event Publishing System Diagnostic

Rapidly diagnoses Discord bot event publishing system for common failure modes.
Provides actionable insights without hanging or long-running processes.
"""
import logging
import json
import uuid
from datetime import datetime, timedelta
from app import create_app

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def diagnose_event_system():
    """Run comprehensive but quick diagnostic of event publishing system."""
    print("🔍 Event Publishing System Diagnostic")
    print("=" * 50)
    
    app = create_app()
    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'tests': {},
        'failures': [],
        'recommendations': []
    }
    
    with app.app_context():
        # 1. Core Component Health Check
        print("\n1. Core Component Health")
        results['tests']['discord_bot'] = check_discord_bot_config()
        results['tests']['event_publisher'] = check_event_publisher()
        results['tests']['postgresql_notify'] = check_postgresql_notify()
        results['tests']['ingestion_listener'] = check_ingestion_listener()
        
        # 2. Recent Activity Analysis
        print("\n2. Recent Activity Analysis")
        results['tests']['recent_events'] = analyze_recent_events()
        results['tests']['recent_messages'] = analyze_recent_messages()
        results['tests']['system_metrics'] = check_system_metrics()
        
        # 3. Event Flow Validation
        print("\n3. Event Flow Validation")
        results['tests']['event_publishing'] = test_event_publishing()
        
        # 4. Failure Mode Detection
        print("\n4. Failure Mode Detection")
        results['failures'] = detect_failure_modes(results['tests'])
        
        # 5. Generate Recommendations
        results['recommendations'] = generate_recommendations(results['failures'])
    
    print_diagnostic_report(results)
    return results


def check_discord_bot_config():
    """Check Discord bot configuration and methods."""
    try:
        from features.discord_bot.bot import TradingDiscordBot
        
        # Check critical methods exist
        has_on_message = hasattr(TradingDiscordBot, 'on_message')
        has_trigger_ingestion = hasattr(TradingDiscordBot, '_trigger_ingestion')
        
        print(f"   Discord Bot Methods: on_message={has_on_message}, _trigger_ingestion={has_trigger_ingestion}")
        
        return {
            'status': 'healthy' if has_on_message and has_trigger_ingestion else 'degraded',
            'on_message_exists': has_on_message,
            'trigger_ingestion_exists': has_trigger_ingestion
        }
    except Exception as e:
        print(f"   ❌ Discord bot check failed: {e}")
        return {'status': 'failed', 'error': str(e)}


def check_event_publisher():
    """Check event publishing functions."""
    try:
        from common.events.publisher import publish_event_async, publish_event_safe
        
        # Check functions exist
        async_exists = callable(publish_event_async)
        safe_exists = callable(publish_event_safe)
        
        print(f"   Event Publishers: async={async_exists}, safe={safe_exists}")
        
        return {
            'status': 'healthy' if async_exists and safe_exists else 'degraded',
            'async_publisher_exists': async_exists,
            'safe_publisher_exists': safe_exists
        }
    except Exception as e:
        print(f"   ❌ Event publisher check failed: {e}")
        return {'status': 'failed', 'error': str(e)}


def check_postgresql_notify():
    """Check PostgreSQL NOTIFY/LISTEN status."""
    try:
        from common.db import db
        from sqlalchemy import text
        
        # Check for active LISTEN connections
        result = db.session.execute(text("""
            SELECT COUNT(*) as listener_count
            FROM pg_stat_activity 
            WHERE query LIKE '%LISTEN%'
        """)).fetchone()
        
        listener_count = result[0] if result else 0
        
        # Check recent NOTIFY activity
        recent_events = db.session.execute(text("""
            SELECT COUNT(*) as recent_count
            FROM events 
            WHERE created_at > NOW() - INTERVAL '10 minutes'
        """)).fetchone()
        
        recent_count = recent_events[0] if recent_events else 0
        
        print(f"   PostgreSQL: {listener_count} listeners, {recent_count} recent events")
        
        return {
            'status': 'healthy' if listener_count > 0 else 'failed',
            'listener_count': listener_count,
            'recent_events': recent_count
        }
    except Exception as e:
        print(f"   ❌ PostgreSQL check failed: {e}")
        return {'status': 'failed', 'error': str(e)}


def check_ingestion_listener():
    """Check ingestion listener status."""
    try:
        from features.ingestion.listener import get_listener_stats
        
        stats = get_listener_stats()
        is_running = stats.get('status') != 'not_running'
        
        print(f"   Ingestion Listener: running={is_running}")
        if is_running:
            print(f"      Events received: {stats.get('events_received', 0)}")
            print(f"      Events processed: {stats.get('events_processed', 0)}")
            print(f"      Errors: {stats.get('errors', 0)}")
        
        return {
            'status': 'healthy' if is_running else 'failed',
            'is_running': is_running,
            'stats': stats
        }
    except Exception as e:
        print(f"   ❌ Ingestion listener check failed: {e}")
        return {'status': 'failed', 'error': str(e)}


def analyze_recent_events():
    """Analyze recent events in the database."""
    try:
        from common.db import db
        from sqlalchemy import text
        
        # Get recent events by type
        result = db.session.execute(text("""
            SELECT event_type, source, COUNT(*) as count
            FROM events 
            WHERE created_at > NOW() - INTERVAL '1 hour'
            GROUP BY event_type, source
            ORDER BY count DESC
            LIMIT 10
        """)).fetchall()
        
        events_summary = {}
        total_events = 0
        
        for row in result:
            event_key = f"{row[1]}.{row[0]}"
            events_summary[event_key] = row[2]
            total_events += row[2]
        
        print(f"   Recent Events (1h): {total_events} total")
        for event, count in list(events_summary.items())[:5]:
            print(f"      {event}: {count}")
        
        return {
            'status': 'healthy' if total_events > 0 else 'degraded',
            'total_recent_events': total_events,
            'event_types': events_summary
        }
    except Exception as e:
        print(f"   ❌ Recent events analysis failed: {e}")
        return {'status': 'failed', 'error': str(e)}


def analyze_recent_messages():
    """Analyze recent Discord messages."""
    try:
        from common.db import db
        from sqlalchemy import text
        
        # Get recent message statistics
        result = db.session.execute(text("""
            SELECT 
                COUNT(*) as total_messages,
                COUNT(CASE WHEN created_at > NOW() - INTERVAL '1 hour' THEN 1 END) as recent_messages,
                MAX(created_at) as latest_message
            FROM discord_messages
        """)).fetchone()
        
        total = result[0] if result else 0
        recent = result[1] if result else 0
        latest = result[2] if result else None
        
        print(f"   Discord Messages: {total} total, {recent} recent")
        if latest:
            print(f"      Latest: {latest}")
        
        return {
            'status': 'healthy' if recent > 0 else 'degraded',
            'total_messages': total,
            'recent_messages': recent,
            'latest_message': latest.isoformat() if latest else None
        }
    except Exception as e:
        print(f"   ❌ Recent messages analysis failed: {e}")
        return {'status': 'failed', 'error': str(e)}


def check_system_metrics():
    """Check ingestion service metrics."""
    try:
        from features.ingestion.service import get_ingestion_service
        
        service = get_ingestion_service()
        metrics = service.get_metrics()
        
        status = metrics.get('service_status', 'unknown')
        success_rate = metrics.get('validation_success_rate', 0)
        total_stored = metrics.get('total_messages_stored', 0)
        
        print(f"   Service Metrics: status={status}, success_rate={success_rate}%")
        print(f"      Total stored: {total_stored}")
        
        return {
            'status': 'healthy' if status == 'active' and success_rate > 90 else 'degraded',
            'service_status': status,
            'success_rate': success_rate,
            'total_stored': total_stored,
            'full_metrics': metrics
        }
    except Exception as e:
        print(f"   ❌ System metrics check failed: {e}")
        return {'status': 'failed', 'error': str(e)}


def test_event_publishing():
    """Test event publishing functionality."""
    try:
        import asyncio
        from common.events.publisher import publish_event_async
        
        # Create test payload
        test_data = {
            'test_id': f'diagnostic_{int(datetime.utcnow().timestamp())}',
            'purpose': 'system_diagnostic',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Test async publishing
        async def test_publish():
            return await publish_event_async(
                event_type="diagnostic.test",
                data=test_data,
                source="diagnostic_tool"
            )
        
        # Run the test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(test_publish())
        finally:
            loop.close()
        
        print(f"   Event Publishing Test: {'✅ passed' if success else '❌ failed'}")
        
        return {
            'status': 'healthy' if success else 'failed',
            'test_successful': success,
            'test_data': test_data
        }
    except Exception as e:
        print(f"   ❌ Event publishing test failed: {e}")
        return {'status': 'failed', 'error': str(e)}


def detect_failure_modes(test_results):
    """Detect common failure modes based on test results."""
    failures = []
    
    # Check for PostgreSQL NOTIFY issues
    if test_results.get('postgresql_notify', {}).get('listener_count', 0) == 0:
        failures.append({
            'mode': 'No PostgreSQL LISTEN connections',
            'symptom': 'Events published but never received',
            'cause': 'Ingestion listener not running or crashed'
        })
    
    # Check for event publishing issues
    if not test_results.get('event_publishing', {}).get('test_successful', False):
        failures.append({
            'mode': 'Event publishing failed',
            'symptom': 'Discord messages not triggering events',
            'cause': 'Async context or database connection issues'
        })
    
    # Check for ingestion processing issues
    if not test_results.get('ingestion_listener', {}).get('is_running', False):
        failures.append({
            'mode': 'Ingestion listener not running',
            'symptom': 'Events received but not processed',
            'cause': 'Listener startup failure or crash'
        })
    
    # Check for low activity
    recent_events = test_results.get('recent_events', {}).get('total_recent_events', 0)
    recent_messages = test_results.get('recent_messages', {}).get('recent_messages', 0)
    
    if recent_events == 0 and recent_messages == 0:
        failures.append({
            'mode': 'No recent activity',
            'symptom': 'System appears inactive',
            'cause': 'Discord bot not receiving messages or not publishing events'
        })
    
    return failures


def generate_recommendations(failures):
    """Generate specific recommendations based on detected failures."""
    recommendations = []
    
    for failure in failures:
        mode = failure['mode']
        
        if 'PostgreSQL LISTEN' in mode:
            recommendations.append(
                "Restart ingestion listener: check app startup logs for listener initialization"
            )
        
        elif 'Event publishing' in mode:
            recommendations.append(
                "Add asyncio.run_coroutine_threadsafe wrapper for Discord bot event publishing"
            )
        
        elif 'Ingestion listener' in mode:
            recommendations.append(
                "Verify ingestion listener starts automatically in app.py create_app()"
            )
        
        elif 'No recent activity' in mode:
            recommendations.append(
                "Check Discord bot token and channel configuration"
            )
    
    # General recommendations
    if len(failures) > 0:
        recommendations.append(
            "Add comprehensive try/catch blocks with logger.exception() in event handlers"
        )
        recommendations.append(
            "Implement health check endpoint to monitor event system status"
        )
    
    return recommendations


def print_diagnostic_report(results):
    """Print comprehensive diagnostic report."""
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC REPORT")
    print("=" * 50)
    
    # Summary
    healthy_tests = sum(1 for test in results['tests'].values() if test.get('status') == 'healthy')
    total_tests = len(results['tests'])
    health_percentage = (healthy_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"System Health: {health_percentage:.1f}% ({healthy_tests}/{total_tests} components healthy)")
    
    # Failures
    if results['failures']:
        print(f"\n❌ DETECTED FAILURE MODES ({len(results['failures'])}):")
        for i, failure in enumerate(results['failures'], 1):
            print(f"   {i}. {failure['mode']}")
            print(f"      Symptom: {failure['symptom']}")
            print(f"      Cause: {failure['cause']}")
    else:
        print("\n✅ No critical failure modes detected")
    
    # Recommendations
    if results['recommendations']:
        print(f"\n💡 RECOMMENDATIONS ({len(results['recommendations'])}):")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"   {i}. {rec}")
    
    # Overall assessment
    if health_percentage >= 90:
        print("\n✅ ASSESSMENT: Event publishing system is healthy")
    elif health_percentage >= 70:
        print("\n⚠️  ASSESSMENT: Event publishing system needs attention")
    else:
        print("\n❌ ASSESSMENT: Event publishing system requires immediate fixes")


if __name__ == "__main__":
    diagnose_event_system()
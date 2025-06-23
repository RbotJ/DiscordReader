"""
Event System Diagnostic - Direct Database Analysis

Analyzes event publishing system health through direct database queries
and file system inspection without initializing the full Flask app.
"""
import os
import sys
import psycopg2
from datetime import datetime, timedelta
import json

def get_database_connection():
    """Get direct PostgreSQL connection."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url)

def analyze_postgresql_listeners():
    """Check PostgreSQL LISTEN/NOTIFY status."""
    print("1. PostgreSQL LISTEN/NOTIFY Analysis")
    print("-" * 40)
    
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Check for active LISTEN connections
        cursor.execute("""
            SELECT application_name, state, query, pid, backend_start
            FROM pg_stat_activity 
            WHERE query LIKE '%LISTEN%'
            ORDER BY backend_start DESC
        """)
        
        listeners = cursor.fetchall()
        print(f"Active LISTEN connections: {len(listeners)}")
        
        for listener in listeners:
            app_name, state, query, pid, start_time = listener
            print(f"  PID {pid}: {state} - {query.strip()}")
            print(f"    Started: {start_time}")
        
        cursor.close()
        conn.close()
        
        return len(listeners) > 0
        
    except Exception as e:
        print(f"ERROR checking PostgreSQL listeners: {e}")
        return False

def analyze_recent_events():
    """Analyze recent event activity."""
    print("\n2. Recent Event Activity Analysis")
    print("-" * 40)
    
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Get recent events summary
        cursor.execute("""
            SELECT 
                event_type,
                source,
                COUNT(*) as count,
                MAX(created_at) as latest
            FROM events 
            WHERE created_at > NOW() - INTERVAL '1 hour'
            GROUP BY event_type, source
            ORDER BY count DESC, latest DESC
        """)
        
        recent_events = cursor.fetchall()
        total_events = sum(row[2] for row in recent_events)
        
        print(f"Recent events (1 hour): {total_events}")
        for event_type, source, count, latest in recent_events:
            print(f"  {source}.{event_type}: {count} events (latest: {latest})")
        
        # Check event distribution over time
        cursor.execute("""
            SELECT 
                DATE_TRUNC('minute', created_at) as minute,
                COUNT(*) as events
            FROM events 
            WHERE created_at > NOW() - INTERVAL '10 minutes'
            GROUP BY minute
            ORDER BY minute DESC
            LIMIT 10
        """)
        
        time_distribution = cursor.fetchall()
        print(f"\nEvent distribution (last 10 minutes):")
        for minute, count in time_distribution:
            print(f"  {minute}: {count} events")
        
        cursor.close()
        conn.close()
        
        return total_events > 0
        
    except Exception as e:
        print(f"ERROR analyzing recent events: {e}")
        return False

def analyze_discord_messages():
    """Analyze Discord message processing."""
    print("\n3. Discord Message Processing Analysis")
    print("-" * 40)
    
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Get message statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_messages,
                COUNT(CASE WHEN created_at > NOW() - INTERVAL '1 hour' THEN 1 END) as recent_messages,
                COUNT(CASE WHEN is_processed = true THEN 1 END) as processed_messages,
                MAX(created_at) as latest_message
            FROM discord_messages
        """)
        
        stats = cursor.fetchone()
        total, recent, processed, latest = stats
        
        print(f"Total messages: {total}")
        print(f"Recent messages (1h): {recent}")
        print(f"Processed messages: {processed}")
        print(f"Latest message: {latest}")
        
        if total > 0:
            processing_rate = (processed / total) * 100
            print(f"Processing rate: {processing_rate:.1f}%")
        
        # Check for unprocessed messages
        cursor.execute("""
            SELECT message_id, content, created_at, is_processed
            FROM discord_messages 
            WHERE is_processed = false
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        unprocessed = cursor.fetchall()
        if unprocessed:
            print(f"\nUnprocessed messages: {len(unprocessed)}")
            for msg_id, content, created, processed in unprocessed:
                content_preview = content[:50] + "..." if len(content) > 50 else content
                print(f"  {msg_id}: {content_preview} ({created})")
        
        cursor.close()
        conn.close()
        
        return recent > 0
        
    except Exception as e:
        print(f"ERROR analyzing Discord messages: {e}")
        return False

def check_event_publishing_components():
    """Check event publishing components exist."""
    print("\n4. Event Publishing Components Check")
    print("-" * 40)
    
    components = {
        'Discord Bot': 'features/discord_bot/bot.py',
        'Event Publisher': 'common/events/publisher.py',
        'Ingestion Listener': 'features/ingestion/listener.py',
        'Ingestion Service': 'features/ingestion/service.py'
    }
    
    all_exist = True
    
    for name, path in components.items():
        if os.path.exists(path):
            print(f"  ✓ {name}: {path}")
            
            # Check for critical functions/classes
            with open(path, 'r') as f:
                content = f.read()
                
            if name == 'Discord Bot':
                has_on_message = 'def on_message' in content
                print(f"    on_message method: {'✓' if has_on_message else '✗'}")
                
            elif name == 'Event Publisher':
                has_async_publish = 'async def publish_event_async' in content
                has_safe_publish = 'def publish_event_safe' in content
                print(f"    async publisher: {'✓' if has_async_publish else '✗'}")
                print(f"    safe publisher: {'✓' if has_safe_publish else '✗'}")
                
            elif name == 'Ingestion Listener':
                has_start_listening = 'async def start_listening' in content
                print(f"    start_listening method: {'✓' if has_start_listening else '✗'}")
        else:
            print(f"  ✗ {name}: {path} (NOT FOUND)")
            all_exist = False
    
    return all_exist

def analyze_failure_patterns():
    """Analyze patterns that indicate failure modes."""
    print("\n5. Failure Pattern Analysis")
    print("-" * 40)
    
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        failures = []
        
        # Check for event publishing but no message storage
        cursor.execute("""
            SELECT COUNT(*) FROM events 
            WHERE event_type = 'discord.message.new'
            AND created_at > NOW() - INTERVAL '1 hour'
        """)
        discord_events = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM discord_messages 
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """)
        stored_messages = cursor.fetchone()[0]
        
        if discord_events > stored_messages + 5:  # Allow some tolerance
            failures.append({
                'pattern': 'Events published but messages not stored',
                'symptom': f'{discord_events} discord events vs {stored_messages} stored messages',
                'likely_cause': 'Ingestion listener not processing events or database errors'
            })
        
        # Check for messages stored but not processed
        cursor.execute("""
            SELECT COUNT(*) FROM discord_messages 
            WHERE is_processed = false
            AND created_at < NOW() - INTERVAL '5 minutes'
        """)
        old_unprocessed = cursor.fetchone()[0]
        
        if old_unprocessed > 0:
            failures.append({
                'pattern': 'Messages stored but not processed',
                'symptom': f'{old_unprocessed} messages unprocessed for >5 minutes',
                'likely_cause': 'Parser errors or validation failures'
            })
        
        # Check for event gaps
        cursor.execute("""
            SELECT 
                EXTRACT(EPOCH FROM (NOW() - MAX(created_at)))/60 as minutes_since_last_event
            FROM events
        """)
        minutes_since = cursor.fetchone()[0]
        
        if minutes_since and minutes_since > 30:
            failures.append({
                'pattern': 'No recent event activity',
                'symptom': f'No events for {minutes_since:.1f} minutes',
                'likely_cause': 'Discord bot not connected or event publishing broken'
            })
        
        cursor.close()
        conn.close()
        
        if failures:
            print("Detected failure patterns:")
            for i, failure in enumerate(failures, 1):
                print(f"  {i}. {failure['pattern']}")
                print(f"     Symptom: {failure['symptom']}")
                print(f"     Likely cause: {failure['likely_cause']}")
        else:
            print("No obvious failure patterns detected")
        
        return len(failures) == 0
        
    except Exception as e:
        print(f"ERROR analyzing failure patterns: {e}")
        return False

def generate_health_report():
    """Generate overall system health report."""
    print("\n" + "=" * 50)
    print("EVENT SYSTEM HEALTH REPORT")
    print("=" * 50)
    
    # Run all diagnostics
    results = {
        'postgresql_listeners': analyze_postgresql_listeners(),
        'recent_events': analyze_recent_events(),
        'discord_messages': analyze_discord_messages(),
        'components': check_event_publishing_components(),
        'failure_patterns': analyze_failure_patterns()
    }
    
    # Calculate health score
    healthy_components = sum(results.values())
    total_components = len(results)
    health_percentage = (healthy_components / total_components) * 100
    
    print(f"\nSystem Health Score: {health_percentage:.1f}% ({healthy_components}/{total_components} components healthy)")
    
    # Component status
    print("\nComponent Status:")
    for component, status in results.items():
        status_text = "✓ HEALTHY" if status else "✗ DEGRADED"
        component_name = component.replace('_', ' ').title()
        print(f"  {component_name}: {status_text}")
    
    # Recommendations
    print("\nRecommendations:")
    if not results['postgresql_listeners']:
        print("  - Restart ingestion listener service")
        print("  - Check app startup logs for listener initialization errors")
    
    if not results['recent_events']:
        print("  - Verify Discord bot is connected and receiving messages")
        print("  - Check event publishing functionality")
    
    if not results['discord_messages']:
        print("  - Check Discord bot token and channel configuration")
        print("  - Verify bot has proper permissions in target channels")
    
    if not results['failure_patterns']:
        print("  - Investigate specific failure patterns identified above")
        print("  - Add comprehensive error handling and logging")
    
    if health_percentage >= 90:
        print("\nOverall Assessment: Event system is healthy and functioning properly")
    elif health_percentage >= 70:
        print("\nOverall Assessment: Event system is functional but needs attention")
    else:
        print("\nOverall Assessment: Event system requires immediate fixes")

if __name__ == "__main__":
    try:
        generate_health_report()
    except Exception as e:
        print(f"DIAGNOSTIC ERROR: {e}")
        sys.exit(1)
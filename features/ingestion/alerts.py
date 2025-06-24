"""
Ingestion Alert System

Monitors ingestion metrics and logs warnings for critical conditions:
- Zero messages during trading hours
- Last message processed > 10 minutes ago  
- Listener not active
"""
import logging
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

def is_trading_hours():
    """Check if current time is within trading hours (9:30 AM - 4:00 PM ET)."""
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    
    # Monday = 0, Sunday = 6
    if now_et.weekday() >= 5:  # Weekend
        return False
    
    trading_start = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    trading_end = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return trading_start <= now_et <= trading_end

def check_ingestion_alerts(metrics):
    """
    Check ingestion metrics and log alerts for critical conditions.
    
    Args:
        metrics: Dictionary containing ingestion metrics
    """
    alerts = []
    
    # Alert: Zero messages during trading hours
    if is_trading_hours():
        messages_today = metrics.get('daily_metrics', {}).get('messages_ingested_today', 0)
        if messages_today == 0:
            alert_msg = "ALERT: Zero messages ingested during trading hours"
            logger.warning(alert_msg)
            alerts.append({
                'type': 'zero_messages_trading_hours',
                'message': alert_msg,
                'severity': 'high'
            })
    
    # Alert: Last message processed > 10 minutes ago
    core_metrics = metrics.get('core_metrics', {})
    if 'last_message_processed' in core_metrics:
        try:
            if isinstance(core_metrics['last_message_processed'], str):
                last_processed = datetime.fromisoformat(core_metrics['last_message_processed'].replace('Z', '+00:00'))
            else:
                last_processed = core_metrics['last_message_processed']
            
            time_since_last = datetime.now() - last_processed.replace(tzinfo=None)
            
            if time_since_last > timedelta(minutes=10):
                alert_msg = f"ALERT: Last message processed {time_since_last.total_seconds()/60:.1f} minutes ago"
                logger.warning(alert_msg)
                alerts.append({
                    'type': 'stale_processing',
                    'message': alert_msg,
                    'severity': 'medium',
                    'minutes_ago': time_since_last.total_seconds()/60
                })
        except Exception as e:
            logger.debug(f"Could not parse last_message_processed: {e}")
    
    # Alert: Service not active
    service_status = core_metrics.get('service_status', 'unknown')
    if service_status != 'active':
        alert_msg = f"ALERT: Ingestion service status is '{service_status}'"
        logger.warning(alert_msg)
        alerts.append({
            'type': 'service_inactive',
            'message': alert_msg,
            'severity': 'critical'
        })
    
    return alerts

def check_listener_status_alert():
    """Check if PostgreSQL LISTEN connection is active and alert if not."""
    try:
        import psycopg2
        import os
        
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM pg_stat_activity 
                    WHERE query = 'LISTEN "events"' AND state = 'idle'
                """)
                listener_count = cur.fetchone()[0]
                
                if listener_count == 0:
                    alert_msg = "ALERT: No active PostgreSQL LISTEN connections found"
                    logger.warning(alert_msg)
                    return {
                        'type': 'listener_inactive',
                        'message': alert_msg,
                        'severity': 'critical'
                    }
                
                return None
                
    except Exception as e:
        logger.error(f"Failed to check listener status: {e}")
        return {
            'type': 'listener_check_failed',
            'message': f"Failed to check listener status: {e}",
            'severity': 'medium'
        }
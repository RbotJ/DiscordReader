"""
Ingestion Dashboard Blueprint

Provides operational insights into message ingestion pipeline, processing metrics,
and validation statistics. This blueprint is isolated to the ingestion feature slice.
"""
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime, timedelta
import logging
from common.utils import utc_now

logger = logging.getLogger(__name__)

ingest_bp = Blueprint('ingest_dashboard', __name__,
                      template_folder='templates',
                      static_folder='static/ingest',
                      url_prefix='/dashboard/ingestion')

def get_ingestion_service():
    """Get ingestion service instance with proper error handling."""
    try:
        from features.ingestion.service import IngestionService
        return IngestionService()
    except ImportError as e:
        logger.warning(f"Could not import IngestionService: {e}")
        return None



@ingest_bp.route('/')
def overview():
    """Ingestion dashboard overview page."""
    try:
        service = get_ingestion_service()
        if service:
            raw_metrics = service.get_metrics()
            logger.debug(f"Raw metrics from service: {raw_metrics}")
            
            # Sanitize metrics to prevent template errors
            metrics = {
                'messages_ingested': raw_metrics.get('messages_ingested', 0),
                'ingestion_errors': raw_metrics.get('ingestion_errors', 0),
                'last_ingestion': raw_metrics.get('last_ingestion', None),
                'service_status': raw_metrics.get('service_status', 'unknown'),
                'service_type': raw_metrics.get('service_type', 'ingestion'),
                'status': raw_metrics.get('status', 'unknown'),
                # Template-specific metrics with defaults
                'messages_processed_today': raw_metrics.get('messages_processed_today', 0),
                'total_messages_stored': raw_metrics.get('total_messages_stored', 0),
                'validation_success_rate': raw_metrics.get('validation_success_rate', 100.0),
                'queue_depth': raw_metrics.get('queue_depth', 0),
                'avg_processing_time_ms': raw_metrics.get('avg_processing_time_ms', 0),
                'validation_failures_today': raw_metrics.get('validation_failures_today', 0),
                'last_processed_message': raw_metrics.get('last_processed_message', None)
            }
            
            # Ensure numeric values are actually numeric
            numeric_keys = [
                'messages_ingested', 'ingestion_errors', 'messages_processed_today',
                'total_messages_stored', 'validation_success_rate', 'queue_depth',
                'avg_processing_time_ms', 'validation_failures_today'
            ]
            for key in numeric_keys:
                if metrics[key] is None or not isinstance(metrics[key], (int, float)):
                    logger.warning(f"Metric {key} is not numeric: {metrics[key]}, defaulting to 0")
                    metrics[key] = 0.0 if 'rate' in key else 0
            
            recent_messages = service.get_recent_messages(limit=20)
            logger.debug(f"Sanitized metrics: {metrics}")
            logger.debug(f"All metric keys: {list(metrics.keys())}")
            logger.debug(f"validation_success_rate type: {type(metrics.get('validation_success_rate'))}, value: {metrics.get('validation_success_rate')}")
            
            return render_template('ingest/overview.html',
                                 metrics=metrics,
                                 recent_messages=recent_messages,
                                 current_time=utc_now())
        else:
            return render_template('ingest/error.html', 
                                 error="Ingestion service unavailable"), 500
    except Exception as e:
        logger.error(f"Error loading ingestion dashboard: {e}")
        return render_template('ingest/error.html', error=str(e)), 500

@ingest_bp.route('/metrics.json')
def metrics():
    """API endpoint for ingestion metrics."""
    try:
        service = get_ingestion_service()
        if service:
            ingestion_metrics = service.get_metrics()
            return jsonify({
                'metrics': ingestion_metrics,
                'timestamp': utc_now().isoformat()
            })
        else:
            return jsonify({'error': 'Ingestion service unavailable'}), 500
    except Exception as e:
        logger.error(f"Error getting ingestion metrics: {e}")
        return jsonify({'error': str(e)}), 500

@ingest_bp.route('/health')
def health():
    """Health check endpoint for ingestion pipeline."""
    try:
        service = get_ingestion_service()
        if service:
            metrics = service.get_metrics()
            is_healthy = metrics['status'] in ['ready', 'processing']
            
            return jsonify({
                'healthy': is_healthy,
                'status': metrics['status'],
                'timestamp': utc_now().isoformat()
            }), 200 if is_healthy else 503
        else:
            return jsonify({
                'healthy': False,
                'status': 'unavailable',
                'timestamp': utc_now().isoformat()
            }), 503
    except Exception as e:
        logger.error(f"Error checking ingestion health: {e}")
        return jsonify({'error': str(e)}), 500

@ingest_bp.route('/enhanced-metrics.json')
def enhanced_metrics():
    """API endpoint for enhanced ingestion metrics with uptime and duplicate handling."""
    try:
        service = get_ingestion_service()
        if service:
            metrics = service.get_metrics()
            
            # Check for alerts and log warnings
            from .alerts import check_ingestion_alerts, check_listener_status_alert
            
            # Extract enhanced metrics
            enhanced_data = {
                'core_metrics': {
                    'messages_ingested': metrics.get('messages_ingested', 0),
                    'ingestion_errors': metrics.get('ingestion_errors', 0),
                    'validation_success_rate': metrics.get('validation_success_rate', 100.0),
                    'service_status': metrics.get('service_status', 'unknown'),
                    'last_message_processed': metrics.get('last_message_processed')
                },
                'uptime_tracking': {
                    'uptime_seconds': metrics.get('uptime_seconds', 0),
                    'service_start_time': (utc_now() - timedelta(seconds=metrics.get('uptime_seconds', 0))).isoformat(),
                    'last_ingestion': metrics.get('last_ingestion')
                },
                'duplicate_handling': {
                    'duplicates_skipped': metrics.get('duplicates_skipped', 0),
                    'duplicates_skipped_today': metrics.get('duplicates_skipped_today', 0),
                    'total_processing_attempts': metrics.get('messages_ingested', 0) + metrics.get('duplicates_skipped', 0)
                },
                'daily_metrics': {
                    'messages_ingested_today': metrics.get('messages_ingested_today', 0),
                    'messages_processed_today': metrics.get('messages_processed_today', 0),
                    'validation_failures_today': metrics.get('validation_failures_today', 0)
                },
                'timestamp': utc_now().isoformat()
            }
            
            # Run alert checks and add to response
            ingestion_alerts = check_ingestion_alerts(enhanced_data)
            listener_alert = check_listener_status_alert()
            
            alerts = ingestion_alerts[:]
            if listener_alert:
                alerts.append(listener_alert)
            
            enhanced_data['alerts'] = alerts
            enhanced_data['alert_count'] = len(alerts)
            
            return jsonify(enhanced_data)
        else:
            return jsonify({'error': 'Ingestion service unavailable'}), 500
    except Exception as e:
        logger.error(f"Error getting enhanced ingestion metrics: {e}")
        return jsonify({'error': str(e)}), 500

@ingest_bp.route('/clear-data', methods=['POST'])
def clear_data():
    """Clear all stored messages from the ingestion pipeline."""
    try:
        service = get_ingestion_service()
        if service:
            cleared_count = service.clear_all_messages()
            logger.info(f"Cleared {cleared_count} messages from ingestion pipeline")
            
            return jsonify({
                'success': True,
                'cleared_count': cleared_count,
                'timestamp': utc_now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ingestion service unavailable'
            }), 500
    except Exception as e:
        logger.error(f"Error clearing ingestion data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
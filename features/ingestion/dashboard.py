"""
Ingestion Dashboard Blueprint

Provides operational insights into message ingestion pipeline, processing metrics,
and validation statistics. This blueprint is isolated to the ingestion feature slice.
"""
from flask import Blueprint, render_template, jsonify
from datetime import datetime, timedelta
import logging

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
                'status': raw_metrics.get('status', 'unknown')
            }
            
            # Ensure numeric values are actually numeric
            for key in ['messages_ingested', 'ingestion_errors']:
                if metrics[key] is None or not isinstance(metrics[key], (int, float)):
                    logger.warning(f"Metric {key} is not numeric: {metrics[key]}, defaulting to 0")
                    metrics[key] = 0
            
            recent_messages = service.get_recent_messages(limit=20)
            logger.debug(f"Sanitized metrics: {metrics}")
            
            return render_template('ingest/overview.html',
                                 metrics=metrics,
                                 recent_messages=recent_messages,
                                 current_time=datetime.utcnow())
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
                'timestamp': datetime.utcnow().isoformat()
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
                'timestamp': datetime.utcnow().isoformat()
            }), 200 if is_healthy else 503
        else:
            return jsonify({
                'healthy': False,
                'status': 'unavailable',
                'timestamp': datetime.utcnow().isoformat()
            }), 503
    except Exception as e:
        logger.error(f"Error checking ingestion health: {e}")
        return jsonify({'error': str(e)}), 500
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
                      template_folder='templates/ingest',
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
            metrics = service.get_metrics()
            return render_template('overview.html',
                                 metrics=metrics,
                                 current_time=datetime.utcnow())
        else:
            return render_template('error.html', 
                                 error="Ingestion service unavailable"), 500
    except Exception as e:
        logger.error(f"Error loading ingestion dashboard: {e}")
        return render_template('error.html', error=str(e)), 500

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
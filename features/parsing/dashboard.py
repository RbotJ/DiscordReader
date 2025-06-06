"""
Parsing Dashboard Module

Operational dashboard for monitoring parsing service health, performance metrics,
and managing parsed trade setups. Follows the discord_channels feature slice pattern.
"""
import logging
from datetime import date, datetime
from flask import Blueprint, render_template, request, jsonify

from .service import get_parsing_service
from .store import get_parsing_store

logger = logging.getLogger(__name__)

# Create blueprint for parsing dashboard
parsing_bp = Blueprint('parsing_dashboard', __name__,
                      template_folder='templates',
                      static_folder='static/parsing',
                      url_prefix='/dashboard/parsing')

def get_parsing_service_safe():
    """Get parsing service instance with proper error handling."""
    try:
        return get_parsing_service()
    except Exception as e:
        logger.warning(f"Could not get parsing service: {e}")
        return None

@parsing_bp.route('/')
def overview():
    """Parsing service dashboard overview page."""
    try:
        service = get_parsing_service_safe()
        if service:
            metrics = service.get_service_stats()
            logger.info(f"Parsing metrics: {metrics}")
            logger.info(f"Metrics type: {type(metrics)}")
            return render_template('parsing/overview.html',
                                 metrics=metrics,
                                 current_time=datetime.utcnow())
        else:
            return render_template('parsing/error.html', 
                                 error="Parsing service unavailable"), 500
    except Exception as e:
        logger.error(f"Error loading parsing dashboard: {e}")
        return render_template('parsing/error.html', error=str(e)), 500

@parsing_bp.route('/metrics.json')
def metrics():
    """Get parsing service metrics as JSON for AJAX updates."""
    try:
        service = get_parsing_service_safe()
        if service:
            metrics = service.get_service_stats()
            # Add operational timestamp
            metrics['dashboard_timestamp'] = datetime.utcnow().isoformat()
            return jsonify(metrics)
        else:
            return jsonify({'error': 'Parsing service unavailable'}), 503
    except Exception as e:
        logger.error(f"Error getting parsing metrics: {e}")
        return jsonify({'error': str(e)}), 500

@parsing_bp.route('/setups')
def setups_view():
    """View parsed setups with filtering"""
    try:
        trading_day_str = request.args.get('trading_day')
        ticker = request.args.get('ticker')
        
        # Parse trading day
        trading_day = None
        if trading_day_str:
            try:
                trading_day = datetime.strptime(trading_day_str, '%Y-%m-%d').date()
            except ValueError:
                trading_day = date.today()
        
        service = get_parsing_service_safe()
        if service:
            setups = service.get_active_setups(trading_day, ticker)
            return render_template('parsing/setups.html', 
                                 setups=setups, 
                                 trading_day=trading_day or date.today(),
                                 ticker=ticker)
        else:
            return render_template('parsing/error.html', 
                                 error="Parsing service unavailable"), 500
            
    except Exception as e:
        logger.error(f"Error loading setups view: {e}")
        return render_template('parsing/error.html', error=str(e)), 500

@parsing_bp.route('/setups.json')
def setups_json():
    """Get parsed setups as JSON"""
    try:
        trading_day_str = request.args.get('trading_day')
        ticker = request.args.get('ticker')
        
        trading_day = None
        if trading_day_str:
            try:
                trading_day = datetime.strptime(trading_day_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        service = get_parsing_service_safe()
        if service:
            setups = service.get_active_setups(trading_day, ticker)
            return jsonify({
                'setups': setups,
                'count': len(setups),
                'trading_day': trading_day.isoformat() if trading_day else None,
                'ticker': ticker
            })
        else:
            return jsonify({'error': 'Parsing service unavailable'}), 503
            
    except Exception as e:
        logger.error(f"Error getting setups JSON: {e}")
        return jsonify({'error': str(e)}), 500

@parsing_bp.route('/health')
def health():
    """Parsing service health check"""
    try:
        service = get_parsing_service_safe()
        if service and service.is_healthy():
            stats = service.get_service_stats()
            return jsonify({
                'status': 'healthy',
                'service_status': stats.get('service_status', 'unknown'),
                'messages_processed': stats.get('listener_stats', {}).get('messages_processed', 0),
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'status': 'unhealthy',
                'error': 'Service not available or unhealthy',
                'timestamp': datetime.utcnow().isoformat()
            }), 503
    except Exception as e:
        logger.error(f"Error in parsing health check: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

def register_dashboard_routes(app):
    """Register parsing dashboard routes"""
    app.register_blueprint(parsing_bp)
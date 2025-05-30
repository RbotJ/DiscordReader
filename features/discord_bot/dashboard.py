"""
Discord Bot Dashboard Blueprint

Provides operational insights into Discord bot status, metrics, and health monitoring.
This blueprint is isolated to the discord_bot feature slice.
"""
from flask import Blueprint, render_template, jsonify
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

discord_bp = Blueprint('discord_dashboard', __name__,
                       template_folder='templates/discord',
                       static_folder='static/discord',
                       url_prefix='/dashboard/discord')

def get_bot_status():
    """Get current bot connection status."""
    # This will be enhanced when bot is properly connected
    return {
        'status': 'disabled',  # connected, disconnected, error, disabled
        'last_ready': None,
        'uptime_seconds': 0,
        'error_message': 'Discord bot dependencies not available - bot disabled'
    }

def get_bot_metrics():
    """Get bot performance metrics."""
    return {
        'uptime_seconds': 0,
        'messages_processed_today': 0,
        'messages_per_minute': 0,
        'channels_monitored': 0,
        'error_count_last_hour': 0,
        'last_activity': None,
        'connection_attempts': 0,
        'successful_connections': 0
    }

@discord_bp.route('/')
def overview():
    """Discord bot dashboard overview page."""
    try:
        status = get_bot_status()
        metrics = get_bot_metrics()
        
        return render_template('overview.html',
                             status=status,
                             metrics=metrics,
                             current_time=datetime.utcnow())
    except Exception as e:
        logger.error(f"Error loading Discord dashboard: {e}")
        return render_template('error.html', error=str(e)), 500

@discord_bp.route('/metrics.json')
def metrics():
    """API endpoint for Discord bot metrics."""
    try:
        status = get_bot_status()
        bot_metrics = get_bot_metrics()
        
        return jsonify({
            'status': status,
            'metrics': bot_metrics,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting Discord metrics: {e}")
        return jsonify({'error': str(e)}), 500

@discord_bp.route('/health')
def health():
    """Health check endpoint for Discord bot."""
    status = get_bot_status()
    is_healthy = status['status'] == 'connected'
    
    return jsonify({
        'healthy': is_healthy,
        'status': status['status'],
        'timestamp': datetime.utcnow().isoformat()
    }), 200 if is_healthy else 503
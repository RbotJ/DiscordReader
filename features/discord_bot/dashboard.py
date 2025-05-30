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

def get_bot_service():
    """Get bot service instance with proper error handling."""
    try:
        from features.discord_bot.service import BotService
        return BotService()
    except ImportError as e:
        logger.warning(f"Could not import BotService: {e}")
        return None

@discord_bp.route('/')
def overview():
    """Discord bot dashboard overview page."""
    try:
        service = get_bot_service()
        if service:
            metrics = service.get_metrics()
            return render_template('overview.html',
                                 metrics=metrics,
                                 current_time=datetime.utcnow())
        else:
            return render_template('error.html', 
                                 error="Bot service unavailable"), 500
    except Exception as e:
        logger.error(f"Error loading Discord dashboard: {e}")
        return render_template('error.html', error=str(e)), 500

@discord_bp.route('/metrics.json')
def metrics():
    """API endpoint for Discord bot metrics."""
    try:
        service = get_bot_service()
        if service:
            bot_metrics = service.get_metrics()
            return jsonify({
                'metrics': bot_metrics,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({'error': 'Bot service unavailable'}), 500
    except Exception as e:
        logger.error(f"Error getting Discord metrics: {e}")
        return jsonify({'error': str(e)}), 500

@discord_bp.route('/health')
def health():
    """Health check endpoint for Discord bot."""
    try:
        service = get_bot_service()
        if service:
            metrics = service.get_metrics()
            is_healthy = metrics['status'] == 'connected'
            
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
        logger.error(f"Error checking Discord health: {e}")
        return jsonify({'error': str(e)}), 500
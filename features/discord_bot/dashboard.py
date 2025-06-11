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

def get_bot_metrics():
    """Get bot metrics directly from the bot instance in app config."""
    try:
        from flask import current_app
        bot = current_app.config.get('DISCORD_BOT')
        
        if not bot:
            return {
                'status': 'disconnected',
                'uptime_seconds': 0,
                'messages_processed_today': 0,
                'messages_per_minute': 0,
                'channels_monitored': 0,
                'error_count_last_hour': 0,
                'last_activity': None,
                'connection_attempts': 0,
                'successful_connections': 0,
                'last_ready': None,
                'error_message': 'Bot not initialized'
            }
        
        uptime_seconds = bot.get_uptime_seconds()
        logger.info(f"Dashboard metrics - Bot uptime: {uptime_seconds} seconds")
        
        return {
            'status': 'connected' if bot.is_ready() else 'disconnected',
            'uptime_seconds': uptime_seconds,
            'messages_processed_today': getattr(bot, '_messages_today', 0),
            'messages_per_minute': 0,  # Can be calculated if needed
            'channels_monitored': 1 if bot.aplus_setups_channel_id else 0,
            'error_count_last_hour': getattr(bot, '_storage_errors_today', 0),
            'storage_errors_today': getattr(bot, '_storage_errors_today', 0),
            'last_storage_error': getattr(bot, '_last_storage_error', None),
            'last_activity': datetime.utcnow().isoformat(),
            'connection_attempts': 1,
            'successful_connections': 1 if bot.is_ready() else 0,
            'last_ready': datetime.utcnow().isoformat() if bot.is_ready() else None,
            'error_message': None
        }
    except Exception as e:
        logger.error(f"Error getting bot metrics: {e}")
        return {
            'status': 'error',
            'uptime_seconds': 0,
            'messages_processed_today': 0,
            'messages_per_minute': 0,
            'channels_monitored': 0,
            'error_count_last_hour': 0,
            'last_activity': None,
            'connection_attempts': 0,
            'successful_connections': 0,
            'last_ready': None,
            'error_message': str(e)
        }

@discord_bp.route('/')
def overview():
    """Discord bot dashboard overview page."""
    try:
        metrics = get_bot_metrics()
        return render_template('overview.html',
                             metrics=metrics,
                             current_time=datetime.utcnow())
    except Exception as e:
        logger.error(f"Error loading Discord dashboard: {e}")
        return render_template('error.html', error=str(e)), 500

@discord_bp.route('/metrics.json')
def metrics():
    """API endpoint for Discord bot metrics."""
    try:
        bot_metrics = get_bot_metrics()
        return jsonify({
            'metrics': bot_metrics,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting Discord metrics: {e}")
        return jsonify({'error': str(e)}), 500

@discord_bp.route('/health')
def health():
    """Health check endpoint for Discord bot."""
    try:
        metrics = get_bot_metrics()
        is_healthy = metrics['status'] == 'connected'
        
        return jsonify({
            'healthy': is_healthy,
            'status': metrics['status'],
            'timestamp': datetime.utcnow().isoformat()
        }), 200 if is_healthy else 503
    except Exception as e:
        logger.error(f"Error checking Discord health: {e}")
        return jsonify({'error': str(e)}), 500
"""
Discord Bot API Endpoints

Provides live metrics and status endpoints for the Discord bot slice.
Stays within vertical slice boundaries - only exposes Discord bot data.
"""
from flask import Blueprint, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

discord_api_bp = Blueprint('discord_api', __name__, url_prefix='/api/discord')


@discord_api_bp.route('/metrics', methods=['GET'])
def get_discord_metrics():
    """
    Get live Discord bot metrics.
    
    Returns real-time counters from the bot instance without database dependency.
    This ensures metrics show actual bot activity regardless of storage issues.
    """
    try:
        # Get bot instance from app config
        bot = current_app.config.get('DISCORD_BOT')
        
        if not bot:
            return jsonify({
                'error': 'Discord bot not initialized',
                'connected': False,
                'live_messages_today': 0,
                'triggers_today': 0,
                'latency_ms': None
            }), 503
        
        # Collect live metrics from bot instance
        metrics = {
            'connected': bot.is_ready(),
            'latency_ms': round(bot.latency * 1000) if bot.latency else None,
            'live_messages_today': bot._messages_today,
            'triggers_today': bot._triggers_today,
            'target_channel_id': bot.aplus_setups_channel_id,
            'last_reset_date': bot._last_reset_date.isoformat() if bot._last_reset_date else None
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error retrieving Discord metrics: {e}")
        return jsonify({
            'error': 'Failed to retrieve metrics',
            'connected': False,
            'live_messages_today': 0,
            'triggers_today': 0,
            'latency_ms': None
        }), 500


@discord_api_bp.route('/status', methods=['GET'])
def get_discord_status():
    """Get basic Discord bot connection status."""
    try:
        bot = current_app.config.get('DISCORD_BOT')
        
        if not bot:
            return jsonify({'status': 'not_initialized'}), 503
        
        return jsonify({
            'status': 'connected' if bot.is_ready() else 'disconnected',
            'user': str(bot.user) if bot.user else None,
            'latency_ms': round(bot.latency * 1000) if bot.latency else None
        })
        
    except Exception as e:
        logger.error(f"Error retrieving Discord status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
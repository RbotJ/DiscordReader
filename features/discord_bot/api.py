"""
Discord Bot API Endpoints

Provides live metrics and status endpoints for the Discord bot slice.
Stays within vertical slice boundaries - only exposes Discord bot data.
"""
from flask import Blueprint, jsonify, current_app, request
import logging
import asyncio
from datetime import datetime

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


@discord_api_bp.route('/sync-history', methods=['POST'])
def sync_message_history():
    """
    Manually trigger message history synchronization.
    
    Optional JSON parameters:
    - limit: Number of messages to sync (default 50, max 200)
    - before_id: Sync messages before this message ID
    """
    try:
        bot = current_app.config.get('DISCORD_BOT')
        
        if not bot:
            return jsonify({
                'success': False,
                'error': 'Discord bot not initialized'
            }), 503
            
        if not bot.is_ready():
            return jsonify({
                'success': False,
                'error': 'Discord bot not connected'
            }), 503
            
        if not bot.aplus_setups_channel_id:
            return jsonify({
                'success': False,
                'error': 'No target channel configured'
            }), 400
        
        # Parse request parameters
        data = request.get_json() if request.is_json else {}
        limit = min(data.get('limit', 50), 200)  # Cap at 200 for safety
        before_id = data.get('before_id')
        
        # Publish sync start event
        from common.events.bus import publish_cross_slice_event
        publish_cross_slice_event(
            "discord.sync_started",
            {
                "channel_id": str(bot.aplus_setups_channel_id),
                "limit": limit,
                "before_id": before_id,
                "source": "manual_api",
                "started_at": datetime.now().isoformat()
            },
            "discord_bot"
        )
        
        # Run async sync operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                bot._manual_sync_history(limit=limit, before_id=before_id)
            )
        finally:
            loop.close()
        
        # Publish completion event
        publish_cross_slice_event(
            "discord.sync_completed",
            {
                "channel_id": str(bot.aplus_setups_channel_id),
                "result": result,
                "completed_at": datetime.now().isoformat()
            },
            "discord_bot"
        )
        
        return jsonify({
            'success': True,
            'result': result,
            'channel_id': str(bot.aplus_setups_channel_id),
            'limit': limit
        })
        
    except Exception as e:
        logger.error(f"Error during manual message sync: {e}")
        
        # Publish error event
        try:
            from common.events.bus import publish_cross_slice_event
            publish_cross_slice_event(
                "discord.sync_failed",
                {
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                },
                "discord_bot"
            )
        except:
            pass  # Don't fail on event publishing errors
            
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
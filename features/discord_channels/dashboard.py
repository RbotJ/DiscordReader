"""
Discord Channels Dashboard Blueprint

Provides operational insights into Discord channel management, monitoring status,
and channel discovery metrics. This blueprint is isolated to the discord_channels feature slice.
"""
from flask import Blueprint, render_template, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

channels_bp = Blueprint('channels_dashboard', __name__,
                        template_folder='templates',
                        static_folder='static/channels',
                        url_prefix='/dashboard/channels')

def get_channel_manager():
    """Get channel manager instance with proper error handling."""
    try:
        from features.discord_channels.channel_manager import ChannelManager
        return ChannelManager()
    except ImportError as e:
        logger.warning(f"Could not import ChannelManager: {e}")
        return None



@channels_bp.route('/')
def overview():
    """Discord channels dashboard overview page."""
    try:
        manager = get_channel_manager()
        if manager:
            metrics = manager.get_metrics()
            logger.info(f"Channel metrics: {metrics}")
            logger.info(f"Metrics type: {type(metrics)}")
            return render_template('channels/overview.html',
                                 metrics=metrics,
                                 current_time=datetime.utcnow())
        else:
            return render_template('channels/error.html', 
                                 error="Channel manager unavailable"), 500
    except Exception as e:
        logger.error(f"Error loading channels dashboard: {e}")
        logger.error(f"Exception type: {type(e)}")
        return render_template('channels/error.html', error=str(e)), 500

@channels_bp.route('/metrics.json')
def metrics():
    """API endpoint for Discord channels metrics."""
    try:
        manager = get_channel_manager()
        if manager:
            channel_metrics = manager.get_metrics()
            return jsonify({
                'metrics': channel_metrics,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({'error': 'Channel manager unavailable'}), 500
    except Exception as e:
        logger.error(f"Error getting channel metrics: {e}")
        return jsonify({'error': str(e)}), 500

@channels_bp.route('/health')
def health():
    """Health check endpoint for channel management."""
    try:
        manager = get_channel_manager()
        if manager:
            metrics = manager.get_metrics()
            is_healthy = metrics['sync_status'] in ['ready', 'syncing']
            
            return jsonify({
                'healthy': is_healthy,
                'sync_status': metrics['sync_status'],
                'timestamp': datetime.utcnow().isoformat()
            }), 200 if is_healthy else 503
        else:
            return jsonify({
                'healthy': False,
                'sync_status': 'unavailable',
                'timestamp': datetime.utcnow().isoformat()
            }), 503
    except Exception as e:
        logger.error(f"Error checking channel health: {e}")
        return jsonify({'error': str(e)}), 500
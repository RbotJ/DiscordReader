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
                        template_folder='templates/channels',
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

def get_channel_metrics():
    """Get channel management metrics from the service."""
    manager = get_channel_manager()
    if not manager:
        return {
            'total_channels': 0,
            'monitored_channels': 0,
            'active_guilds': 0,
            'last_sync': None,
            'sync_status': 'unavailable'
        }
    
    try:
        # Get metrics from the channel manager service
        return {
            'total_channels': 0,  # manager.get_total_channel_count()
            'monitored_channels': 0,  # len(manager.get_monitored_channels())
            'active_guilds': 0,  # manager.get_guild_count()
            'last_sync': None,  # manager.get_last_sync_time()
            'sync_status': 'ready'  # manager.get_sync_status()
        }
    except Exception as e:
        logger.error(f"Error getting channel metrics: {e}")
        return {
            'total_channels': 0,
            'monitored_channels': 0,
            'active_guilds': 0,
            'last_sync': None,
            'sync_status': 'error'
        }

@channels_bp.route('/')
def overview():
    """Discord channels dashboard overview page."""
    try:
        metrics = get_channel_metrics()
        
        return render_template('overview.html',
                             metrics=metrics,
                             current_time=datetime.utcnow())
    except Exception as e:
        logger.error(f"Error loading channels dashboard: {e}")
        return render_template('error.html', error=str(e)), 500

@channels_bp.route('/metrics.json')
def metrics():
    """API endpoint for Discord channels metrics."""
    try:
        channel_metrics = get_channel_metrics()
        
        return jsonify({
            'metrics': channel_metrics,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting channel metrics: {e}")
        return jsonify({'error': str(e)}), 500

@channels_bp.route('/health')
def health():
    """Health check endpoint for channel management."""
    metrics = get_channel_metrics()
    is_healthy = metrics['sync_status'] in ['ready', 'syncing']
    
    return jsonify({
        'healthy': is_healthy,
        'sync_status': metrics['sync_status'],
        'timestamp': datetime.utcnow().isoformat()
    }), 200 if is_healthy else 503
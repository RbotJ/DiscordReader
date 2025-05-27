"""
Discord Admin Routes

Flask routes for Discord channel management and monitoring.
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template
from sqlalchemy import desc

from common.db import db
from features.ingestion.models import DiscordMessageModel
from features.parsing.models import SetupModel
from features.discord.channel_sync import (
    set_channel_listen, set_channel_announce, 
    get_listening_channels, get_announce_channels
)

logger = logging.getLogger(__name__)

# Create Blueprint
discord_admin_bp = Blueprint('discord_admin', __name__, url_prefix='/admin/discord')

# =============================================================================
# WEB PAGES
# =============================================================================

@discord_admin_bp.route('/channels')
def channels_page():
    """Discord channels management page."""
    return render_template('discord/channels.html')

@discord_admin_bp.route('/messages')
def messages_page():
    """Discord messages monitoring page."""
    return render_template('discord/messages.html')

@discord_admin_bp.route('/tickers')
def tickers_page():
    """Discord ticker activity page."""
    return render_template('discord/tickers.html')

# =============================================================================
# API ENDPOINTS
# =============================================================================

@discord_admin_bp.route('/api/channels', methods=['GET'])
def get_channels():
    """Get all Discord channels."""
    try:
        channels = DiscordChannelModel.query.order_by(DiscordChannelModel.name).all()
        
        channels_data = []
        for channel in channels:
            channels_data.append({
                'id': channel.id,
                'guild_id': channel.guild_id,
                'channel_id': channel.channel_id,
                'name': channel.name,
                'channel_type': channel.channel_type,
                'is_listen': channel.is_listen,
                'is_announce': channel.is_announce,
                'is_active': channel.is_active,
                'last_seen': channel.last_seen.isoformat() if channel.last_seen else None,
                'created_at': channel.created_at.isoformat() if channel.created_at else None
            })
        
        return jsonify({
            'status': 'success',
            'channels': channels_data,
            'total': len(channels_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching channels: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@discord_admin_bp.route('/api/channels/config', methods=['POST'])
def update_channel_config():
    """Update channel configuration."""
    try:
        data = request.get_json()
        channel_id = data.get('channel_id')
        config_type = data.get('type')  # 'listen' or 'announce'
        enabled = data.get('enabled', False)
        
        if not channel_id or config_type not in ['listen', 'announce']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid parameters'
            }), 400
        
        success = False
        if config_type == 'listen':
            success = set_channel_listen(channel_id, enabled)
        elif config_type == 'announce':
            success = set_channel_announce(channel_id, enabled)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Channel {config_type} setting updated'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update channel configuration'
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating channel config: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@discord_admin_bp.route('/api/messages/recent', methods=['GET'])
def get_recent_messages():
    """Get recent Discord messages from A+ setups."""
    try:
        # Get last 5 messages from setup_messages table
        messages = SetupMessageModel.query.filter_by(
            source='discord'
        ).order_by(desc(SetupMessageModel.created_at)).limit(5).all()
        
        messages_data = []
        for msg in messages:
            # Parse raw_text to extract author if possible
            author = "Unknown"
            if hasattr(msg, 'parsed_data') and msg.parsed_data:
                author = msg.parsed_data.get('author', 'Unknown')
            
            messages_data.append({
                'id': msg.id,
                'content_preview': msg.raw_text[:100] + '...' if len(msg.raw_text) > 100 else msg.raw_text,
                'full_content': msg.raw_text,
                'author': author,
                'date': msg.date.isoformat(),
                'created_at': msg.created_at.isoformat(),
                'source': msg.source
            })
        
        return jsonify({
            'status': 'success',
            'messages': messages_data,
            'total': len(messages_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching recent messages: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@discord_admin_bp.route('/api/tickers/activity', methods=['GET'])
def get_ticker_activity():
    """Get ticker activity for the last 3 days."""
    try:
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=2)  # Last 3 days including today
        
        # Query ticker setups for the date range
        # Note: Using existing schema without setup_message_id relationship
        ticker_setups = TickerSetupModel.query.filter(
            TickerSetupModel.created_at >= start_date,
            TickerSetupModel.created_at <= end_date
        ).all()
        
        # Group by date and ticker
        activity_by_date = {}
        
        for setup in ticker_setups:
            setup_date = setup.created_at.date().isoformat()
            ticker = setup.symbol
            
            if setup_date not in activity_by_date:
                activity_by_date[setup_date] = {}
            
            if ticker not in activity_by_date[setup_date]:
                activity_by_date[setup_date][ticker] = {
                    'ticker': ticker,
                    'setup_count': 0,
                    'categories': [],
                    'price_levels': []
                }
            
            activity_by_date[setup_date][ticker]['setup_count'] += 1
            if setup.category:
                activity_by_date[setup_date][ticker]['categories'].append(setup.category)
            if setup.price_level:
                activity_by_date[setup_date][ticker]['price_levels'].append(setup.price_level)
        
        # Convert to list format
        activity_data = []
        for date_str in sorted(activity_by_date.keys(), reverse=True):
            tickers_for_date = list(activity_by_date[date_str].values())
            activity_data.append({
                'date': date_str,
                'tickers': tickers_for_date,
                'total_tickers': len(tickers_for_date),
                'total_setups': sum(t['setup_count'] for t in tickers_for_date)
            })
        
        return jsonify({
            'status': 'success',
            'activity': activity_data,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching ticker activity: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@discord_admin_bp.route('/api/stats', methods=['GET'])
def get_discord_stats():
    """Get Discord integration statistics."""
    try:
        # Channel stats
        total_channels = DiscordChannelModel.query.count()
        listening_channels = DiscordChannelModel.query.filter_by(is_listen=True).count()
        announce_channels = DiscordChannelModel.query.filter_by(is_announce=True).count()
        
        # Message stats
        total_messages = SetupMessageModel.query.filter_by(source='discord').count()
        today_messages = SetupMessageModel.query.filter(
            SetupMessageModel.source == 'discord',
            SetupMessageModel.date == datetime.now().date()
        ).count()
        
        # Setup stats
        total_setups = TickerSetupModel.query.count()
        
        return jsonify({
            'status': 'success',
            'stats': {
                'channels': {
                    'total': total_channels,
                    'listening': listening_channels,
                    'announcing': announce_channels
                },
                'messages': {
                    'total': total_messages,
                    'today': today_messages
                },
                'setups': {
                    'total': total_setups
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching Discord stats: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
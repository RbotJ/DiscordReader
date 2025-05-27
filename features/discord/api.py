
"""
Discord API Routes

Optional REST endpoints for triggering Discord operations
"""
from flask import Blueprint, jsonify, request
import asyncio
import logging

from .service import discord_service

logger = logging.getLogger(__name__)

# Create blueprint
discord_api = Blueprint('discord_api', __name__, url_prefix='/api/discord')

@discord_api.route('/fetch', methods=['POST'])
def fetch_messages():
    """
    Trigger message fetching and storage
    
    Body (optional):
    {
        "limit": 50
    }
    """
    try:
        data = request.get_json() or {}
        limit = data.get('limit', 50)
        
        # Run async operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                discord_service.process_latest_messages(limit)
            )
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"API error fetching messages: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@discord_api.route('/latest', methods=['POST'])
def fetch_latest():
    """Fetch and store the latest single message"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            stored_id = loop.run_until_complete(
                discord_service.fetch_and_store_single_message()
            )
        finally:
            loop.close()
        
        if stored_id:
            return jsonify({
                'success': True,
                'stored_id': stored_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No message stored'
            })
            
    except Exception as e:
        logger.error(f"API error fetching latest message: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@discord_api.route('/status', methods=['GET'])
def get_status():
    """Get Discord integration status"""
    # Could add health checks, last message info, etc.
    return jsonify({
        'status': 'active',
        'service': 'discord_integration'
    })

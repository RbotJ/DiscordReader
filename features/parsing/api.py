"""
Parsing API Routes

API endpoints for parsing trading messages and managing parsed data.
Part of the vertical slice architecture migration.
"""
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime

from .parser import MessageParser
from features.parsing.store import SetupStore

logger = logging.getLogger(__name__)

# Create blueprint for parsing routes
parsing_bp = Blueprint('parsing', __name__, url_prefix='/api/parsing')
parser = MessageParser()
store = SetupStore()

@parsing_bp.route('/parse', methods=['POST'])
def parse_message():
    """Parse a trading message and extract setups"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message content required'}), 400
        
        message_text = data['message']
        message_id = data.get('message_id', None)
        
        # Parse the message
        setups = parser.parse_message(message_text, message_id)
        
        if not setups:
            return jsonify({
                'success': True,
                'setups': [],
                'message': 'No trading setups found in message'
            })
        
        # Convert to dictionary format for JSON response
        setup_data = []
        for setup in setups:
            setup_data.append({
                'ticker': setup.ticker,
                'setup_type': setup.setup_type,
                'direction': setup.direction,
                'price_level': setup.price_level,
                'confidence': setup.confidence
            })
        
        return jsonify({
            'success': True,
            'setups': setup_data,
            'count': len(setups)
        })
        
    except Exception as e:
        logger.error(f"Error parsing message: {e}")
        return jsonify({'error': 'Failed to parse message'}), 500

@parsing_bp.route('/health', methods=['GET'])
def health():
    """Health check for parsing service"""
    return jsonify({
        'status': 'healthy',
        'service': 'parsing',
        'timestamp': datetime.now().isoformat()
    })

def register_routes(app):
    """Register parsing routes with the Flask app"""
    app.register_blueprint(parsing_bp)
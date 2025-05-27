"""
Authentication Routes Module

This module provides routes for authentication-related features.
"""
import json
import logging
from flask import Blueprint, jsonify, request
from features.setups.auth import generate_signature

logger = logging.getLogger(__name__)
auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/api/auth/generate-signature', methods=['POST'])
def generate_auth_signature():
    """
    Generate authentication signature for testing webhooks.
    
    Accepts:
        - text: The setup message text
        - source: The setup source
        - timestamp: Optional Unix timestamp
        
    Returns:
        JSON with headers for webhook
    """
    if not request.is_json:
        return jsonify({
            'status': 'error',
            'message': 'Request must be JSON'
        }), 400
        
    data = request.get_json()
    
    # Validate inputs
    text = data.get('text')
    source = data.get('source', 'webhook')
    timestamp = data.get('timestamp')
    
    if not text:
        return jsonify({
            'status': 'error',
            'message': 'Text is required'
        }), 400
        
    # Create the payload that will be sent to the webhook
    payload = {
        'text': text,
        'source': source
    }
    
    # Generate signature for this payload
    payload_bytes = json.dumps(payload).encode()
    headers = generate_signature(payload_bytes, timestamp)
    
    return jsonify({
        'status': 'success',
        'headers': headers
    })

def register_routes(app):
    """Register authentication routes with Flask app."""
    app.register_blueprint(auth_blueprint)
    logger.info("Auth routes registered")
"""
Setups API Module

Flask blueprint for setup management endpoints including:
- Setup parsing from Discord messages
- Signal retrieval and management
- Setup status updates
"""
import logging
from datetime import datetime, date
from flask import Blueprint, jsonify, request

from .models import SetupMessage, TickerSetup, Signal
from .service import SetupService
from common.db import db

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
setups_bp = Blueprint('setups', __name__, url_prefix='/api/setups')

def get_setup_service():
    """Get setup service instance."""
    return SetupService()

@setups_bp.route('/messages', methods=['GET'])
def get_setup_messages():
    """Get setup messages with optional filtering."""
    try:
        processed = request.args.get('processed', type=bool)
        limit = request.args.get('limit', 50, type=int)
        
        query = SetupMessage.query
        if processed is not None:
            query = query.filter_by(is_processed=processed)
        
        messages = query.order_by(SetupMessage.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'messages': [{
                'id': msg.id,
                'message_id': msg.message_id,
                'channel_id': msg.channel_id,
                'content': msg.content[:200] + '...' if len(msg.content) > 200 else msg.content,
                'is_processed': msg.is_processed,
                'processing_status': msg.processing_status,
                'created_at': msg.created_at.isoformat(),
                'ticker_count': len(msg.ticker_setups)
            } for msg in messages],
            'total': len(messages)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving setup messages: {e}")
        return jsonify({'error': 'Failed to retrieve setup messages'}), 500

@setups_bp.route('/messages/<message_id>', methods=['GET'])
def get_setup_message(message_id):
    """Get a specific setup message by ID."""
    try:
        message = SetupMessage.get_by_message_id(message_id)
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        return jsonify({
            'id': message.id,
            'message_id': message.message_id,
            'channel_id': message.channel_id,
            'author_id': message.author_id,
            'content': message.content,
            'is_processed': message.is_processed,
            'processing_status': message.processing_status,
            'created_at': message.created_at.isoformat(),
            'ticker_setups': [{
                'id': setup.id,
                'symbol': setup.symbol,
                'setup_type': setup.setup_type,
                'direction': setup.direction,
                'entry_price': float(setup.entry_price) if setup.entry_price else None,
                'target_price': float(setup.target_price) if setup.target_price else None,
                'stop_loss': float(setup.stop_loss) if setup.stop_loss else None,
                'status': setup.status,
                'signal_count': len(setup.signals)
            } for setup in message.ticker_setups]
        })
        
    except Exception as e:
        logger.error(f"Error retrieving setup message {message_id}: {e}")
        return jsonify({'error': 'Failed to retrieve setup message'}), 500

@setups_bp.route('/tickers', methods=['GET'])
def get_ticker_setups():
    """Get ticker setups with optional filtering."""
    try:
        symbol = request.args.get('symbol')
        active_only = request.args.get('active_only', True, type=bool)
        limit = request.args.get('limit', 50, type=int)
        
        if active_only:
            setups = TickerSetup.get_active_setups(symbol)
        else:
            query = TickerSetup.query
            if symbol:
                query = query.filter_by(symbol=symbol.upper())
            setups = query.order_by(TickerSetup.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'setups': [{
                'id': setup.id,
                'symbol': setup.symbol,
                'setup_type': setup.setup_type,
                'direction': setup.direction,
                'entry_price': float(setup.entry_price) if setup.entry_price else None,
                'target_price': float(setup.target_price) if setup.target_price else None,
                'stop_loss': float(setup.stop_loss) if setup.stop_loss else None,
                'confidence': float(setup.confidence) if setup.confidence else None,
                'status': setup.status,
                'created_at': setup.created_at.isoformat(),
                'signal_count': len(setup.signals)
            } for setup in setups],
            'total': len(setups)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving ticker setups: {e}")
        return jsonify({'error': 'Failed to retrieve ticker setups'}), 500

@setups_bp.route('/tickers/<int:setup_id>', methods=['GET'])
def get_ticker_setup(setup_id):
    """Get a specific ticker setup by ID."""
    try:
        setup = TickerSetup.query.get(setup_id)
        if not setup:
            return jsonify({'error': 'Setup not found'}), 404
        
        return jsonify({
            'id': setup.id,
            'symbol': setup.symbol,
            'setup_type': setup.setup_type,
            'direction': setup.direction,
            'entry_price': float(setup.entry_price) if setup.entry_price else None,
            'target_price': float(setup.target_price) if setup.target_price else None,
            'stop_loss': float(setup.stop_loss) if setup.stop_loss else None,
            'confidence': float(setup.confidence) if setup.confidence else None,
            'status': setup.status,
            'notes': setup.notes,
            'created_at': setup.created_at.isoformat(),
            'signals': [{
                'id': signal.id,
                'signal_type': signal.signal_type,
                'trigger_price': float(signal.trigger_price) if signal.trigger_price else None,
                'target_price': float(signal.target_price) if signal.target_price else None,
                'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                'confidence': float(signal.confidence) if signal.confidence else None,
                'status': signal.status,
                'created_at': signal.created_at.isoformat()
            } for signal in setup.signals]
        })
        
    except Exception as e:
        logger.error(f"Error retrieving ticker setup {setup_id}: {e}")
        return jsonify({'error': 'Failed to retrieve ticker setup'}), 500

@setups_bp.route('/tickers/<int:setup_id>/status', methods=['PUT'])
def update_setup_status(setup_id):
    """Update the status of a ticker setup."""
    try:
        setup = TickerSetup.query.get(setup_id)
        if not setup:
            return jsonify({'error': 'Setup not found'}), 404
        
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        setup.status = data['status']
        setup.updated_at = datetime.utcnow()
        
        if 'notes' in data:
            setup.notes = data['notes']
        
        db.session.commit()
        
        return jsonify({
            'id': setup.id,
            'symbol': setup.symbol,
            'status': setup.status,
            'updated_at': setup.updated_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error updating setup status {setup_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update setup status'}), 500

@setups_bp.route('/parse', methods=['POST'])
def parse_setup_message():
    """Parse a setup message and extract trading setups."""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Message content is required'}), 400
        
        service = get_setup_service()
        result = service.parse_message_content(
            content=data['content'],
            message_id=data.get('message_id', ''),
            channel_id=data.get('channel_id', ''),
            author_id=data.get('author_id', ''),
            source=data.get('source', 'api')
        )
        
        return jsonify({
            'success': True,
            'message_id': result.get('message_id'),
            'ticker_setups_created': result.get('ticker_setups_created', 0),
            'signals_created': result.get('signals_created', 0)
        })
        
    except Exception as e:
        logger.error(f"Error parsing setup message: {e}")
        return jsonify({'error': 'Failed to parse setup message'}), 500

@setups_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the setups service."""
    try:
        # Test database connectivity
        db.session.execute('SELECT 1')
        
        # Get some basic stats
        total_messages = SetupMessage.query.count()
        processed_messages = SetupMessage.query.filter_by(is_processed=True).count()
        active_setups = TickerSetup.query.filter_by(status='active').count()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'stats': {
                'total_messages': total_messages,
                'processed_messages': processed_messages,
                'active_setups': active_setups
            }
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
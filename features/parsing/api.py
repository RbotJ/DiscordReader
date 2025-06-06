"""
Parsing API Routes

API endpoints for parsing trading messages and managing parsed data.
Part of the vertical slice architecture migration.
"""
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime, date

from .parser import MessageParser
from .store import get_parsing_store
from .listener import get_parsing_listener

logger = logging.getLogger(__name__)

# Create blueprint for parsing routes
parsing_bp = Blueprint('parsing', __name__, url_prefix='/api/parsing')

@parsing_bp.route('/parse', methods=['POST'])
def parse_message():
    """Parse a trading message and extract setups"""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Message content required'}), 400
        
        message_data = {
            'content': data['content'],
            'message_id': data.get('message_id', f"manual_{int(datetime.now().timestamp())}"),
            'author_id': data.get('author_id'),
            'channel_id': data.get('channel_id'),
            'timestamp': data.get('timestamp', datetime.now().isoformat())
        }
        
        # Process manually using the listener
        listener = get_parsing_listener()
        result = listener.process_message_manually(message_data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error parsing message: {e}")
        return jsonify({'error': 'Failed to parse message'}), 500

@parsing_bp.route('/setups', methods=['GET'])
def get_setups():
    """Get parsed setups with optional filtering"""
    try:
        # Query parameters
        trading_day_str = request.args.get('trading_day')
        ticker = request.args.get('ticker')
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        # Parse trading day
        trading_day = None
        if trading_day_str:
            try:
                trading_day = datetime.strptime(trading_day_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        store = get_parsing_store()
        
        if trading_day:
            setups = store.get_active_setups_for_day(trading_day)
        else:
            setups = store.get_active_setups_for_day(date.today())
        
        # Filter by ticker if specified
        if ticker:
            setups = [setup for setup in setups if setup.ticker.upper() == ticker.upper()]
        
        # Filter by active status
        if active_only:
            setups = [setup for setup in setups if setup.active]
        
        # Convert to dict format
        setup_list = []
        for setup in setups:
            setup_dict = setup.to_dict()
            # Get levels for this setup
            levels = store.get_levels_by_setup(setup.id)
            setup_dict['levels'] = [level.to_dict() for level in levels]
            setup_list.append(setup_dict)
        
        return jsonify({
            'success': True,
            'setups': setup_list,
            'count': len(setup_list),
            'filters': {
                'trading_day': trading_day.isoformat() if trading_day else None,
                'ticker': ticker,
                'active_only': active_only
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting setups: {e}")
        return jsonify({'error': 'Failed to get setups'}), 500

@parsing_bp.route('/setups/<int:setup_id>', methods=['GET'])
def get_setup(setup_id):
    """Get a specific setup by ID"""
    try:
        from .models import TradeSetup
        store = get_parsing_store()
        setup = store.session.query(TradeSetup).filter_by(id=setup_id).first()
        
        if not setup:
            return jsonify({'error': 'Setup not found'}), 404
        
        # Get levels for this setup
        levels = store.get_levels_by_setup(setup_id)
        
        setup_dict = setup.to_dict()
        setup_dict['levels'] = [level.to_dict() for level in levels]
        
        return jsonify({
            'success': True,
            'setup': setup_dict
        })
        
    except Exception as e:
        logger.error(f"Error getting setup {setup_id}: {e}")
        return jsonify({'error': 'Failed to get setup'}), 500

@parsing_bp.route('/setups/<int:setup_id>/deactivate', methods=['POST'])
def deactivate_setup(setup_id):
    """Deactivate a setup"""
    try:
        store = get_parsing_store()
        success = store.deactivate_setup(setup_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Setup deactivated'})
        else:
            return jsonify({'error': 'Setup not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deactivating setup {setup_id}: {e}")
        return jsonify({'error': 'Failed to deactivate setup'}), 500

@parsing_bp.route('/levels/<int:level_id>/trigger', methods=['POST'])
def trigger_level(level_id):
    """Trigger a level"""
    try:
        store = get_parsing_store()
        success = store.trigger_level(level_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Level triggered'})
        else:
            return jsonify({'error': 'Level not found'}), 404
            
    except Exception as e:
        logger.error(f"Error triggering level {level_id}: {e}")
        return jsonify({'error': 'Failed to trigger level'}), 500

@parsing_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get parsing service statistics"""
    try:
        store = get_parsing_store()
        listener = get_parsing_listener()
        
        parsing_stats = store.get_parsing_statistics()
        listener_stats = listener.get_stats()
        
        return jsonify({
            'success': True,
            'parsing_stats': parsing_stats,
            'listener_stats': listener_stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@parsing_bp.route('/health', methods=['GET'])
def health():
    """Health check for parsing service"""
    try:
        listener = get_parsing_listener()
        stats = listener.get_stats()
        
        return jsonify({
            'status': 'healthy',
            'service': 'parsing',
            'listener_status': stats.get('status', 'unknown'),
            'messages_processed': stats.get('messages_processed', 0),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'parsing',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def register_routes(app):
    """Register parsing routes with the Flask app"""
    app.register_blueprint(parsing_bp)
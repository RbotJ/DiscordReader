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

# Create blueprint for parsing API routes
parsing_api_bp = Blueprint('parsing_api', __name__, url_prefix='/api/parsing')

@parsing_api_bp.route('/parse', methods=['POST'])
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

@parsing_api_bp.route('/setups', methods=['GET'])
def get_setups():
    """Get parsed setups with optional filtering"""
    try:
        # Query parameters
        trading_day_str = request.args.get('trading_day')
        ticker = request.args.get('ticker')
        label = request.args.get('label')  # New filter for setup labels
        direction = request.args.get('direction')  # New filter for direction (long/short)
        index = request.args.get('index', type=int)  # New filter for setup index
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
        
        # Apply filters
        if ticker:
            setups = [setup for setup in setups if setup.ticker.upper() == ticker.upper()]
        
        if label:
            setups = [setup for setup in setups if setup.label and setup.label.lower() == label.lower()]
        
        if direction:
            setups = [setup for setup in setups if setup.direction and setup.direction.lower() == direction.lower()]
        
        if index is not None:
            setups = [setup for setup in setups if setup.index == index]
        
        if active_only:
            setups = [setup for setup in setups if setup.active]
        
        # Convert to dict format with updated field mappings
        setup_list = []
        for setup in setups:
            setup_dict = {
                'id': setup.id,
                'message_id': setup.message_id,
                'ticker': setup.ticker,
                'trading_day': setup.trading_day.isoformat(),
                'index': setup.index,
                'trigger_level': float(setup.trigger_level) if setup.trigger_level else None,
                'target_prices': setup.target_prices,  # New field: list of target prices
                'direction': setup.direction,  # Updated field mapping
                'label': setup.label,  # New field: was setup_type
                'keywords': setup.keywords,  # New field: list of keywords
                'emoji_hint': setup.emoji_hint,  # New field: emoji hint
                'raw_line': setup.raw_line,
                'active': setup.active,
                'confidence_score': setup.confidence_score,
                'created_at': setup.created_at.isoformat() if hasattr(setup, 'created_at') else None,
                'updated_at': setup.updated_at.isoformat() if hasattr(setup, 'updated_at') else None
            }
            
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
                'label': label,  # New filter
                'direction': direction,  # New filter
                'index': index,  # New filter
                'active_only': active_only
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting setups: {e}")
        return jsonify({'error': 'Failed to get setups'}), 500

@parsing_api_bp.route('/setups/<int:setup_id>', methods=['GET'])
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
        
        # Use updated field mappings
        setup_dict = {
            'id': setup.id,
            'message_id': setup.message_id,
            'ticker': setup.ticker,
            'trading_day': setup.trading_day.isoformat(),
            'index': setup.index,
            'trigger_level': float(setup.trigger_level) if setup.trigger_level else None,
            'target_prices': setup.target_prices,  # New field: list of target prices
            'direction': setup.direction,  # Updated field mapping
            'label': setup.label,  # New field: was setup_type
            'keywords': setup.keywords,  # New field: list of keywords
            'emoji_hint': setup.emoji_hint,  # New field: emoji hint
            'raw_line': setup.raw_line,
            'active': setup.active,
            'confidence_score': setup.confidence_score,
            'created_at': setup.created_at.isoformat() if hasattr(setup, 'created_at') else None,
            'updated_at': setup.updated_at.isoformat() if hasattr(setup, 'updated_at') else None,
            'levels': [level.to_dict() for level in levels]
        }
        
        return jsonify({
            'success': True,
            'setup': setup_dict
        })
        
    except Exception as e:
        logger.error(f"Error getting setup {setup_id}: {e}")
        return jsonify({'error': 'Failed to get setup'}), 500

@parsing_api_bp.route('/setups/<int:setup_id>/deactivate', methods=['POST'])
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

@parsing_api_bp.route('/levels/<int:level_id>/trigger', methods=['POST'])
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

@parsing_api_bp.route('/setups/by-day', methods=['GET'])
def get_setups_by_trading_day():
    """Get setups filtered by trading day with dropdown options"""
    try:
        store = get_parsing_store()
        
        # Get query parameter for specific trading day
        trading_day_param = request.args.get('trading_day')
        trading_day = None
        if trading_day_param:
            try:
                from datetime import datetime
                trading_day = datetime.strptime(trading_day_param, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Get available trading days and setups
        available_days = store.get_available_trading_days()
        setups = store.get_setups_by_trading_day(trading_day)
        
        # Determine selected day (most recent if none specified)
        selected_day = trading_day
        if not selected_day and available_days:
            selected_day = available_days[0]
        
        # Convert setups to dict format with new field mappings
        setup_list = []
        for setup in setups:
            setup_dict = {
                'id': setup.id,
                'message_id': setup.message_id,
                'ticker': setup.ticker,
                'trading_day': setup.trading_day.isoformat(),
                'index': setup.index,
                'trigger_level': float(setup.trigger_level) if setup.trigger_level else None,
                'target_prices': setup.target_prices,  # New field: list of target prices
                'direction': setup.direction,  # Updated field mapping
                'label': setup.label,  # New field: was setup_type
                'keywords': setup.keywords,  # New field: list of keywords
                'emoji_hint': setup.emoji_hint,  # New field: emoji hint
                'raw_line': setup.raw_line,
                'active': setup.active,
                'confidence_score': setup.confidence_score,
                'created_at': setup.created_at.isoformat() if hasattr(setup, 'created_at') else None,
                'updated_at': setup.updated_at.isoformat() if hasattr(setup, 'updated_at') else None
            }
            
            # Get levels for this setup
            levels = store.get_levels_by_setup(setup.id)
            setup_dict['levels'] = [level.to_dict() for level in levels]
            setup_list.append(setup_dict)
        
        return jsonify({
            'success': True,
            'setups': setup_list,
            'available_days': [day.isoformat() for day in available_days],
            'selected_day': selected_day.isoformat() if selected_day else None,
            'count': len(setup_list)
        })
        
    except Exception as e:
        logger.error(f"Error fetching setups by day: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'setups': [],
            'available_days': [],
            'selected_day': None,
            'count': 0
        }), 500

@parsing_api_bp.route('/backlog/trigger', methods=['POST'])
def trigger_backlog():
    """Trigger manual backlog parsing for unparsed messages"""
    try:
        # Get optional parameters from request
        data = request.get_json() or {}
        channel_id = data.get('channel_id')
        since_timestamp = data.get('since_timestamp')
        limit = int(data.get('limit', 50))
        requested_by = data.get('requested_by', 'api_user')
        
        logger.info(f"Manual backlog parsing requested by {requested_by}")
        
        # Get parsing store and service directly
        from .service import get_parsing_service
        parsing_store = get_parsing_store()
        parsing_service = get_parsing_service()
        
        if not parsing_service:
            return jsonify({
                'success': False,
                'error': 'Parsing service not available'
            }), 503
        
        # Get unparsed messages
        unparsed_messages = parsing_store.get_unparsed_messages(
            channel_id=channel_id,
            since_timestamp=since_timestamp,
            limit=limit
        )
        
        processed_count = 0
        error_count = 0
        
        logger.info(f"Found {len(unparsed_messages)} unparsed messages for backlog processing")
        
        # Process each message directly
        for message in unparsed_messages:
            try:
                # Process the message through parsing service
                message_data = {
                    'message_id': message.get('message_id'),
                    'content': message.get('content', ''),
                    'channel_id': message.get('channel_id'),
                    'timestamp': message.get('timestamp'),
                    'author_id': message.get('author_id')
                }
                result = parsing_service.parse_message(message_data)
                
                if result and result.get('setup_created'):
                    processed_count += 1
                    logger.debug(f"Successfully processed message {message.get('message_id')}")
                else:
                    logger.debug(f"No setup found in message {message.get('message_id')}")
                    
            except Exception as e:
                logger.error(f"Error processing message {message.get('message_id')}: {e}")
                error_count += 1
        
        return jsonify({
            'success': True,
            'message': 'Backlog parsing completed',
            'results': {
                'messages_found': len(unparsed_messages),
                'messages_processed': processed_count,
                'errors': error_count,
                'requested_by': requested_by
            }
        })
            
    except Exception as e:
        logger.error(f"Error in manual backlog parsing: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Backlog parsing failed: {str(e)}'
        }), 500

@parsing_api_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get parsing service statistics for frontend consumption"""
    try:
        store = get_parsing_store()
        stats = store.get_parsing_statistics()
        
        # Return flattened structure for frontend compatibility
        return jsonify(stats.get('parsing_stats', stats))
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@parsing_api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get parsing service statistics (legacy endpoint)"""
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

@parsing_api_bp.route('/health', methods=['GET'])
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
    """Register parsing API routes with the Flask app"""
    app.register_blueprint(parsing_api_bp)
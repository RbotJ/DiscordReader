"""
Parsing Dashboard Module

Operational dashboard for monitoring parsing service health, performance metrics,
and managing parsed trade setups. Follows the discord_channels feature slice pattern.
"""
import logging
from datetime import date, datetime
from flask import Blueprint, render_template, request, jsonify
from common.utils import utc_now

from .service import get_parsing_service
from .store import get_parsing_store
from .events import trigger_backlog_parsing

logger = logging.getLogger(__name__)

# Create blueprint for parsing dashboard
parsing_bp = Blueprint('parsing_dashboard', __name__,
                      template_folder='templates',
                      static_folder='static/parsing',
                      url_prefix='/dashboard/parsing')

def get_parsing_service_safe():
    """Get parsing service instance with proper error handling."""
    try:
        return get_parsing_service()
    except Exception as e:
        logger.warning(f"Could not get parsing service: {e}")
        return None

@parsing_bp.route('/')
def overview():
    """Parsing service dashboard overview page."""
    try:
        service = get_parsing_service_safe()
        if service:
            metrics = service.get_service_stats()
            
            # Get audit data for anomaly monitoring
            from .store import get_parsing_store
            store = get_parsing_store()
            audit_data = store.get_audit_anomalies()
            
            logger.info(f"Parsing metrics: {metrics}")
            logger.info(f"Metrics type: {type(metrics)}")
            logger.info(f"Audit anomalies found: {audit_data.get('weekend_setup_count', 0)} weekend setups")
            
            return render_template('parsing/overview.html',
                                 metrics=metrics,
                                 audit_data=audit_data,
                                 current_time=utc_now())
        else:
            return render_template('parsing/error.html', 
                                 error="Parsing service unavailable"), 500
    except Exception as e:
        logger.error(f"Error loading parsing dashboard: {e}")
        return render_template('parsing/error.html', error=str(e)), 500

@parsing_bp.route('/metrics.json')
def metrics():
    """Get parsing service metrics as JSON for AJAX updates."""
    try:
        service = get_parsing_service_safe()
        if service:
            metrics = service.get_service_stats()
            # Add operational timestamp
            metrics['dashboard_timestamp'] = utc_now().isoformat()
            return jsonify(metrics)
        else:
            return jsonify({'error': 'Parsing service unavailable'}), 503
    except Exception as e:
        logger.error(f"Error getting parsing metrics: {e}")
        return jsonify({'error': str(e)}), 500



@parsing_bp.route('/setups.json')
def setups_json():
    """Get parsed setups as JSON with available trading days"""
    try:
        trading_day_str = request.args.get('trading_day')
        ticker = request.args.get('ticker')
        
        service = get_parsing_service_safe()
        if not service:
            return jsonify({'success': False, 'error': 'Parsing service unavailable'}), 503
        
        # Get available trading days from database
        try:
            from features.parsing.store import get_parsing_store
            store = get_parsing_store()
            available_days = store.get_available_trading_days()
        except Exception as e:
            logger.error(f"Error getting available trading days: {e}")
            available_days = []
        
        # Determine selected day
        trading_day = None
        if trading_day_str:
            try:
                trading_day = datetime.strptime(trading_day_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # If no specific day requested, use the most recent available day
        if not trading_day and available_days:
            trading_day = max(available_days)
        elif not trading_day:
            trading_day = date.today()
        
        # Get setups for the selected day using store directly to ensure new field mappings
        store = get_parsing_store()
        setups_query = store.get_active_setups_for_day(trading_day)
        
        # Filter by ticker if specified
        if ticker:
            setups_query = [setup for setup in setups_query if setup.ticker.upper() == ticker.upper()]
        
        # Convert setups to dict format with new field mappings
        setups = []
        for setup in setups_query:
            setup_dict = {
                'id': setup.id,
                'message_id': setup.message_id,
                'ticker': setup.ticker,
                'trading_day': setup.trading_day.isoformat(),
                'index': setup.index,
                'trigger_level': float(setup.trigger_level) if setup.trigger_level else None,
                'target_prices': setup.target_prices,  # New field: list of target prices
                'direction': setup.direction,  # Updated field mapping
                'label': setup.label,  # New field: was setup_type/profile_name
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
            setups.append(setup_dict)
        
        return jsonify({
            'success': True,
            'setups': setups,
            'count': len(setups),
            'available_days': [day.isoformat() for day in available_days],
            'selected_day': trading_day.isoformat(),
            'ticker': ticker
        })
            
    except Exception as e:
        logger.error(f"Error getting setups JSON: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@parsing_bp.route('/backlog/trigger', methods=['POST'])
def trigger_backlog():
    """Trigger manual backlog parsing for unparsed messages"""
    from flask import current_app
    
    try:
        # Get optional parameters from request
        channel_id = request.json.get('channel_id') if request.json else None
        since_timestamp = request.json.get('since_timestamp') if request.json else None
        limit = int(request.json.get('limit', 100)) if request.json else 100
        requested_by = request.json.get('requested_by', 'dashboard_user') if request.json else 'dashboard_user'
        
        logger.info(f"Manual backlog parsing requested by {requested_by}")
        
        # Ensure Flask application context for database operations
        with current_app.app_context():
            # Get parsing store and service directly
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
            
            # Process each message directly with detailed logging
            successful_inserts = 0
            parsing_failures = 0
            
            for message in unparsed_messages:
                message_id = message.get('message_id')
                content = message.get('content', '')
                
                logger.info(f"[ParseBacklog] Processing message {message_id} with content length: {len(content)}")
                
                try:
                    # Check if this is an A+ message and route to specialized service
                    from .aplus_parser import get_aplus_parser
                    aplus_parser = get_aplus_parser()
                    
                    # Log content preview for debugging
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    logger.info(f"[ParseBacklog] Message {message_id} content preview: {content_preview}")
                    
                    if aplus_parser.validate_message(content):
                        logger.info(f"[ParseBacklog] Routing A+ message {message_id} to specialized service")
                        # Use specialized A+ service to preserve individual setups
                        result = parsing_service.parse_aplus_message(content, message_id)
                    else:
                        # Process the message through generic parsing service
                        message_data = {
                            'message_id': message_id,
                            'content': content,
                            'channel_id': message.get('channel_id'),
                            'timestamp': message.get('timestamp'),
                            'author_id': message.get('author_id')
                        }
                        result = parsing_service.parse_message(message_data)
                    
                    if result and result.get('success'):
                        successful_inserts += 1
                        setups_created = result.get('setups_created', 0)
                        logger.info(f"[ParseBacklog] Message {message_id} → {setups_created} setups created")
                        processed_count += 1
                    elif result:
                        # Parse attempt was made but no setups found
                        parsing_failures += 1
                        logger.warning(f"[ParseBacklog] Message {message_id} → no valid setups found (content not recognized)")
                        processed_count += 1
                    else:
                        # Parse service returned None/False
                        parsing_failures += 1
                        logger.error(f"[ParseBacklog] Message {message_id} → parsing service returned null")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"[ParseBacklog] Message {message_id} failed completely: {e}")
                    
            logger.info(f"Backlog processing complete:")
            logger.info(f"  - Total messages found: {len(unparsed_messages)}")
            logger.info(f"  - Successfully parsed & stored: {successful_inserts}")
            logger.info(f"  - Parsing failures (content not recognized): {parsing_failures}")
            logger.info(f"  - Storage/system failures: {error_count}")
            
            return jsonify({
                'success': True,
                'message': 'Backlog parsing completed',
                'results': {
                    'messages_found': len(unparsed_messages),
                    'messages_processed': processed_count,
                    'created': successful_inserts,
                    'parsing_failed': parsing_failures,
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

@parsing_bp.route('/backlog/status')
def backlog_status():
    """Get status of unparsed messages available for backlog processing"""
    try:
        parsing_store = get_parsing_store()
        
        # Get count of unparsed messages
        unparsed_messages = parsing_store.get_unparsed_messages(limit=1000)
        
        # Group by channel for summary
        channel_counts = {}
        total_unparsed = len(unparsed_messages)
        
        for message in unparsed_messages:
            channel_id = message.get('channel_id', 'unknown')
            channel_counts[channel_id] = channel_counts.get(channel_id, 0) + 1
        
        return jsonify({
            'total_unparsed': total_unparsed,
            'channel_breakdown': channel_counts,
            'sample_messages': unparsed_messages[:5],  # Show first 5 as samples
            'timestamp': utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting backlog status: {e}")
        return jsonify({'error': str(e)}), 500

@parsing_bp.route('/health')
def health():
    """Parsing service health check"""
    try:
        service = get_parsing_service_safe()
        if service and service.is_healthy():
            stats = service.get_service_stats()
            return jsonify({
                'status': 'healthy',
                'service_status': stats.get('service_status', 'unknown'),
                'messages_processed': stats.get('listener_stats', {}).get('messages_processed', 0),
                'timestamp': utc_now().isoformat()
            })
        else:
            return jsonify({
                'status': 'unhealthy',
                'error': 'Service not available or unhealthy',
                'timestamp': utc_now().isoformat()
            }), 503
    except Exception as e:
        logger.error(f"Error in parsing health check: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': utc_now().isoformat()
        }), 500

@parsing_bp.route('/setups/clear', methods=['POST'])
def clear_trade_setups():
    """Clear all trade setups and their associated parsed levels"""
    try:
        # Get confirmation parameter
        data = request.get_json() or {}
        confirmed = data.get('confirmed', False)
        
        if not confirmed:
            return jsonify({
                'success': False,
                'error': 'Confirmation required to clear all trade setups'
            }), 400
        
        # Get the parsing store and call clear method
        store = get_parsing_store()
        result = store.clear_all_trade_setups()
        
        if result['success']:
            logger.info(f"Trade setups cleared: {result['deleted_setups']} setups, {result['deleted_levels']} levels")
            return jsonify(result)
        else:
            logger.error(f"Failed to clear trade setups: {result['message']}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Error in clear trade setups endpoint: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to clear trade setups: {str(e)}',
            'timestamp': utc_now().isoformat()
        }), 500

def register_dashboard_routes(app):
    """Register parsing dashboard routes"""
    app.register_blueprint(parsing_bp)
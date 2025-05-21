"""
Trade Workflow API Routes

This module provides Flask API routes for the trade workflow integration.
"""
import logging
from flask import Blueprint, jsonify, request, current_app
from features.integration.trade_workflow import (
    initialize_trade_workflow,
    shutdown_trade_workflow,
    process_discord_message,
    evaluate_setups,
    monitor_active_trades,
    get_active_setups,
    get_active_trades,
    get_trade_history,
    generate_performance_report
)

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
integration_bp = Blueprint('integration_api', __name__)

def register_integration_routes(app, db):
    """
    Register integration API routes with the Flask application.
    
    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
    """
    # Register blueprint
    app.register_blueprint(integration_bp, url_prefix='/api/integration')
    
    # Initialize the trade workflow
    with app.app_context():
        if initialize_trade_workflow():
            logger.info("Trade workflow integration initialized")
        else:
            logger.warning("Failed to initialize trade workflow integration")
    
    logger.info("Integration API routes registered")
    
    # Register shutdown handler
    @app.teardown_appcontext
    def shutdown_integration(exception=None):
        shutdown_trade_workflow()

@integration_bp.route('/process-message', methods=['POST'])
def api_process_message():
    """Process a Discord message for trading signals."""
    try:
        # Get message text from request
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400
            
        message = data['message']
        
        # Process the message
        result = process_discord_message(message)
        
        if result:
            return jsonify({
                'success': True,
                'setup': result
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No valid trading setup found in the message'
            })
            
    except Exception as e:
        logger.error(f"Error processing message API request: {e}")
        return jsonify({'error': str(e)}), 500

@integration_bp.route('/evaluate', methods=['POST'])
def api_evaluate_setups():
    """Evaluate active setups and execute trades if appropriate."""
    try:
        # Evaluate setups
        processed = evaluate_setups()
        
        return jsonify({
            'success': True,
            'processed_count': len(processed),
            'processed': processed
        })
        
    except Exception as e:
        logger.error(f"Error evaluating setups API request: {e}")
        return jsonify({'error': str(e)}), 500

@integration_bp.route('/monitor', methods=['POST'])
def api_monitor_trades():
    """Monitor active trades and update their status."""
    try:
        # Monitor trades
        updated = monitor_active_trades()
        
        return jsonify({
            'success': True,
            'updated_count': len(updated),
            'updated': updated
        })
        
    except Exception as e:
        logger.error(f"Error monitoring trades API request: {e}")
        return jsonify({'error': str(e)}), 500

@integration_bp.route('/active-setups', methods=['GET'])
def api_active_setups():
    """Get all active trading setups."""
    try:
        setups = get_active_setups()
        
        return jsonify({
            'success': True,
            'count': len(setups),
            'setups': setups
        })
        
    except Exception as e:
        logger.error(f"Error getting active setups API request: {e}")
        return jsonify({'error': str(e)}), 500

@integration_bp.route('/active-trades', methods=['GET'])
def api_active_trades():
    """Get all active trades."""
    try:
        trades = get_active_trades()
        
        return jsonify({
            'success': True,
            'count': len(trades),
            'trades': trades
        })
        
    except Exception as e:
        logger.error(f"Error getting active trades API request: {e}")
        return jsonify({'error': str(e)}), 500

@integration_bp.route('/trade-history', methods=['GET'])
def api_trade_history():
    """Get all completed trades."""
    try:
        history = get_trade_history()
        
        return jsonify({
            'success': True,
            'count': len(history),
            'history': history
        })
        
    except Exception as e:
        logger.error(f"Error getting trade history API request: {e}")
        return jsonify({'error': str(e)}), 500

@integration_bp.route('/performance-report', methods=['GET'])
def api_performance_report():
    """Generate a performance report for all trades."""
    try:
        report = generate_performance_report()
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        logger.error(f"Error generating performance report API request: {e}")
        return jsonify({'error': str(e)}), 500
import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import redis

from features.setups.api import setup_routes
from features.market.price_feed import start_price_feed
from features.strategy.detector import start_signal_detector
from features.options_selector.chain_fetcher import get_options_chain
from features.execution.executor import submit_order, get_trade_execution_status
from features.management.positions import get_positions, get_position_history
from features.management.exit_engine import start_exit_monitor
from features.notifications.notifier import send_notification

# Create Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "development-key")

# Configure logging
logger = logging.getLogger(__name__)

# Register blueprint routes
app.register_blueprint(setup_routes)

# Main dashboard route
@app.route('/')
def dashboard():
    return render_template('dashboard.html', 
                          title='A+ Trading Dashboard',
                          current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Setups view route
@app.route('/setups')
def view_setups():
    from features.setups.parser import get_stored_setups
    setups = get_stored_setups()
    return render_template('setups.html', 
                          title='Trading Setups',
                          setups=setups)

# Positions view route
@app.route('/positions')
def view_positions():
    positions = get_positions()
    history = get_position_history()
    return render_template('positions.html', 
                          title='Position Management',
                          positions=positions,
                          history=history)

# API endpoint for fetching options chain
@app.route('/api/options/<symbol>')
def options_api(symbol):
    try:
        expiry = request.args.get('expiry')
        chain = get_options_chain(symbol, expiry)
        return jsonify({"status": "success", "data": chain})
    except Exception as e:
        logger.error(f"Error fetching options chain: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# API endpoint for executing trades
@app.route('/api/execute', methods=['POST'])
def execute_trade():
    try:
        data = request.json
        result = submit_order(
            symbol=data.get('symbol'),
            quantity=data.get('quantity'),
            side=data.get('side'),
            option_symbol=data.get('option_symbol'),
            order_type=data.get('order_type', 'market'),
            time_in_force=data.get('time_in_force', 'day'),
            limit_price=data.get('limit_price')
        )
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error executing trade: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# API endpoint for system status
@app.route('/api/status')
def system_status():
    price_feed_status = "running" # This would be dynamic in a full implementation
    execution_status = get_trade_execution_status()
    return jsonify({
        "price_feed": price_feed_status,
        "execution": execution_status,
        "timestamp": datetime.now().isoformat()
    })

# Initialize system components - in a production app, these would be backgrounded
@app.before_first_request
def initialize_system():
    try:
        # Start critical services
        start_price_feed()
        start_signal_detector()
        start_exit_monitor()
        send_notification("System started successfully")
    except Exception as e:
        logger.error(f"Error initializing system: {str(e)}")
        send_notification(f"Error starting system: {str(e)}", level="error")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

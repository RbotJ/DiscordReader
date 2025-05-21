"""
A+ Trading Application Main Module

This is the main entry point for the trading application.
It configures the Flask application, initializes components,
and sets up the routes.
"""

import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from flask import Flask, jsonify, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
from common.db import db, init_db
# Import models from the main models.py file
import models

# Create Socket.IO instance
socketio = SocketIO()

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure app secret key
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
    
    # Initialize database
    init_db(app)
    
    # Initialize SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Register feature-specific routes
    register_feature_routes(app)
    
    # Register API routes
    try:
        from api_routes import register_api_routes
        register_api_routes(app, db)
        logging.info("API routes registered")
    except ImportError as e:
        logging.warning(f"Could not register API routes: {e}")
    
    # Register web UI routes
    register_web_routes(app)
    
    # Register SocketIO event handlers
    register_socketio_events()
    
    return app

def register_socketio_events():
    """Register Socket.IO event handlers."""
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logging.info("Client connected")
        emit('connection_response', {'status': 'connected'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logging.info("Client disconnected")

    @socketio.on('subscribe_tickers')
    def handle_subscribe_tickers(data):
        """
        Handle ticker subscription requests.
        
        Args:
            data: Dictionary containing tickers to subscribe to
        """
        tickers = data.get('tickers', [])
        if tickers:
            logging.info(f"Client subscribed to tickers: {tickers}")
            # Emit confirmation back to the client
            emit('subscription_response', {'status': 'success', 'tickers': tickers})
            
            # Send initial data for the subscribed tickers
            # This would normally come from our market data cache
            for ticker in tickers:
                emit('market_data', {
                    'ticker': ticker,
                    'price': 0,  # Will be filled with real data later
                    'timestamp': datetime.now().isoformat()
                })
    
    @socketio.on('subscribe_setups')
    def handle_subscribe_setups():
        """
        Handle setup subscription requests.
        Allows clients to receive real-time notifications for new trading setups.
        """
        logging.info("Client subscribed to trading setup notifications")
        
        # Emit confirmation back to the client
        emit('subscription_response', {'status': 'success', 'type': 'setups'})
        
        # Get most recent setup to send as initial data
        try:
            from features.setups.multi_ticker_controller import get_recent_setups
            recent_setups = get_recent_setups(limit=1)
            
            if recent_setups and len(recent_setups) > 0:
                # Send the most recent setup as initial data
                emit('new_setup', recent_setups[0])
        except Exception as e:
            logging.error(f"Error sending initial setup data: {e}")

def register_feature_routes(app):
    """Register feature-specific routes from the features directory."""
    # Import necessary route registrations
    try:
        # Register webhook routes
        from features.setups.webhook_api import register_routes as register_webhook_routes
        register_webhook_routes(app)
        logging.info("Setup webhook routes registered")
    except ImportError as e:
        logging.warning(f"Could not import setup webhook routes: {e}")
        
    # Register setup API routes
    try:
        from features.setups.api import register_routes as register_setup_api_routes
        register_setup_api_routes(app)
        logging.info("Setup API routes registered")
    except ImportError as e:
        logging.warning(f"Could not import setup API routes: {e}")
    
    # Register Alpaca trading routes
    try:
        from features.alpaca.api import register_routes as register_alpaca_routes
        register_alpaca_routes(app)
        logging.info("Alpaca trading routes registered")
    except ImportError as e:
        logging.warning(f"Could not import Alpaca trading routes: {e}")
    
    # Register Options API routes
    try:
        from features.alpaca.options_api import register_options_api
        register_options_api(app)
        logging.info("Options API routes registered")
    except ImportError as e:
        logging.warning(f"Could not import Options API routes: {e}")
    
    # Register market data routes
    try:
        from features.market.api_routes import register_routes as register_market_routes
        register_market_routes(app)
        logging.info("Market data routes registered")
    except ImportError as e:
        logging.warning(f"Could not import market data routes: {e}")
    
    # Register options data routes
    try:
        from features.options.api_routes import register_routes as register_options_routes
        register_options_routes(app)
        logging.info("Options data routes registered")
    except ImportError as e:
        logging.warning(f"Could not import options data routes: {e}")
    
    # Register execution routes
    try:
        from features.execution.api_routes import register_routes as register_execution_routes
        register_execution_routes(app)
        logging.info("Execution routes registered")
    except ImportError as e:
        logging.warning(f"Could not import execution routes: {e}")
        
    # Register account information routes
    try:
        from features.account.api_routes import register_routes as register_account_routes
        register_account_routes(app)
        logging.info("Account information routes registered")
    except ImportError as e:
        logging.warning(f"Could not import account information routes: {e}")
    
    # Register strategy routes
    try:
        from features.strategy.api import register_routes as register_strategy_routes
        register_strategy_routes(app)
        logging.info("Strategy routes registered")
    except ImportError as e:
        logging.warning(f"Could not import strategy routes: {e}")

def register_web_routes(app):
    """Register web UI routes."""
    
    @app.route('/monitor')
    def monitor():
        """Setup monitoring page with candlestick charts and real-time updates."""
        return render_template('monitor.html', title="Setup Monitor")
    # Main UI routes
    @app.route('/')
    def index():
        """Main landing page."""
        # Get today's date for display in Eastern Time (ET) for NYSE
        from datetime import datetime
        import pytz
        
        eastern = pytz.timezone('US/Eastern')
        et_now = datetime.now(pytz.utc).astimezone(eastern)
        today = et_now.strftime('%A, %B %d, %Y %I:%M %p ET')
        
        # Get today's tickers from Discord messages
        import re
        import json
        import os
        
        MESSAGE_HISTORY_FILE = "discord_message_history.json"
        todays_tickers = []
        message_count = 0
        
        if os.path.exists(MESSAGE_HISTORY_FILE):
            try:
                with open(MESSAGE_HISTORY_FILE, 'r') as f:
                    messages = json.load(f)
                
                # Filter for today's messages
                today_date = date.today().isoformat()
                todays_messages = [msg for msg in messages if msg.get("timestamp", "").startswith(today_date)]
                message_count = len(todays_messages)
                
                # Extract tickers using regex
                ticker_pattern = r'\$([A-Z]{1,5})'
                ticker_set = set()
                
                for message in todays_messages:
                    content = message.get("content", "")
                    found_tickers = re.findall(ticker_pattern, content)
                    ticker_set.update(found_tickers)
                
                todays_tickers = list(ticker_set)
            except Exception as e:
                app.logger.error(f"Error processing message history: {e}")
        
        return render_template(
            'index.html', 
            title="A+ Trading App",
            today=today, 
            tickers=todays_tickers, 
            message_count=message_count
        )
    
    @app.route('/dashboard')
    def dashboard():
        """Trading dashboard page."""
        return render_template('dashboard.html', title="Trading Dashboard")
    
    @app.route('/recent-setups')
    def recent_setups():
        """Recent setups page displaying messages from Discord."""
        return render_template('recent_setups.html', title="Recent Trading Setups")
    
    @app.route('/setup/<int:setup_id>')
    def setup_detail(setup_id):
        """View details of a specific setup."""
        return render_template('setup_detail.html', title="Setup Details", setup_id=setup_id)
    
    # Add health check endpoint for web dashboard
    @app.route('/web/health')
    def web_health():
        """Web application health check endpoint."""
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "app": os.environ.get("REPL_SLUG", "aplus-trading-app"),
            "version": "0.1.0"
        })

# Create the application
app = create_app()

# Initialize app components
def initialize_app_components():
    """Initialize app components on first request."""
    # Initialize Discord integration
    try:
        from features.discord import init_discord
        success = init_discord()
        if success:
            logging.info("Discord integration initialized")
        else:
            logging.warning("Discord integration initialization failed")
    except ImportError as e:
        logging.warning(f"Could not initialize Discord integration: {e}")

    # Initialize message consumer service
    try:
        from features.setups.consumer_service import start_message_consumer_service
        success = start_message_consumer_service()
        if success:
            logging.info("Discord message consumer service initialized")
        else:
            logging.warning("Discord message consumer service initialization failed")
    except ImportError as e:
        logging.warning(f"Could not initialize Discord message consumer service: {e}")

    # Initialize market data components
    try:
        from features.market.price_monitor import init_price_monitor
        success = init_price_monitor()
        if success:
            logging.info("Price monitor initialized")
        else:
            logging.warning("Price monitor initialization failed")
    except ImportError as e:
        logging.warning(f"Could not initialize price monitor: {e}")
    
    # Initialize historical data provider
    try:
        from features.market.historical_data import init_historical_data_provider
        success = init_historical_data_provider()
        if success:
            logging.info("Historical data provider initialized")
        else:
            logging.warning("Historical data provider initialization failed")
    except ImportError as e:
        logging.warning(f"Could not initialize historical data provider: {e}")
    
    # Initialize signal detection components
    try:
        from features.strategy import start_candle_detector
        success = start_candle_detector()
        if success:
            logging.info("Candle detector initialized")
        else:
            logging.warning("Candle detector initialization failed")
    except ImportError as e:
        logging.warning(f"Could not initialize candle detector: {e}")
    
    # Initialize options trading components
    try:
        from features.execution.options_trader import init_options_trader
        success = init_options_trader()
        if success:
            logging.info("Options trader initialized")
        else:
            logging.warning("Options trader initialization failed")
    except ImportError as e:
        logging.warning(f"Could not initialize options trader: {e}")
    
    # Schedule end-of-day position cleanup
    try:
        from features.alpaca.position_management import schedule_eod_cleanup
        schedule_eod_cleanup()
        logging.info("End-of-day position cleanup scheduled")
    except ImportError as e:
        logging.warning(f"Could not schedule end-of-day position cleanup: {e}")

# Initialize components after database creation
with app.app_context():
    try:
        initialize_app_components()
    except Exception as e:
        logging.error(f"Error initializing app components: {e}")

if __name__ == '__main__':
    # Run the application
    socketio.run(app, host='0.0.0.0', port=5000)
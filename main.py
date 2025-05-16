import logging
import os
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from flask import Flask, jsonify, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
from common.db import db
# Import models from the main models.py file
import models

# Create Socket.IO instance
socketio = SocketIO()

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure SQLAlchemy
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Configure app secret key
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Register routes
    register_routes(app)
    
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

def register_routes(app):
    """Register API routes with the Flask application."""
    # Import necessary route registrations
    try:
        # Register webhook routes
        from features.setups.webhook_api import register_routes as register_webhook_routes
        register_webhook_routes(app)
        logging.info("Setup webhook routes registered")
    except ImportError as e:
        logging.warning(f"Could not import setup webhook routes: {e}")
    
    # Register Alpaca trading routes
    try:
        from features.alpaca.api import register_routes as register_alpaca_routes
        register_alpaca_routes(app)
        logging.info("Alpaca trading routes registered")
    except ImportError as e:
        logging.warning(f"Could not import Alpaca trading routes: {e}")
    
    # Add other route registrations here as they are implemented
    
    # Add API health check endpoint
    @app.route('/api/health')
    def health_check():
        """API health check endpoint."""
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "app": os.environ.get("REPL_SLUG", "aplus-trading-app"),
            "version": "0.1.0"
        })
    
    # Add main application routes
    @app.route('/')
    def index():
        """Main landing page."""
        return render_template('index.html', title="A+ Trading App")
    
    @app.route('/dashboard')
    def dashboard():
        """Trading dashboard page."""
        return render_template('dashboard.html', title="Trading Dashboard")
    
    @app.route('/setup')
    def setup():
        """Setup submission page."""
        return render_template('setup.html', title="Create Setup")
    
    # API endpoints for the dashboard
    @app.route('/api/tickers')
    def get_tickers():
        """
        Get available tickers with trading setups.
        Returns a list of ticker symbols that have active setups.
        """
        # We'll implement this to fetch tickers from our database later
        tickers = ["SPY", "AAPL", "MSFT", "NVDA", "TSLA"]
        return jsonify({'tickers': tickers})
    
    @app.route('/api/account')
    def get_account():
        """
        Get account information.
        Returns account balance, buying power, etc.
        """
        # We'll implement this to fetch from Alpaca later
        account_info = {
            'portfolio_value': 100000.00,
            'cash': 75000.00,
            'buying_power': 150000.00,
            'positions_count': 5
        }
        return jsonify(account_info)

# Create the application
app = create_app()

# Create database tables on startup
with app.app_context():
    db.create_all()
    logging.info("Database tables created")

def initialize_app_components():
    """Initialize app components on first request."""
    # Initialize Discord integration (when implemented)
    try:
        # Import Discord initialization
        from features.discord import init_discord
        success = init_discord()
        if success:
            logging.info("Discord integration initialized")
        else:
            logging.warning("Discord integration initialization failed")
    except ImportError as e:
        logging.warning(f"Could not initialize Discord integration: {e}")

# Initialize components after database creation
with app.app_context():
    try:
        initialize_app_components()
    except Exception as e:
        logging.error(f"Error initializing app components: {e}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
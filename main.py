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
        try:
            # Query the database for unique tickers from ticker_setups table
            from models import TickerSetup
            ticker_results = db.session.query(TickerSetup.symbol).distinct().all()
            tickers = [result[0] for result in ticker_results]
            
            # If no tickers found in the database, return a few sample tickers
            if not tickers:
                tickers = ["SPY", "AAPL", "MSFT", "NVDA", "TSLA"]
            
            return jsonify(tickers)
        except Exception as e:
            logging.error(f"Error fetching tickers: {e}")
            return jsonify([])
    
    @app.route('/api/account')
    def get_account():
        """
        Get account information.
        Returns account balance, buying power, etc.
        """
        try:
            # Try to get account info from Alpaca
            from features.alpaca.client import alpaca_trading_client
            account = alpaca_trading_client.get_account()
            return jsonify(account)
        except Exception as e:
            logging.error(f"Error fetching account information: {e}")
            # Return fallback account info if there's an error
            return jsonify({
                'id': 'paper-account',
                'equity': 100000.00,
                'cash': 75000.00,
                'buying_power': 150000.00,
                'portfolio_value': 100000.00,
                'positions_count': 0,
                'status': 'ACTIVE'
            })
    
    @app.route('/api/positions')
    def get_positions():
        """
        Get current positions.
        Returns a list of open positions.
        """
        try:
            # Try to get positions from Alpaca
            from features.alpaca.client import alpaca_trading_client
            positions = alpaca_trading_client.get_positions()
            return jsonify(positions)
        except Exception as e:
            logging.error(f"Error fetching positions: {e}")
            return jsonify([])
    
    @app.route('/api/candles/<ticker>')
    def get_candles(ticker):
        """
        Get candle data for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Query params:
            timeframe: Candle timeframe (default: 1min)
            limit: Number of candles to return (default: 100)
        """
        from flask import request
        
        timeframe = request.args.get('timeframe', '1min')
        limit = int(request.args.get('limit', 100))
        
        try:
            # Try to get candles from Alpaca
            from features.alpaca.client import alpaca_market_client
            candles = alpaca_market_client.get_bars(ticker, timeframe, limit)
            return jsonify(candles)
        except Exception as e:
            logging.error(f"Error fetching candles for {ticker}: {e}")
            return jsonify([])
    
    @app.route('/api/signals/<ticker>')
    def get_signals(ticker):
        """
        Get signals for a ticker.
        
        Args:
            ticker: Ticker symbol
        """
        try:
            # Query the database for signals associated with the ticker
            from models import TickerSetup, Signal
            
            # Get the most recent ticker setup
            ticker_setup = TickerSetup.query.filter_by(symbol=ticker).order_by(TickerSetup.id.desc()).first()
            
            if not ticker_setup:
                return jsonify(None)
            
            # Get signals for the ticker setup
            signals = Signal.query.filter_by(ticker_setup_id=ticker_setup.id).all()
            
            if not signals:
                return jsonify(None)
            
            # Return the first signal (we'll enhance this later)
            signal = signals[0]
            
            signal_data = {
                'id': signal.id,
                'category': signal.category.value,
                'aggressiveness': signal.aggressiveness.value,
                'comparison': signal.comparison.value,
                'trigger': signal.trigger,
                'targets': signal.targets
            }
            
            return jsonify(signal_data)
        except Exception as e:
            logging.error(f"Error fetching signals for {ticker}: {e}")
            return jsonify(None)

# Create the application
app = create_app()

# Create database tables on startup
with app.app_context():
    db.create_all()
    logging.info("Database tables created")

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
        from features.strategy.candle_detector import init_candle_detector
        success = init_candle_detector()
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
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
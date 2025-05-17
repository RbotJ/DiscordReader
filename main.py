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
    
    # Register Options API routes
    try:
        from features.alpaca.options_api import register_options_api
        register_options_api(app)
        logging.info("Options API routes registered")
    except ImportError as e:
        logging.warning(f"Could not import Options API routes: {e}")
    
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
        
    @app.route('/api/test')
    def api_test():
        """Test API endpoints."""
        results = {}
        
        # Test account endpoint
        try:
            from features.alpaca.client import get_account_info
            account = get_account_info()
            results['account'] = {
                'status': 'success',
                'data': account
            }
        except Exception as e:
            results['account'] = {
                'status': 'error',
                'error': str(e)
            }
            
        # Test positions endpoint
        try:
            from features.alpaca.client import get_positions
            positions = get_positions()
            results['positions'] = {
                'status': 'success',
                'count': len(positions),
                'data': positions[:2] if positions else []  # Show first 2 positions only
            }
        except Exception as e:
            results['positions'] = {
                'status': 'error',
                'error': str(e)
            }
            
        # Test candles endpoint
        try:
            from features.alpaca.client import get_bars
            candles = get_bars('SPY', '1Min', 10)
            results['candles'] = {
                'status': 'success',
                'count': len(candles),
                'data': candles[:2] if candles else []  # Show only first 2 candles
            }
        except Exception as e:
            results['candles'] = {
                'status': 'error',
                'error': str(e)
            }
            
        # Test signals endpoint
        try:
            from features.strategy import get_candle_signals
            signals = get_candle_signals('SPY')
            results['signals'] = {
                'status': 'success',
                'count': len(signals) if signals else 0,
                'data': signals[:2] if signals else []  # Show only first 2 signals
            }
        except Exception as e:
            results['signals'] = {
                'status': 'error',
                'error': str(e)
            }
            
        return jsonify(results)
    
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
            # Use raw SQL to avoid model registry conflicts
            from sqlalchemy import text
            results = db.session.execute(text("SELECT DISTINCT symbol FROM ticker_setups")).fetchall()
            tickers = [row[0] for row in results]
            
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
            from features.alpaca.client import get_account_info
            account = get_account_info()
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
            from features.alpaca.client import get_positions
            positions = get_positions()
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
        
        timeframe = request.args.get('timeframe', '1Min')
        limit = int(request.args.get('limit', 100))
        
        try:
            # First try to get candles from historical data provider
            try:
                from features.market.historical_data import get_historical_candles
                candles = get_historical_candles(ticker, timeframe, limit)
                if candles and len(candles) > 0:
                    return jsonify(candles)
            except ImportError:
                logging.warning(f"Could not import historical data provider for {ticker}")
            
            # Fall back to Alpaca client if historical data not available
            from features.alpaca.client import get_bars
            candles = get_bars(ticker, timeframe, limit)
            return jsonify(candles or [])
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
            # First check for active candle signals
            try:
                from features.strategy import get_candle_signals
                active_signals = get_candle_signals(ticker)
                
                if active_signals:
                    # Return all active candle signals
                    return jsonify(active_signals)
            except ImportError:
                logging.warning(f"Could not import candle signals module for {ticker}")
            
            # Fall back to database signals if no active candle signals
            try:
                from sqlalchemy import text
                import json
                
                # Use raw SQL to avoid model registry conflicts
                # First get the most recent ticker setup ID
                setup_query = text("""
                    SELECT id FROM ticker_setups 
                    WHERE symbol = :symbol 
                    ORDER BY id DESC LIMIT 1
                """)
                setup_result = db.session.execute(setup_query, {"symbol": ticker}).fetchone()
                
                if not setup_result:
                    return jsonify([])
                
                setup_id = setup_result[0]
                
                # Then get signals for that ticker setup
                signals_query = text("""
                    SELECT id, category, aggressiveness, comparison, trigger, targets, created_at
                    FROM signals
                    WHERE ticker_setup_id = :setup_id
                """)
                signals = db.session.execute(signals_query, {"setup_id": setup_id}).fetchall()
                
                if not signals:
                    return jsonify([])
                
                # Convert database signals to API format
                signal_list = []
                for signal in signals:
                    try:
                        # Parse JSON fields
                        trigger = json.loads(signal[4]) if isinstance(signal[4], str) else signal[4]
                        targets = json.loads(signal[5]) if isinstance(signal[5], str) else signal[5]
                        
                        signal_data = {
                            'id': signal[0],
                            'ticker': ticker,
                            'category': signal[1],
                            'aggressiveness': signal[2],
                            'comparison': signal[3],
                            'trigger': trigger,
                            'targets': targets,
                            'status': 'pending',  # Default status
                            'source': 'database'
                        }
                        signal_list.append(signal_data)
                    except Exception as signal_error:
                        logging.error(f"Error processing signal {signal[0]}: {signal_error}")
                        continue
                
                return jsonify(signal_list)
            except Exception as db_error:
                logging.error(f"Database error fetching signals for {ticker}: {db_error}")
                return jsonify([])
        except Exception as e:
            logging.error(f"Error fetching signals for {ticker}: {e}")
            return jsonify([])
            
    @app.route('/api/signals/add', methods=['POST'])
    def add_signal():
        """
        Add a candle signal for testing.
        
        Expected JSON payload format:
        {
            "ticker": "SPY",
            "category": "breakout",  # or "breakdown", "rejection", "bounce"
            "trigger": {
                "price": 450.0,
                "timeframe": "15Min"
            },
            "targets": [
                {"price": 455.0, "percentage": 0.25},
                {"price": 460.0, "percentage": 0.5},
                {"price": 465.0, "percentage": 0.25}
            ],
            "status": "pending"
        }
        """
        try:
            from flask import request
            from features.strategy import add_candle_signal
            
            # Parse request JSON
            signal_data = request.json
            
            if not signal_data or 'ticker' not in signal_data or 'trigger' not in signal_data:
                return jsonify({"success": False, "error": "Invalid signal data"}), 400
            
            # Add signal to candle detector
            success = add_candle_signal(signal_data)
            
            if success:
                return jsonify({"success": True, "message": f"Signal added for {signal_data['ticker']}"}), 201
            else:
                return jsonify({"success": False, "error": "Failed to add signal"}), 500
        except Exception as e:
            logging.error(f"Error adding signal: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

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
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
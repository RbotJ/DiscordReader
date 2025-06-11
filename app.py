"""
A+ Trading Application Main Module

This is the main entry point for the Flask-based trading application.
It configures the application, initializes components,
and sets up the routes.
"""

print(f"▶️  Starting DiscordReader from {__file__}")

import logging
import os
import importlib
from datetime import datetime
from flask import Flask, jsonify, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
from common.db import db, initialize_db
from features.blueprint_registry import BLUEPRINT_CONFIGS, REQUIRED_ENV_VARS, OPTIONAL_ENV_VARS

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Socket.IO instance
socketio = SocketIO()

def validate_environment():
    """Validate required environment variables and log warnings for missing optional ones."""
    missing_required = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing_required:
        logging.error(f"Missing required environment variables: {', '.join(missing_required)}")
        return False
    
    missing_optional = [var for var, default in OPTIONAL_ENV_VARS.items() 
                       if not os.getenv(var) and var in ["ALPACA_API_KEY", "ALPACA_API_SECRET"]]
    if missing_optional:
        logging.warning(f"Missing optional environment variables: {', '.join(missing_optional)}")
    
    return True

def register_all_blueprints(app):
    """
    Centralized blueprint registration using dynamic imports.
    This function registers all feature blueprints in a consistent manner.
    """
    registered_count = 0
    
    for name, module_path, attr in BLUEPRINT_CONFIGS:
        try:
            module = importlib.import_module(module_path)
            blueprint = getattr(module, attr)
            
            if blueprint is not None:
                app.register_blueprint(blueprint)
                logging.info(f"Registered {name} blueprint successfully")
                registered_count += 1
            else:
                logging.warning(f"Blueprint {name} is None, skipping registration")
                
        except (ImportError, AttributeError) as e:
            logging.warning(f"Failed to register {name} blueprint: {e}")
        except Exception as e:
            logging.error(f"Unexpected error registering {name} blueprint: {e}")
    
    logging.info(f"Successfully registered {registered_count}/{len(BLUEPRINT_CONFIGS)} blueprints")

def register_feature_routes(app):
    """Legacy function - now redirects to centralized blueprint registration"""
    register_all_blueprints(app)

def register_web_routes(app):
    """Register main web routes with error handling"""
    @app.route('/')
    def index():
        try:
            return render_template('index.html')
        except Exception as e:
            logging.error(f"Error rendering index template: {e}")
            return jsonify({"error": "Template not found", "redirect": "/health"}), 404
    
    @app.route('/health')
    def health():
        try:
            # Basic health check with database connection test
            from common.db import check_database_connection
            db_status = "connected" if check_database_connection() else "disconnected"
            
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "database": db_status,
                "version": "1.0.0"
            })
        except Exception as e:
            logging.error(f"Health check failed: {e}")
            return jsonify({
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }), 500

def register_socketio_events():
    """Register Socket.IO event handlers"""
    @socketio.on('connect')
    def handle_connect():
        logging.info('Client connected')
        emit('status', {'msg': 'Connected to trading server'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logging.info('Client disconnected')

def validate_discord_token():
    """Validate Discord bot token availability."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logging.warning("Discord token missing; bot disabled.")
        return None
    return token

def initialize_bot_services(app):
    """Initialize bot services and dependencies."""
    try:
        from features.ingestion.service import IngestionService
        from features.discord_channels.channel_manager import ChannelManager
        from features.parsing.service import start_parsing_service
        from features.discord_bot.bot import TradingDiscordBot

        # Initialize services
        ingestion_svc = IngestionService()
        channel_svc = ChannelManager()
        
        # Start parsing service
        parsing_service = start_parsing_service(app=app)
        logging.info("Parsing service started successfully")

        # Create bot instance
        bot = TradingDiscordBot(
            ingestion_service=ingestion_svc,
            channel_manager=channel_svc
        )
        
        # Store bot instance in app config for API access
        app.config['DISCORD_BOT'] = bot
        
        return bot
        
    except ImportError as e:
        logging.error(f"Discord bot import error: {e}")
        logging.warning("Discord bot dependencies not available - bot disabled")
        return None

def start_discord_bot(bot, token):
    """Start the Discord bot with proper event loop handling."""
    import asyncio
    
    try:
        logging.info("Starting Discord bot...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.start(token))
    except Exception as e:
        logging.error(f"Discord bot startup failed: {e}")

def start_discord_bot_background(app):
    """Start Discord bot in background thread with improved error handling."""
    import threading
    
    # Check if bot is enabled
    bot_enabled = os.getenv("ENABLE_DISCORD_BOT", "true").lower() == "true"
    if not bot_enabled:
        logging.info("Discord bot disabled via ENABLE_DISCORD_BOT environment variable")
        return
    
    def run_bot():
        try:
            with app.app_context():
                # Validate token
                token = validate_discord_token()
                if not token:
                    return
                
                # Initialize services
                bot = initialize_bot_services(app)
                if not bot:
                    return
                
                # Start bot
                start_discord_bot(bot, token)
                
        except Exception:
            logging.exception("Discord bot startup failed")

    t = threading.Thread(target=run_bot, daemon=True, name="DiscordBot")
    t.start()
    logging.info("Discord bot background thread launched")

def create_app():
    """Create and configure Flask application with improved error handling."""
    
    # Validate environment before proceeding
    if not validate_environment():
        logging.error("Environment validation failed - some features may not work properly")
    
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

    # Database configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # Alpaca configuration with live data toggle
    use_live_data = os.getenv("USE_LIVE_DATA", "false").lower() == "true"
    app.config.update({
        "ALPACA_API_KEY": os.environ.get("ALPACA_API_KEY", ""),
        "ALPACA_API_SECRET": os.environ.get("ALPACA_API_SECRET", ""),
        "ALPACA_TRADING_URL": "https://api.alpaca.markets" if use_live_data else "https://paper-api.alpaca.markets",
        "ALPACA_DATA_URL": "https://data.alpaca.markets/v2",
        "PAPER_TRADING": not use_live_data,
        "ALPACA_USE_LIVE_DATA": use_live_data
    })

    initialize_db(app)

    # Import feature-specific models with better error handling
    try:
        from features.ingestion.models import DiscordMessageModel
        from features.parsing.models import TradeSetup, ParsedLevel
        logging.info("Core models imported successfully")
    except ImportError as e:
        logging.warning(f"Could not import some models: {e}")
    
    # Initialize enhanced event system
    try:
        from common.events.cleanup_service import cleanup_service
        cleanup_service.start_cleanup_scheduler()
        logging.info("Event cleanup service started")
    except ImportError as e:
        logging.warning(f"Could not start event cleanup service: {e}")
    
    # Initialize Alpaca WebSocket for real-time ticker prices (optional)
    live_stream_enabled = os.getenv("ENABLE_LIVE_PRICE_STREAM", "false").lower() == "true"
    
    if live_stream_enabled and app.config["ALPACA_API_KEY"] and app.config["ALPACA_API_SECRET"]:
        try:
            from features.alpaca.websocket_service import initialize_websocket_service
            websocket_service = initialize_websocket_service(
                api_key=app.config["ALPACA_API_KEY"],
                api_secret=app.config["ALPACA_API_SECRET"],
                paper_trading=app.config["PAPER_TRADING"]
            )
            if websocket_service:
                # Start with common tickers for real-time price updates
                common_tickers = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA']
                websocket_service.start_price_streaming(common_tickers)
                logging.info("Alpaca WebSocket service initialized for real-time prices")
        except Exception as e:
            logging.warning(f"Could not initialize Alpaca WebSocket service: {e}")
    else:
        if live_stream_enabled:
            logging.warning("Live price streaming enabled but Alpaca credentials missing")
        else:
            logging.info("Live price streaming disabled")

    socketio.init_app(app, cors_allowed_origins="*")
    register_feature_routes(app)
    register_web_routes(app)
    register_socketio_events()

    return app

# Build & wire everything
app = create_app()

# Start the bot using the same function, now with proper dependencies
start_discord_bot_background(app)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

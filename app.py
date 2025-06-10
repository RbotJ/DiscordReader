"""
A+ Trading Application Main Module

This is the main entry point for the Flask-based trading application.
It configures the application, initializes components,
and sets up the routes.
"""

print(f"▶️  Starting DiscordReader from {__file__}")

import logging
import os
from datetime import datetime
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO, emit
from common.db import db, initialize_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Socket.IO instance
socketio = SocketIO()

def register_all_blueprints(app):
    """
    Centralized blueprint registration to avoid duplicates.
    This function registers all feature blueprints in a consistent manner.
    """
    blueprints_to_register = []
    
    try:
        # Market features - standardize on api_routes.py
        try:
            from features.market.api_routes import bp as market_bp
            blueprints_to_register.append(('market', market_bp))
        except ImportError as e:
            logging.warning(f"Could not import market blueprint: {e}")
        
        # Execution features  
        try:
            from features.execution.api_routes import bp as execution_bp
            blueprints_to_register.append(('execution', execution_bp))
        except ImportError as e:
            logging.warning(f"Could not import execution blueprint: {e}")
        
        # Options features
        try:
            from features.options.api_routes import bp as options_bp
            blueprints_to_register.append(('options', options_bp))
        except ImportError as e:
            logging.warning(f"Could not import options blueprint: {e}")
        
        # Account features
        try:
            from features.account.api_routes import bp as account_bp
            blueprints_to_register.append(('account', account_bp))
        except ImportError as e:
            logging.warning(f"Could not import account blueprint: {e}")
        
        # Alpaca features
        try:
            from features.alpaca.api import alpaca_bp as alpaca_bp
            blueprints_to_register.append(('alpaca', alpaca_bp))
        except ImportError as e:
            logging.warning(f"Could not import alpaca blueprint: {e}")
        
        # Parsing features
        try:
            from features.parsing.api import parsing_bp as parsing_api_bp
            blueprints_to_register.append(('parsing_api', parsing_api_bp))
        except ImportError as e:
            logging.warning(f"Could not import parsing API blueprint: {e}")
            
        # Parsing dashboard
        try:
            from features.parsing.dashboard import parsing_bp as parsing_dashboard_bp
            blueprints_to_register.append(('parsing_dashboard', parsing_dashboard_bp))
        except ImportError as e:
            logging.warning(f"Could not import parsing dashboard blueprint: {e}")
        
        # Setups features
        try:
            from features.setups.api import setups_bp as setups_bp
            blueprints_to_register.append(('setups', setups_bp))
        except ImportError as e:
            logging.warning(f"Could not import setups blueprint: {e}")
        
        # Register all blueprints
        for name, blueprint in blueprints_to_register:
            if blueprint is not None:
                app.register_blueprint(blueprint)
                logging.info(f"Registered {name} blueprint successfully")
            else:
                logging.warning(f"Blueprint {name} is None, skipping registration")
                
    except Exception as e:
        logging.error(f"Error registering blueprints: {e}")

def register_feature_routes(app):
    """Legacy function - now redirects to centralized blueprint registration"""
    register_all_blueprints(app)
    
    # Register Discord API routes directly
    try:
        from features.discord_bot.api import discord_api_bp
        app.register_blueprint(discord_api_bp)
        logging.info("Discord API routes registered successfully")
    except ImportError as e:
        logging.warning(f"Could not register Discord API routes: {e}")
    
    # Note: Parsing API routes are registered through centralized blueprint registration

def register_web_routes(app):
    """Register main web routes"""
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/health')
    def health():
        return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

def register_socketio_events():
    """Register Socket.IO event handlers"""
    @socketio.on('connect')
    def handle_connect():
        logging.info('Client connected')
        emit('status', {'msg': 'Connected to trading server'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logging.info('Client disconnected')

def start_discord_bot_background(app):
    """Start Discord bot in background thread."""
    import threading
    import asyncio
    
    def run_bot():
        try:
            # Ensure we're in Flask context so ingestion can access DB, events, etc.
            with app.app_context():
                # Gather credentials & early exit if missing
                token = os.getenv("DISCORD_BOT_TOKEN")
                if not token:
                    logging.warning("Discord token missing; bot disabled.")
                    return

                # Build your vertical slices
                try:
                    from features.ingestion.service import IngestionService
                    from features.discord_channels.channel_manager import ChannelManager
                    from common.events.publisher import publish_event
                    from common.db import db

                    # Ingestion slice
                    ingestion_svc = IngestionService()

                    # Channel slice
                    channel_svc = ChannelManager()
                    
                    # Parsing slice
                    from features.parsing.service import start_parsing_service
                    parsing_service = start_parsing_service(app=app)
                    logging.info("Parsing service started successfully")

                    # Discord slice
                    from features.discord_bot.bot import TradingDiscordBot
                    bot = TradingDiscordBot(
                        ingestion_service=ingestion_svc,
                        channel_manager=channel_svc
                    )
                    
                    # Store bot instance in app config for API access
                    app.config['DISCORD_BOT'] = bot

                    logging.info("🔄 Starting Discord bot...")
                    # Get token from environment
                    from features.discord_bot.config.settings import get_discord_token
                    token = get_discord_token()
                    
                    if not token:
                        logging.error("Discord bot token not found in environment")
                        return
                    
                    # Boot the bot
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(bot.start(token))
                    
                except ImportError as e:
                    logging.error(f"Discord bot import error: {e}")
                    logging.warning("Discord bot dependencies not available - bot disabled")
                    return

        except Exception:
            logging.exception("Discord bot startup failed")

    t = threading.Thread(target=run_bot, daemon=True, name="DiscordBot")
    t.start()
    logging.info("Discord bot background thread launched")

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

    # Database configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    app.config.update({
        "ALPACA_API_KEY": os.environ.get("ALPACA_API_KEY", ""),
        "ALPACA_API_SECRET": os.environ.get("ALPACA_API_SECRET", ""),
        "ALPACA_TRADING_URL": "https://paper-api.alpaca.markets",
        "ALPACA_DATA_URL": "https://data.alpaca.markets/v2",
        "PAPER_TRADING": True
    })


    if not app.config["ALPACA_API_KEY"] or not app.config["ALPACA_API_SECRET"]:
        logging.warning("Alpaca API credentials not set. Some features may not work.")

    initialize_db(app)

    # Import feature-specific models instead of centralized models_db
    try:
        from features.ingestion.models import DiscordMessageModel
        from features.discord_bot.models import DiscordChannel
        from features.parsing.models import TradeSetup, ParsedLevel
    except ImportError as e:
        logging.warning(f"Could not import some models: {e}")
    
    # Initialize enhanced event system
    from common.events.cleanup_service import cleanup_service
    cleanup_service.start_cleanup_scheduler()
    
    # Initialize Alpaca WebSocket for real-time ticker prices (optional)
    # Use ENABLE_LIVE_PRICE_STREAM=true to enable (default: disabled)
    live_stream_enabled = app.config.get("ENABLE_LIVE_PRICE_STREAM", "false").lower() == "true"
    
    if live_stream_enabled:
        try:
            from features.alpaca.websocket_service import initialize_websocket_service
            websocket_service = initialize_websocket_service(
                api_key=app.config.get("ALPACA_API_KEY"),
                api_secret=app.config.get("ALPACA_API_SECRET"),
                paper_trading=app.config.get("PAPER_TRADING", True)
            )
            if websocket_service:
                # Start with common tickers for real-time price updates
                common_tickers = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA']
                websocket_service.start_price_streaming(common_tickers)
                logging.info("Alpaca WebSocket service initialized for real-time prices")
        except Exception as e:
            logging.warning(f"Could not initialize Alpaca WebSocket service: {e}")
    else:
        logging.info("Live price streaming disabled (ENABLE_LIVE_PRICE_STREAM=false)")

    socketio.init_app(app, cors_allowed_origins="*")
    register_feature_routes(app)
    register_web_routes(app)
    register_socketio_events()
    
    # Register feature dashboard blueprints
    try:
        from features.discord_bot.dashboard import discord_bp
        from features.discord_channels.dashboard import channels_bp
        from features.ingestion.dashboard import ingest_bp
        from features.parsing.dashboard import parsing_bp
        
        app.register_blueprint(discord_bp)
        app.register_blueprint(channels_bp)
        app.register_blueprint(ingest_bp)
        app.register_blueprint(parsing_bp)
        logging.info("Feature dashboard blueprints registered successfully")
    except ImportError as e:
        logging.warning(f"Could not register dashboard blueprints: {e}")

    return app

# Build & wire everything
app = create_app()

# Start the bot using the same function, now with proper dependencies
start_discord_bot_background(app)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

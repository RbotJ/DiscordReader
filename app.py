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

def register_feature_routes(app):
    """Register feature-specific routes using the new Route Registry"""
    from common.route_registry import register_feature, bootstrap_routes
    
    # Register all feature modules with their route functions
    try:
        # Import and register each feature module
        # Setups functionality now distributed across vertical slices:
        # - Parsing: features.parsing.api
        # - Management: features.management.api 
        # - Dashboard: features.dashboard.api
        import features.parsing.api as parsing_api
        register_feature('parsing', parsing_api)
        
        import features.market.api as market_api  
        register_feature('market', market_api)
        
        import features.execution.api_routes as execution_api
        register_feature('execution', execution_api)
        
        import features.options.api_routes as options_api
        register_feature('options', options_api)
        
        import features.alpaca.api as alpaca_api
        register_feature('alpaca', alpaca_api)
        
        import features.account.api_routes as account_api
        register_feature('account', account_api)
        
        import features.dashboard.api_routes as dashboard_api
        register_feature('dashboard', dashboard_api)
        
        # Bootstrap all registered routes
        bootstrap_routes(app)
        logging.info("All feature routes registered successfully via Route Registry")
        
    except Exception as e:
        logging.error(f"Error registering feature routes: {e}")
        # Fallback to individual registration if needed
        logging.warning("Falling back to individual route registration")
    try:
        from features.dashboard import dashboard_bp
        app.register_blueprint(dashboard_bp)
        logging.info("Dashboard routes registered successfully")
    except ImportError as e:
        logging.warning(f"Could not register dashboard routes: {e}")
    
    # Register enhanced dashboard API routes
    try:
        from features.dashboard.api_routes import dashboard_api
        app.register_blueprint(dashboard_api)
        logging.info("Enhanced dashboard API routes registered successfully")
    except ImportError as e:
        logging.warning(f"Could not register enhanced dashboard API routes: {e}")
    
    # Discord admin routes not yet implemented
    # Future: Add Discord bot management interface

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

                    # Discord slice
                    from features.discord_bot.bot import TradingDiscordBot
                    bot = TradingDiscordBot(
                        token=token,
                        ingestion_service=ingestion_svc,
                        channel_service=channel_svc
                    )

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
    except ImportError as e:
        logging.warning(f"Could not import some models: {e}")
    
    # Initialize enhanced event system
    from common.events.cleanup_service import cleanup_service
    cleanup_service.start_cleanup_scheduler()
    
    # Initialize Alpaca WebSocket for real-time ticker prices
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

    socketio.init_app(app, cors_allowed_origins="*")
    register_feature_routes(app)
    register_web_routes(app)
    register_socketio_events()
    
    # Register feature dashboard blueprints
    try:
        from features.discord_bot.dashboard import discord_bp
        from features.discord_channels.dashboard import channels_bp
        from features.ingestion.dashboard import ingest_bp
        
        app.register_blueprint(discord_bp)
        app.register_blueprint(channels_bp)
        app.register_blueprint(ingest_bp)
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

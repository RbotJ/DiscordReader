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
from common.utils import format_timestamp_local, to_local
import importlib
import pkgutil

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Socket.IO instance
socketio = SocketIO()

def register_all_blueprints(app):
    """
    Centralized blueprint registration using the blueprint registry.
    This function registers all feature blueprints in a consistent manner.
    """
    import importlib
    from features.blueprint_registry import BLUEPRINT_REGISTRY
    
    for name, module_path, attr in BLUEPRINT_REGISTRY:
        try:
            # Use importlib for safer dynamic imports
            module = importlib.import_module(module_path)
            blueprint = getattr(module, attr)
            
            if blueprint is not None:
                app.register_blueprint(blueprint)
                logging.info(f"Registered {name} blueprint successfully")
            else:
                logging.warning(f"Blueprint {name} is None, skipping registration")
                
        except (ImportError, AttributeError) as e:
            logging.warning(f"Failed to register {name} blueprint: {e}")
        except Exception as e:
            logging.error(f"Unexpected error registering {name} blueprint: {e}")

def discover_plugins():
    """Yield all feature plugins discovered in the features package."""
    for _, name, _ in pkgutil.iter_modules(['features']):
        module = importlib.import_module(f'features.{name}')
        if hasattr(module, 'get_plugin'):
            yield module.get_plugin()

def register_plugins(app):
    """Register plugins with the Flask application."""
    for plugin in discover_plugins():
        try:
            plugin.register(app)
        except Exception as e:
            logging.warning(f"Failed to register plugin {plugin}: {e}")

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
    from flask import current_app
    
    @socketio.on('connect')
    def handle_connect():
        logging.info('Client connected')
        emit('status', {'msg': 'Connected to trading server'})
        
        # Start async services if they haven't been started yet
        if hasattr(current_app, 'config') and not current_app.config.get('ASYNC_SERVICES_STARTED'):
            starter = current_app.config.get('ASYNC_SERVICES_STARTER')
            if starter:
                starter()
                current_app.config['ASYNC_SERVICES_STARTED'] = True
                logging.info("✅ Async services triggered via SocketIO connect")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logging.info('Client disconnected')

async def start_unified_async_services(app):
    """Start Discord bot and PostgreSQL listener in unified async context."""
    import asyncio
    
    try:
        # Ensure we're in Flask context so services can access DB, events, etc.
        with app.app_context():
            # Gather credentials & early exit if missing
            token = os.getenv("DISCORD_BOT_TOKEN")
            if not token:
                logging.warning("Discord token missing; bot disabled.")
                return

            # Build your vertical slices
            try:
                from common.plugin_loader import discover_class
                from features.discord_channels.channel_manager import ChannelManager
                from common.events.publisher import publish_event
                from common.db import db

                # Ingestion slice via plugin discovery
                IngestionService = discover_class(
                    "IngestionService", ["features.ingestion.service"]
                )
                if not IngestionService:
                    logging.error("IngestionService plugin not found")
                    return
                ingestion_svc = IngestionService()

                # Channel slice
                channel_svc = ChannelManager()
                
                # Parsing slice
                from features.parsing.service import start_parsing_service
                parsing_service = start_parsing_service(app=app)
                logging.info("Parsing service started successfully")

                # Start PostgreSQL event listener in shared async context
                from features.ingestion.listener import start_ingestion_listener
                
                # Create task for PostgreSQL listener
                listener_task = asyncio.create_task(start_ingestion_listener())
                logging.info("PostgreSQL ingestion listener started in shared async context")

                # Discord slice
                from features.discord_bot.bot import TradingDiscordBot
                bot = TradingDiscordBot(
                    ingestion_service=ingestion_svc,
                    channel_manager=channel_svc,
                    flask_app=app
                )
                
                # Store bot instance in app config for API access BEFORE starting
                app.config['DISCORD_BOT'] = bot
                logging.info("✅ Discord bot initialized and registered in app.config['DISCORD_BOT']")

                logging.info("Starting Discord bot in shared async context...")
                # Get token from environment
                from features.discord_bot.config.settings import get_discord_token
                token = get_discord_token()
                
                if not token:
                    logging.error("Discord bot token not found in environment")
                    return
                
                # Create task for Discord bot
                bot_task = asyncio.create_task(bot.start(token))
                logging.info("Discord bot task created in shared async context")
                
                # Wait for both tasks to complete
                await asyncio.gather(listener_task, bot_task, return_exceptions=True)
                
            except ImportError as e:
                logging.error(f"Discord bot import error: {e}")
                logging.warning("Discord bot dependencies not available - bot disabled")
                return

    except Exception:
        logging.exception("Unified async services startup failed")

def initialize_async_services(app):
    """Initialize async services and immediately create bot instance."""
    try:
        # Create and register Discord bot instance immediately
        with app.app_context():
            try:
                # Get credentials early
                token = os.getenv("DISCORD_BOT_TOKEN")
                if not token:
                    logging.warning("Discord token missing; bot registration skipped.")
                    return
                
                logging.info("Creating Discord bot services...")
                
                # Create services
                from common.plugin_loader import discover_class
                from features.discord_channels.channel_manager import ChannelManager
                
                IngestionService = discover_class(
                    "IngestionService", ["features.ingestion.service"]
                )
                if not IngestionService:
                    logging.error("IngestionService plugin not found")
                    return
                ingestion_svc = IngestionService()
                channel_svc = ChannelManager()
                logging.info("Discord bot services created successfully")
                
                # Create bot instance
                from features.discord_bot.bot import TradingDiscordBot
                logging.info("Creating TradingDiscordBot instance...")
                
                bot = TradingDiscordBot(
                    ingestion_service=ingestion_svc,
                    channel_manager=channel_svc,
                    flask_app=app
                )
                
                # Store bot immediately for API access
                app.config['DISCORD_BOT'] = bot
                logging.info("✅ Discord bot instance created and registered in app.config['DISCORD_BOT']")
                
                # Schedule background startup and start immediately
                def start_services():
                    try:
                        # Use SocketIO's background task for async operations
                        def async_wrapper():
                            import asyncio
                            try:
                                # Create new event loop for background task
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                # Start the Discord bot connection
                                async def connect_bot():
                                    try:
                                        logging.info("Starting Discord bot connection...")
                                        await bot.start(token)
                                    except Exception as e:
                                        logging.error(f"Discord bot connection failed: {e}")
                                
                                loop.run_until_complete(connect_bot())
                            except Exception as e:
                                logging.error(f"Error in async wrapper: {e}")
                            finally:
                                try:
                                    loop.close()
                                except:
                                    pass
                        
                        socketio.start_background_task(async_wrapper)
                        logging.info("Discord bot background startup scheduled and initiated")
                    except Exception as e:
                        logging.error(f"Failed to start async services: {e}")
                
                app.config['ASYNC_SERVICES_STARTER'] = start_services
                
                # Start services immediately during initialization
                start_services()
                
            except ImportError as e:
                logging.error(f"Discord bot import error during initialization: {e}")
                logging.exception("Full import traceback:")
            except Exception as e:
                logging.error(f"Unexpected error during Discord bot initialization: {e}")
                logging.exception("Full initialization traceback:")
        
    except Exception as e:
        logging.error(f"Failed to initialize async services: {e}")

def run_async_services_safe(app):
    """Safely run async services using SocketIO's event loop."""
    import asyncio
    
    try:
        # Run async services in the current event loop if available, otherwise schedule
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        
        if loop:
            # We're in an async context, create a task
            async def run_services():
                try:
                    with app.app_context():
                        await start_unified_async_services(app)
                except Exception as e:
                    logging.error(f"Error in async services: {e}")
            
            task = loop.create_task(run_services())
            logging.info("✅ Discord bot async task created")
            return task
        else:
            # No event loop, let SocketIO handle it
            logging.info("No event loop available, services will start on SocketIO connect")
            return None
            
    except Exception as e:
        logging.error(f"Error setting up async services: {e}")
        return None

def validate_environment():
    """
    Validate required and optional environment variables.
    Provides early detection of configuration issues.
    """
    # Required environment variables
    REQUIRED_ENV_VARS = [
        "DATABASE_URL",
    ]
    
    # Optional but recommended environment variables
    RECOMMENDED_ENV_VARS = [
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET", 
        "DISCORD_BOT_TOKEN",
        "SESSION_SECRET"
    ]
    
    # Check required variables
    missing_required = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing_required:
        logging.error(f"Missing required environment variables: {', '.join(missing_required)}")
        raise ValueError(f"Required environment variables not set: {', '.join(missing_required)}")
    
    # Check recommended variables
    missing_recommended = [var for var in RECOMMENDED_ENV_VARS if not os.getenv(var)]
    if missing_recommended:
        logging.warning(f"Missing recommended environment variables: {', '.join(missing_recommended)}")
        logging.warning("Some features may not work properly without these variables")
    
    # Log configuration status
    logging.info("Environment validation completed successfully")
    if not missing_recommended:
        logging.info("All recommended environment variables are configured")

def create_app():
    # Validate environment before creating app
    validate_environment()
    
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
        from features.parsing.models import TradeSetup, ParsedLevel
        # Discord channel model import is optional - skip if not available
        pass
    except ImportError as e:
        logging.warning(f"Could not import some models: {e}")
    
    # Initialize enhanced event system
    from common.events.cleanup_service import cleanup_service
    cleanup_service.start_cleanup_scheduler()
    
    # Start ingestion listener after database initialization
    print("[init] About to attempt ingestion listener startup")
    logging.info("[init] About to attempt ingestion listener startup")
    
    try:
        print("[init] Importing required modules for ingestion listener")
        import threading
        import asyncio
        from features.ingestion.listener import start_ingestion_listener
        
        print("[init] Modules imported successfully")
        logging.info("[init] Modules imported successfully")
        
        def start_ingestion_background():
            """Start ingestion listener in background thread."""
            print("[init] Starting ingestion listener background thread execution...")
            logging.info("[init] Starting ingestion listener background thread execution...")
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                print("[init] Event loop created")
                
                # Start the ingestion listener
                loop.run_until_complete(start_ingestion_listener())
                print("✅ PostgreSQL ingestion listener started")
                logging.info("✅ PostgreSQL ingestion listener started")
                
                # Keep the listener running
                loop.run_forever()
            except Exception as e:
                print(f"Error in ingestion listener background thread: {e}")
                logging.error(f"Error in ingestion listener background thread: {e}")
                import traceback
                logging.error(f"Traceback: {traceback.format_exc()}")
            finally:
                try:
                    loop.close()
                except:
                    pass
        
        # Start in daemon thread to avoid blocking app startup
        print("[init] Creating ingestion background thread")
        ingestion_thread = threading.Thread(target=start_ingestion_background, daemon=True)
        ingestion_thread.start()
        print("[init] Ingestion listener background thread started")
        logging.info("[init] Ingestion listener background thread started")
        
    except Exception as e:
        print(f"Failed to start ingestion listener: {e}")
        logging.error(f"Failed to start ingestion listener: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
    
    # Initialize Alpaca WebSocket for real-time ticker prices (optional)
    # Use ENABLE_LIVE_PRICE_STREAM=true to enable (default: disabled)
    live_stream_enabled = app.config.get("ENABLE_LIVE_PRICE_STREAM", "false").lower() == "true"
    
    if live_stream_enabled:
        try:
            from features.alpaca.websocket_service import initialize_websocket_service
            api_key = app.config.get("ALPACA_API_KEY")
            api_secret = app.config.get("ALPACA_API_SECRET")
            
            if api_key and api_secret:
                websocket_service = initialize_websocket_service(
                    api_key=str(api_key),
                    api_secret=str(api_secret),
                    paper_trading=app.config.get("PAPER_TRADING", True)
                )
            else:
                logging.warning("Alpaca API credentials missing - WebSocket service disabled")
                websocket_service = None
            if websocket_service:
                # Start with common tickers for real-time price updates
                common_tickers = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA']
                websocket_service.start_price_streaming(common_tickers)
                logging.info("Alpaca WebSocket service initialized for real-time prices")
        except Exception as e:
            logging.warning(f"Could not initialize Alpaca WebSocket service: {e}")
    else:
        logging.info("Live price streaming disabled (ENABLE_LIVE_PRICE_STREAM=false)")

    # Add Jinja template filters for timezone conversion
    @app.template_filter('localtime')
    def localtime_filter(utc_dt, format_str='%Y-%m-%d %H:%M:%S %Z', tz_name="America/Chicago"):
        """Convert UTC datetime to local timezone for display."""
        from datetime import datetime
        from common.utils import to_local, ensure_utc
        
        if utc_dt is None:
            return "N/A"
        
        # Ensure we have a timezone-aware datetime object
        try:
            utc_dt = ensure_utc(utc_dt)
            local_dt = to_local(utc_dt, tz_name)
            return local_dt.strftime(format_str)
        except Exception as e:
            logging.warning(f"Failed to convert timestamp to local time: {e}")
            return str(utc_dt)
    
    @app.template_filter('localdate')
    def localdate_filter(utc_dt, tz_name="America/Chicago"):
        """Convert UTC datetime to local date for display."""
        from datetime import datetime
        from common.utils import to_local, ensure_utc
        
        if utc_dt is None:
            return "N/A"
        
        try:
            utc_dt = ensure_utc(utc_dt)
            local_dt = to_local(utc_dt, tz_name)
            return local_dt.strftime('%b %d, %Y')
        except Exception as e:
            logging.warning(f"Failed to convert date to local time: {e}")
            return str(utc_dt) if utc_dt else "N/A"

    socketio.init_app(app, cors_allowed_origins="*")
    register_plugins(app)
    register_web_routes(app)
    register_socketio_events()
    
    # Start ingestion listener automatically during app creation (no curl dependency)
    if os.getenv("DISCORD_BOT_TOKEN"):
        print("[STARTUP] Starting PostgreSQL ingestion listener automatically...")
        logging.info("[STARTUP] Starting PostgreSQL ingestion listener automatically...")
        
        try:
            import threading
            import asyncio
            from features.ingestion.listener import start_ingestion_listener
            
            def start_ingestion_background():
                """Start ingestion listener in background thread at app startup."""
                print("[STARTUP] Starting ingestion listener background thread...")
                logging.info("[STARTUP] Starting ingestion listener background thread...")
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Start the ingestion listener
                    loop.run_until_complete(start_ingestion_listener())
                    print("✅ PostgreSQL ingestion listener started at app startup")
                    logging.info("✅ PostgreSQL ingestion listener started at app startup")
                    
                    # Keep the listener running
                    loop.run_forever()
                except Exception as e:
                    print(f"Error in ingestion listener at startup: {e}")
                    logging.error(f"Error in ingestion listener at startup: {e}")
                    import traceback
                    logging.error(f"Traceback: {traceback.format_exc()}")
                finally:
                    try:
                        loop.close()
                    except:
                        pass
            
            # Start in daemon thread immediately during app creation
            ingestion_thread = threading.Thread(target=start_ingestion_background, daemon=True)
            ingestion_thread.start()
            print("[STARTUP] Ingestion listener thread started automatically")
            logging.info("[STARTUP] Ingestion listener thread started automatically")
            
        except Exception as e:
            print(f"Failed to start ingestion listener at startup: {e}")
            logging.error(f"Failed to start ingestion listener at startup: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
    else:
        print("[STARTUP] Discord bot disabled - ingestion listener not started")
        logging.info("[STARTUP] Discord bot disabled - ingestion listener not started")

    
    # Note: Feature dashboard blueprints are already registered through register_all_blueprints

    return app

# Build & wire everything
print("[STARTUP] About to create Flask app...")
app = create_app()
print("[STARTUP] Flask app created successfully")

# Initialize async services (Discord bot, event listeners) only if enabled
print("[STARTUP] Checking DISCORD_BOT_TOKEN setting...")
logging.info("[STARTUP] Checking DISCORD_BOT_TOKEN setting...")

if os.getenv("DISCORD_BOT_TOKEN") is not None:
    print("[STARTUP] Starting initialize_async_services...")
    logging.info("[STARTUP] Starting initialize_async_services...")
    initialize_async_services(app)
    print("[STARTUP] Async services initialization enabled")
    logging.info("[STARTUP] Async services initialization enabled")
    
    # Start ingestion listener immediately at module level
    print("[STARTUP] Starting ingestion listener initialization...")
    logging.info("[STARTUP] Starting ingestion listener initialization...")
    
    try:
        import threading
        import asyncio
        from features.ingestion.listener import start_ingestion_listener
        
        print("[STARTUP] Successfully imported start_ingestion_listener")
        logging.info("[STARTUP] Successfully imported start_ingestion_listener")
        
        def start_ingestion_background():
            """Start ingestion listener in background thread at module level."""
            print("[STARTUP] Starting ingestion listener background thread execution...")
            logging.info("[STARTUP] Starting ingestion listener background thread execution...")
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                print("[STARTUP] Event loop created for ingestion listener")
                
                # Start the ingestion listener
                loop.run_until_complete(start_ingestion_listener())
                print("✅ PostgreSQL ingestion listener started")
                logging.info("✅ PostgreSQL ingestion listener started")
                
                # Keep the listener running
                loop.run_forever()
            except Exception as e:
                print(f"Error in ingestion listener background thread: {e}")
                logging.error(f"Error in ingestion listener background thread: {e}")
                import traceback
                logging.error(f"Traceback: {traceback.format_exc()}")
            finally:
                try:
                    loop.close()
                except:
                    pass
        
        # Start in daemon thread at module level
        print("[STARTUP] Creating ingestion background thread")
        ingestion_thread = threading.Thread(target=start_ingestion_background, daemon=True)
        ingestion_thread.start()
        print("[STARTUP] Ingestion listener background thread started")
        logging.info("[STARTUP] Ingestion listener background thread started")
        
    except Exception as e:
        print(f"Failed to start ingestion listener: {e}")
        logging.error(f"Failed to start ingestion listener: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
else:
    print("[STARTUP] Discord bot disabled via ENABLE_DISCORD_BOT")
    logging.info("[STARTUP] Discord bot disabled via ENABLE_DISCORD_BOT")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, log_output=True)

"""
A+ Trading Application Main Module

This is the main entry point for the Flask-based trading application.
It configures the application, initializes components,
and sets up the routes.
"""

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
    """Register feature-specific routes"""
    try:
        from features.dashboard import dashboard_bp
        app.register_blueprint(dashboard_bp)
        logging.info("Dashboard routes registered successfully")
    except ImportError as e:
        logging.warning(f"Could not register dashboard routes: {e}")
    
    try:
        from features.discord.admin_routes import discord_admin_bp
        app.register_blueprint(discord_admin_bp)
        logging.info("Discord admin routes registered successfully")
    except ImportError as e:
        logging.warning(f"Could not register Discord admin routes: {e}")

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

    from common import models_db  # Import models after db init

    socketio.init_app(app, cors_allowed_origins="*")
    register_feature_routes(app)
    register_web_routes(app)
    register_socketio_events()

    return app

# Application setup
app = create_app()

# Register socket events and features
# (Functions unchanged from original, omitted here for brevity)
# See full source if needed for `register_socketio_events`, `register_feature_routes`, etc.

# Component initialization on startup
with app.app_context():
    try:
        # Initialize database tables
        from common.db import db
        db.create_all()
        logging.info("Database tables initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing database: {e}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

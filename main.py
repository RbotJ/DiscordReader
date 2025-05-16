import logging
import os
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from flask import Flask, jsonify
from common.db import db
from features.setups.models import (
    SetupMessage, TickerSetup, Signal, SignalTarget, Bias
)

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
    
    # Register routes
    register_routes(app)
    
    return app

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
    app.run(host='0.0.0.0', port=5000, debug=True)
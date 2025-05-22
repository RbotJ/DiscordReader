"""
A+ Trading Application Core

This module initializes the Flask application, sets up configuration,
and provides access to core components for the trading application.
"""
import os
import logging
from flask import Flask, render_template, redirect, url_for
import redis

# Initialize logger
logger = logging.getLogger(__name__)

# Import our database module
from common.db import db, initialize_db

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "a_secure_temporary_secret_for_development")

# Initialize database
initialize_db(app)

# Initialize event system
from common.events.compat import ensure_event_system, event_client
ensure_event_system()

# Configure Alpaca API credentials
ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_API_SECRET = os.environ.get("ALPACA_API_SECRET", "")
ALPACA_API_BASE_URL = os.environ.get("ALPACA_API_BASE_URL", "https://paper-api.alpaca.markets")

# Configuration for paper trading
PAPER_TRADING = True

# Store application configuration
app_config = {
    "ALPACA_API_KEY": ALPACA_API_KEY,
    "ALPACA_API_SECRET": ALPACA_API_SECRET,
    "ALPACA_API_BASE_URL": ALPACA_API_BASE_URL,
    "PAPER_TRADING": PAPER_TRADING
}

# Add configuration to Flask app
app.config.update(app_config)

# Check if Alpaca API credentials are set
if not ALPACA_API_KEY or not ALPACA_API_SECRET:
    logger.warning("Alpaca API credentials not set. Some features may not work.")

# Note: Routes are now defined in main.py to avoid duplication

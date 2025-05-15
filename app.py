import os
import logging
from flask import Flask, render_template, redirect, url_for
import redis

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "a_secure_temporary_secret_for_development")

# Configure Redis connection
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_client = redis.from_url(redis_url)

# Initialize logger
logger = logging.getLogger(__name__)

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
    "PAPER_TRADING": PAPER_TRADING,
    "REDIS_URL": redis_url
}

# Add configuration to Flask app
app.config.update(app_config)

# Check if Alpaca API credentials are set
if not ALPACA_API_KEY or not ALPACA_API_SECRET:
    logger.warning("Alpaca API credentials not set. Some features may not work.")

# Define routes for the main application
@app.route('/')
def index():
    """Render the main dashboard."""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Render the detailed dashboard."""
    return render_template('dashboard.html')

import os
import logging
from flask import Flask, render_template, redirect, url_for
import redis
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Initialize logger
logger = logging.getLogger(__name__)

# Define SQLAlchemy base class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with our base class
db = SQLAlchemy(model_class=Base)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "a_secure_temporary_secret_for_development")

# Configure database
database_url = os.environ.get("DATABASE_URL")
if database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
else:
    logger.warning("DATABASE_URL not set. Using SQLite for development.")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///aplus_trading.db"

# Configure Redis connection
from common.redis_utils import RedisClient, ensure_redis_is_running
# Try to start Redis server first
ensure_redis_is_running()
redis_url = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
# Initialize the global redis client
import common.redis_utils
redis_client = RedisClient(redis_url)
common.redis_utils.redis_client = redis_client

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

# Initialize SQLAlchemy with the app
db.init_app(app)

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

@app.route('/setup')
def setup_form():
    """Render the setup submission form."""
    return render_template('setup_form.html')

@app.route('/trading')
def trading_dashboard():
    """Render the trading dashboard."""
    return render_template('trading_dashboard.html')

@app.route('/parser')
def setup_parser():
    """Render the setup parser UI."""
    return render_template('setup_parser.html')

@app.route('/webhook-tester')
def webhook_tester():
    """Render the webhook tester UI."""
    return render_template('setup_webhook_tester.html')

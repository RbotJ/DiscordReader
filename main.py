import logging
import os
import subprocess
import time
import sys

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from app import app, db
from flask import jsonify

# Import SQLAlchemy models
from common.db_models import (
    SetupModel, TickerSetupModel, SignalModel, BiasModel,
    OptionsContractModel, OrderModel, PositionModel, PriceTriggerModel,
    MarketDataModel, WatchlistModel, NotificationModel
)

# Import route registrations (try/except for each in case files don't exist yet)
try:
    # Import the setup routes
    from features.setups.api import register_routes as register_setup_routes
    register_setup_routes(app)
    logging.info("Setup routes registered")
except ImportError as e:
    logging.warning(f"Could not import setup routes: {e}")

try:
    # Market data routes
    from features.market.api import market_routes
    app.register_blueprint(market_routes)
    logging.info("Market routes registered")
except ImportError as e:
    logging.warning(f"Could not import market routes: {e}")

try:
    # Strategy detector routes
    from features.strategy.detector import strategy_routes
    app.register_blueprint(strategy_routes)
    logging.info("Strategy routes registered")
except ImportError as e:
    logging.warning(f"Could not import strategy routes: {e}")

try:
    # Options chain routes
    from features.options.chain import register_options_routes
    register_options_routes(app)
    logging.info("Options routes registered")
except ImportError as e:
    logging.warning(f"Could not import options chain routes: {e}")

try:
    # Contract filter routes
    from features.options.contract_filter import register_contract_filter_routes
    register_contract_filter_routes(app)
    logging.info("Contract filter routes registered")
except ImportError as e:
    logging.warning(f"Could not import contract filter routes: {e}")

try:
    # Greeks calculator routes
    from features.options.greeks_calculator import register_greeks_routes
    register_greeks_routes(app)
    logging.info("Greeks calculator routes registered")
except ImportError as e:
    logging.warning(f"Could not import Greeks calculator routes: {e}")

try:
    # Risk assessor routes
    from features.options.risk_assessor import register_risk_assessor_routes
    register_risk_assessor_routes(app)
    logging.info("Risk assessor routes registered")
except ImportError as e:
    logging.warning(f"Could not import risk assessor routes: {e}")

try:
    # Trade execution routes
    from features.execution.trader import execution_routes
    app.register_blueprint(execution_routes)
    logging.info("Execution routes registered")
except ImportError as e:
    logging.warning(f"Could not import execution routes: {e}")

try:
    # Position management routes
    from features.management.position_manager import register_position_routes
    register_position_routes(app)
    logging.info("Position management routes registered")
except ImportError as e:
    logging.warning(f"Could not import position management routes: {e}")

try:
    # Exit rules routes
    from features.management.exit_rules import register_exit_rules_routes
    register_exit_rules_routes(app)
    logging.info("Exit rules routes registered")
except ImportError as e:
    logging.warning(f"Could not import exit rules routes: {e}")

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create database tables
with app.app_context():
    db.create_all()
    logging.info("Database tables created")

# Add API health check endpoint
@app.route('/api/health')
def health_check():
    """API health check endpoint."""
    return jsonify({
        "status": "ok",
        "timestamp": str(os.environ.get("REPL_SLUG", "aplus-trading-app")),
        "version": "0.1.0"
    })

# Initialize app components after startup
def initialize_app_components():
    """Initialize app components on first request."""
    # Initialize position manager
    try:
        from features.management.position_manager import start_position_manager
        start_position_manager()
        logging.info("Position manager initialized")
    except ImportError as e:
        logging.warning(f"Could not initialize position manager: {e}")
        
    # Initialize exit rules engine
    try:
        from features.management.exit_rules import init_exit_rules_engine
        init_exit_rules_engine()
        logging.info("Exit rules engine initialized")
    except ImportError as e:
        logging.warning(f"Could not initialize exit rules engine: {e}")

# Set up a function to initialize components with the app context
with app.app_context():
    # Try to initialize components after database setup
    try:
        initialize_app_components()
    except Exception as e:
        logging.error(f"Error initializing app components: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

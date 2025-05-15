import logging
import os
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
    from features.setups.api import setup_routes
    app.register_blueprint(setup_routes)
except ImportError:
    logging.warning("Setup routes not found, skipping registration")

try:
    from features.market.price_monitor import market_routes
    app.register_blueprint(market_routes)
except ImportError:
    logging.warning("Market routes not found, skipping registration")

try:
    from features.strategy.detector import strategy_routes
    app.register_blueprint(strategy_routes)
except ImportError:
    logging.warning("Strategy routes not found, skipping registration")

try:
    from features.options_selector.chain_fetcher import options_routes
    app.register_blueprint(options_routes)
except ImportError:
    logging.warning("Options routes not found, skipping registration")

try:
    from features.execution.executor import execution_routes
    app.register_blueprint(execution_routes)
except ImportError:
    logging.warning("Execution routes not found, skipping registration")

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

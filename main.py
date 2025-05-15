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
# Import the setup routes
from features.setups.api import setup_routes
app.register_blueprint(setup_routes)
logging.info("Setup routes registered")

# Market data routes
from features.market.api import market_routes
app.register_blueprint(market_routes)
logging.info("Market routes registered")

# Strategy detector routes
from features.strategy.detector import strategy_routes
app.register_blueprint(strategy_routes)
logging.info("Strategy routes registered")

# Options chain routes
from features.options.chain import options_routes
app.register_blueprint(options_routes)
logging.info("Options routes registered")

# Trade execution routes
from features.execution.trader import execution_routes
app.register_blueprint(execution_routes)
logging.info("Execution routes registered")

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

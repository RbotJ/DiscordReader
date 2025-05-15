import logging
import os
from app import app
from features.setups.api import setup_routes
from features.market.price_monitor import market_routes
from features.strategy.detector import strategy_routes
from features.options_selector.chain_fetcher import options_routes
from features.execution.executor import execution_routes

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Register route blueprints
app.register_blueprint(setup_routes)
app.register_blueprint(market_routes)
app.register_blueprint(strategy_routes)
app.register_blueprint(options_routes)
app.register_blueprint(execution_routes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

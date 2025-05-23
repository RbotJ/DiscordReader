    """
    A+ Trading Application Main Module

    This is the main entry point for the trading application.
    It configures the Flask application, initializes components,
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

    def create_app():
        app = Flask(__name__)
        app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

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
            from main_components import initialize_app_components
            initialize_app_components()
        except Exception as e:
            logging.error(f"Error initializing app components: {e}")

    if __name__ == '__main__':
        socketio.run(app, host='0.0.0.0', port=5000)

    """
    Common Utilities

    General-purpose helpers for logging, config loading, value parsing, trade calculations, and setup analysis.
    """

    import os
    import logging
    import json
    import uuid
    from datetime import datetime, date
    from typing import List, Optional, Set, Dict, Any, Union

    from common.models import TickerSetupDTO, Signal, Bias

    # --- Logging ---
    def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
        """Get a configured logger instance."""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    logger = get_logger(__name__)

    # --- JSON Support ---
    class DateTimeEncoder(json.JSONEncoder):
        """Custom JSON encoder for datetime and date objects."""
        def default(self, obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return super().default(obj)

    # --- Configuration Loader ---
    def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from a JSON file or environment variables."""
        config = {}

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Configuration loaded from {config_path}")
            except Exception as e:
                logger.error(f"Error loading config from {config_path}: {e}")

        env_vars = {
            "ALPACA_API_KEY": os.environ.get("ALPACA_API_KEY"),
            "ALPACA_API_SECRET": os.environ.get("ALPACA_API_SECRET"),
            "ALPACA_API_BASE_URL": os.environ.get("ALPACA_API_BASE_URL"),
            "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO"),
        }

        for key, value in env_vars.items():
            if value is not None:
                config[key] = value

        return config

    # --- Value Parsers & Formatters ---
    def parse_float(value: str) -> Optional[float]:
        """Parse a string to a float, returning None if parsing fails."""
        try:
            return float(value.replace('$', '').replace(',', '').strip())
        except (ValueError, AttributeError):
            return None

    def format_currency(value: float) -> str:
        """Format a float as a currency string."""
        return f"${value:,.2f}"

    # --- Trade Calculations ---
    def calculate_risk_reward(entry: float, target: float, stop: float) -> Optional[float]:
        """Calculate risk/reward ratio for a trade."""
        try:
            reward = abs(target - entry)
            risk = abs(entry - stop)
            if risk == 0:
                return None
            return reward / risk
        except (TypeError, ZeroDivisionError):
            return None

    # --- Order ID Generator ---
    def generate_client_order_id(prefix: str = "aplus") -> str:
        """Generate a unique client order ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = uuid.uuid4().hex[:8]
        return f"{prefix}_{timestamp}_{random_suffix}"

    # --- Trade Logging ---
    def log_trade_execution(trade_data: Dict[str, Any]) -> None:
        """Log trade execution details."""
        logger.info(f"Trade executed: {json.dumps(trade_data, cls=DateTimeEncoder)}")

    # --- Setup Analysis ---
    def extract_all_levels(setups: List[TickerSetupDTO]) -> Set[float]:
        """
        Extract all unique price levels from a list of ticker setups.
        Includes triggers, targets, bias prices, and flip levels.
        """
        levels: Set[float] = set()

        for setup in setups:
            for signal in setup.signals:
                if isinstance(signal.trigger, (int, float)):
                    levels.add(float(signal.trigger))
                elif isinstance(signal.trigger, tuple):
                    levels.update(float(t) for t in signal.trigger)
                levels.update(float(t) for t in signal.targets)

            if setup.bias:
                levels.add(float(setup.bias.price))
                if setup.bias.flip and setup.bias.flip.price_level:
                    levels.add(float(setup.bias.flip.price_level))

        return levels

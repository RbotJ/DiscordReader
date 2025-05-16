"""
Strategy detection and execution module initialization.

This module handles the detection of trading signals based on price triggers
and candle patterns, as well as order execution based on those signals.
"""
import logging
from flask import Blueprint

from features.strategy.detector import strategy_routes
from features.strategy.candle_detector import (
    start_candle_detector,
    stop_candle_detector,
    get_candle_detector
)

# Export blueprint
__all__ = ["strategy_routes", "initialize_strategy", "shutdown_strategy"]

# Configure logger
logger = logging.getLogger(__name__)


def initialize_strategy():
    """Initialize and start strategy components."""
    try:
        # Start candle detector
        start_candle_detector()
        logger.info("Candle detector started")
        
        # Initialize options trader if available
        try:
            from features.execution.options_trader import start_options_trader
            start_options_trader()
            logger.info("Options trader started")
        except ImportError:
            logger.warning("Options trader module not found")
        
        logger.info("Strategy components initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing strategy components: {e}")
        return False


def shutdown_strategy():
    """Shutdown strategy components."""
    try:
        # Stop candle detector
        stop_candle_detector()
        logger.info("Candle detector stopped")
        
        # Stop options trader if available
        try:
            from features.execution.options_trader import stop_options_trader
            stop_options_trader()
            logger.info("Options trader stopped")
        except ImportError:
            logger.warning("Options trader module not found")
        
        logger.info("Strategy components shutdown successfully")
        return True
    except Exception as e:
        logger.error(f"Error shutting down strategy components: {e}")
        return False
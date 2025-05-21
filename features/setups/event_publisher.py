"""
Event Publisher for Setup Events

This module provides functionality to publish setup events to the PostgreSQL event system
or a fallback in-memory queue when the database is not available.
"""
import json
import logging
from typing import Dict, Any, Optional, List

from common.events import publish_event
from common.models import TradeSetupMessage, TickerSetup
from common.event_constants import SETUP_CREATED_CHANNEL, SIGNAL_CREATED_CHANNEL, EventType

logger = logging.getLogger(__name__)


def publish_setup_event(setup_message: TradeSetupMessage) -> bool:
    """
    Publish a setup message created event to Redis.
    
    Args:
        setup_message: The trade setup message to publish
        
    Returns:
        bool: True if published successfully, False otherwise
    """
    try:
        # Get Redis client
        redis_client = get_redis_client()
        if not redis_client:
            logger.warning("Redis client not available, using fallback")
            return _publish_to_fallback(setup_message)
        
        # Prepare event data
        event_data = {
            "event_type": "setup_created",
            "setup": {
                "date": setup_message.date.isoformat(),
                "source": setup_message.source,
                "ticker_count": len(setup_message.setups),
                "tickers": [setup.symbol for setup in setup_message.setups]
            }
        }
        
        # Publish to Redis
        redis_client.publish(
            SETUP_CREATED_CHANNEL,
            json.dumps(event_data)
        )
        
        # Also publish individual signal events
        for ticker_setup in setup_message.setups:
            _publish_signals_for_ticker(redis_client, ticker_setup)
        
        return True
    
    except Exception as e:
        logger.error(f"Error publishing setup event: {str(e)}")
        return _publish_to_fallback(setup_message)


def _publish_signals_for_ticker(redis_client, ticker_setup: TickerSetup) -> None:
    """
    Publish signal events for a ticker setup.
    
    Args:
        redis_client: The Redis client to use
        ticker_setup: The ticker setup to publish signals for
    """
    for signal in ticker_setup.signals:
        event_data = {
            "event_type": "signal_created",
            "symbol": ticker_setup.symbol,
            "signal": {
                "category": signal.category.value,
                "aggressiveness": signal.aggressiveness.value,
                "comparison": signal.comparison.value,
                "trigger": signal.trigger if isinstance(signal.trigger, float) else str(signal.trigger),
                "targets": signal.targets
            },
            "bias": None
        }
        
        # Add bias if present
        if ticker_setup.bias:
            event_data["bias"] = {
                "direction": ticker_setup.bias.direction.value,
                "condition": ticker_setup.bias.condition.value,
                "price": ticker_setup.bias.price
            }
        
        # Publish to Redis
        redis_client.publish(
            SIGNAL_CREATED_CHANNEL,
            json.dumps(event_data)
        )


def _publish_to_fallback(setup_message: TradeSetupMessage) -> bool:
    """
    Publish to fallback mechanism when Redis is not available.
    Logs the events that would have been published.
    
    Args:
        setup_message: The trade setup message
        
    Returns:
        bool: True to indicate fallback was used
    """
    logger.info(
        f"FALLBACK EVENT: Setup created with {len(setup_message.setups)} tickers: "
        f"{[setup.symbol for setup in setup_message.setups]}"
    )
    
    # Log individual signal events
    for ticker_setup in setup_message.setups:
        for signal in ticker_setup.signals:
            logger.info(
                f"FALLBACK EVENT: Signal created for {ticker_setup.symbol} - "
                f"{signal.category.value} {signal.comparison.value} {signal.trigger}"
            )
    
    return True
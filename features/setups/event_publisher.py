"""
Setup Event Publisher Module

This module publishes setup-related events to Redis for other components to consume.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from common.redis_utils import redis_client
from common.event_constants import (
    SETUP_CREATED_CHANNEL,
    SETUP_UPDATED_CHANNEL,
    SIGNAL_CREATED_CHANNEL,
    SIGNAL_TRIGGERED_CHANNEL,
    BIAS_CREATED_CHANNEL,
    BIAS_FLIPPED_CHANNEL,
    EventType
)
from common.db_models import (
    SetupModel,
    TickerSetupModel,
    SignalModel,
    BiasModel
)
from common.models import TradeSetupMessage

logger = logging.getLogger(__name__)

def is_redis_available() -> bool:
    """Check if Redis is available for event publishing."""
    if redis_client is None:
        logger.warning("Redis client not initialized")
        return False
    return redis_client.available

def publish_setup_created(setup: SetupModel) -> bool:
    """
    Publish a setup created event to Redis.
    
    Args:
        setup: The setup model that was created
        
    Returns:
        bool: True if the event was published, False otherwise
    """
    if not is_redis_available():
        logger.warning("Redis unavailable, skipping setup created event")
        return False
    
    try:
        # Create event payload
        timestamp = datetime.utcnow().isoformat()
        
        # Extract ticker symbols for easier consumption
        ticker_symbols = [ticker.symbol for ticker in setup.ticker_setups]
        
        event_data = {
            "event_type": EventType.SETUP_CREATED,
            "timestamp": timestamp,
            "setup_id": setup.id,
            "date": setup.date.isoformat(),
            "source": setup.source,
            "tickers": ticker_symbols,
            "created_at": setup.created_at.isoformat(),
        }
        
        # Publish to Redis
        if redis_client:
            result = redis_client.publish(SETUP_CREATED_CHANNEL, event_data)
            logger.info(f"Published setup created event for setup ID {setup.id}")
            return result > 0
        else:
            logger.warning("Redis client not available for publishing")
            return False
        
    except Exception as e:
        logger.exception(f"Error publishing setup created event: {str(e)}")
        return False

def publish_signals_created(ticker_setup: TickerSetupModel, signals: List[SignalModel]) -> bool:
    """
    Publish signal created events to Redis.
    
    Args:
        ticker_setup: The ticker setup model
        signals: The signal models that were created
        
    Returns:
        bool: True if all events were published, False otherwise
    """
    if not is_redis_available():
        logger.warning("Redis unavailable, skipping signal created events")
        return False
    
    try:
        success = True
        timestamp = datetime.utcnow().isoformat()
        
        for signal in signals:
            # Create event payload
            trigger_value = signal.trigger_value
            if isinstance(trigger_value, str):
                try:
                    trigger_value = json.loads(trigger_value)
                except Exception:
                    pass
                
            event_data = {
                "event_type": EventType.SIGNAL_CREATED,
                "timestamp": timestamp,
                "setup_id": ticker_setup.setup_id,
                "ticker_setup_id": ticker_setup.id,
                "signal_id": signal.id,
                "symbol": ticker_setup.symbol,
                "category": signal.category,
                "aggressiveness": signal.aggressiveness,
                "comparison": signal.comparison,
                "trigger_value": trigger_value,
                "targets": signal.targets,
                "created_at": signal.created_at.isoformat(),
            }
            
            # Publish to Redis
            if redis_client:
                result = redis_client.publish(SIGNAL_CREATED_CHANNEL, event_data)
                
                if result <= 0:
                    success = False
                    logger.warning(f"Failed to publish signal created event for signal ID {signal.id}")
                else:
                    logger.debug(f"Published signal created event for signal ID {signal.id}")
            else:
                success = False
                logger.warning("Redis client not available for publishing")
        
        return success
        
    except Exception as e:
        logger.exception(f"Error publishing signal created events: {str(e)}")
        return False

def publish_bias_created(ticker_setup: TickerSetupModel, bias: BiasModel) -> bool:
    """
    Publish a bias created event to Redis.
    
    Args:
        ticker_setup: The ticker setup model
        bias: The bias model that was created
        
    Returns:
        bool: True if the event was published, False otherwise
    """
    if not is_redis_available():
        logger.warning("Redis unavailable, skipping bias created event")
        return False
    
    try:
        # Create event payload
        timestamp = datetime.utcnow().isoformat()
        
        # Check if flip fields exist in model and have values
        has_flip = False
        if hasattr(bias, 'flip_direction') and hasattr(bias, 'flip_price_level'):
            flip_dir = getattr(bias, 'flip_direction')
            flip_price = getattr(bias, 'flip_price_level')
            has_flip = flip_dir is not None and flip_price is not None
        
        event_data = {
            "event_type": EventType.BIAS_CREATED,
            "timestamp": timestamp,
            "setup_id": ticker_setup.setup_id,
            "ticker_setup_id": ticker_setup.id,
            "bias_id": bias.id,
            "symbol": ticker_setup.symbol,
            "direction": bias.direction,
            "condition": bias.condition,
            "price": bias.price,
            "has_flip": has_flip,
            "created_at": bias.created_at.isoformat(),
        }
        
        # Add flip information if available
        if has_flip:
            event_data["flip"] = {
                "direction": bias.flip_direction,
                "price_level": bias.flip_price_level
            }
        
        # Publish to Redis
        if redis_client:
            result = redis_client.publish(BIAS_CREATED_CHANNEL, event_data)
            logger.info(f"Published bias created event for bias ID {bias.id}")
            return result > 0
        else:
            logger.warning("Redis client not available for publishing")
            return False
        
    except Exception as e:
        logger.exception(f"Error publishing bias created event: {str(e)}")
        return False

def publish_setup_message_created(setup: SetupModel) -> bool:
    """
    Publish all events related to a newly created setup message.
    
    Args:
        setup: The complete setup model with related ticker setups, signals, and biases
        
    Returns:
        bool: True if all events were published successfully, False otherwise
    """
    if not is_redis_available():
        logger.warning("Redis unavailable, skipping all setup message events")
        return False
    
    try:
        # First publish the setup created event
        setup_success = publish_setup_created(setup)
        
        # Then publish events for each ticker setup and its components
        for ticker_setup in setup.ticker_setups:
            # Publish signals
            if hasattr(ticker_setup, 'signals') and ticker_setup.signals:
                signal_success = publish_signals_created(ticker_setup, ticker_setup.signals)
                setup_success = setup_success and signal_success
            
            # Publish bias if exists
            if hasattr(ticker_setup, 'bias') and ticker_setup.bias is not None:
                bias_success = publish_bias_created(ticker_setup, ticker_setup.bias)
                setup_success = setup_success and bias_success
        
        return setup_success
        
    except Exception as e:
        logger.exception(f"Error publishing setup message events: {str(e)}")
        return False
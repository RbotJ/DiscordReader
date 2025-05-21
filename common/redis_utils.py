"""
Redis Compatibility Layer

This module provides a compatibility layer that maps Redis operations to PostgreSQL
using the events.py module.
"""
import logging
from typing import Any, Optional, Dict
from datetime import datetime
from common.events import (
    publish_event,
    subscribe_to_events,
    cache_data,
    get_from_cache,
    delete_from_cache
)

logger = logging.getLogger(__name__)

def ensure_redis_is_running() -> bool:
    """Compatibility function that checks if the event system is running"""
    try:
        from common.events import get_status
        status = get_status()
        return status.get('running', False)
    except Exception as e:
        logger.error(f"Error checking event system status: {e}")
        return False

def init_redis_client() -> bool:
    """Initialize the Redis compatibility layer"""
    logger.info("Redis compatibility layer initialized (using PostgreSQL)")
    return True

def ping_redis() -> bool:
    """Check if the event system is accessible"""
    return ensure_redis_is_running()

__all__ = [
    'ensure_redis_is_running',
    'init_redis_client',
    'ping_redis'
]
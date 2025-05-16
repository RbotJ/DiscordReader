"""
Rate Limiter Module

This module provides utility functions for configuring rate limits on API endpoints.
"""
import logging
from functools import wraps
from typing import List, Callable, Any

from flask_limiter import Limiter

logger = logging.getLogger(__name__)

def configure_rate_limits(limiter: Limiter, limits: List[str]) -> Callable:
    """
    Configure rate limits for an API endpoint.
    
    Args:
        limiter: The Flask-Limiter instance
        limits: List of limit strings (e.g., ["100 per day", "20 per hour"])
        
    Returns:
        Callable: Decorator function for applying rate limits
    """
    def decorator(f):
        for limit in limits:
            f = limiter.limit(limit)(f)
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator
"""
Setup Authentication Module

This module handles authentication and security for setup webhooks.
"""
import os
import logging
import hashlib
import hmac
import time
from functools import wraps
from typing import Optional
from flask import request, jsonify

logger = logging.getLogger(__name__)

# Default webhook secret (for development only)
DEFAULT_WEBHOOK_SECRET = "dev_webhook_secret"

def get_webhook_secret() -> str:
    """Get the webhook secret from environment variables or use default."""
    return os.environ.get("WEBHOOK_SECRET", DEFAULT_WEBHOOK_SECRET)

def validate_webhook_signature(payload: bytes, signature: Optional[str], timestamp: Optional[str]) -> bool:
    """
    Validate the webhook signature using HMAC.
    
    Args:
        payload: The raw request body as bytes
        signature: The X-Signature header from the request
        timestamp: The X-Timestamp header from the request
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not signature or not timestamp:
        logger.warning("Missing signature or timestamp headers")
        return False
    
    # Check if timestamp is recent (within 5 minutes)
    try:
        request_time = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - request_time) > 300:  # 5 minutes
            logger.warning(f"Webhook timestamp too old: {timestamp}")
            return False
    except ValueError:
        logger.warning(f"Invalid timestamp format: {timestamp}")
        return False
    
    # Get the webhook secret
    webhook_secret = get_webhook_secret()
    
    # Create the expected signature
    message = timestamp.encode() + b"." + payload
    expected_signature = hmac.new(
        webhook_secret.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (using constant-time comparison)
    return hmac.compare_digest(expected_signature, signature)

def require_auth(f):
    """
    Decorator to require webhook authentication.
    
    Args:
        f: The route function to wrap
        
    Returns:
        function: The wrapped function
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Skip auth in development mode if configured
        if os.environ.get("SKIP_WEBHOOK_AUTH", "").lower() == "true":
            return f(*args, **kwargs)
        
        # Get headers
        signature = request.headers.get("X-Signature")
        timestamp = request.headers.get("X-Timestamp")
        
        # Get request payload
        payload = request.get_data()
        
        # Validate signature
        if not validate_webhook_signature(payload, signature, timestamp):
            logger.warning("Invalid webhook signature")
            return jsonify({
                "status": "error",
                "message": "Invalid webhook signature"
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated

def generate_signature(payload: bytes, timestamp: Optional[str] = None) -> dict:
    """
    Generate a signature for testing webhooks.
    
    Args:
        payload: The request payload as bytes
        timestamp: Optional timestamp (uses current time if not provided)
        
    Returns:
        dict: Dictionary with X-Signature and X-Timestamp headers
    """
    current_timestamp = str(int(time.time()))
    if timestamp is None:
        timestamp = current_timestamp
    
    webhook_secret = get_webhook_secret()
    message = timestamp.encode() + b"." + payload
    signature = hmac.new(
        webhook_secret.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    return {
        "X-Signature": signature,
        "X-Timestamp": timestamp
    }
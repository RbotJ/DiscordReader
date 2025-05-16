"""
Setup Service Layer

Provides business logic for processing and storing trade setups.
Acts as a mediator between API controllers and data access layers.
"""
import logging
import hmac
import hashlib
import base64
import json
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from common.models import TradeSetupMessage
from features.setups.parser import parse_setup_message
from features.setups.repository_fixed import SetupRepository
from features.setups.event_publisher import publish_setup_event

logger = logging.getLogger(__name__)

# Shared secret for message authentication
# In production, this should be loaded securely from environment variables
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "your_webhook_secret_here")


class SetupService:
    """Service for processing trade setup messages."""
    
    @staticmethod
    def process_webhook(payload: Dict[str, Any], signature: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a webhook message containing trade setup information.
        
        Args:
            payload: The JSON payload from the webhook
            signature: Optional HMAC signature for verification
            
        Returns:
            Tuple[bool, Dict[str, Any]]: Success status and response data
        """
        # Validate signature if provided
        if signature:
            is_valid = SetupService._verify_signature(payload, signature)
            if not is_valid:
                logger.warning("Invalid webhook signature")
                return False, {
                    "success": False,
                    "error": "Invalid signature",
                    "code": "INVALID_SIGNATURE"
                }
        
        # Extract and validate required fields
        try:
            if "text" not in payload:
                return False, {
                    "success": False,
                    "error": "Missing required field: text",
                    "code": "MISSING_FIELD"
                }
            
            # Get text and source
            message_text = payload["text"]
            source = payload.get("source", "webhook")
            
            # Parse the setup message
            setup_message = parse_setup_message(message_text, source)
            
            # Make sure we have at least one valid setup
            if not setup_message.setups:
                return False, {
                    "success": False,
                    "error": "No valid trading setups found in message",
                    "code": "NO_SETUPS_FOUND"
                }
            
            # Save to database
            message_id = SetupRepository.save_setup_message(setup_message)
            
            # Publish event
            publish_setup_event(setup_message)
            
            # Return success response
            return True, {
                "success": True,
                "message_id": message_id,
                "tickers": [setup.symbol for setup in setup_message.setups],
                "setup_count": len(setup_message.setups)
            }
        
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return False, {
                "success": False,
                "error": f"Error processing webhook: {str(e)}",
                "code": "PROCESSING_ERROR"
            }
    
    @staticmethod
    def get_recent_setups(limit: int = 10) -> List[TradeSetupMessage]:
        """
        Get recent trade setup messages.
        
        Args:
            limit: Maximum number of messages to retrieve
            
        Returns:
            List[TradeSetupMessage]: List of recent setup messages
        """
        return SetupRepository.get_latest_setups(limit)
    
    @staticmethod
    def get_setups_for_symbol(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trade setups for a specific ticker symbol.
        
        Args:
            symbol: The ticker symbol to filter by
            limit: Maximum number of setups to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of setups with message context
        """
        return SetupRepository.get_setups_by_symbol(symbol, limit)
    
    @staticmethod
    def _verify_signature(payload: Dict[str, Any], signature: str) -> bool:
        """
        Verify HMAC signature of the webhook payload.
        
        Args:
            payload: The webhook payload to verify
            signature: The provided signature to check against
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            # Convert payload to JSON string
            payload_str = json.dumps(payload)
            
            # Create HMAC signature
            computed_signature = hmac.new(
                WEBHOOK_SECRET.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).digest()
            
            # Encode as base64
            computed_signature_b64 = base64.b64encode(computed_signature).decode()
            
            # Compare signatures
            return hmac.compare_digest(signature, computed_signature_b64)
        except Exception as e:
            logger.error(f"Error verifying signature: {str(e)}")
            return False
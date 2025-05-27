"""
Unified Setup Service Module

This module provides the single, centralized service for handling trading setups,
including webhook processing, parsing, validation, persistence, and retrieval.
"""
import logging
import hmac
import hashlib
import base64
import json
import os
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union, Tuple

from common.models import TradeSetupMessage
from features.parsing.parser import MessageParser
from features.management.store import SetupStore
from common.db import publish_event

# Configure logger
logger = logging.getLogger(__name__)

# Webhook secret for message authentication
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "your_webhook_secret_here")


class SetupService:
    """
    Unified service for handling all trading setup operations.
    
    This service encapsulates:
    - Webhook processing and signature verification
    - Message parsing and validation
    - Database persistence and retrieval
    - Event publishing
    """
    
    def __init__(self, repository=None):
        """Initialize the service with optional repository dependency."""
        self.repository = repository or SetupStore()
        self.parser = MessageParser()
    
    def process_webhook(self, payload: Dict[str, Any], signature: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
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
            is_valid = self._verify_signature(payload, signature)
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
            
            # Parse the setup message using new vertical slice parser
            setup_models = self.parser.parse_message(message_text)
            
            # Validate parsed content
            if not setup_models:
                return False, {
                    "success": False,
                    "error": "No valid trading setups found in message",
                    "code": "NO_SETUPS_FOUND"
                }
            
            # Save to database using new repository
            saved_setups = []
            for setup_model in setup_models:
                saved_setup = self.repository.save_setup(setup_model)
                if saved_setup:
                    saved_setups.append(saved_setup)
            
            if not saved_setups:
                return False, {
                    "success": False,
                    "error": "Failed to save setups to database",
                    "code": "SAVE_ERROR"
                }
            
            # Publish events for other components using new event system
            try:
                for setup in saved_setups:
                    publish_event("setup:created", {
                        "ticker": setup.ticker,
                        "setup_type": setup.setup_type,
                        "source": source
                    })
            except Exception as e:
                logger.warning(f"Failed to publish setup events: {e}")
                # Don't fail the request if event publishing fails
            
            # Return success response
            return True, {
                "success": True,
                "setups_saved": len(saved_setups),
                "tickers": [setup.ticker for setup in saved_setups],
                "setup_count": len(saved_setups)
            }
        
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return False, {
                "success": False,
                "error": f"Error processing webhook: {str(e)}",
                "code": "PROCESSING_ERROR"
            }
    
    def save_setup(self, setup_message: TradeSetupMessage) -> Optional[int]:
        """
        Save a parsed setup message to the database.
        
        Args:
            setup_message: The parsed setup message object
            
        Returns:
            Optional[int]: ID of the saved message or None if error
        """
        try:
            return self.repository.save_setup_message(setup_message)
        except Exception as e:
            logger.error(f"Failed to save setup message: {e}")
            return None
    
    def get_setup_by_id(self, setup_id: int) -> Optional[Dict]:
        """
        Get a setup message by ID with all related data.
        
        Args:
            setup_id: The ID of the setup message
            
        Returns:
            Optional[Dict]: Setup message data as dictionary or None if not found
        """
        try:
            return self.repository.get_setup_by_id(setup_id)
        except Exception as e:
            logger.error(f"Failed to get setup by ID {setup_id}: {e}")
            return None
    
    def get_recent_setups(self, limit: int = 10, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get recent setup messages with optional filtering by ticker symbol.
        
        Args:
            limit: Maximum number of setups to return
            symbol: Optional ticker symbol to filter by
            
        Returns:
            List[Dict]: List of setup messages
        """
        try:
            if symbol:
                return self.repository.get_setups_by_symbol(symbol, limit)
            else:
                return self.repository.get_latest_setups(limit)
        except Exception as e:
            logger.error(f"Failed to get recent setups: {e}")
            return []
    
    def get_setups_by_symbol(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        Get setup messages for a specific ticker symbol.
        
        Args:
            symbol: Ticker symbol to filter by
            limit: Maximum number of setups to return
            
        Returns:
            List[Dict]: List of ticker setups for the specified symbol
        """
        try:
            return self.repository.get_setups_by_symbol(symbol, limit)
        except Exception as e:
            logger.error(f"Failed to get setups for symbol {symbol}: {e}")
            return []
    
    def _verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
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
            payload_str = json.dumps(payload, sort_keys=True)
            
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
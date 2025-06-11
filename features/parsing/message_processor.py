"""
Message Processing Service

Single entry point for processing Discord messages through the parsing pipeline.
Coordinates between parsing and setup storage slices.
"""
import logging
from typing import Dict, Any, List
from datetime import date

from .parser import MessageParser
from ..setups.service import SetupService

logger = logging.getLogger(__name__)


class MessageProcessingService:
    """
    Unified message processing service that coordinates parsing and storage.
    This serves as the single entry point for processing Discord messages.
    """
    
    def __init__(self):
        self.parser = MessageParser()
        self.setup_service = SetupService()
    
    def process_discord_message(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a Discord message through the complete pipeline.
        
        Args:
            raw_message: Raw Discord message data
            
        Returns:
            Dict with processing results
            
        Raises:
            ValueError: If parsing fails for A+ messages
        """
        try:
            message_id = raw_message.get('message_id', raw_message.get('id', ''))
            logger.info(f"Processing Discord message {message_id}")
            
            # Parse the message using the unified parser
            result = self.parser.parse_message_to_setups(raw_message)
            
            if not result["success"]:
                error_msg = f"Parsing failed for message {result['message_id']}"
                logger.warning(error_msg)
                raise ValueError(error_msg)
            
            # Convert ParsedSetupDTO objects to storage format
            storage_setups = []
            for setup_dto in result["setups"]:
                storage_setup = {
                    'symbol': setup_dto.ticker,
                    'setup_type': setup_dto.setup_type,
                    'direction': setup_dto.direction,
                    'entry_price': None,  # Will be extracted from levels
                    'target_price': None,  # Will be extracted from levels
                    'stop_loss': None,
                    'confidence': setup_dto.confidence_score,
                    'notes': setup_dto.bias_note,
                    'signals': []
                }
                
                # Extract price levels from the levels data
                entry_prices = []
                target_prices = []
                stop_prices = []
                
                for level_dto in result["levels"]:
                    if level_dto.level_type == 'entry':
                        entry_prices.append(level_dto.trigger_price)
                    elif level_dto.level_type == 'target':
                        target_prices.append(level_dto.trigger_price)
                    elif level_dto.level_type == 'stop':
                        stop_prices.append(level_dto.trigger_price)
                
                # Use first price of each type
                if entry_prices:
                    storage_setup['entry_price'] = entry_prices[0]
                if target_prices:
                    storage_setup['target_price'] = target_prices[0]
                if stop_prices:
                    storage_setup['stop_loss'] = stop_prices[0]
                
                # Create signals from the parsed data
                if setup_dto.direction:
                    signal = {
                        'signal_type': setup_dto.direction,
                        'trigger_price': storage_setup['entry_price'],
                        'target_price': storage_setup['target_price'],
                        'stop_loss': storage_setup['stop_loss'],
                        'confidence': setup_dto.confidence_score or 0.7
                    }
                    storage_setup['signals'].append(signal)
                
                storage_setups.append(storage_setup)
            
            # Store the parsed setups
            storage_result = self.setup_service.store_parsed_setups(
                setups=storage_setups,
                trading_day=result["trading_day"] or date.today(),
                message_id=message_id,
                channel_id=raw_message.get('channel_id', ''),
                author_id=raw_message.get('author_id', ''),
                source='discord_parsing'
            )
            
            logger.info(f"Successfully processed message {message_id}: "
                       f"{storage_result['ticker_setups_created']} setups, "
                       f"{storage_result['signals_created']} signals")
            
            return {
                'success': True,
                'message_id': message_id,
                'setups_created': storage_result['ticker_setups_created'],
                'signals_created': storage_result['signals_created'],
                'trading_day': result["trading_day"],
                'parser_type': 'aplus_specialized'
            }
            
        except ValueError as e:
            # Re-raise parsing validation errors
            logger.error(f"Message processing validation error: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error processing message {message_id}: {e}")
            return {
                'success': False,
                'message_id': message_id,
                'error': str(e),
                'setups_created': 0,
                'signals_created': 0
            }


# Global service instance
_message_processor = None

def get_message_processor() -> MessageProcessingService:
    """Get the global message processing service instance."""
    global _message_processor
    if _message_processor is None:
        _message_processor = MessageProcessingService()
    return _message_processor
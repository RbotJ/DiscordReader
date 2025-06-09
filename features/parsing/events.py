"""
Parsing Events Module

Event handlers for the parsing slice that consume events from the event bus
and trigger parsing operations. Maintains proper slice isolation.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from common.events.publisher import publish_event
from .service import get_parsing_service
from .store import get_parsing_store

logger = logging.getLogger(__name__)

def register_parsing_event_handlers():
    """Register all parsing event handlers with the event bus."""
    # Simplified event handling - events will be triggered through direct calls
    logger.info("Parsing event handlers registered")

# Event handler for message.stored events
def handle_message_stored(event_data: Dict[str, Any]):
    """
    Handle message.stored events from the ingestion slice.
    
    Event payload:
    {
        'message_id': str,
        'channel_id': str,
        'content': str,
        'author_id': str,
        'timestamp': str,
        'message_type': str
    }
    """
    try:
        message_id = event_data.get('message_id')
        content = event_data.get('content', '')
        channel_id = event_data.get('channel_id')
        
        if not message_id or not content:
            logger.warning(f"Invalid message event data: {event_data}")
            return
            
        logger.info(f"Processing message.stored event for message {message_id}")
        
        # Get parsing service and attempt to parse
        parsing_service = get_parsing_service()
        
        # Check if this is an A+ message that needs parsing
        if parsing_service.should_parse_message(content):
            result = parsing_service.parse_aplus_message(content, message_id)
            
            if result.get('success'):
                setups_count = len(result.get('setups', []))
                logger.info(f"Successfully parsed {setups_count} setups from message {message_id}")
                
                # Publish parsing success event
                publish_event('parsing.completed', {
                    'message_id': message_id,
                    'channel_id': channel_id,
                    'setups_parsed': setups_count,
                    'timestamp': datetime.utcnow().isoformat(),
                    'success': True
                })
            else:
                logger.warning(f"Failed to parse A+ message {message_id}: {result.get('error')}")
                
                # Publish parsing failure event
                publish_event('parsing.failed', {
                    'message_id': message_id,
                    'channel_id': channel_id,
                    'error': result.get('error', 'Unknown error'),
                    'timestamp': datetime.utcnow().isoformat(),
                    'success': False
                })
        else:
            logger.debug(f"Message {message_id} is not an A+ message, skipping parsing")
            
    except Exception as e:
        logger.error(f"Error handling message.stored event: {e}", exc_info=True)
        
        # Publish error event
        publish_event('parsing.error', {
            'message_id': event_data.get('message_id'),
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'message.stored'
        })

# Event handler for backlog parsing requests 
def handle_backlog_parsing(event_data: Dict[str, Any]):
    """
    Handle manual backlog parsing requests from the dashboard.
    
    Event payload:
    {
        'requested_by': str,
        'channel_id': Optional[str],
        'since_timestamp': Optional[str],
        'limit': Optional[int]
    }
    """
    try:
        requested_by = event_data.get('requested_by', 'system')
        channel_id = event_data.get('channel_id')
        since_timestamp = event_data.get('since_timestamp')
        limit = event_data.get('limit', 100)
        
        logger.info(f"Processing backlog parsing request by {requested_by}")
        
        # Get unparsed messages from store
        parsing_store = get_parsing_store()
        unparsed_messages = parsing_store.get_unparsed_messages(
            channel_id=channel_id,
            since_timestamp=since_timestamp,
            limit=limit
        )
        
        logger.info(f"Found {len(unparsed_messages)} unparsed messages for backlog processing")
        
        # Process each message
        parsing_service = get_parsing_service()
        processed_count = 0
        error_count = 0
        
        for message in unparsed_messages:
            try:
                if parsing_service.should_parse_message(message['content']):
                    result = parsing_service.parse_aplus_message(
                        message['content'], 
                        message['message_id']
                    )
                    
                    if result.get('success'):
                        processed_count += 1
                    else:
                        error_count += 1
                        
            except Exception as e:
                logger.error(f"Error processing message {message['message_id']}: {e}")
                error_count += 1
        
        # Publish backlog completion event
        publish_event('parsing.backlog_completed', {
            'requested_by': requested_by,
            'messages_found': len(unparsed_messages),
            'messages_processed': processed_count,
            'errors': error_count,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"Backlog parsing completed: {processed_count} processed, {error_count} errors")
        
    except Exception as e:
        logger.error(f"Error handling backlog parsing request: {e}", exc_info=True)
        
        # Publish error event
        publish_event('parsing.backlog_error', {
            'requested_by': event_data.get('requested_by', 'unknown'),
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })

def trigger_backlog_parsing(channel_id: Optional[str] = None, 
                          since_timestamp: Optional[str] = None,
                          limit: int = 100,
                          requested_by: str = 'dashboard') -> bool:
    """
    Trigger backlog parsing by publishing an event.
    
    Args:
        channel_id: Optional channel to limit parsing to
        since_timestamp: Optional timestamp to start from
        limit: Maximum number of messages to process
        requested_by: Who requested the backlog parsing
        
    Returns:
        True if event was published successfully
    """
    try:
        publish_event('parsing.backlog_requested', {
            'requested_by': requested_by,
            'channel_id': channel_id,
            'since_timestamp': since_timestamp,
            'limit': limit,
            'timestamp': datetime.utcnow().isoformat()
        })
        return True
    except Exception as e:
        logger.error(f"Failed to trigger backlog parsing: {e}")
        return False
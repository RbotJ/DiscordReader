"""
Event Bus for Cross-Slice Communication

Provides an async event bus to eliminate direct cross-slice dependencies
while maintaining loose coupling and supporting event-driven architecture.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import json
import uuid

from common.events.publisher import publish_event
from common.schema_validator import validate_event_data, SchemaViolationError

logger = logging.getLogger(__name__)


@dataclass
class EventMessage:
    """Event message structure."""
    event_id: str
    event_type: str
    data: Dict[str, Any]
    source: str
    channel: str
    timestamp: datetime
    correlation_id: Optional[str] = None


class EventBus:
    """
    Async event bus for inter-slice communication.
    
    Supports:
    - Event publishing/subscribing
    - Event routing by type/channel
    - Async handlers
    - Event correlation
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._running = False
        self._event_queue = asyncio.Queue()
        self._correlation_map: Dict[str, List[str]] = defaultdict(list)
        
    async def start(self):
        """Start the event bus."""
        if self._running:
            return
            
        self._running = True
        logger.info("Event bus started")
        
        # Start event processing task
        asyncio.create_task(self._process_events())
        
    async def stop(self):
        """Stop the event bus."""
        self._running = False
        logger.info("Event bus stopped")
        
    def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of events to subscribe to
            handler: Async function to handle events
        """
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type}")
        
    def unsubscribe(self, event_type: str, handler: Callable):
        """
        Unsubscribe from events.
        
        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to remove
        """
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(f"Unsubscribed handler from {event_type}")
            
    async def publish(self, event_type: str, data: Dict[str, Any], 
                     source: str, channel: str = "default",
                     correlation_id: Optional[str] = None) -> str:
        """
        Publish an event to the bus.
        
        Args:
            event_type: Type of event
            data: Event data
            source: Source of the event
            channel: Event channel
            correlation_id: Optional correlation ID
            
        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())
        
        event = EventMessage(
            event_id=event_id,
            event_type=event_type,
            data=validated_data,
            source=source,
            channel=channel,
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )
        
        # Add to queue for async processing
        await self._event_queue.put(event)
        
        # Track correlation if provided
        if correlation_id:
            self._correlation_map[correlation_id].append(event_id)
            
        # Also publish to persistent event store
        publish_event(event_type, validated_data, channel, source, correlation_id or "")
        
        return event_id
        
    async def request_response(self, request_type: str, data: Dict[str, Any],
                              source: str, response_type: str,
                              timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Send a request and wait for a response.
        
        Args:
            request_type: Type of request event
            data: Request data
            source: Source of request
            response_type: Expected response event type
            timeout: Timeout in seconds
            
        Returns:
            Response data or None if timeout
        """
        correlation_id = str(uuid.uuid4())
        response_future = asyncio.Future()
        
        # Subscribe to response
        async def response_handler(event: EventMessage):
            if event.correlation_id == correlation_id:
                response_future.set_result(event.data)
                
        self.subscribe(response_type, response_handler)
        
        try:
            # Send request
            await self.publish(request_type, data, source, 
                             correlation_id=correlation_id)
            
            # Wait for response
            response = await asyncio.wait_for(response_future, timeout)
            return response
            
        except asyncio.TimeoutError:
            logger.warning(f"Request {request_type} timed out after {timeout}s")
            return None
            
        finally:
            # Clean up subscription
            self.unsubscribe(response_type, response_handler)
            
    async def _process_events(self):
        """Process events from the queue."""
        while self._running:
            try:
                # Wait for events with timeout
                event = await asyncio.wait_for(
                    self._event_queue.get(), timeout=1.0
                )
                
                # Find handlers for this event type
                handlers = self._handlers.get(event.event_type, [])
                
                if not handlers:
                    logger.debug(f"No handlers for event type: {event.event_type}")
                    continue
                    
                # Execute all handlers concurrently
                tasks = []
                for handler in handlers:
                    task = asyncio.create_task(self._execute_handler(handler, event))
                    tasks.append(task)
                    
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                
    async def _execute_handler(self, handler: Callable, event: EventMessage):
        """Execute an event handler safely."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                # Run sync handler in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler, event)
                
        except Exception as e:
            logger.error(f"Error in event handler {handler.__name__}: {e}")
            
    def get_correlated_events(self, correlation_id: str) -> List[str]:
        """Get all event IDs for a correlation ID."""
        return self._correlation_map.get(correlation_id, [])
        
    def get_handler_count(self, event_type: str) -> int:
        """Get number of handlers for an event type."""
        return len(self._handlers.get(event_type, []))


# Global event bus instance
_event_bus = None


async def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.start()
    return _event_bus


# Convenience functions for common patterns
async def publish_cross_slice_event(event_type: str, data: Dict[str, Any], 
                                   source: str) -> str:
    """Publish an event for cross-slice communication."""
    bus = await get_event_bus()
    return await bus.publish(event_type, data, source, "cross_slice")


async def subscribe_to_slice_events(slice_name: str, handler: Callable):
    """Subscribe to events from a specific slice."""
    bus = await get_event_bus()
    event_pattern = f"{slice_name}.*"
    
    # Wrapper to filter events by source pattern
    async def filtered_handler(event: EventMessage):
        if event.source.startswith(slice_name) or event.event_type.startswith(slice_name):
            await handler(event)
    
    bus.subscribe(event_pattern, filtered_handler)


async def request_from_slice(target_slice: str, request_type: str, 
                           data: Dict[str, Any], source: str,
                           timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """Send a request to another slice and wait for response."""
    bus = await get_event_bus()
    response_type = f"{target_slice}.response"
    
    return await bus.request_response(
        f"{target_slice}.{request_type}",
        data,
        source,
        response_type,
        timeout
    )
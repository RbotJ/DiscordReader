"""
Event Schema Validation Framework

Provides Pydantic models and validation for all event types in the system.
Ensures data integrity and schema consistency across the event bus.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class EventVersion(str, Enum):
    """Event schema versions for backward compatibility."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


class EventType(str, Enum):
    """Standard event types across the system."""
    # Discord events
    DISCORD_MESSAGE_RECEIVED = "discord.message.received"
    DISCORD_CHANNEL_ADDED = "discord.channel.added"
    DISCORD_CHANNEL_UPDATED = "discord.channel.updated"
    
    # Market data events
    MARKET_DATA_UPDATED = "market.data.updated"
    MARKET_QUOTE_RECEIVED = "market.quote.received"
    
    # Trading events
    SIGNAL_GENERATED = "trading.signal.generated"
    ORDER_SUBMITTED = "trading.order.submitted"
    ORDER_FILLED = "trading.order.filled"
    
    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_ERROR = "system.error"
    
    # Ingestion events
    INGESTION_STARTED = "ingestion.started"
    INGESTION_COMPLETED = "ingestion.completed"


class BaseEventData(BaseModel):
    """Base class for all event data schemas."""
    version: EventVersion = EventVersion.V2_0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str
    correlation_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))


class DiscordMessageEventData(BaseEventData):
    """Schema for Discord message events."""
    message_id: str
    channel_id: str
    author_id: str
    content: str
    guild_id: Optional[str] = None
    author_username: Optional[str] = None
    channel_name: Optional[str] = None
    embeds: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    
    @validator('message_id', 'channel_id', 'author_id')
    def validate_discord_ids(cls, v):
        """Validate Discord snowflake IDs."""
        if not v or not v.isdigit() or len(v) < 15:
            raise ValueError("Invalid Discord ID format")
        return v


class DiscordChannelEventData(BaseEventData):
    """Schema for Discord channel events."""
    channel_id: str
    guild_id: str
    name: str
    channel_type: str
    is_monitored: bool = False
    
    @validator('channel_id', 'guild_id')
    def validate_discord_ids(cls, v):
        """Validate Discord snowflake IDs."""
        if not v or not v.isdigit() or len(v) < 15:
            raise ValueError("Invalid Discord ID format")
        return v


class MarketDataEventData(BaseEventData):
    """Schema for market data events."""
    symbol: str
    price: Decimal
    volume: Optional[int] = None
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[float] = None
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate stock symbol format."""
        if not v or len(v) > 10:
            raise ValueError("Invalid symbol format")
        return v.upper()


class TradingSignalEventData(BaseEventData):
    """Schema for trading signal events."""
    signal_id: str
    symbol: str
    signal_type: str  # 'buy', 'sell', 'hold'
    confidence: float = Field(ge=0.0, le=1.0)
    price_target: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('signal_type')
    def validate_signal_type(cls, v):
        """Validate signal type."""
        valid_types = ['buy', 'sell', 'hold']
        if v.lower() not in valid_types:
            raise ValueError(f"Signal type must be one of {valid_types}")
        return v.lower()


class OrderEventData(BaseEventData):
    """Schema for order events."""
    order_id: str
    symbol: str
    quantity: int = Field(gt=0)
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market', 'limit', etc.
    status: str
    filled_quantity: int = Field(ge=0)
    average_fill_price: Optional[Decimal] = None
    limit_price: Optional[Decimal] = None
    
    @validator('side')
    def validate_side(cls, v):
        """Validate order side."""
        valid_sides = ['buy', 'sell']
        if v.lower() not in valid_sides:
            raise ValueError(f"Side must be one of {valid_sides}")
        return v.lower()


class SystemEventData(BaseEventData):
    """Schema for system events."""
    event_category: str
    message: str
    severity: str = Field(regex=r'^(info|warning|error|critical)$')
    component: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class IngestionEventData(BaseEventData):
    """Schema for ingestion events."""
    ingestion_type: str
    messages_processed: int = Field(ge=0)
    errors_count: int = Field(ge=0)
    duration_ms: Optional[int] = None
    status: str = Field(regex=r'^(started|completed|failed)$')


class EventValidator:
    """Validates event data against schemas."""
    
    SCHEMA_MAP = {
        EventType.DISCORD_MESSAGE_RECEIVED: DiscordMessageEventData,
        EventType.DISCORD_CHANNEL_ADDED: DiscordChannelEventData,
        EventType.DISCORD_CHANNEL_UPDATED: DiscordChannelEventData,
        EventType.MARKET_DATA_UPDATED: MarketDataEventData,
        EventType.MARKET_QUOTE_RECEIVED: MarketDataEventData,
        EventType.SIGNAL_GENERATED: TradingSignalEventData,
        EventType.ORDER_SUBMITTED: OrderEventData,
        EventType.ORDER_FILLED: OrderEventData,
        EventType.SYSTEM_STARTUP: SystemEventData,
        EventType.SYSTEM_ERROR: SystemEventData,
        EventType.INGESTION_STARTED: IngestionEventData,
        EventType.INGESTION_COMPLETED: IngestionEventData,
    }
    
    @classmethod
    def validate_event(cls, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate event data against the appropriate schema.
        
        Args:
            event_type: The type of event
            data: Event data to validate
            
        Returns:
            Validated and normalized event data
            
        Raises:
            ValueError: If validation fails
        """
        try:
            event_enum = EventType(event_type)
        except ValueError:
            raise ValueError(f"Unknown event type: {event_type}")
        
        schema_class = cls.SCHEMA_MAP.get(event_enum)
        if not schema_class:
            raise ValueError(f"No schema defined for event type: {event_type}")
        
        try:
            validated_data = schema_class(**data)
            return validated_data.dict()
        except Exception as e:
            raise ValueError(f"Event validation failed for {event_type}: {str(e)}")
    
    @classmethod
    def get_schema_version(cls, event_type: str) -> str:
        """Get the current schema version for an event type."""
        try:
            event_enum = EventType(event_type)
            schema_class = cls.SCHEMA_MAP.get(event_enum)
            if schema_class:
                return EventVersion.V2_0.value
            return EventVersion.V1_0.value
        except ValueError:
            return EventVersion.V1_0.value


def validate_event_data(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to validate event data.
    
    Args:
        event_type: The type of event
        data: Event data to validate
        
    Returns:
        Validated event data
    """
    return EventValidator.validate_event(event_type, data)


class SchemaViolationError(Exception):
    """Raised when event data violates schema constraints."""
    
    def __init__(self, event_type: str, errors: List[str]):
        self.event_type = event_type
        self.errors = errors
        super().__init__(f"Schema violation in {event_type}: {', '.join(errors)}")
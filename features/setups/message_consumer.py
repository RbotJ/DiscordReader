"""
Discord Message Consumer

This module polls the PostgreSQL event bus for Discord messages and processes
incoming messages into structured ticker setup objects ready for charting
and monitoring.
"""
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from app import db
from models import (
    SetupMessage, 
    TickerSetup,
    Signal,
    Bias,
    BiasFlip,
    SignalCategoryEnum,
    AggressivenessEnum,
    ComparisonTypeEnum,
    BiasDirectionEnum
)
from common.events import poll_events, publish_event, get_latest_event_id
from common.event_constants import (
    DISCORD_SETUP_MESSAGE_CHANNEL, 
    DISCORD_RAW_MESSAGE_CHANNEL,
    EventType
)
from features.setups.parser import SetupParser

# Configure logger
logger = logging.getLogger(__name__)

# Initialize parser
parser = SetupParser()

@dataclass
class SignalDTO:
    """Data Transfer Object for a trading signal."""
    category: str         # e.g. "rejection", "breakdown", "breakout", "bounce"
    subcategory: Optional[str] = None  # e.g. "aggressive", "conservative"
    direction: Optional[str] = None    # "below" or "above"
    level: float = 0.0               # the anchor price (e.g. 590.20)
    targets: List[float] = None      # target prices (e.g. [588.00, 585.50, 582.80])
    
    def __post_init__(self):
        if self.targets is None:
            self.targets = []


@dataclass
class TickerSetupDTO:
    """Data Transfer Object for a ticker setup."""
    symbol: str                    # "SPY", "TSLA", etc.
    signals: List[SignalDTO]       # List of signals
    bias_note: Optional[str] = None  # Free-form bias note (⚠️ line)
    current_price: Optional[float] = None  # Current stock price if available


class MessageConsumer:
    """Consumes Discord messages from PostgreSQL event bus and processes them into structured data."""
    
    def __init__(self):
        """Initialize the message consumer."""
        self.parser = SetupParser()
        self.last_event_id = get_latest_event_id()
        self.running = True
        
    def start(self):
        """Start polling for Discord setup messages."""
        try:
            logger.info("Starting Discord message consumer")
            
            # Main polling loop
            while self.running:
                try:
                    # Poll for new events on the Discord setup message channel
                    events = poll_events([DISCORD_SETUP_MESSAGE_CHANNEL], self.last_event_id)
                    
                    # Process any new events
                    for event in events:
                        self._process_event(event)
                        self.last_event_id = max(self.last_event_id, event['id'])
                    
                    # Sleep briefly to avoid excessive database queries
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error in event polling loop: {e}")
                    time.sleep(2)  # Sleep longer on error
                        
        except Exception as e:
            logger.error(f"Error in message consumer: {e}")
        finally:
            logger.info("Discord message consumer stopped")
            
    def _process_event(self, event):
        """
        Process an event from the PostgreSQL event bus.
        
        Args:
            event: Event data from the event bus
        """
        try:
            # Extract the payload
            payload = event.get('payload', {})
            
            # Check if this is a setup message event
            if payload.get('event_type') == EventType.DISCORD_SETUP_MESSAGE_RECEIVED:
                message_data = payload.get('data', {})
                
                # Extract message details
                message_id = message_data.get('message_id')
                content = message_data.get('content')
                timestamp_str = message_data.get('timestamp')
                
                if not content:
                    logger.warning(f"Received empty message content for message ID {message_id}")
                    return
                
                # Convert timestamp string to datetime
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except (ValueError, TypeError):
                    timestamp = datetime.now()
                
                # Process the setup message
                self._process_setup_message(message_id, content, timestamp)
                
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON message from event payload")
        except Exception as e:
            logger.error(f"Error processing event: {e}")
    
    def _process_setup_message(self, message_id: str, content: str, timestamp: datetime):
        """
        Process a Discord setup message.
        
        Args:
            message_id: Discord message ID
            content: Message content
            timestamp: Message timestamp
        """
        try:
            # Use the parser to extract ticker sections
            ticker_sections = self.parser.extract_ticker_sections(content)
            ticker_setups = []
            
            for ticker, section_text in ticker_sections.items():
                # Extract signals and bias for this ticker
                signals = self.parser.extract_signals(ticker, section_text)
                bias = self.parser.extract_bias(ticker, section_text)
                
                # Convert to our DTO format
                signal_dtos = []
                for signal in signals:
                    # Get the main trigger price or range
                    level = 0.0
                    if isinstance(signal.trigger, dict) and 'price' in signal.trigger:
                        level = signal.trigger['price']
                    elif isinstance(signal.trigger, (int, float)):
                        level = signal.trigger
                    
                    # Extract targets
                    targets = []
                    if signal.targets:
                        for target in signal.targets:
                            if isinstance(target, dict) and 'price' in target:
                                targets.append(target['price'])
                            elif isinstance(target, (int, float)):
                                targets.append(target)
                    
                    # Create SignalDTO
                    signal_dto = SignalDTO(
                        category=signal.category.value if hasattr(signal.category, 'value') else str(signal.category),
                        subcategory=signal.aggressiveness.value if hasattr(signal.aggressiveness, 'value') else None,
                        direction=signal.comparison.value if hasattr(signal.comparison, 'value') else None,
                        level=level,
                        targets=targets
                    )
                    signal_dtos.append(signal_dto)
                
                # Extract bias note
                bias_note = None
                if bias:
                    direction = bias.direction.value if hasattr(bias.direction, 'value') else str(bias.direction)
                    condition = bias.condition.value if hasattr(bias.condition, 'value') else str(bias.condition)
                    price = bias.price
                    bias_note = f"{direction.capitalize()} {condition} {price}"
                
                # Create TickerSetupDTO
                ticker_setup = TickerSetupDTO(
                    symbol=ticker,
                    signals=signal_dtos,
                    bias_note=bias_note
                )
                ticker_setups.append(ticker_setup)
            
            # Log the processed setups
            logger.info(f"Processed {len(ticker_setups)} ticker setups from message {message_id}")
            
            # Store in database - this uses the existing DB models
            self._save_to_database(content, ticker_sections, timestamp)
            
            # Publish the processed setups for charting/monitoring
            self._publish_for_charting(ticker_setups)
            
        except Exception as e:
            logger.error(f"Error processing setup message {message_id}: {e}")
    
    def _save_to_database(self, content: str, ticker_sections: Dict[str, str], timestamp: datetime):
        """
        Save the processed setup message to the database.
        
        Args:
            content: Raw message content
            ticker_sections: Dictionary of ticker symbols to section text
            timestamp: Message timestamp
        """
        try:
            # Create setup message
            setup_message = SetupMessage(
                date=timestamp.date(),
                raw_text=content,
                source='discord',
                created_at=datetime.utcnow()
            )
            
            db.session.add(setup_message)
            db.session.flush()  # Get ID without committing
            
            # Process each ticker setup
            for ticker, section_text in ticker_sections.items():
                # Create ticker setup
                ticker_setup = TickerSetup(
                    symbol=ticker,
                    text=section_text,
                    message_id=setup_message.id
                )
                
                db.session.add(ticker_setup)
                db.session.flush()  # Get ID without committing
                
                # Extract signals for this ticker
                signals = self.parser.extract_signals(ticker, section_text)
                for signal_obj in signals:
                    # Map the DTO signal to database model
                    signal = Signal(
                        ticker_setup_id=ticker_setup.id,
                        category=SignalCategoryEnum[signal_obj.category.name] if hasattr(signal_obj.category, 'name') else SignalCategoryEnum.BREAKOUT,
                        aggressiveness=AggressivenessEnum[signal_obj.aggressiveness.name] if hasattr(signal_obj.aggressiveness, 'name') else AggressivenessEnum.NONE,
                        comparison=ComparisonTypeEnum[signal_obj.comparison.name] if hasattr(signal_obj.comparison, 'name') else ComparisonTypeEnum.ABOVE,
                        trigger=signal_obj.trigger,
                        targets=signal_obj.targets
                    )
                    db.session.add(signal)
                
                # Extract bias for this ticker
                bias_obj = self.parser.extract_bias(ticker, section_text)
                if bias_obj:
                    # Map the DTO bias to database model
                    bias = Bias(
                        ticker_setup_id=ticker_setup.id,
                        direction=BiasDirectionEnum[bias_obj.direction.name] if hasattr(bias_obj.direction, 'name') else BiasDirectionEnum.BULLISH,
                        condition=ComparisonTypeEnum[bias_obj.condition.name] if hasattr(bias_obj.condition, 'name') else ComparisonTypeEnum.ABOVE,
                        price=bias_obj.price
                    )
                    db.session.add(bias)
                    
                    # Add bias flip if present
                    if bias_obj.flip:
                        bias_flip = BiasFlip(
                            bias_id=bias.id,
                            direction=BiasDirectionEnum[bias_obj.flip.direction.name] if hasattr(bias_obj.flip.direction, 'name') else BiasDirectionEnum.BEARISH,
                            price_level=bias_obj.flip.price_level
                        )
                        db.session.add(bias_flip)
            
            # Commit all changes
            db.session.commit()
            logger.info(f"Saved setup message with {len(ticker_sections)} tickers to database")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving setup to database: {e}")
            raise
    
    def _publish_for_charting(self, ticker_setups: List[TickerSetupDTO]):
        """
        Publish the processed ticker setups for charting and monitoring.
        
        Args:
            ticker_setups: List of processed ticker setups
        """
        try:
            # Prepare data for charting
            for ticker_setup in ticker_setups:
                # Create a serializable representation of the ticker setup
                setup_data = {
                    'symbol': ticker_setup.symbol,
                    'bias_note': ticker_setup.bias_note,
                    'current_price': ticker_setup.current_price,
                    'signals': [
                        {
                            'category': signal.category,
                            'subcategory': signal.subcategory,
                            'direction': signal.direction,
                            'level': signal.level,
                            'targets': signal.targets
                        }
                        for signal in ticker_setup.signals
                    ]
                }
                
                # Publish event for this ticker setup using PostgreSQL event bus
                publish_event(
                    f"events:charting:ticker:{ticker_setup.symbol}", 
                    "setup_created", 
                    setup_data
                )
                
            logger.debug(f"Published {len(ticker_setups)} ticker setups for charting")
            
        except Exception as e:
            logger.error(f"Error publishing ticker setups for charting: {e}")


def start_consumer():
    """Start the Discord message consumer."""
    from app import app
    with app.app_context():
        consumer = MessageConsumer()
        consumer.start()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Start the consumer
    start_consumer()
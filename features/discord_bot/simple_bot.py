"""
Simplified Discord Bot Implementation

Clean Discord bot following vertical slice architecture.
Uses dependency injection to avoid circular imports.
"""
import logging
import discord
from discord.ext import commands
from typing import Optional
from .dto import RawMessageDto
from .interfaces import IIngestionService

logger = logging.getLogger(__name__)


class SimpleTradingBot(discord.Client):
    """Simplified Discord bot for trading messages."""
    
    def __init__(self, ingestion_service: IIngestionService, target_channel_id: Optional[str] = None, **kwargs):
        """Initialize bot with ingestion service dependency."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents, **kwargs)
        
        self.ingestion_service = ingestion_service
        self.target_channel_id = target_channel_id
        self.is_ready = False
    
    async def on_ready(self):
        """Bot startup event."""
        logger.info(f"✅ Discord bot connected as {self.user}")
        self.is_ready = True
        
        # Log available guilds and channels for debugging
        for guild in self.guilds:
            logger.info(f"Connected to guild: {guild.name} (ID: {guild.id})")
    
    async def on_message(self, message):
        """Handle incoming Discord messages."""
        # Skip bot's own messages
        if message.author == self.user:
            return
        
        # Only process messages from target channel if specified
        if self.target_channel_id and str(message.channel.id) != self.target_channel_id:
            return
        
        try:
            # Convert Discord message to DTO
            raw_message = RawMessageDto.from_discord(message)
            
            # Hand off to ingestion service
            await self.ingestion_service.ingest_raw_message(raw_message)
            
            logger.debug(f"Processed message {raw_message.message_id} from channel {raw_message.channel_id}")
            
        except Exception as e:
            logger.error(f"Error processing Discord message {message.id}: {e}")
    
    def get_status(self) -> dict:
        """Get bot status information."""
        return {
            'connected': self.is_ready,
            'user': str(self.user) if self.user else None,
            'guild_count': len(self.guilds) if self.guilds else 0,
            'target_channel': self.target_channel_id
        }
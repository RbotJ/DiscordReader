"""
Ingestion DTO Module

Data Transfer Objects for ingestion functionality.
Provides clean interfaces for message data transfer.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class DiscordMessageDTO:
    """DTO for Discord messages in the ingestion pipeline."""
    message_id: str
    channel_id: str
    author_id: str
    content: str
    created_at: datetime
    is_setup: bool = False
    processed: bool = False
    embed_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations."""
        return {
            'id': self.message_id,
            'channel_id': self.channel_id,
            'author_id': self.author_id,
            'content': self.content,
            'timestamp': self.created_at,
            'is_setup': self.is_setup,
            'processed': self.processed,
            'embeds': self.embed_data
        }
"""
Discord Bot DTO Module

Data Transfer Objects for Discord bot functionality.
Provides clean interfaces between Discord and other features.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from common.utils import ensure_utc


@dataclass(frozen=True)
class RawMessageDto:
    """DTO for raw Discord messages."""
    message_id: str
    channel_id: str
    author_id: str
    author_name: str
    content: str
    timestamp: datetime
    
    @classmethod
    def from_discord(cls, msg) -> 'RawMessageDto':
        """Create DTO from Discord message object."""
        return cls(
            message_id=str(msg.id),
            channel_id=str(msg.channel.id),
            author_id=str(msg.author.id),
            author_name=str(msg.author.display_name),
            content=msg.content,
            timestamp=ensure_utc(msg.created_at)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'message_id': self.message_id,
            'channel_id': self.channel_id,
            'author_id': self.author_id,
            'author': self.author_name,
            'content': self.content,
            'timestamp': self.timestamp
        }
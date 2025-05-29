"""
Discord Channels Interfaces

Abstract interfaces for Discord channel management functionality.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import discord


class IDiscordChannelService(ABC):
    """Interface for Discord channel management operations."""
    
    @abstractmethod
    async def discover_and_sync_channels(self, bot_client: discord.Client) -> Dict[str, int]:
        """Discover and synchronize channels with database."""
        pass
    
    @abstractmethod
    def get_target_channel_id(self, target_name: str) -> Optional[str]:
        """Get channel ID for a target channel name."""
        pass
    
    @abstractmethod
    def mark_channel_for_listening(self, channel_id: str, listen: bool) -> bool:
        """Mark a channel for message listening."""
        pass
    
    @abstractmethod
    def update_channel_activity(self, channel_id: str, message_id: str) -> bool:
        """Update channel activity metadata."""
        pass
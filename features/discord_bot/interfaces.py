"""
Discord Bot Interfaces Module

Abstract interfaces for Discord bot functionality.
Provides clean contracts between Discord and other features.
"""
from abc import ABC, abstractmethod
from .dto import RawMessageDto


class IIngestionService(ABC):
    """Interface for ingesting Discord messages."""
    
    @abstractmethod
    async def ingest_raw_message(self, raw: RawMessageDto) -> None:
        """
        Ingest a raw Discord message.
        
        Args:
            raw: Raw message DTO from Discord
        """
        ...
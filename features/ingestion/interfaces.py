"""
Ingestion Interfaces Module

Abstract interfaces for message ingestion functionality.
"""
from abc import ABC, abstractmethod
from features.discord_bot.dto import RawMessageDto


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
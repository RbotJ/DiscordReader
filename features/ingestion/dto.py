"""
Ingestion DTO Module

Consolidated data transfer objects for ingestion functionality.
Uses common DiscordMessageDTO as single source of truth.
"""
from common.models import DiscordMessageDTO

# Re-export the common DTO for backward compatibility
__all__ = ['DiscordMessageDTO']
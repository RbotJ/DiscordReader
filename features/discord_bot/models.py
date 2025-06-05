"""
Discord Bot Models

This module now imports models from their canonical locations to avoid duplication.
The DiscordChannel model is maintained in features.discord_channels.models.
"""

# Import from canonical location to avoid model duplication
from common.models import DiscordMessageDTO

# Re-export for backward compatibility
__all__ = ['DiscordChannel']
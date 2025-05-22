"""
Discord Environment Utilities

This module provides utilities for validating and accessing Discord environment variables.
"""
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Required environment variables for Discord
REQUIRED_ENV_VARS = [
    'DISCORD_TOKEN',
    'DISCORD_CHANNEL_ID',
    'DISCORD_GUILD_ID'
]

# Optional environment variables with defaults
OPTIONAL_ENV_VARS = {
    'DISCORD_TEST_CHANNEL_ID': None,
    'DISCORD_SETUPS_CHANNEL_ID': None
}

# Channel type mapping
CHANNEL_TYPES = {
    'default': 'DISCORD_CHANNEL_ID',
    'test': 'DISCORD_TEST_CHANNEL_ID',
    'setups': 'DISCORD_SETUPS_CHANNEL_ID'
}

def validate_discord_env() -> bool:
    """
    Validate that all required Discord environment variables are set.
    
    Returns:
        bool: True if all required variables are set, False otherwise
    """
    missing_vars = []
    
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing_vars.append(var)
            
    if missing_vars:
        logger.error(f"Missing required Discord environment variables: {', '.join(missing_vars)}")
        return False
        
    logger.info("Discord environment variables validated successfully")
    return True
    
def validate_discord_token() -> bool:
    """
    Validate that the Discord token is set.
    
    Returns:
        bool: True if the token is set, False otherwise
    """
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        logger.error("Discord token not set")
        return False
        
    # Simple validation - tokens are typically long strings
    if len(token) < 20:
        logger.warning("Discord token seems too short, might be invalid")
        
    return True
    
def get_discord_token() -> Optional[str]:
    """
    Get the Discord token from environment variables.
    
    Returns:
        str: Discord token or None if not set
    """
    return os.environ.get('DISCORD_TOKEN')
    
def get_channel_id(channel_type: str = 'default') -> Optional[str]:
    """
    Get the channel ID for a specific channel type.
    
    Args:
        channel_type: Type of channel ('default', 'test', 'setups')
        
    Returns:
        str: Channel ID or None if not set
    """
    env_var = CHANNEL_TYPES.get(channel_type, 'DISCORD_CHANNEL_ID')
    return os.environ.get(env_var)
    
def get_guild_id() -> Optional[str]:
    """
    Get the Discord guild ID from environment variables.
    
    Returns:
        str: Guild ID or None if not set
    """
    return os.environ.get('DISCORD_GUILD_ID')
    
def get_environment_status() -> Dict[str, bool]:
    """
    Get the status of all Discord environment variables.
    
    Returns:
        Dict[str, bool]: Dictionary with variable names as keys and boolean status as values
    """
    status = {}
    
    # Check required variables
    for var in REQUIRED_ENV_VARS:
        status[var] = bool(os.environ.get(var))
        
    # Check optional variables
    for var in OPTIONAL_ENV_VARS:
        status[var] = bool(os.environ.get(var))
        
    return status
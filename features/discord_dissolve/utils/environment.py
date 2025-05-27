"""
Discord Environment Utilities

This module provides utilities for validating and accessing Discord environment variables.
"""
import os
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# Required environment variables
REQUIRED_VARS = [
    'DISCORD_TOKEN',
    'DISCORD_CHANNEL_ID',
    'DISCORD_GUILD_ID'
]

# Optional environment variables with defaults
OPTIONAL_VARS = {
    'DISCORD_TEST_CHANNEL_ID': None,
    'DISCORD_SETUPS_CHANNEL_ID': None
}

def validate_discord_env() -> bool:
    """
    Validate that all required Discord environment variables are set.
    
    Returns:
        bool: True if all required variables are set, False otherwise
    """
    missing = []
    
    for var in REQUIRED_VARS:
        if not os.environ.get(var):
            missing.append(var)
            
    if missing:
        logger.error(f"Missing required Discord environment variables: {', '.join(missing)}")
        return False
        
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
    if channel_type == 'default':
        return os.environ.get('DISCORD_CHANNEL_ID')
    elif channel_type == 'test':
        return os.environ.get('DISCORD_TEST_CHANNEL_ID')
    elif channel_type == 'setups':
        return os.environ.get('DISCORD_SETUPS_CHANNEL_ID')
    else:
        logger.warning(f"Unknown channel type: {channel_type}")
        return None

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
    for var in REQUIRED_VARS:
        status[var] = bool(os.environ.get(var))
        
    # Check optional variables
    for var in OPTIONAL_VARS:
        status[var] = bool(os.environ.get(var))
        
    return status


def check_environment() -> tuple[bool, Dict[str, bool]]:
    """
    Check Discord environment variables and return status.
    
    Returns:
        tuple: (success, status_dict)
            - success (bool): True if all required variables are set
            - status_dict (Dict[str, bool]): Dictionary with status of all variables
    """
    # Get environment status
    status = get_environment_status()
    
    # Check if all required variables are set
    success = all(status[var] for var in REQUIRED_VARS)
    
    # If not successful, log missing variables
    if not success:
        missing = [var for var in REQUIRED_VARS if not status[var]]
        logger.error(f"Missing required Discord environment variables: {', '.join(missing)}")
    
    return success, status
"""
Discord Environment Validation

This module provides utility functions for validating Discord environment variables.
"""
import os
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# Required environment variables
REQUIRED_VARIABLES = [
    'DISCORD_BOT_TOKEN',
    'DISCORD_CHANNEL_ID'
]

# Optional but recommended variables
OPTIONAL_VARIABLES = [
    'DISCORD_CHANNEL_BOT_DIALOGUE',
    'DISCORD_CHANNEL_APLUS_SETUPS',
    'DISCORD_CHANNEL_TEST_HERE_ONE'
]

def check_environment() -> Tuple[bool, Dict[str, str]]:
    """
    Check Discord environment variables are properly set.
    
    Returns:
        Tuple[bool, Dict[str, str]]: Success status and dictionary of variables
    """
    env_vars = {}
    success = True
    
    # Check required variables
    for var_name in REQUIRED_VARIABLES:
        value = os.environ.get(var_name)
        if value:
            if var_name == 'DISCORD_BOT_TOKEN':
                # Show only first 5 characters for security
                logger.info(f"{var_name} found: {value[:5]}*** (truncated)")
            else:
                logger.info(f"{var_name} found: {value}")
            env_vars[var_name] = value
        else:
            logger.error(f"{var_name} not found")
            success = False
    
    # Check optional variables
    for var_name in OPTIONAL_VARIABLES:
        value = os.environ.get(var_name)
        if value:
            logger.info(f"{var_name} found: {value}")
            env_vars[var_name] = value
        else:
            logger.warning(f"{var_name} not found")
    
    # Validate channel IDs are integers
    issues = False
    for var_name, value in env_vars.items():
        if 'CHANNEL' in var_name and value:
            try:
                int(value)
                logger.info(f"{var_name} is a valid integer")
            except ValueError:
                logger.error(f"{var_name} is not a valid integer: {value}")
                issues = True
    
    if issues:
        logger.error("Issues found with Discord environment variables")
        success = False
    
    if success:
        logger.info("All required Discord environment variables look good")
    
    return success, env_vars

def get_channel_id(channel_type: str = 'default') -> Optional[str]:
    """
    Get a Discord channel ID based on type.
    
    Args:
        channel_type: Type of channel to retrieve ('default', 'bot_dialogue', 
                     'setups', or 'test')
    
    Returns:
        Channel ID or None if not found
    """
    if channel_type == 'default':
        return os.environ.get('DISCORD_CHANNEL_ID')
    elif channel_type == 'bot_dialogue':
        return os.environ.get('DISCORD_CHANNEL_BOT_DIALOGUE')
    elif channel_type == 'setups':
        return os.environ.get('DISCORD_CHANNEL_APLUS_SETUPS')
    elif channel_type == 'test':
        return os.environ.get('DISCORD_CHANNEL_TEST_HERE_ONE')
    else:
        logger.error(f"Unknown channel type: {channel_type}")
        return None

def validate_discord_token() -> bool:
    """
    Validate that the Discord bot token is set.
    
    Returns:
        bool: True if token is set, False otherwise
    """
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN not found")
        return False
    
    # Basic validation (not empty and has a reasonable length)
    if len(token) < 20:
        logger.error("DISCORD_BOT_TOKEN appears to be invalid (too short)")
        return False
    
    return True

def get_all_channel_ids() -> List[str]:
    """
    Get all configured Discord channel IDs.
    
    Returns:
        List[str]: List of channel IDs
    """
    channels = []
    for var_name, value in os.environ.items():
        if var_name.startswith('DISCORD_CHANNEL_') and value:
            try:
                # Validate it's an integer
                int(value)
                channels.append(value)
            except ValueError:
                logger.warning(f"Invalid channel ID for {var_name}: {value}")
    
    return channels

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Run environment check
    success, env_vars = check_environment()
    
    # Exit with appropriate status code
    import sys
    sys.exit(0 if success else 1)
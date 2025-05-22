"""
Discord Environment Variables Checker

Utility module to verify that Discord environment variables are properly set.
"""
import os
import sys
import logging

# Configure logging
logger = logging.getLogger(__name__)

def check_discord_env():
    """
    Check Discord environment variables.
    
    Returns:
        True if all required variables are set, False otherwise
    """
    # Check bot token
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if token:
        # Show only first 5 characters for security
        logger.info(f"DISCORD_BOT_TOKEN found: {token[:5]}*** (truncated)")
    else:
        logger.error("DISCORD_BOT_TOKEN not found")
        return False
        
    # Check channel IDs
    bot_channel = os.environ.get('DISCORD_CHANNEL_BOT_DIALOGUE')
    if bot_channel:
        logger.info(f"DISCORD_CHANNEL_BOT_DIALOGUE: {bot_channel}")
    else:
        logger.warning("DISCORD_CHANNEL_BOT_DIALOGUE not found")
        
    setups_channel = os.environ.get('DISCORD_CHANNEL_APLUS_SETUPS')
    if setups_channel:
        logger.info(f"DISCORD_CHANNEL_APLUS_SETUPS: {setups_channel}")
    else:
        logger.warning("DISCORD_CHANNEL_APLUS_SETUPS not found")
        
    test_channel = os.environ.get('DISCORD_CHANNEL_TEST_HERE_ONE')
    if test_channel:
        logger.info(f"DISCORD_CHANNEL_TEST_HERE_ONE: {test_channel}")
    else:
        logger.warning("DISCORD_CHANNEL_TEST_HERE_ONE not found")
        
    # Check values are integers
    issues = False
    
    for name, value in [
        ('DISCORD_CHANNEL_BOT_DIALOGUE', bot_channel),
        ('DISCORD_CHANNEL_APLUS_SETUPS', setups_channel),
        ('DISCORD_CHANNEL_TEST_HERE_ONE', test_channel)
    ]:
        if value:
            try:
                int(value)
                logger.info(f"{name} is a valid integer")
            except ValueError:
                logger.error(f"{name} is not a valid integer: {value}")
                issues = True
                
    if issues:
        logger.error("Issues found with Discord environment variables")
        return False
    else:
        logger.info("All Discord environment variables look good")
        return True

# Command-line entry point
def main():
    """Command-line entry point for checking Discord environment variables."""
    # Configure logging for command-line use
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    result = check_discord_env()
    return 0 if result else 1

if __name__ == '__main__':
    sys.exit(main())
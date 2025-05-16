"""
Check Discord Environment Variables

Simple script to verify that Discord environment variables are properly set.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Check Discord environment variables."""
    # Check bot token
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if token:
        # Show only first 5 characters for security
        logging.info(f"DISCORD_BOT_TOKEN found: {token[:5]}*** (truncated)")
    else:
        logging.error("DISCORD_BOT_TOKEN not found")
        
    # Check channel IDs
    bot_channel = os.environ.get('DISCORD_CHANNEL_BOT_DIALOGUE')
    if bot_channel:
        logging.info(f"DISCORD_CHANNEL_BOT_DIALOGUE: {bot_channel}")
    else:
        logging.warning("DISCORD_CHANNEL_BOT_DIALOGUE not found")
        
    setups_channel = os.environ.get('DISCORD_CHANNEL_APLUS_SETUPS')
    if setups_channel:
        logging.info(f"DISCORD_CHANNEL_APLUS_SETUPS: {setups_channel}")
    else:
        logging.warning("DISCORD_CHANNEL_APLUS_SETUPS not found")
        
    test_channel = os.environ.get('DISCORD_CHANNEL_TEST_HERE_ONE')
    if test_channel:
        logging.info(f"DISCORD_CHANNEL_TEST_HERE_ONE: {test_channel}")
    else:
        logging.warning("DISCORD_CHANNEL_TEST_HERE_ONE not found")
        
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
                logging.info(f"{name} is a valid integer")
            except ValueError:
                logging.error(f"{name} is not a valid integer: {value}")
                issues = True
                
    if issues:
        logging.error("Issues found with Discord environment variables")
        return 1
    else:
        logging.info("All Discord environment variables look good")
        return 0

if __name__ == '__main__':
    sys.exit(main())
"""
Check Discord Environment Variables

Simple script to verify that Discord environment variables are properly set.
"""
import logging
import sys
from features.discord.utils.environment import check_environment

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Run environment check
    success, _ = check_environment()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
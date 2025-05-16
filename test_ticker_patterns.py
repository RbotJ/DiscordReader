"""
Test Ticker Pattern Recognition

This script tests the pattern recognition for ticker symbols.
"""
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_patterns():
    # Sample messages with different formats
    test_messages = [
        """A+ Trade Setups (Thu, May 16)

1) SPY: Rejection Near 500.5
   - Resistance: 500.5
   - Target: 495
   - Bearish bias below 500.5""",
        
        """A+ Trade Setups (Thu, May 16)

SPY
🔻 Breakdown Below 500.5
Resistance: 500.5
Target 1: 495
⚠️ Bearish bias below 500.5""",
        
        """A+ Trade Setups (Thu, May 16)

1. SPY: Breakdown Below 500.5
   - Resistance: 500.5
   - Target 1: 495
   - Bearish bias below 500.5"""
    ]
    
    # Define patterns to test
    patterns = [
        (r"\d+\)\s+([A-Z]+)", "Numbered pattern with parenthesis"),
        (r"\d+\.\s+([A-Z]+)", "Numbered pattern with period"),
        (r"^([A-Z]+)$", "Standalone line"),
        (r"^\s*(\d+)[.)]?\s+([A-Z]+)", "General numbered pattern")
    ]
    
    # Test each pattern against each message
    for i, message in enumerate(test_messages):
        logger.info(f"Testing message format {i+1}")
        logger.info("-" * 40)
        logger.info(message)
        logger.info("-" * 40)
        
        # Test each pattern
        for pattern, description in patterns:
            matches = re.findall(pattern, message, re.MULTILINE)
            logger.info(f"Pattern: {description} ({pattern})")
            logger.info(f"Matches: {matches}")
            logger.info("")
    
    return True

def main():
    """Main function."""
    logger.info("Testing ticker pattern recognition")
    
    result = test_patterns()
    
    logger.info(f"Pattern test {'succeeded' if result else 'failed'}")
    return 0 if result else 1

if __name__ == '__main__':
    main()
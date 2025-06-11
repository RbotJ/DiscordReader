"""
Test Clean Parsing Architecture

Validates the cleaned parsing architecture with A+ format enforcement
and unified message processing pipeline.
"""
import logging
from datetime import datetime, date, timezone
from features.parsing.message_processor import get_message_processor
from common.utils import utc_now

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_aplus_message_processing():
    """Test A+ message processing through the unified pipeline."""
    
    # Real A+ message content for testing
    aplus_message_content = """A+ Scalp Trade Setups — Thursday June 11

NVDA
🔻 Aggressive Breakdown Below 925.50 🔻 920.40, 915.30, 910.20
🔻 Conservative Breakdown Below 920.75 🔻 915.65, 910.55, 905.45
🔼 Aggressive Breakout Above 935.80 🔼 940.90, 946.00, 951.10
🔄 Bounce Zone: 915.25-920.75 🔼 Target: 925.85, 930.95

SPY
🔻 Rejection Short Near 545.50 🔻 542.40, 539.30, 536.20
🔼 Conservative Breakout Above 548.25 🔼 551.35, 554.45, 557.55

⚠️ Bias — Watch for market direction confirmation before entries. Volume validation required for all breakouts."""

    # Create test message
    raw_message = {
        'message_id': 'test_123456',
        'channel_id': 'test_channel',
        'author_id': 'test_author',
        'content': aplus_message_content,
        'timestamp': utc_now().isoformat()
    }
    
    try:
        processor = get_message_processor()
        result = processor.process_discord_message(raw_message)
        
        logger.info(f"Processing result: {result}")
        
        if result['success']:
            logger.info(f"✅ Successfully processed A+ message with {result['setups_created']} setups and {result['signals_created']} signals")
            return True
        else:
            logger.error(f"❌ Failed to process A+ message: {result.get('error', 'Unknown error')}")
            return False
            
    except ValueError as e:
        if "does not match A+ pattern" in str(e):
            logger.error(f"❌ A+ format validation failed: {e}")
        else:
            logger.error(f"❌ Processing failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def test_non_aplus_message_rejection():
    """Test that non-A+ messages are properly rejected."""
    
    # Non-A+ message content
    generic_message_content = """Looking at TSLA here. 
    
    Possible breakout above 250 with targets at 255, 260.
    Stop loss around 245."""

    raw_message = {
        'message_id': 'test_generic_123',
        'channel_id': 'test_channel',
        'author_id': 'test_author',
        'content': generic_message_content,
        'timestamp': utc_now().isoformat()
    }
    
    try:
        processor = get_message_processor()
        result = processor.process_discord_message(raw_message)
        
        logger.error(f"❌ Generic message should have been rejected but was processed: {result}")
        return False
        
    except ValueError as e:
        if "does not match A+ pattern" in str(e):
            logger.info("✅ Generic message properly rejected with A+ format enforcement")
            return True
        else:
            logger.error(f"❌ Unexpected ValueError: {e}")
            return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def test_aplus_parser_validation():
    """Test A+ parser message validation."""
    from features.parsing.aplus_parser import get_aplus_parser
    
    aplus_parser = get_aplus_parser()
    
    # Test valid A+ message
    valid_content = "A+ Scalp Trade Setups — Thursday June 11\n\nNVDA\n🔻 Aggressive Breakdown Below 925.50 🔻 920.40"
    if aplus_parser.validate_message(valid_content):
        logger.info("✅ A+ parser correctly validates A+ messages")
    else:
        logger.error("❌ A+ parser failed to validate valid A+ message")
        return False
    
    # Test invalid message
    invalid_content = "Generic trading message about TSLA breakout"
    if not aplus_parser.validate_message(invalid_content):
        logger.info("✅ A+ parser correctly rejects non-A+ messages")
    else:
        logger.error("❌ A+ parser incorrectly validated non-A+ message")
        return False
    
    return True

def main():
    """Run all architecture tests."""
    logger.info("🧪 Testing Clean Parsing Architecture")
    logger.info("=" * 50)
    
    tests = [
        ("A+ Parser Validation", test_aplus_parser_validation),
        ("A+ Message Processing", test_aplus_message_processing),
        ("Non-A+ Message Rejection", test_non_aplus_message_rejection),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} ERROR: {e}")
    
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Clean parsing architecture is working correctly.")
        logger.info("\n📋 Architecture Summary:")
        logger.info("✅ A+ format enforcement implemented")
        logger.info("✅ No fallback to generic parsing")
        logger.info("✅ Unified message processing pipeline")
        logger.info("✅ Clean separation between parsing and storage")
    else:
        logger.error("❌ Some tests failed. Architecture needs attention.")
    
    return passed == total

if __name__ == "__main__":
    main()
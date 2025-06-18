#!/usr/bin/env python3
"""
Test Core Parsing Restoration

Validates that the core parsing pipeline is working after removing broken duplicate detection logic.
This test focuses on ensuring basic parsing functionality is restored.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date
from features.parsing.service import get_parsing_service
from features.parsing.aplus_parser import get_aplus_parser

def test_basic_parsing():
    """Test that basic A+ message parsing works without errors."""
    print("Testing basic A+ message parsing...")
    
    # Test message from the validation fix
    test_message = """A+ Scalp Trade Setups – Monday June 10

SPY Scalp setups:
$520 C – watch for move above $520.50
$521 C – watch for move above $521.50
$519 P – watch for move below $519.50

NVDA Scalp setups:
$1220 C – watch for move above $1222
$1240 C – watch for move above $1242
$1200 P – watch for move below $1198

Key levels to watch:
- Market open momentum
- 10:30 AM reversal zone
- 2:00 PM strength continuation"""

    try:
        # Get parser instance
        parser = get_aplus_parser()
        
        # Test parser validation
        is_valid = parser.validate_message(test_message)
        print(f"✅ Message validation: {is_valid}")
        
        if not is_valid:
            print("❌ Message validation failed - this indicates a problem")
            return False
        
        # Test parsing
        parsed_result = parser.parse_message(test_message, "test_message_123")
        print(f"✅ Parsing result: {len(parsed_result.get('setups', []))} setups found")
        
        # Verify setups
        setups = parsed_result.get('setups', [])
        if len(setups) > 0:
            for setup in setups[:2]:  # Show first 2 setups
                print(f"   - {setup.ticker}: {setup.direction} {setup.trigger_level}")
        
        return True
        
    except Exception as e:
        print(f"❌ Parsing failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_integration():
    """Test that the parsing service works without duplicate detection errors."""
    print("\nTesting parsing service integration...")
    
    try:
        # Get service instance
        service = get_parsing_service()
        
        # Test service health
        is_healthy = service.is_healthy()
        print(f"✅ Service health: {is_healthy}")
        
        # Test message parsing through service
        test_message_data = {
            'content': """A+ Trade Setups – Tuesday June 11

QQQ Scalp setups:
$350 C – watch for move above $350.50
$348 P – watch for move below $347.50""",
            'id': 'test_service_msg_456',
            'timestamp': '2025-06-11T10:00:00Z'
        }
        
        result = service.parse_message(test_message_data)
        print(f"✅ Service parsing result: {result.get('success', False)}")
        
        if result.get('success'):
            print(f"   - Setups processed: {len(result.get('setups', []))}")
        else:
            print(f"   - Error: {result.get('error', 'Unknown error')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Service integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation_accuracy():
    """Test that the validation fix is still working correctly."""
    print("\nTesting validation accuracy...")
    
    parser = get_aplus_parser()
    
    # Test valid A+ messages (should all return True)
    valid_messages = [
        "A+ Scalp Trade Setups – Monday June 10\n\nSPY $520 C – watch above $520.50",
        "A+ Trade Setups – Tuesday June 11\n\nQQQ $350 C – watch above $350.50", 
        "A+ Scalp Setups – Wednesday June 12\n\nNVDA $1200 C – watch above $1202"
    ]
    
    # Test invalid messages (should all return False)
    invalid_messages = [
        "Good morning! Here's today's market outlook",
        "SPY looks bullish today, watching for breakout",
        "NVDA earnings coming up next week"
    ]
    
    valid_count = 0
    for i, msg in enumerate(valid_messages):
        is_valid = parser.is_aplus_message(msg)
        print(f"   Valid message {i+1}: {is_valid}")
        if is_valid:
            valid_count += 1
    
    invalid_count = 0
    for i, msg in enumerate(invalid_messages):
        is_valid = parser.is_aplus_message(msg)
        print(f"   Invalid message {i+1}: {not is_valid}")
        if not is_valid:
            invalid_count += 1
    
    accuracy = (valid_count + invalid_count) / (len(valid_messages) + len(invalid_messages))
    print(f"✅ Validation accuracy: {accuracy:.1%} ({valid_count}/{len(valid_messages)} valid, {invalid_count}/{len(invalid_messages)} invalid)")
    
    return accuracy >= 1.0

def main():
    """Run all restoration tests."""
    print("=" * 60)
    print("CORE PARSING RESTORATION TEST")
    print("=" * 60)
    
    tests = [
        test_basic_parsing,
        test_service_integration, 
        test_validation_accuracy
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print("✅ PASSED")
            else:
                print("❌ FAILED")
        except Exception as e:
            print(f"❌ FAILED with exception: {e}")
        print("-" * 40)
    
    print(f"\nRESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Core parsing pipeline is restored.")
    else:
        print("⚠️  Some tests failed. Core parsing pipeline needs more work.")
    
    return passed == total

if __name__ == "__main__":
    main()
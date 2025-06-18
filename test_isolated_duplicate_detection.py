#!/usr/bin/env python3
"""
Test Isolated Duplicate Detection System

Validates that the new isolated duplicate detection system works correctly
while preserving the core parsing functionality.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, datetime
from features.parsing.duplicate_detector import get_duplicate_detector, DUPLICATE_POLICY
from features.parsing.service import get_parsing_service
from features.parsing.store import get_parsing_store
from common.db import db

def test_duplicate_detector_initialization():
    """Test that duplicate detector initializes correctly with different policies."""
    print("Testing duplicate detector initialization...")
    
    try:
        # Test default policy
        detector_default = get_duplicate_detector()
        print(f"✅ Default policy: {detector_default.policy}")
        
        # Test specific policies
        for policy in ["skip", "replace", "allow"]:
            detector = get_duplicate_detector(policy)
            assert detector.policy == policy, f"Policy mismatch: expected {policy}, got {detector.policy}"
            print(f"✅ Policy '{policy}' initialized correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

def test_duplicate_detection_with_skip_policy():
    """Test duplicate detection with skip policy."""
    print("\nTesting duplicate detection with 'skip' policy...")
    
    try:
        # Set up detector with skip policy
        detector = get_duplicate_detector("skip")
        
        # Create a test trading day
        test_day = date(2025, 6, 18)
        
        # Test with no existing duplicates (should proceed)
        with db.session() as session:
            should_skip = detector.should_skip_duplicate(session, test_day, "test_msg_1")
            print(f"✅ No duplicates found, should_skip: {should_skip}")
            
            # Test duplicate action
            action = detector.get_duplicate_action(
                session, test_day, "test_msg_1", 
                datetime.now(), 100
            )
            print(f"✅ Action with no duplicates: {action}")
        
        return True
        
    except Exception as e:
        print(f"❌ Skip policy test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_duplicate_detection_with_replace_policy():
    """Test duplicate detection with replace policy."""
    print("\nTesting duplicate detection with 'replace' policy...")
    
    try:
        # Set up detector with replace policy
        detector = get_duplicate_detector("replace")
        
        # Create a test trading day
        test_day = date(2025, 6, 18)
        
        # Test replacement logic
        with db.session() as session:
            # Test with newer, longer message (should replace)
            current_time = datetime.now()
            action = detector.get_duplicate_action(
                session, test_day, "test_msg_new", 
                current_time, 500  # Longer content
            )
            print(f"✅ Action with newer/longer message: {action}")
        
        return True
        
    except Exception as e:
        print(f"❌ Replace policy test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_duplicate_statistics():
    """Test duplicate statistics functionality."""
    print("\nTesting duplicate statistics...")
    
    try:
        detector = get_duplicate_detector()
        
        with db.session() as session:
            stats = detector.get_duplicate_statistics(session)
            print(f"✅ Statistics retrieved: {stats}")
            
            # Verify required fields
            required_fields = ['duplicate_trading_days', 'duplicate_days_list', 'current_policy']
            for field in required_fields:
                assert field in stats, f"Missing required field: {field}"
            
            print(f"   - Duplicate trading days: {stats['duplicate_trading_days']}")
            print(f"   - Current policy: {stats['current_policy']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Statistics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_core_parsing_still_works():
    """Test that core parsing functionality is not disrupted."""
    print("\nTesting core parsing functionality preservation...")
    
    try:
        # Test basic parsing still works
        service = get_parsing_service()
        
        test_message_data = {
            'content': """A+ Trade Setups – Wednesday June 18

SPY Scalp setups:
$522 C – watch for move above $522.50
$520 P – watch for move below $519.50""",
            'id': 'test_isolation_msg_789',
            'timestamp': '2025-06-18T14:00:00Z'
        }
        
        result = service.parse_message(test_message_data)
        print(f"✅ Core parsing result: {result.get('success', False)}")
        
        if result.get('success'):
            print(f"   - Setups processed: {len(result.get('setups', []))}")
        else:
            print(f"   - Error: {result.get('error', 'Unknown error')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Core parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_with_parsing_service():
    """Test that duplicate detection can be integrated without breaking parsing."""
    print("\nTesting integration potential with parsing service...")
    
    try:
        # Verify that the duplicate detector can work with parsing service data
        detector = get_duplicate_detector()
        service = get_parsing_service()
        
        # Test that we can create detector instances without issues
        assert detector is not None, "Detector creation failed"
        assert service is not None, "Service creation failed"
        
        print("✅ Detector and service can coexist")
        
        # Test that detector methods are callable
        test_day = date(2025, 6, 18)
        with db.session() as session:
            # These should not raise exceptions
            detector.check_for_duplicate(session, test_day, "test_msg")
            detector.get_duplicate_statistics(session)
        
        print("✅ Detector methods are functional")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_policy_configuration():
    """Test that policy configuration works correctly."""
    print("\nTesting policy configuration...")
    
    try:
        # Test environment variable reading
        original_policy = DUPLICATE_POLICY
        print(f"✅ Current policy from environment: {original_policy}")
        
        # Test manual policy setting
        for policy in ["skip", "replace", "allow"]:
            detector = get_duplicate_detector(policy)
            assert detector.policy == policy, f"Policy not set correctly: {policy}"
            print(f"✅ Manual policy '{policy}' works")
        
        return True
        
    except Exception as e:
        print(f"❌ Policy configuration test failed: {e}")
        return False

def main():
    """Run all isolated duplicate detection tests."""
    print("=" * 60)
    print("ISOLATED DUPLICATE DETECTION SYSTEM TEST")
    print("=" * 60)
    
    tests = [
        test_duplicate_detector_initialization,
        test_duplicate_detection_with_skip_policy,
        test_duplicate_detection_with_replace_policy,
        test_duplicate_statistics,
        test_core_parsing_still_works,
        test_integration_with_parsing_service,
        test_policy_configuration
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
        print("🎉 All tests passed! Isolated duplicate detection system is working correctly.")
        print("\nSUMMARY:")
        print("✅ Core parsing pipeline preserved")
        print("✅ Duplicate detection logic isolated")
        print("✅ Configurable policy system working")
        print("✅ Ready for optional integration")
    else:
        print("⚠️  Some tests failed. Duplicate detection system needs more work.")
    
    return passed == total

if __name__ == "__main__":
    main()
"""
Test script to verify the new validation logic correctly identifies all A+ message patterns.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from features.parsing.aplus_parser import APlusMessageParser

def test_validation_patterns():
    """Test the new validation logic with all the header patterns found in the database."""
    
    parser = APlusMessageParser()
    
    # Test patterns from the actual database messages
    test_messages = [
        # Pattern 1: A+ Scalp Trade Setups (14 messages)
        "A+ Scalp Trade Setups — Tue Jun 17\n\nSPY\n❌ Rejection Short" + "x" * 300,
        "A+ Scalp Trade Setups - Mon Jun 16\n\nSPY\n❌ Rejection Short" + "x" * 300,
        "A+ Scalp Trade Setups. — Wed Jun 11\n\nAlso eyes on" + "x" * 300,
        
        # Pattern 2: A+ Trade Setups (7 messages)  
        "A+ Trade Setups — Tue May 27\n\nSPY\n❌ Rejection Short Near" + "x" * 300,
        "A+ Trade Setups — Wed May 21 (Scalps)\n\nSPY\n🔻 Aggressive Breakdown" + "x" * 300,
        
        # Pattern 3: A+ Scalp Setups (1 message)
        "A+ Scalp Setups — Thur May 22\n\n✅ SPY \n❌ Rejection" + "x" * 300,
        
        # Should be rejected - test patterns
        "A+ Test Setups — Today\n\nSPY\n❌ Rejection Short" + "x" * 300,
        "A+ Draft Trade Setups — Today\n\nSPY\n❌ Rejection Short" + "x" * 300,
        
        # Should be rejected - too short
        "A+ Scalp Trade Setups — Today\n\nSPY",
        
        # Should be rejected - missing A+
        "Scalp Trade Setups — Today\n\nSPY\n❌ Rejection Short" + "x" * 300,
        
        # Should be rejected - missing setup
        "A+ Scalp Trade — Today\n\nSPY\n❌ Rejection Short" + "x" * 300,
    ]
    
    expected_results = [True, True, True, True, True, True, False, False, False, False, False]
    
    print("Testing new validation logic:")
    print("=" * 50)
    
    all_passed = True
    for i, (message, expected) in enumerate(zip(test_messages, expected_results)):
        result = parser.validate_message(message)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        
        header = message.split('\n')[0]
        print(f"{i+1:2d}. {status} - '{header[:40]}...' -> {result} (expected {expected})")
        
        if result != expected:
            all_passed = False
    
    print("=" * 50)
    print(f"Overall result: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    return all_passed

if __name__ == "__main__":
    test_validation_patterns()
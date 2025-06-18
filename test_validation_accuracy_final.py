#!/usr/bin/env python3
"""
Final Validation Accuracy Test

Quick test to confirm 100% validation accuracy is restored.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from features.parsing.aplus_parser import get_aplus_parser

def test_validation_accuracy():
    """Test validation accuracy with known test cases."""
    print("Testing A+ message validation accuracy...")
    
    parser = get_aplus_parser()
    
    # Test cases with expected results
    test_cases = [
        ("A+ Scalp Trade Setups – Monday June 10\n\nSPY $520 C", True),
        ("A+ Trade Setups – Tuesday June 11\n\nQQQ $350 C", True),
        ("A+ Scalp Setups – Wednesday June 12\n\nNVDA $1200 C", True),
        ("Good morning traders", False),
        ("Market outlook for today", False),
        ("Random message", False)
    ]
    
    correct = 0
    for content, expected in test_cases:
        result = parser.validate_message(content)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{content[:30]}...' → {result} (expected {expected})")
        if result == expected:
            correct += 1
    
    accuracy = correct / len(test_cases)
    print(f"\nValidation Accuracy: {accuracy:.1%} ({correct}/{len(test_cases)})")
    
    return accuracy >= 1.0

if __name__ == "__main__":
    success = test_validation_accuracy()
    if success:
        print("🎉 Validation accuracy restored to 100%!")
    else:
        print("⚠️ Validation accuracy still needs work.")
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Test A+ message validation to debug why messages aren't being recognized
"""

import re
from features.parsing.aplus_parser import get_aplus_parser

def test_validation():
    """Test A+ validation with actual message content"""
    
    # Get the parser
    parser = get_aplus_parser()
    
    # Test messages from database
    test_messages = [
        "A+ Scalp Trade Setups — Tue Jun 17\n\nSPY\n❌ Rejection Short 602.68 🔻 600.50, 598.30, 595.60",
        "A+ Scalp Trade Setups - Mon Jun 16\n\nSPY\n❌ Rejection Short 601.35 🔻 599.75, 597.40, 595.60",
        "A+ Scalp Trade Setups. — Wed Jun 11\n\nSPY\n❌ Rejection Short 606.37",
        "A+ Scalp Trade Setups — Tue Jun 10\n\nSPY\n🔻 Breakdown Below 599.00 (598.40, 597.80, 597.20)"
    ]
    
    print("Testing A+ message validation:")
    print("=" * 50)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}:")
        print(f"Content preview: {message[:50]}...")
        
        # Test the validation
        is_valid = parser.validate_message(message)
        print(f"Validation result: {is_valid}")
        
        # Test the regex directly
        header_pattern = re.compile(r'A\+\s*(?:SCALP|Scalp)\s*(?:TRADE\s*)?(?:SETUPS|Setups)', re.IGNORECASE)
        regex_match = bool(header_pattern.search(message))
        print(f"Direct regex match: {regex_match}")
        
        if not is_valid:
            print(f"❌ Validation failed for message {i}")
        else:
            print(f"✅ Validation passed for message {i}")

if __name__ == "__main__":
    test_validation()
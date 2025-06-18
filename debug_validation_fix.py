#!/usr/bin/env python3
"""
Debug Validation Fix

Test the exact validation logic to see why it's failing on known good messages.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from features.parsing.aplus_parser import get_aplus_parser

def debug_validation():
    """Debug the validation logic step by step."""
    print("Debugging A+ message validation...")
    
    parser = get_aplus_parser()
    
    # Test the failing cases
    test_cases = [
        "A+ Scalp Trade Setups – Monday June 10",
        "A+ Trade Setups – Tuesday June 11", 
        "A+ Scalp Setups – Wednesday June 12"
    ]
    
    for content in test_cases:
        print(f"\nTesting: '{content}'")
        
        # Check basic conditions
        header = content.strip().splitlines()[0].lower() if content.strip() else ""
        print(f"Header: '{header}'")
        print(f"Contains 'a+': {'a+' in header}")
        print(f"Contains 'setup': {'setup' in header}")
        print(f"Contains 'setups': {'setups' in header}")
        print(f"Length: {len(content)}")
        
        # Test validation
        result = parser.validate_message(content)
        print(f"Validation result: {result}")
        
        # Check individual conditions
        if not content or not isinstance(content, str):
            print("❌ Failed: empty or invalid content")
        elif "a+" not in header:
            print("❌ Failed: missing 'A+' in header")
        elif "setup" not in header and "setups" not in header:
            print("❌ Failed: missing 'setup' or 'setups' in header")
        elif any(flag in header for flag in ["test", "draft", "ignore", "template"]):
            print("❌ Failed: test indicators found")
        elif len(content) < 50:
            print(f"❌ Failed: content too short ({len(content)} < 50 chars)")
        else:
            print("✅ Should pass validation")

if __name__ == "__main__":
    debug_validation()
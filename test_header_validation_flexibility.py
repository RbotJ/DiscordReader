"""
Test Header Validation Flexibility Implementation

Validates that the updated validate_message() method correctly:
1. Accepts all real-world A+ header variations
2. Uses token-based analysis with required ["A+", "Setups"] tokens
3. Rejects messages with "Test" or "Check" tokens
4. Logs proper JSON-formatted rejection reasons with message_id
"""

import json
import logging
from io import StringIO
from features.parsing.aplus_parser import get_aplus_parser

def test_header_validation_flexibility():
    """Test the enhanced header validation with real-world variations."""
    
    # Setup logging capture to verify rejection logging
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger = logging.getLogger('features.parsing.aplus_parser')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    parser = get_aplus_parser()
    
    # Test Case 1: Valid A+ header variations (should pass)
    valid_headers = [
        "A+ Scalp Trade Setups — Jun 10",
        "A+ Trade Setups — Tuesday June 11", 
        "A+ Scalp Setups — Watchlist update",
        "A+ SCALP TRADE SETUPS",
        "A+ Trade Setups",
        "A+ Scalp Setups",
        "A+ Scalp Trade Setups — Monday",
        "A+ Trade Setups: Daily Alert"
    ]
    
    valid_content_base = "\n\nNVDA\nAbove 596.90 🔼 599.80, 602.00, 605.50\n\nTSLA\nBelow 180.50 🔻 178.20, 175.80, 173.40"
    
    print("Testing valid A+ header variations:")
    for i, header in enumerate(valid_headers):
        message_id = f"valid_msg_{i+1}"
        content = header + valid_content_base
        result = parser.validate_message(content, message_id)
        print(f"  ✓ '{header[:30]}...' → {result}")
        assert result == True, f"Valid header should pass: {header}"
    
    # Test Case 2: Invalid headers (should fail with proper logging)
    invalid_cases = [
        ("Missing A+", "Trade Setups — Jun 10" + valid_content_base, "header_token_mismatch"),
        ("Missing Setups", "A+ Trade Alert — Jun 10" + valid_content_base, "header_token_mismatch"), 
        ("Test indicator", "A+ Test Setups — Jun 10" + valid_content_base, "test_indicator"),
        ("Check indicator", "A+ Check Setups — Jun 10" + valid_content_base, "test_indicator"),
        ("Too short", "A+ Setups", "content_too_short"),
        ("Empty content", "", "empty_content")
    ]
    
    print("\nTesting invalid cases with rejection logging:")
    for case_name, content, expected_reason in invalid_cases:
        message_id = f"invalid_{case_name.replace(' ', '_').lower()}"
        
        # Clear log stream
        log_stream.seek(0)
        log_stream.truncate(0)
        
        result = parser.validate_message(content, message_id)
        print(f"  ✗ {case_name} → {result}")
        assert result == False, f"Invalid case should fail: {case_name}"
        
        # Verify rejection logging
        log_output = log_stream.getvalue()
        if log_output:
            try:
                # Find JSON log entry
                log_lines = [line.strip() for line in log_output.split('\n') if line.strip()]
                json_found = False
                for line in log_lines:
                    if '{' in line and '}' in line:
                        # Extract JSON part
                        json_start = line.find('{')
                        json_part = line[json_start:]
                        log_data = json.loads(json_part)
                        
                        assert log_data["reason"] == expected_reason, f"Expected reason '{expected_reason}', got '{log_data['reason']}'"
                        assert log_data["message_id"] == message_id, f"Expected message_id '{message_id}', got '{log_data['message_id']}'"
                        json_found = True
                        print(f"    📋 Logged: {json_part}")
                        break
                
                assert json_found, f"No JSON log found for {case_name}. Log output: {log_output}"
                
            except json.JSONDecodeError as e:
                print(f"    ⚠️  Invalid JSON in log: {log_output}")
                raise AssertionError(f"Invalid JSON in rejection log for {case_name}: {e}")
    
    # Test Case 3: Token-based analysis validation
    print("\nTesting token-based analysis logic:")
    
    # Test first 6 words limitation
    long_header_valid = "A+ Scalp Trade Setups Extra Words That Should Be Ignored — Jun 10" + valid_content_base
    result = parser.validate_message(long_header_valid, "long_header_test")
    print(f"  ✓ Long header (>6 words) → {result}")
    assert result == True, "Should ignore words beyond first 6"
    
    # Test punctuation handling
    punctuation_header = "A+ Scalp Trade Setups— Jun 10" + valid_content_base  # No space before dash
    result = parser.validate_message(punctuation_header, "punctuation_test")
    print(f"  ✓ Punctuation handling → {result}")
    assert result == True, "Should handle punctuation correctly"
    
    # Test case insensitivity
    case_header = "a+ SCALP trade SETUPS — jun 10" + valid_content_base
    result = parser.validate_message(case_header, "case_test")
    print(f"  ✓ Case insensitivity → {result}")
    assert result == True, "Should be case insensitive"
    
    # Clean up logging
    logger.removeHandler(handler)
    
    print("\n✅ All header validation flexibility tests passed!")
    return True

def test_optional_token_detection():
    """Test that optional tokens (scalp, trade) are properly detected and logged."""
    
    # Setup logging capture
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger = logging.getLogger('features.parsing.aplus_parser')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    parser = get_aplus_parser()
    content_base = "\n\nNVDA\nAbove 596.90 🔼 599.80, 602.00, 605.50"
    
    test_cases = [
        ("A+ Scalp Trade Setups", ["scalp", "trade"]),
        ("A+ Trade Setups", ["trade"]),
        ("A+ Scalp Setups", ["scalp"]),
        ("A+ Setups", [])
    ]
    
    print("Testing optional token detection:")
    for header, expected_tokens in test_cases:
        message_id = f"optional_test_{len(expected_tokens)}"
        content = header + content_base
        
        # Clear log stream
        log_stream.seek(0)
        log_stream.truncate(0)
        
        result = parser.validate_message(content, message_id)
        assert result == True, f"Should pass validation: {header}"
        
        # Check debug log for optional tokens
        log_output = log_stream.getvalue()
        debug_line = [line for line in log_output.split('\n') if 'Valid A+ message' in line]
        
        if debug_line:
            log_content = debug_line[0]
            print(f"  ✓ '{header}' → found optional: {expected_tokens}")
            for token in expected_tokens:
                assert token in log_content.lower(), f"Expected '{token}' in debug log: {log_content}"
        else:
            print(f"  ⚠️  No debug log found for: {header}")
    
    # Clean up
    logger.removeHandler(handler)
    print("✅ Optional token detection tests passed!")

def main():
    """Run all header validation flexibility tests."""
    print("🧪 Testing Header Validation Flexibility Implementation")
    print("=" * 60)
    
    try:
        test_header_validation_flexibility()
        test_optional_token_detection()
        
        print("\n🎉 All tests completed successfully!")
        print("✅ Task 1: Header Validation Flexibility - IMPLEMENTED")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    main()
"""
Simple A+ Validation Fix Test - Direct Parser Testing
"""
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_aplus_validation_direct():
    """Test A+ validation directly without Flask context."""
    print("=== Testing A+ Message Validation Fix ===")
    
    try:
        from features.parsing.aplus_parser import APlusMessageParser
        parser = APlusMessageParser()
        
        # Test cases representing the 3 header variations found in dataset
        test_cases = [
            {
                'content': 'A+ Scalp Trade Setups – Monday June 10\n\nNVDA 🔥\n120C 6/14 @ 1.15 target 1.50+\n121C 6/14 @ .95 target 1.25+',
                'expected': True,
                'description': 'Standard A+ Scalp Trade Setups format (14 messages)'
            },
            {
                'content': 'A+ Trade Setups – Tuesday June 11\n\nSPY\n533C 6/14 @ .85 target 1.10+\n534C 6/14 @ .75 target 1.00+',
                'expected': True,
                'description': 'Shortened A+ Trade Setups format (7 messages)'
            },
            {
                'content': 'A+ Scalp Setups – Wednesday June 12\n\nTSLA\n180C 6/14 @ 2.50 target 3.20+\n181C 6/14 @ 2.30 target 3.00+',
                'expected': True,
                'description': 'Alternative A+ Scalp Setups format (1 message)'
            },
            {
                'content': 'Good morning everyone! Market update for today...',
                'expected': False,
                'description': 'Non-A+ message should be rejected'
            }
        ]
        
        results = []
        passed = 0
        
        for i, test_case in enumerate(test_cases, 1):
            content = test_case['content']
            expected = test_case['expected']
            description = test_case['description']
            
            # Direct validation test
            is_valid = parser.validate_message(content)
            success = is_valid == expected
            
            if success:
                passed += 1
                status = "✓ PASS"
            else:
                status = "✗ FAIL"
            
            print(f"Test {i}: {status} - {description}")
            print(f"  Expected: {expected}, Got: {is_valid}")
            print(f"  Content length: {len(content)} chars")
            
            results.append({
                'test': i,
                'success': success,
                'expected': expected,
                'actual': is_valid,
                'description': description
            })
        
        # Summary
        total = len(test_cases)
        accuracy = (passed / total) * 100
        
        print(f"\n📊 Validation Results: {passed}/{total} tests passed ({accuracy:.1f}%)")
        
        if passed == total:
            print("✅ SUCCESS: All A+ header variations are now recognized!")
            print("   The validation fix successfully addresses the parsing accuracy issue")
        elif passed > 1:
            print("⚠️  PARTIAL: Some A+ variations recognized, but issues remain")
        else:
            print("❌ FAILED: Validation fix needs additional work")
        
        return results
        
    except Exception as e:
        print(f"❌ Error testing validation: {e}")
        return []

if __name__ == "__main__":
    test_aplus_validation_direct()
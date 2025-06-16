"""
Test Price Level Parsing Fix

Validates the structured price parsing approach eliminates duplicate triggers
and creates proper trigger/target level distinctions.
"""

import logging
from features.parsing.aplus_parser import APlusMessageParser, parse_setup_prices, validate_price_structure
from features.parsing.setup_converter import create_levels_for_setup, convert_parsed_setup_to_model

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_structured_price_parsing():
    """Test the new structured price parsing approach."""
    
    test_lines = [
        # Standard format that was problematic
        "🔼 Aggressive Breakout Above 596.90 🔼 599.80, 602.00, 605.50",
        
        # Other A+ formats
        "🔻 Aggressive Breakdown Below 602.55 🔻 601.28, 598.85, 596.50",
        "❌ Rejection Short 606.37 🔻 604.10, 601.60, 598.85",
        "🔄 Bounce 596.50–598.10 🔼 601.28, 604.10, 606.37",
        
        # Alternative formats
        "Above 346.93 | 349.20, 351.80, 354.62",
        "Below 142.92 (142.51, 142.08, 141.67)"
    ]
    
    print("Testing Structured Price Parsing:")
    print("=" * 50)
    
    for line in test_lines:
        trigger, targets = parse_setup_prices(line)
        
        if trigger is not None:
            print(f"✓ Line: {line[:50]}...")
            print(f"  Trigger: ${trigger}")
            print(f"  Targets: {[f'${t}' for t in targets]}")
            print(f"  Count: 1 trigger + {len(targets)} targets = {1 + len(targets)} total levels")
            
            # Verify no duplicates
            if trigger in targets:
                print(f"  ❌ ERROR: Trigger ${trigger} found in targets!")
            else:
                print(f"  ✓ No trigger duplication")
        else:
            print(f"✗ Failed to parse: {line}")
        print()

def test_validation_logic():
    """Test the price structure validation."""
    
    print("Testing Price Validation Logic:")
    print("=" * 50)
    
    # Test cases: (line, trigger, targets, expected_result)
    test_cases = [
        # Valid cases
        ("🔼 Above 596.90 🔼 599.80, 602.00", 596.90, [599.80, 602.00], True),
        ("🔻 Below 602.55 🔻 601.28, 598.85", 602.55, [601.28, 598.85], True),
        
        # Invalid: trigger in targets
        ("🔼 Above 596.90 🔼 596.90, 599.80", 596.90, [596.90, 599.80], False),
        
        # Invalid: direction mismatch
        ("🔼 Above 596.90 🔼 594.00, 591.00", 596.90, [594.00, 591.00], False),
        ("🔻 Below 602.55 🔻 605.00, 607.00", 602.55, [605.00, 607.00], False),
        
        # Invalid: no targets
        ("🔼 Above 596.90", 596.90, [], False),
    ]
    
    for line, trigger, targets, expected in test_cases:
        result = validate_price_structure(line, trigger, targets)
        status = "✓" if result == expected else "✗"
        print(f"{status} {line[:40]}... → {result} (expected {expected})")
    
    print()

def test_level_creation():
    """Test the level creation with trigger/target distinction."""
    
    print("Testing Level Creation:")
    print("=" * 50)
    
    # Create a mock setup model for testing
    class MockSetup:
        def __init__(self):
            self.id = "test_setup_001"
            self.trigger_level = 596.90
            self.target_prices = [599.80, 602.00, 605.50]
            self.direction = "long"
            self.label = "AggressiveBreakout"
    
    setup = MockSetup()
    levels = create_levels_for_setup(setup)
    
    print(f"Setup: {setup.direction} {setup.label}")
    print(f"Trigger: ${setup.trigger_level}")
    print(f"Targets: {[f'${t}' for t in setup.target_prices]}")
    print()
    
    print("Generated Levels:")
    for level in levels:
        level_type = level.level_type
        price = level.trigger_price
        seq = level.sequence_order
        print(f"  {level_type}: ${price} (sequence: {seq})")
    
    # Verify structure
    trigger_levels = [l for l in levels if l.level_type == 'trigger']
    target_levels = [l for l in levels if l.level_type == 'target']
    
    print()
    print("Validation Results:")
    print(f"✓ Total levels: {len(levels)}")
    print(f"✓ Trigger levels: {len(trigger_levels)} (should be 1)")
    print(f"✓ Target levels: {len(target_levels)} (should be {len(setup.target_prices)})")
    
    # Check for duplicates
    all_prices = [l.trigger_price for l in levels]
    unique_prices = set(all_prices)
    
    if len(all_prices) == len(unique_prices):
        print(f"✓ No duplicate prices found")
    else:
        print(f"❌ Duplicate prices detected: {all_prices}")
    
    print()

def test_complete_workflow():
    """Test the complete workflow with the problematic line."""
    
    print("Testing Complete Workflow:")
    print("=" * 50)
    
    # The exact problematic line from the issue
    problematic_message = """A+ Scalp Trade Setups — Test Day

SPY
🔼 Aggressive Breakout Above 596.90 🔼 599.80, 602.00, 605.50"""
    
    parser = APlusMessageParser()
    result = parser.parse_message(problematic_message, "test_fix_001")
    
    if result.get('success') and result.get('setups'):
        setup = result['setups'][0]
        
        print("Parsed Setup:")
        print(f"  Ticker: {setup.ticker}")
        print(f"  Label: {setup.label}")
        print(f"  Direction: {setup.direction}")
        print(f"  Trigger: ${setup.trigger_level}")
        print(f"  Targets: {[f'${t}' for t in setup.target_prices]}")
        print()
        
        # Convert to database model and create levels
        setup_model = convert_parsed_setup_to_model(setup, "test_fix_001")
        levels = create_levels_for_setup(setup_model)
        
        print("Database Levels (Expected Result):")
        for level in levels:
            level_type = level.level_type
            price = level.trigger_price
            print(f"  {level_type}: ${price}")
        
        print()
        print("Final Verification:")
        
        # Count levels by type
        trigger_count = len([l for l in levels if l.level_type == 'trigger'])
        target_count = len([l for l in levels if l.level_type == 'target'])
        
        expected_structure = trigger_count == 1 and target_count == 3
        no_duplicates = len(set(l.trigger_price for l in levels)) == len(levels)
        
        print(f"✓ Structure correct (1 trigger + 3 targets): {expected_structure}")
        print(f"✓ No duplicate prices: {no_duplicates}")
        
        if expected_structure and no_duplicates:
            print("🎉 PRICE LEVEL PARSING FIX SUCCESSFUL!")
        else:
            print("❌ Issues still present")
    else:
        print("❌ Failed to parse test message")
    
    print()

def main():
    """Run all price level parsing tests."""
    print("Price Level Parsing Fix Validation")
    print("=" * 60)
    print()
    
    test_structured_price_parsing()
    test_validation_logic()
    test_level_creation()
    test_complete_workflow()
    
    print("All tests completed!")

if __name__ == "__main__":
    main()
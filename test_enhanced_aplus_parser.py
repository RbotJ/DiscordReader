"""
Test Enhanced A+ Parser with Real Message Data
"""
from features.parsing.aplus_parser import get_aplus_parser
from features.parsing.service import ParsingService

def test_enhanced_aplus_parser():
    """Test the enhanced A+ parser with real message data and new schema fields."""
    
    # Real A+ scalp setups message from May 29th
    real_message = """
**A+ SCALP SETUPS 5/29/24**

**NVDA** 
🔽 **Aggressive Breakdown:** 1110 → 1105, 1095, 1088
🔼 **Aggressive Breakout:** 1130 → 1140, 1150, 1158
📍 **Bounce Zone:** 1095–1105 → 1120, 1135, 1145
⚠️ **Rejection Near:** 1158 → 1140, 1125, 1110

**SPY**
🔽 **Conservative Breakdown:** 530.50 → 529.80, 528.90, 527.50
🔼 **Conservative Breakout:** 533.00 → 534.25, 535.80, 537.20
📍 **Bounce Zone:** 528.90–530.50 → 532.75, 534.00, 535.50

**TSLA**
🔽 **Aggressive Breakdown:** 185.00 → 183.50, 181.80, 179.90
🔼 **Aggressive Breakout:** 188.50 → 190.20, 192.80, 195.40
⚠️ **Rejection Near:** 195.40 → 192.00, 189.50, 186.75
    """.strip()
    
    print("=== Testing Enhanced A+ Parser with Profile Names ===")
    
    parser = get_aplus_parser()
    
    # Test validation
    print("1. Testing message validation...")
    is_valid = parser.validate_message(real_message)
    print(f"   Message validation: {is_valid}")
    
    if is_valid:
        # Test enhanced parsing
        print("\n2. Testing enhanced message parsing...")
        result = parser.parse_message(real_message, "test_message_123")
        
        print(f"   Parse result success: {result.get('success', False)}")
        print(f"   Trading day: {result.get('trading_day')}")
        print(f"   Number of setups: {len(result.get('setups', []))}")
        
        # Print each enhanced setup with new schema fields
        print("\n3. Enhanced setup details:")
        for i, setup in enumerate(result.get('setups', []), 1):
            print(f"\n   Setup {i}:")
            print(f"     Ticker: {setup.ticker}")
            print(f"     Setup Type: {setup.setup_type}")
            print(f"     Profile Name: {setup.profile_name}")  # NEW FIELD
            print(f"     Direction: {setup.direction}")
            print(f"     Strategy: {setup.strategy}")
            print(f"     Trigger Level: {setup.trigger_level}")  # NEW FIELD
            print(f"     Target Prices: {setup.target_prices}")
            print(f"     Entry Condition: {setup.entry_condition}")  # NEW FIELD
            print(f"     Raw Line: {setup.raw_line}")
    
    # Test integration with parsing service
    print("\n=== Testing Integration with Parsing Service ===")
    
    service = ParsingService()
    
    print("4. Testing A+ message parsing through service...")
    service_result = service.parse_aplus_message(
        message_content=real_message,
        message_id="service_test_123"
    )
    
    print(f"   Service result success: {service_result.get('success', False)}")
    if service_result.get('success'):
        print(f"   Setups created: {service_result.get('setups_created', 0)}")
        print(f"   Levels created: {service_result.get('levels_created', 0)}")
        print(f"   Trading day: {service_result.get('trading_day')}")
        print(f"   Tickers processed: {service_result.get('tickers', [])}")
        
        # Show enhanced features
        enhanced = service_result.get('enhanced_features', {})
        print(f"   Profile names: {enhanced.get('profile_names', [])}")
        print(f"   Trigger levels: {enhanced.get('trigger_levels', [])}")
        print(f"   Entry conditions count: {len(enhanced.get('entry_conditions', []))}")
    else:
        print(f"   Error: {service_result.get('error', 'Unknown error')}")
    
    print("\n=== Enhanced A+ Parser Test Completed! ===")

if __name__ == "__main__":
    test_enhanced_aplus_parser()
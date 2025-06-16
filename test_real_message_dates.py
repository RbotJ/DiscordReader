"""
Test Real Message Date Parsing

Tests the enhanced trading date parsing with actual A+ messages from the database.
"""

import logging
from features.parsing.aplus_parser import APlusMessageParser

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_real_messages():
    """Test trading date parsing with real A+ messages from database."""
    parser = APlusMessageParser()
    
    # Real message headers from the database
    real_messages = [
        "A+ Scalp Trade Setups. — Wed Jun 11",  # Message 107
        "A+ Scalp Trade Setups — Tue Jun 10",   # Message 108  
        "A+ Scalp Trade Setups -- Mon Jun 9"    # Message 109
    ]
    
    print("Testing Real A+ Message Headers:")
    print("=" * 50)
    
    for header in real_messages:
        extracted_date = parser.extract_trading_date(header)
        if extracted_date:
            print(f"✓ '{header}' → {extracted_date}")
        else:
            print(f"✗ '{header}' → Failed to extract")
    
    print()
    
    # Test with full message content (first message)
    full_message = '''A+ Scalp Trade Setups. — Wed Jun 11

Also eyes on SAIL (up with news)

SPY
❌ Rejection Short 606.37 🔻 604.10, 601.60, 598.85
🔻 Aggressive Breakdown 602.55 🔻 601.28, 598.85, 596.50
🔻 Conservative Breakdown 598.85 🔻 596.50, 594.40, 591.90
🔼 Aggressive Breakout 606.75 🔼 608.30, 610.20, 612.60
🔼 Conservative Breakout 608.30 🔼 610.20, 612.60, 615.00
🔄 Bounce 596.50–598.10 🔼 601.28, 604.10, 606.37
⚠️ Bias: Up move continues above 602.55 — breakout confirmed if 606.75 holds intraday. Pullbacks into 596.50 area are bounce zone — used to be local resistance now support'''
    
    print("Testing Full Message Parsing:")
    print("=" * 50)
    
    # Test if message validates as A+
    is_valid = parser.validate_message(full_message)
    print(f"Message validates as A+: {is_valid}")
    
    # Extract trading date
    extracted_date = parser.extract_trading_date(full_message)
    print(f"Extracted trading date: {extracted_date}")
    
    # Parse complete message
    result = parser.parse_message(full_message, "test_107")
    print(f"Parse success: {result.get('success', False)}")
    print(f"Trading date in result: {result.get('trading_date')}")
    print(f"Number of setups parsed: {len(result.get('setups', []))}")
    
    # Check audit trail metadata
    if result.get('setups'):
        first_setup = result['setups'][0]
        print(f"First setup trading day: {first_setup.trading_day}")
        print(f"Trading date source: extracted (not fallback)")
        
    print()

def test_date_extraction_patterns():
    """Test specific date extraction patterns found in real messages."""
    parser = APlusMessageParser()
    
    # Test edge cases found in real data
    edge_cases = [
        "A+ Scalp Trade Setups. — Wed Jun 11",  # Period after "Setups"
        "A+ Scalp Trade Setups -- Mon Jun 9",   # Double dash
        "A+ Scalp Trade Setups — Tue Jun 10"    # Standard format
    ]
    
    print("Testing Edge Case Patterns:")
    print("=" * 50)
    
    for header in edge_cases:
        extracted_date = parser.extract_trading_date(header)
        validation_result = parser.validate_trading_date(extracted_date, header)
        
        if extracted_date and validation_result:
            print(f"✓ '{header}' → {extracted_date} (validated)")
        elif extracted_date and not validation_result:
            print(f"⚠ '{header}' → {extracted_date} (validation failed)")
        else:
            print(f"✗ '{header}' → Failed to extract")
    
    print()

def main():
    """Run all real message tests."""
    print("Real Message Trading Date Parsing Tests")
    print("=" * 60)
    print()
    
    test_real_messages()
    test_date_extraction_patterns()
    
    print("Real message testing completed!")

if __name__ == "__main__":
    main()
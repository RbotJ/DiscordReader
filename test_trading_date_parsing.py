"""
Test Trading Date Parsing Resolution

Validates the enhanced trading date extraction patterns and error handling
to ensure proper date extraction from A+ message headers.
"""

import logging
from datetime import date
from features.parsing.aplus_parser import APlusMessageParser

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_enhanced_date_patterns():
    """Test the enhanced regex patterns with various header formats."""
    parser = APlusMessageParser()
    
    test_headers = [
        "A+ Scalp Trade Setups — Sunday June 15",
        "A+ Scalp Trade Setups — Jun 15", 
        "A+ SCALP TRADE SETUPS — Thursday May 29",
        "A+ Scalp Trade Setups – December 31",  # en-dash
        "A+ Scalp Trade Setups - Dec 25",       # hyphen
        "A+ Scalp Trade Setups — June 2",
        "A+ Scalp Trade Setups — Monday January 1",
        "A+ Scalp Trade Setups — Wed Sep 18"
    ]
    
    print("Testing Enhanced Date Patterns:")
    print("=" * 50)
    
    for header in test_headers:
        extracted_date = parser.extract_trading_date(header)
        if extracted_date:
            print(f"✓ '{header}' → {extracted_date}")
        else:
            print(f"✗ '{header}' → Failed to extract")
    
    print()

def test_month_abbreviations():
    """Test month abbreviation support."""
    parser = APlusMessageParser()
    
    abbreviation_tests = [
        "A+ Scalp Trade Setups — Jan 1",
        "A+ Scalp Trade Setups — Feb 14", 
        "A+ Scalp Trade Setups — Mar 15",
        "A+ Scalp Trade Setups — Apr 20",
        "A+ Scalp Trade Setups — May 25",
        "A+ Scalp Trade Setups — Jun 30",
        "A+ Scalp Trade Setups — Jul 4",
        "A+ Scalp Trade Setups — Aug 15",
        "A+ Scalp Trade Setups — Sep 30",
        "A+ Scalp Trade Setups — Oct 31",
        "A+ Scalp Trade Setups — Nov 28",
        "A+ Scalp Trade Setups — Dec 25"
    ]
    
    print("Testing Month Abbreviations:")
    print("=" * 50)
    
    for header in abbreviation_tests:
        extracted_date = parser.extract_trading_date(header)
        if extracted_date:
            print(f"✓ '{header}' → {extracted_date}")
        else:
            print(f"✗ '{header}' → Failed to extract")
    
    print()

def test_validation_logic():
    """Test the date validation logic."""
    parser = APlusMessageParser()
    
    # Test reasonable dates
    reasonable_date = date(2025, 6, 15)
    assert parser.validate_trading_date(reasonable_date, "test content") == True
    print("✓ Reasonable date validation passed")
    
    # Test unrealistic dates (over 1 year away)
    unrealistic_date = date(2027, 6, 15)  # 2+ years in future
    assert parser.validate_trading_date(unrealistic_date, "test content") == False
    print("✓ Unrealistic date validation failed as expected")
    
    # Test None date
    assert parser.validate_trading_date(None, "test content") == False
    print("✓ None date validation failed as expected")
    
    print()

def test_full_message_parsing():
    """Test complete message parsing with trading date extraction."""
    parser = APlusMessageParser()
    
    sample_message = """A+ Scalp Trade Setups — Sunday June 15

NVDA
🔼 442.75 | 446.00, 448.50, 451.25
Bearish Breakdown → 440.25 | 437.50, 435.00, 432.75
Rejection off 445.50 | 443.00, 441.25, 439.50

⚠️ Bias — Cautiously bullish on NVDA"""
    
    print("Testing Full Message Parsing:")
    print("=" * 50)
    
    # Test trading date extraction
    extracted_date = parser.extract_trading_date(sample_message)
    print(f"Extracted trading date: {extracted_date}")
    
    # Test full message parsing
    result = parser.parse_message(sample_message, "test_message_123")
    
    print(f"Parse success: {result.get('success', False)}")
    print(f"Trading date in result: {result.get('trading_date')}")
    print(f"Number of setups: {len(result.get('setups', []))}")
    
    if result.get('setups'):
        for setup in result['setups']:
            print(f"  - {setup.ticker}: {setup.label} (date: {setup.trading_day})")
    
    print()

def test_error_handling():
    """Test error handling for malformed headers."""
    parser = APlusMessageParser()
    
    malformed_headers = [
        "Random message without A+ header",
        "A+ Scalp Trade Setups — Invalid Month 15",
        "A+ Scalp Trade Setups — June 99",  # Invalid day
        "A+ Scalp Trade Setups — ",  # Incomplete header
        ""  # Empty string
    ]
    
    print("Testing Error Handling:")
    print("=" * 50)
    
    for header in malformed_headers:
        extracted_date = parser.extract_trading_date(header)
        if extracted_date is None:
            print(f"✓ Correctly failed: '{header}'")
        else:
            print(f"✗ Unexpectedly succeeded: '{header}' → {extracted_date}")
    
    print()

def main():
    """Run all trading date parsing tests."""
    print("Trading Date Parsing Resolution Tests")
    print("=" * 60)
    print()
    
    test_enhanced_date_patterns()
    test_month_abbreviations()
    test_validation_logic()
    test_full_message_parsing()
    test_error_handling()
    
    print("All tests completed!")

if __name__ == "__main__":
    main()
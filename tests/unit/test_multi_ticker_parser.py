#!/usr/bin/env python
"""
Test Multi-Ticker Parser

This script tests the new multi-ticker parser implementation on various message formats.
"""
import logging
import sys
from datetime import date
from pprint import pprint

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import parser modules
from features.setups.multi_ticker_parser import (
    normalize_text,
    extract_ticker_sections,
    extract_signal_from_section,
    extract_bias_from_section,
    process_ticker_sections
)

from features.setups.parser import parse_setup_message
from common.models import (
    SignalCategory, 
    ComparisonType, 
    Aggressiveness,
    BiasDirection
)

# Test messages in different formats
TEST_MESSAGES = {
    "numbered_with_parenthesis": """
A+ Trade Setups — Wed May 15

1) SPY: Breakout Above 587
- Target 1: 588.5
- Target 2: 590
Bullish bias above 585

2) AAPL: Breakdown Below 182.5
- Target 1: 180
- Target 2: 178.5
Bearish bias below 183
""",

    "numbered_with_period": """
A+ Trade Setups — Wed May 15

1. SPY: Breakout Above 587
- Target 1: 588.5
- Target 2: 590
Bullish bias above 585

2. AAPL: Breakdown Below 182.5
- Target 1: 180
- Target 2: 178.5
Bearish bias below 183
""",

    "emoji_format": """
A+ Trade Setups — Wed May 15

SPY 
🔼 Breakout Above 587
Target: 590
⚠️ Bullish above 585

AAPL
🔻 Breakdown Below 182.5
Target: 180
⚠️ Bearish below 183
""",

    "multiple_tickers": """
A+ Trade Setups (Wed, May 15)

AAPL: Breakout Above 180
Target: 185

SPY: Breakdown Below 500.5
Target: 495
"""
}

def test_normalize_text():
    """Test the emoji normalization function."""
    print("\n=== Testing emoji normalization ===")
    
    text = "🔼 Breakout Above 100\n🔻 Breakdown Below 90\n❌ Rejection Near 95\n🔄 Bounce From 85\n⚠️ Bullish above 88"
    normalized = normalize_text(text)
    
    print(f"Original:\n{text}\n")
    print(f"Normalized:\n{normalized}")
    
    assert "[BREAKOUT]" in normalized
    assert "[BREAKDOWN]" in normalized
    assert "[REJECTION]" in normalized
    assert "[BOUNCE]" in normalized
    assert "[WARNING]" in normalized
    print("✅ All emoji types successfully normalized")

def test_extract_ticker_sections():
    """Test the section extraction for different message formats."""
    print("\n=== Testing ticker section extraction ===")
    
    for format_name, message in TEST_MESSAGES.items():
        print(f"\nTesting format: {format_name}")
        normalized_text = normalize_text(message)
        sections = extract_ticker_sections(normalized_text)
        
        print(f"Found {len(sections)} ticker sections:")
        for i, section in enumerate(sections):
            print(f"  {i+1}. {section['symbol']}: {section['text'][:50]}...")
        
        # Verify we found the expected number of tickers
        if format_name in ["numbered_with_parenthesis", "numbered_with_period"]:
            assert len(sections) == 2, f"Expected 2 sections for {format_name}, found {len(sections)}"
        elif format_name == "emoji_format":
            assert len(sections) >= 1, f"Expected at least 1 section for {format_name}, found {len(sections)}"
        elif format_name == "multiple_tickers":
            assert len(sections) == 2, f"Expected 2 sections for {format_name}, found {len(sections)}"
    
    print("✅ Ticker section extraction completed")

def test_extract_signals():
    """Test signal extraction from ticker sections."""
    print("\n=== Testing signal extraction from sections ===")
    
    for format_name, message in TEST_MESSAGES.items():
        print(f"\nTesting format: {format_name}")
        normalized_text = normalize_text(message)
        sections = extract_ticker_sections(normalized_text)
        
        for section in sections:
            symbol = section['symbol']
            signals = extract_signal_from_section(section)
            
            print(f"Signals for {symbol}: {len(signals)}")
            for i, signal in enumerate(signals):
                print(f"  Signal {i+1}: {signal.category.name} {signal.comparison.name} {signal.trigger}, targets={signal.targets}")
            
            # Verify we found at least one signal
            assert len(signals) > 0, f"No signals found for {symbol} in {format_name}"
    
    print("✅ Signal extraction completed")

def test_extract_bias():
    """Test bias extraction from ticker sections."""
    print("\n=== Testing bias extraction from sections ===")
    
    for format_name, message in TEST_MESSAGES.items():
        print(f"\nTesting format: {format_name}")
        normalized_text = normalize_text(message)
        sections = extract_ticker_sections(normalized_text)
        
        for section in sections:
            symbol = section['symbol']
            bias = extract_bias_from_section(section)
            
            if bias:
                print(f"Bias for {symbol}: {bias.direction.name} {bias.condition.name} {bias.price}")
            else:
                print(f"No bias found for {symbol}")
    
    print("✅ Bias extraction completed")

def test_process_ticker_sections():
    """Test the complete processing of ticker sections."""
    print("\n=== Testing complete section processing ===")
    
    for format_name, message in TEST_MESSAGES.items():
        print(f"\nTesting format: {format_name}")
        normalized_text = normalize_text(message)
        sections = extract_ticker_sections(normalized_text)
        
        if not sections:
            print(f"No sections found for {format_name}")
            continue
        
        ticker_setups = process_ticker_sections(sections)
        
        print(f"Found {len(ticker_setups)} ticker setups:")
        for setup in ticker_setups:
            print(f"  {setup.symbol}: {len(setup.signals)} signals, bias={setup.bias is not None}")
            
            # Verify the ticker symbol matches for each setup
            assert setup.symbol in [s['symbol'] for s in sections], f"Ticker mismatch: {setup.symbol}"
    
    print("✅ Complete section processing completed")

def test_parse_setup_message():
    """Test the complete message parsing using our new approach."""
    print("\n=== Testing complete message parsing ===")
    
    for format_name, message in TEST_MESSAGES.items():
        print(f"\nTesting format: {format_name}")
        
        # Parse the complete message
        setup_message = parse_setup_message(message, source="test")
        
        # Check the date
        if setup_message.date != date.today():
            print(f"Date: {setup_message.date}")
        
        # Check the ticker setups
        print(f"Found {len(setup_message.setups)} ticker setups:")
        for setup in setup_message.setups:
            print(f"  {setup.symbol}: {len(setup.signals)} signals, bias={setup.bias is not None}")
            for i, signal in enumerate(setup.signals):
                print(f"    Signal {i+1}: {signal.category.name} {signal.comparison.name} {signal.trigger}, targets={signal.targets}")
            
            if setup.bias:
                print(f"    Bias: {setup.bias.direction.name} {setup.bias.condition.name} {setup.bias.price}")
    
    # Test specific message formats we know should work
    print("\nVerification test - SPY and AAPL:")
    setup_message = parse_setup_message(TEST_MESSAGES["multiple_tickers"], source="test")
    
    # Verify tickers
    tickers = [setup.symbol for setup in setup_message.setups]
    print(f"Tickers found: {tickers}")
    assert "SPY" in tickers, "SPY ticker not found"
    assert "AAPL" in tickers, "AAPL ticker not found"
    
    # Verify signals
    for setup in setup_message.setups:
        if setup.symbol == "SPY":
            assert len(setup.signals) > 0, "No signals found for SPY"
            assert setup.signals[0].category == SignalCategory.BREAKDOWN, f"Wrong signal for SPY: {setup.signals[0].category.name}"
            assert setup.signals[0].trigger == 500.5, f"Wrong trigger price for SPY: {setup.signals[0].trigger}"
        elif setup.symbol == "AAPL":
            assert len(setup.signals) > 0, "No signals found for AAPL"
            assert setup.signals[0].category == SignalCategory.BREAKOUT, f"Wrong signal for AAPL: {setup.signals[0].category.name}"
            assert setup.signals[0].trigger == 180.0, f"Wrong trigger price for AAPL: {setup.signals[0].trigger}"
    
    print("✅ Complete message parsing completed")

def main():
    """Main function to run all tests."""
    print("Testing Multi-Ticker Parser")
    
    tests = [
        test_normalize_text,
        test_extract_ticker_sections,
        test_extract_signals,
        test_extract_bias,
        test_process_ticker_sections,
        test_parse_setup_message
    ]
    
    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test failed: {test_func.__name__}")
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main()
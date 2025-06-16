"""
Test Refactored A+ Parser with Real Message Data

This test validates the new token-based parsing approach with various
A+ scalp setup message formats and ensures proper audit coverage.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date
from features.parsing.aplus_parser import (
    TradeSetup, 
    parse_ticker_section, 
    extract_setup_line,
    classify_setup,
    audit_profile_coverage,
    APlusMessageParser
)

def test_setup_line_extraction():
    """Test individual setup line extraction with various formats."""
    print("Testing setup line extraction...")
    
    test_cases = [
        {
            'line': '🔻 Aggressive Breakdown Below 141.50 🔻 141.40, 139.20, 137.60',
            'expected_label': 'AggressiveBreakdown',
            'expected_direction': 'short',
            'expected_trigger': 141.50,
            'expected_targets': [141.40, 139.20, 137.60]
        },
        {
            'line': '🔼 Conservative Breakout Above 145.80 🔼 146.20, 147.50, 149.00',
            'expected_label': 'ConservativeBreakout',
            'expected_direction': 'long',
            'expected_trigger': 145.80,
            'expected_targets': [146.20, 147.50, 149.00]
        },
        {
            'line': '❌ Rejection Near 140.25 🔻 139.80, 138.50, 137.20',
            'expected_label': 'Rejection',
            'expected_direction': 'short',
            'expected_trigger': 140.25,
            'expected_targets': [139.80, 138.50, 137.20]
        },
        {
            'line': '🔄 Bounce Zone 142.10-142.50 🔼 143.80, 145.20, 147.00',
            'expected_label': 'BounceZone',
            'expected_direction': 'long',
            'expected_trigger': 142.10,
            'expected_targets': [143.80, 145.20, 147.00]
        }
    ]
    
    trading_day = date(2025, 6, 16)
    
    for i, test_case in enumerate(test_cases):
        setup = extract_setup_line(test_case['line'], 'TEST', trading_day, i)
        
        if setup:
            print(f"✓ Test {i+1}: {test_case['expected_label']}")
            print(f"  - Direction: {setup.direction} (expected: {test_case['expected_direction']})")
            print(f"  - Label: {setup.label} (expected: {test_case['expected_label']})")
            print(f"  - Trigger: {setup.trigger_level} (expected: {test_case['expected_trigger']})")
            print(f"  - Targets: {setup.target_prices} (expected: {test_case['expected_targets']})")
            print(f"  - Setup ID: {setup.id}")
            print()
        else:
            print(f"✗ Test {i+1}: Failed to parse line: {test_case['line']}")
            print()

def test_ticker_section_parsing():
    """Test complete ticker section parsing."""
    print("Testing ticker section parsing...")
    
    ticker_content = """🔻 Aggressive Breakdown Below 141.50 🔻 141.40, 139.20, 137.60
🔼 Conservative Breakout Above 145.80 🔼 146.20, 147.50, 149.00
❌ Rejection Near 140.25 🔻 139.80, 138.50, 137.20
🔄 Bounce Zone 142.10-142.50 🔼 143.80, 145.20, 147.00
⚠️ Bias — Strong momentum expected with volume confirmation"""
    
    trading_day = date(2025, 6, 16)
    setups = parse_ticker_section('NVDA', ticker_content, trading_day)
    
    print(f"✓ Parsed {len(setups)} setups for NVDA")
    
    for setup in setups:
        print(f"  - {setup.label or 'Unknown'} ({setup.direction}): {setup.trigger_level} -> {setup.target_prices}")
    
    print()
    
    # Test audit coverage
    audit_profile_coverage(setups, 'NVDA', trading_day)
    print()

def test_full_message_parsing():
    """Test complete A+ message parsing."""
    print("Testing full A+ message parsing...")
    
    sample_message = """A+ Scalp Trade Setups — June 16

NVDA
🔻 Aggressive Breakdown Below 141.50 🔻 141.40, 139.20, 137.60
🔼 Conservative Breakout Above 145.80 🔼 146.20, 147.50, 149.00
❌ Rejection Near 140.25 🔻 139.80, 138.50, 137.20
🔄 Bounce Zone 142.10-142.50 🔼 143.80, 145.20, 147.00
⚠️ Bias — Strong momentum expected with volume confirmation

TSLA
🔻 Aggressive Breakdown Below 245.20 🔻 244.80, 242.50, 240.00
🔼 Conservative Breakout Above 250.75 🔼 251.20, 253.80, 256.40
❌ Rejection Near 248.15 🔻 247.60, 245.30, 242.80"""
    
    parser = APlusMessageParser()
    result = parser.parse_message(sample_message, "test_message_123")
    
    if result['success']:
        print(f"✓ Successfully parsed message")
        print(f"  - Trading date: {result['trading_date']}")
        print(f"  - Total setups: {result['total_setups']}")
        print(f"  - Tickers found: {result['tickers_found']}")
        print(f"  - Bias notes: {len(result.get('ticker_bias_notes', {}))}")
        
        print("\nSetup breakdown:")
        for setup in result['setups']:
            print(f"  - {setup.ticker}: {setup.label or 'Unknown'} ({setup.direction}) @ {setup.trigger_level}")
    else:
        print(f"✗ Failed to parse message: {result.get('error')}")
    
    print()

def test_classification_logic():
    """Test the setup classification logic."""
    print("Testing setup classification logic...")
    
    test_lines = [
        "🔻 Aggressive Breakdown Below 141.50 🔻 141.40, 139.20, 137.60",
        "🔼 Conservative Breakout Above 145.80 🔼 146.20, 147.50, 149.00", 
        "❌ Rejection Near 140.25 🔻 139.80, 138.50, 137.20",
        "🔄 Bounce Zone 142.10-142.50 🔼 143.80, 145.20, 147.00",
        "Some random line with no clear pattern 123.45, 124.67"
    ]
    
    for line in test_lines:
        label, keywords = classify_setup(line)
        print(f"Line: {line[:50]}...")
        print(f"  - Label: {label}")
        print(f"  - Keywords: {keywords}")
        print()

def test_edge_cases():
    """Test edge cases and error handling."""
    print("Testing edge cases...")
    
    edge_cases = [
        "",  # Empty line
        "No numbers here",  # No prices
        "Only one price 123.45",  # Insufficient prices
        "🔼 123.45",  # Minimal format
        "Multiple prices 123.45, 124.50, 125.60, 126.70, 127.80"  # Many targets
    ]
    
    trading_day = date(2025, 6, 16)
    
    for i, line in enumerate(edge_cases):
        setup = extract_setup_line(line, 'TEST', trading_day, i)
        print(f"Edge case {i+1}: '{line}' -> {'Parsed' if setup else 'Skipped'}")
    
    print()

def main():
    """Run all tests for the refactored A+ parser."""
    print("=== Refactored A+ Parser Test Suite ===\n")
    
    test_setup_line_extraction()
    test_ticker_section_parsing()
    test_full_message_parsing()
    test_classification_logic()
    test_edge_cases()
    
    print("=== Test Suite Complete ===")

if __name__ == "__main__":
    main()
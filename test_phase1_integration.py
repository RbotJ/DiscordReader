#!/usr/bin/env python3
"""
Test Phase 1 Integration - Store and Setup Converter

Validates that the refactored store.py works correctly with the new
TradeSetup dataclass and setup_converter service.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from features.parsing.aplus_parser import get_aplus_parser
from features.parsing.store import ParsingStore
from features.parsing.setup_converter import convert_model_to_dict

def test_message_content():
    """Test with real A+ message content."""
    message_content = """
NVDA
💥 Overnight Gap Fill 506 - scalp setup
⚡ Gap Down scalp 498.50
🚀 Flag Break 510
🎯 Targets: 512, 515, 518

SPY
⚡ Breakout above 435
🎯 Targets: 436, 437, 438
    """
    
    return {
        'message_id': 'test_message_123',
        'content': message_content,
        'channel_id': 'test_channel',
        'author_id': 'test_user',
        'timestamp': '2025-06-16T12:00:00Z'
    }

def test_phase1_data_flow():
    """Test the complete data flow from parsing to storage."""
    print("Testing Phase 1 data flow integration...")
    
    # Get test message
    raw_message = test_message_content()
    message_id = raw_message['message_id']
    content = raw_message['content']
    
    print(f"1. Parsing message: {message_id}")
    
    # Parse message using refactored parser
    try:
        parser = get_aplus_parser()
        result = parser.parse_message(content, message_id)
        
        if not result.get('success', False):
            print(f"   ✗ Parsing failed: {result.get('error', 'Unknown error')}")
            return False
            
        parsed_setups = result.get('setups', [])
        print(f"   ✓ Parser extracted {len(parsed_setups)} setups")
        
        for setup in parsed_setups:
            print(f"   - {setup.ticker}: {setup.label} (trigger: {setup.trigger_level})")
    except Exception as e:
        print(f"   ✗ Parsing failed: {e}")
        return False
    
    # Test store integration
    print(f"2. Testing store integration...")
    try:
        store = ParsingStore()
        
        # Store parsed setups using new method signature
        created_setups, created_levels = store.store_parsed_message(
            message_id=message_id,
            parsed_setups=parsed_setups,
            trading_day=date.today(),
            ticker_bias_notes={'NVDA': 'Bullish gap setup', 'SPY': 'Breakout momentum'}
        )
        
        print(f"   ✓ Stored {len(created_setups)} setups and {len(created_levels)} levels")
        
        # Test data conversion
        for setup in created_setups:
            try:
                setup_dict = convert_model_to_dict(setup)
                print(f"   - {setup_dict.get('ticker')}: {setup_dict.get('label')} converted successfully")
            except Exception as e:
                print(f"   ✗ Conversion failed for {setup.ticker}: {e}")
                
    except Exception as e:
        print(f"   ✗ Store integration failed: {e}")
        return False
    
    print("Phase 1 integration test completed successfully!")
    return True

if __name__ == "__main__":
    test_phase1_data_flow()
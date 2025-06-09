#!/usr/bin/env python3
"""
Debug script to test A+ parser with real message content
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from features.parsing.aplus_parser import AplusParser
from datetime import datetime

def test_real_message():
    """Test parser with real A+ message content from database"""
    
    # Real message content from the database
    message_content = """A+ Scalp Trade Setups – May 28, 2025

SPY
❌ Rejection Short Near 592.09 🔻 589.80, 586.60, 583.30 
🔻 Aggressive Breakdown Below 588.11 🔻 585.50, 582.75, 579.60 
🔻 Conservative Breakdown Below 583.25 🔻 579.80, 575.40, 571.90 
🔼 Aggressive Breakout Above 592.10 🔼 595.00, 597.40, 600.25 
🔼 Conservative Breakout Above 595.05 🔼 598.90, 602.00, 606.20 
🔄 Bounce Zone: 586.25–587.00
⚠️ Bias - most likely to open with a rejection off 592.09 — breakdown below 588.11 will likely trigger a fast flush to 585.50 —wait for volume confirmation and 2-candle close under for cleaner entry

NVDA
🔻 Aggressive Breakdown Below 134.30 🔻 132.90, 131.50, 130.20 
🔻 Conservative Breakdown Below 132.25 🔻 130.20, 128.10, 126.40 
🔄 Bounce Zone 130.20–130.80 🔼 Target 132.25, 134.30 
🔼 Aggressive Breakout Above 137.45 🔼 139.20, 141.50, 143.10 
🔼 Conservative Breakout Above 139.20 🔼 141.50, 143.10, 145.00 
❌ Rejection Near 137.45 🔻 135.60, 133.80, 132.25
⚠️ Bearish bias under 134.30. VPVR shows volume vacuum under 132. Price struggling to reclaim 137.45 and upside only continues above 139.20 with volume — if earnings aren't great this stock is getting very heavy technically right now

TSLA
❌ Rejection Short Near 370.30 🔻 367.50, 364.80, 362.00
🔻 Aggressive Breakdown Below 362.75 🔻 359.90, 357.40, 353.80
🔻 Conservative Breakdown Below 359.00 🔻 355.80, 353.10, 350.00
🔼 Aggressive Breakout Above 372.80 🔼 376.30, 379.60, 382.00
🔼 Conservative Breakout Above 376.30 🔼 379.60, 382.00, 386.00
🔄 Bounce From 353.10 🔼 357.40, 360.80, 362.75
⚠️ Bullish bias while price is above 362.50 —  breakout continuation in play — dips are likely to get bought unless 360 breaks

@everyone"""

    message_data = {
        'message_id': '1377278128598155294',
        'content': message_content,
        'channel_id': '1372012942848954388',
        'timestamp': datetime.now(),
        'author_id': '808743496341127200'
    }
    
    print("=" * 80)
    print("TESTING A+ PARSER WITH REAL MESSAGE")
    print("=" * 80)
    print(f"Message ID: {message_data['message_id']}")
    print(f"Content length: {len(message_content)} characters")
    print()
    
    # Initialize parser
    parser = AplusParser()
    
    try:
        # Parse the message
        print("Attempting to parse message...")
        result = parser.parse_message(message_data)
        
        if result:
            print("✅ PARSING SUCCESSFUL!")
            print(f"Number of setups found: {len(result)}")
            print()
            
            for i, setup in enumerate(result, 1):
                print(f"Setup {i}:")
                print(f"  - Ticker: {setup.get('ticker')}")
                print(f"  - Setup Type: {setup.get('setup_type')}")
                print(f"  - Direction: {setup.get('direction')}")
                print(f"  - Bias Note: {setup.get('bias_note', 'N/A')}")
                print(f"  - Levels: {len(setup.get('levels', []))}")
                print()
        else:
            print("❌ PARSING FAILED - No setups returned")
            
    except Exception as e:
        print(f"❌ PARSING ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_message()
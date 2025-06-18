#!/usr/bin/env python3
"""
Debug script to analyze why specific A+ messages are failing to parse.
"""

import re
from features.parsing.aplus_parser import APlusMessageParser
from features.parsing.service import ParsingService
from datetime import datetime

def test_message_validation():
    """Test validation for the 3 unparsed messages."""
    
    parser = APlusMessageParser()
    
    # The 3 unparsed messages from database
    messages = [
        {
            'id': '1380536097012060342',
            'content': """A+ Scalp Trade Setups — Jun 6 

SPY
❌ Rejection Short 598.10 🔻 596.35, 594.20, 591.75
🔻 Aggressive Breakdown 595.20 🔻 593.35, 591.75, 589.10
🔻 Conservative Breakdown 591.75 🔻 589.10, 586.60, 583.95
🔼 Aggressive Breakout 598.50 🔼 600.20, 602.10, 603.85
🔼 Conservative Breakout 600.20 🔼 602.10, 603.85, 605.75
🔄 Bounce 589.10–590.40 🔼 591.75, 594.20, 596.35
⚠️ Bias: Upside move in play as long as 595.20 holds but 598.10 may be tough to break through  — breakout needs high volume push above 600.20 to confirm bull trend continuation

NVDA
❌ Rejection Short 143.35 🔻 141.70, 139.90, 137.80
🔻 Aggressive Breakdown 140.75 🔻 139.15, 137.60, 135.40
🔻 Conservative Breakdown 139.15 🔻 137.60, 135.40, 133.10
🔼 Aggressive Breakout 142.10 🔼 143.40, 144.75, 146.20
🔼 Conservative Breakout 143.40 🔼 144.75, 146.20, 148.10
🔄 Bounce 137.25–138.20 🔼 139.15, 140.75, 141.70
⚠️ Bias: Reversal bounce forming — 140.75 must hold as base for continuation — if 142.10 breaks with volume, expect a strong push up

TSLA
❌ Rejection Short 304.50 🔻 298.60, 295.10, 291.40
🔻 Aggressive Breakdown 292.75 🔻 288.90, 285.60, 281.50
🔻 Conservative Breakdown 288.90 🔻 285.60, 281.50, 277.80
🔼 Aggressive Breakout 298.95 🔼 303.40, 308.10, 312.75
🔼 Conservative Breakout 303.40 🔼 308.10, 312.75, 318.25
🔄 Bounce 284.80–286.50 🔼 288.90, 292.75, 295.10
⚠️ Bias: Price still heavy from broader breakdown but relief bounce off 285 zone looks good — 298.95 must flip with volume for relief trend to continue

@everyone"""
        },
        {
            'id': '1379096469340164237',
            'content': """A+ Scalp Trade Setups — Jun 2

SPY
❌ Rejection Short Near 591.82 🔻 589.10, 586.20, 583.40 
🔻 Aggressive Breakdown Below 586.01 🔻 583.30, 579.80, 576.75 
🔻 Conservative Breakdown Below 583.00 🔻 579.80, 576.75, 573.60 
🔼 Aggressive Breakout Above 589.85 🔼 591.80, 593.90, 596.00 
🔼 Conservative Breakout Above 592.15 🔼 593.90, 596.00, 599.30 
🔄 Bounce Zone 579.40–580.20 🔼 583.00, 586.20, 589.00
⚠️ Bias: watching for weakness rejecting from 591.80–592.15 zone 
—  breakdown retest is more likely


NVDA
❌ Rejection Near 135.95 🔻 134.22, 133.10, 131.88 
🔻 Aggressive Breakdown Below 133.30 🔻 131.88, 130.41  {edited}
🔻 Conservative Breakdown Below 131.88 🔻 130.41, 128.30, 126.65 
🔼 Aggressive Breakout Above 135.95 🔼 137.40, 138.88, 140.50 
🔼 Conservative Breakout Above 138.88 🔼 140.50, 142.35, 144.22 
🔄 Bounce Zone 130.41–131.00 🔼 133.10, 134.10, 135.20
⚠️ Bias: Leaning bearish under 135.95 
— Breakdown under 134.10 likely to test 130s

TSLA
❌ Rejection Short Near 347.33 🔻 342.40, 339.70, 336.10 
🔻 Aggressive Breakdown Below 339.50 🔻 336.10, 332.75, 329.80 
🔻 Conservative Breakdown Below 336.00 🔻 332.75, 329.80, 325.10 
🔼 Aggressive Breakout Above 347.34 🔼 350.00, 352.80, 355.50 
🔼 Conservative Breakout Above 350.01 🔼 352.80, 355.50, 359.20 
🔄 Bounce Zone: 332.75–336.00 🔼 339.70, 342.40, 347.33
⚠️ Bias: Breakdown is in play below 347 
— price has to reclaim above 350 to shift short-term trend

@everyone
❤️=🐐"""
        },
        {
            'id': '1377278128598155294',
            'content': """A+ Scalp Trade Setups – May 28, 2025

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
        }
    ]
    
    print("=== DEBUGGING UNPARSED A+ MESSAGES ===")
    
    for msg in messages:
        print(f"\n--- Message {msg['id']} ---")
        content = msg['content']
        
        # Test header pattern matching
        header_match = parser.header_pattern.search(content)
        print(f"Header pattern match: {bool(header_match)}")
        if header_match:
            print(f"Matched text: '{header_match.group()}'")
        
        # Test validation method
        is_valid = parser.validate_message(content)
        print(f"validate_message() result: {is_valid}")
        
        # Test first line analysis
        first_line = content.split('\n')[0]
        print(f"First line: '{first_line}'")
        
        # Check for punctuation variations
        if "—" in first_line:
            print("Contains em dash (—)")
        if "–" in first_line:
            print("Contains en dash (–)")
        if "-" in first_line:
            print("Contains hyphen (-)")
            
        # Test with parsing service
        try:
            service = ParsingService()
            should_parse = service.should_parse_message(content)
            print(f"should_parse_message() result: {should_parse}")
            
            if should_parse:
                print("Attempting to parse...")
                result = service.parse_aplus_message(content, msg['id'])
                print(f"Parse result: {result.get('success', False)}")
                if not result.get('success'):
                    print(f"Parse error: {result.get('error', 'Unknown')}")
            else:
                print("Parsing service says should NOT parse")
                
        except Exception as e:
            print(f"Error during parsing test: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_message_validation()
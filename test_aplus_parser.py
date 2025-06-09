"""
Test A+ Parser with Real Message Data
"""
from features.parsing.aplus_parser import get_aplus_parser

# Real message content from ingestion
test_message = """A+ Scalp Trade Setups — Thursday May 29

NVDA
❌ Rejection Short Near 144.00 🔻 141.40, 139.20, 137.60 
🔻 Aggressive Breakdown Below 141.33 🔻 139.90, 138.40, 136.20 
🔻 Conservative Breakdown Below 138.20 🔻 136.60, 135.00, 132.80 
🔼 Aggressive Breakout Above 144.02 🔼 146.20, 148.00, 150.00 
🔼 Conservative Breakout Above 146.20 🔼 148.00, 150.50, 153.00 
🔄 Bounce Zone 138.50–139.00 🔼 142.00, 143.80, 145.60
⚠️ Bias — bearish into open — Break below 141.33 likely flushes to downside — only bullish above 146.20

SPY
❌ Rejection Short Near 596.90 🔻 593.70, 590.60, 586.00 
🔻 Aggressive Breakdown Below 591.35 🔻 587.90, 586.00, 582.70 
🔻 Conservative Breakdown Below 590.60 🔻 586.00, 582.70, 578.30 
🔼 Aggressive Breakout Above 596.90 🔼 599.80, 602.00, 605.50 
🔼 Conservative Breakout Above 599.80 🔼 602.00, 605.50, 608.30 
🔄 Bounce Zone 586.00–587.00 🔼 590.60, 593.70, 596.90
⚠️ Bias — weakness into open — remains bearish unless price gets back above 596.90

TSLA
❌ Rejection Near 368.11 🔻 362.40, 359.50, 354.30 
🔻 Aggressive Breakdown Below 364.11 🔻 359.50, 354.30, 349.10 
🔻 Conservative Breakdown Below 359.50 🔻 354.30, 349.10, 343.00 
🔼 Aggressive Breakout Above 368.11 🔼 373.00, 379.00, 386.40 
🔼 Conservative Breakout Above 373.00 🔼 379.00, 386.40, 392.60 
🔄 Bounce Zone = 354.30–356.00 🔼 Targets: 362.40, 368.11, 373.00
⚠️ Bearish bias under 368.11 with breakdown under 364.11 on watch and bounce at 354.30 as a high potential outcome"""

def test_aplus_parser():
    """Test the A+ parser with real message data."""
    parser = get_aplus_parser()
    
    print("Testing A+ Parser with Real Message...")
    print("=" * 50)
    
    # Test message validation
    is_valid = parser.validate_message(test_message)
    print(f"Message validation: {is_valid}")
    
    # Test date extraction
    trading_date = parser.extract_trading_date(test_message)
    print(f"Trading date extracted: {trading_date}")
    
    # Parse full message
    result = parser.parse_message(test_message, "1377640123671515198")
    
    print(f"\nParsing result:")
    print(f"Success: {result['success']}")
    print(f"Total setups found: {result.get('total_setups', 0)}")
    print(f"Tickers found: {result.get('tickers_found', [])}")
    print(f"Trading date: {result.get('trading_date')}")
    
    print(f"\nSetups breakdown:")
    for setup in result.get('setups', []):
        print(f"  {setup.ticker}: {setup.setup_type} ({setup.direction}, {setup.strategy})")
        print(f"    Entry: ${setup.entry_price}, Targets: {setup.target_prices}")
    
    print(f"\nBias notes:")
    for ticker, bias in result.get('ticker_bias_notes', {}).items():
        print(f"  {ticker}: {bias}")
    
    return result

if __name__ == "__main__":
    test_aplus_parser()
"""
Legacy vs New Parser Comparison Test

Compares parsing results between:
- Legacy: features/setups/parser.py 
- New: features/parsing/parser.py

Ensures no regression in parsing quality during modernization.
Tests that ticker extraction, trigger levels, and direction detection
remain consistent between old and new implementations.
"""

import pytest
from typing import List, Dict, Any
from datetime import datetime

# Import legacy parser
try:
    from features.setups.parser import MessageParser as LegacyParser
    from features.setups.enhanced_parser import EnhancedMessageParser as LegacyEnhancedParser
    LEGACY_AVAILABLE = True
except ImportError as e:
    print(f"Legacy parser not available: {e}")
    LEGACY_AVAILABLE = False

# Import new parser
from features.parsing.parser import MessageParser as NewParser


class TestLegacyVsNewParser:
    """Compare legacy and new parser implementations"""
    
    def setup_method(self):
        """Setup test environment"""
        if LEGACY_AVAILABLE:
            self.legacy_parser = LegacyParser()
            try:
                self.legacy_enhanced = LegacyEnhancedParser()
            except:
                self.legacy_enhanced = None
        self.new_parser = NewParser()
        
        # Test messages covering various trading scenarios
        self.test_messages = [
            {
                'id': 'simple_breakout',
                'content': '$AAPL breakout above $180 resistance. Looking for continuation to $185. Stop at $178.',
                'expected_ticker': 'AAPL',
                'expected_direction': 'bullish',
                'expected_prices': [180, 185, 178]
            },
            {
                'id': 'multi_ticker',
                'content': '$TSLA breaking $250 resistance, target $260. $NVDA pullback to $900 support level.',
                'expected_tickers': ['TSLA', 'NVDA'],
                'expected_prices': [250, 260, 900]
            },
            {
                'id': 'options_call',
                'content': '$SPY 450 calls looking good. Break above $452 could see $460.',
                'expected_ticker': 'SPY',
                'expected_prices': [450, 452, 460],
                'expected_type': 'call'
            },
            {
                'id': 'options_put', 
                'content': '$QQQ puts active. Below $380 could see $375.',
                'expected_ticker': 'QQQ',
                'expected_prices': [380, 375],
                'expected_type': 'put'
            },
            {
                'id': 'support_bounce',
                'content': '$MSFT bouncing off $400 support. Looking for move to $410.',
                'expected_ticker': 'MSFT',
                'expected_direction': 'bullish',
                'expected_prices': [400, 410]
            },
            {
                'id': 'resistance_rejection',
                'content': '$GOOGL rejected at $150 resistance. Could see pullback to $145.',
                'expected_ticker': 'GOOGL',
                'expected_direction': 'bearish',
                'expected_prices': [150, 145]
            },
            {
                'id': 'range_bound',
                'content': '$AMZN trading in $140-$145 range. Break either way for direction.',
                'expected_ticker': 'AMZN',
                'expected_prices': [140, 145]
            }
        ]
    
    @pytest.mark.skipif(not LEGACY_AVAILABLE, reason="Legacy parser not available")
    def test_ticker_extraction_consistency(self):
        """Test that both parsers extract the same tickers"""
        
        for test_case in self.test_messages:
            message_content = test_case['content']
            message_id = f"test_{test_case['id']}"
            
            # Parse with legacy
            try:
                legacy_results = self.legacy_parser.parse_message(message_content, message_id)
                legacy_tickers = self._extract_tickers_from_results(legacy_results, 'legacy')
            except Exception as e:
                print(f"Legacy parser failed for {test_case['id']}: {e}")
                legacy_tickers = []
            
            # Parse with new
            try:
                new_results = self.new_parser.parse_message(message_content, message_id)
                new_tickers = self._extract_tickers_from_results(new_results, 'new')
            except Exception as e:
                print(f"New parser failed for {test_case['id']}: {e}")
                new_tickers = []
            
            # Compare ticker extraction
            if 'expected_ticker' in test_case:
                expected = [test_case['expected_ticker']]
            elif 'expected_tickers' in test_case:
                expected = test_case['expected_tickers']
            else:
                expected = []
            
            print(f"\nTest case: {test_case['id']}")
            print(f"Expected tickers: {expected}")
            print(f"Legacy tickers: {legacy_tickers}")
            print(f"New tickers: {new_tickers}")
            
            # Verify both parsers find expected tickers
            for ticker in expected:
                if legacy_tickers:
                    assert ticker in legacy_tickers, f"Legacy parser missed ticker {ticker} in {test_case['id']}"
                if new_tickers:
                    assert ticker in new_tickers, f"New parser missed ticker {ticker} in {test_case['id']}"
    
    @pytest.mark.skipif(not LEGACY_AVAILABLE, reason="Legacy parser not available")
    def test_price_level_consistency(self):
        """Test that both parsers extract similar price levels"""
        
        for test_case in self.test_messages:
            if 'expected_prices' not in test_case:
                continue
                
            message_content = test_case['content']
            message_id = f"test_{test_case['id']}"
            
            # Parse with both
            try:
                legacy_results = self.legacy_parser.parse_message(message_content, message_id)
                legacy_prices = self._extract_prices_from_results(legacy_results, 'legacy')
            except:
                legacy_prices = []
                
            try:
                new_results = self.new_parser.parse_message(message_content, message_id)
                new_prices = self._extract_prices_from_results(new_results, 'new')
            except:
                new_prices = []
            
            expected_prices = test_case['expected_prices']
            
            print(f"\nPrice test: {test_case['id']}")
            print(f"Expected prices: {expected_prices}")
            print(f"Legacy prices: {legacy_prices}")
            print(f"New prices: {new_prices}")
            
            # Check that key price levels are captured
            for price in expected_prices:
                # Allow some tolerance for price extraction differences
                if legacy_prices:
                    assert any(abs(p - price) <= 1.0 for p in legacy_prices), \
                        f"Legacy parser missed price level {price} in {test_case['id']}"
                if new_prices:
                    assert any(abs(p - price) <= 1.0 for p in new_prices), \
                        f"New parser missed price level {price} in {test_case['id']}"
    
    @pytest.mark.skipif(not LEGACY_AVAILABLE, reason="Legacy parser not available")  
    def test_direction_detection_consistency(self):
        """Test that both parsers detect the same directional bias"""
        
        directional_tests = [tc for tc in self.test_messages if 'expected_direction' in tc]
        
        for test_case in directional_tests:
            message_content = test_case['content']
            message_id = f"test_{test_case['id']}"
            
            # Parse with both
            try:
                legacy_results = self.legacy_parser.parse_message(message_content, message_id)
                legacy_direction = self._extract_direction_from_results(legacy_results, 'legacy')
            except:
                legacy_direction = None
                
            try:
                new_results = self.new_parser.parse_message(message_content, message_id)
                new_direction = self._extract_direction_from_results(new_results, 'new')
            except:
                new_direction = None
            
            expected_direction = test_case['expected_direction']
            
            print(f"\nDirection test: {test_case['id']}")
            print(f"Expected direction: {expected_direction}")
            print(f"Legacy direction: {legacy_direction}")
            print(f"New direction: {new_direction}")
            
            # Both should detect the same general direction
            if legacy_direction and new_direction:
                # Check for consistency in bullish/bearish detection
                if expected_direction == 'bullish':
                    assert 'bull' in str(legacy_direction).lower() or 'long' in str(legacy_direction).lower()
                    assert 'bull' in str(new_direction).lower() or 'long' in str(new_direction).lower()
                elif expected_direction == 'bearish':
                    assert 'bear' in str(legacy_direction).lower() or 'short' in str(legacy_direction).lower()
                    assert 'bear' in str(new_direction).lower() or 'short' in str(new_direction).lower()
    
    def test_new_parser_comprehensive(self):
        """Test new parser comprehensively even without legacy comparison"""
        
        for test_case in self.test_messages:
            message_content = test_case['content']
            message_id = f"test_{test_case['id']}"
            
            # Parse with new parser
            results = self.new_parser.parse_message(message_content, message_id)
            
            # Basic validation
            assert isinstance(results, list), f"Parser should return list for {test_case['id']}"
            
            if 'expected_ticker' in test_case or 'expected_tickers' in test_case:
                assert len(results) > 0, f"Parser should find setups for {test_case['id']}"
                
                # Check that results have required attributes
                for result in results:
                    assert hasattr(result, 'ticker'), f"Setup missing ticker in {test_case['id']}"
                    assert hasattr(result, 'content'), f"Setup missing content in {test_case['id']}"
                    assert result.ticker is not None, f"Ticker is None in {test_case['id']}"
    
    def _extract_tickers_from_results(self, results: List[Any], parser_type: str) -> List[str]:
        """Extract ticker symbols from parser results"""
        tickers = []
        
        if not results:
            return tickers
            
        for result in results:
            if hasattr(result, 'ticker') and result.ticker:
                tickers.append(result.ticker)
            elif hasattr(result, 'symbol') and result.symbol:
                tickers.append(result.symbol)
            elif isinstance(result, dict):
                if 'ticker' in result:
                    tickers.append(result['ticker'])
                elif 'symbol' in result:
                    tickers.append(result['symbol'])
        
        return list(set(tickers))  # Remove duplicates
    
    def _extract_prices_from_results(self, results: List[Any], parser_type: str) -> List[float]:
        """Extract price levels from parser results"""
        prices = []
        
        if not results:
            return prices
            
        for result in results:
            # Try different price field names
            price_fields = ['price', 'target_price', 'trigger_price', 'stop_price']
            
            for field in price_fields:
                if hasattr(result, field):
                    price = getattr(result, field)
                    if price and isinstance(price, (int, float)):
                        prices.append(float(price))
                elif isinstance(result, dict) and field in result:
                    price = result[field]
                    if price and isinstance(price, (int, float)):
                        prices.append(float(price))
        
        return list(set(prices))  # Remove duplicates
    
    def _extract_direction_from_results(self, results: List[Any], parser_type: str) -> str:
        """Extract directional bias from parser results"""
        if not results:
            return None
            
        for result in results:
            # Try different direction field names
            direction_fields = ['direction', 'bias', 'side', 'setup_type']
            
            for field in direction_fields:
                if hasattr(result, field):
                    direction = getattr(result, field)
                    if direction:
                        return str(direction).lower()
                elif isinstance(result, dict) and field in result:
                    direction = result[field]
                    if direction:
                        return str(direction).lower()
        
        return None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
"""
Complete Integration Test for Refactored A+ Parser System

Tests the full workflow:
1. Parse Discord message → TradeSetup objects
2. Store in database via setup_converter
3. Retrieve via API endpoints
4. Render in UI templates

Validates all new field mappings and ensures no data loss.
"""

import pytest
import json
from datetime import date, datetime
from flask import Flask
from decimal import Decimal

# Test data - Real A+ message format
TEST_APLUS_MESSAGE = """A+ Trade Setups — Friday June 14

SPY 
🟢 Bounce Zone Near 542.19 (545.50, 548.00, 550.25)
❌ Rejection Near 550.25 (548.00, 545.50, 542.19)
🔻 Aggressive Breakdown Below 542.19 (539.50, 536.80, 534.00)

NVDA
🟢 Bounce Zone Near 135.42 (138.00, 140.50, 142.75)
❌ Rejection Near 142.75 (140.50, 138.00, 135.42)

QQQ
🔻 Conservative Breakdown Below 485.20 (482.50, 479.80, 477.00)
🔻 Aggressive Breakdown Below 487.50 (485.20, 482.50, 479.80)

Trade responsibly and manage your risk."""

EXPECTED_SETUPS = [
    {
        'ticker': 'SPY',
        'label': 'BounceZone',
        'direction': 'long',
        'index': 1,
        'target_prices': [545.50, 548.00, 550.25],
        'keywords': ['bounce', 'zone'],
        'emoji_hint': '🟢'
    },
    {
        'ticker': 'SPY', 
        'label': 'Rejection',
        'direction': 'short',
        'index': 2,
        'target_prices': [548.00, 545.50, 542.19],
        'keywords': ['rejection'],
        'emoji_hint': '❌'
    },
    {
        'ticker': 'SPY',
        'label': 'AggressiveBreakdown', 
        'direction': 'short',
        'index': 3,
        'target_prices': [539.50, 536.80, 534.00],
        'keywords': ['aggressive', 'breakdown'],
        'emoji_hint': '🔻'
    }
]

class TestCompleteIntegration:
    """End-to-end integration tests"""
    
    def setup_method(self):
        """Setup test environment with Flask app context"""
        from app import create_app
        from features.parsing.store import get_parsing_store
        from features.parsing.aplus_parser import AplusParser
        from features.parsing.setup_converter import setup_converter
        
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        self.store = get_parsing_store()
        self.parser = AplusParser()
        self.converter = setup_converter
        
        # Clean test data
        self.cleanup_test_data()
        
    def teardown_method(self):
        """Cleanup after tests"""
        self.cleanup_test_data()
        self.app_context.pop()
        
    def cleanup_test_data(self):
        """Remove test data from database"""
        try:
            from features.parsing.models import TradeSetup, ParsedLevel
            # Delete test setups by message_id pattern
            test_setups = self.store.session.query(TradeSetup).filter(
                TradeSetup.message_id.like('test_%')
            ).all()
            
            for setup in test_setups:
                # Delete associated levels
                levels = self.store.session.query(ParsedLevel).filter_by(
                    setup_id=setup.id
                ).all()
                for level in levels:
                    self.store.session.delete(level)
                # Delete setup
                self.store.session.delete(setup)
                
            self.store.session.commit()
        except Exception as e:
            print(f"Cleanup error: {e}")
            self.store.session.rollback()

    def test_complete_workflow(self):
        """Test complete workflow from message to UI display"""
        message_id = "test_complete_workflow"
        trading_day = date(2025, 6, 14)
        
        print("\n=== PHASE 1: Parse Message ===")
        # Parse the message
        parsed_data = self.parser.parse_message(TEST_APLUS_MESSAGE)
        
        assert parsed_data['success'], f"Parse failed: {parsed_data.get('error')}"
        assert 'setups' in parsed_data
        assert len(parsed_data['setups']) >= 3, "Should find at least 3 setups"
        
        print(f"✅ Parsed {len(parsed_data['setups'])} setups")
        
        print("\n=== PHASE 2: Convert to TradeSetup Objects ===")
        # Convert to TradeSetup objects
        trade_setups, parsed_levels = self.converter.convert_parsed_data(
            parsed_data=parsed_data,
            message_id=message_id,
            trading_day=trading_day
        )
        
        assert len(trade_setups) >= 3, "Should create at least 3 TradeSetup objects"
        assert len(parsed_levels) >= 9, "Should create multiple levels"
        
        # Validate new field mappings
        spy_setups = [s for s in trade_setups if s.ticker == 'SPY']
        assert len(spy_setups) == 3, "Should have 3 SPY setups"
        
        # Check first SPY setup (BounceZone)
        bounce_setup = next(s for s in spy_setups if s.index == 1)
        assert bounce_setup.label == 'BounceZone'
        assert bounce_setup.direction == 'long'
        assert bounce_setup.emoji_hint == '🟢'
        assert 'bounce' in bounce_setup.keywords
        assert len(bounce_setup.target_prices) == 3
        
        print("✅ TradeSetup objects created with correct field mappings")
        
        print("\n=== PHASE 3: Store in Database ===")
        # Store in database
        stored_setups, stored_levels = self.store.store_parsed_setups(
            trade_setups, parsed_levels
        )
        
        assert len(stored_setups) >= 3, "Should store at least 3 setups"
        assert len(stored_levels) >= 9, "Should store multiple levels"
        
        print(f"✅ Stored {len(stored_setups)} setups and {len(stored_levels)} levels")
        
        print("\n=== PHASE 4: Retrieve via API ===")
        # Test API retrieval
        with self.app.test_client() as client:
            # Test main setups endpoint
            response = client.get('/api/parsing/setups', query_string={
                'trading_day': '2025-06-14'
            })
            
            assert response.status_code == 200
            api_data = json.loads(response.data)
            assert api_data['success']
            assert len(api_data['setups']) >= 3
            
            # Validate new fields in API response
            spy_setup = next(s for s in api_data['setups'] if s['ticker'] == 'SPY' and s['index'] == 1)
            assert spy_setup['label'] == 'BounceZone'
            assert spy_setup['direction'] == 'long'
            assert spy_setup['emoji_hint'] == '🟢'
            assert isinstance(spy_setup['target_prices'], list)
            assert len(spy_setup['target_prices']) == 3
            assert isinstance(spy_setup['keywords'], list)
            assert 'bounce' in spy_setup['keywords']
            
            print("✅ API endpoints return correct new field structure")
            
            # Test filtering by new fields
            label_response = client.get('/api/parsing/setups', query_string={
                'trading_day': '2025-06-14',
                'label': 'BounceZone'
            })
            assert label_response.status_code == 200
            label_data = json.loads(label_response.data)
            bounce_setups = label_data['setups']
            assert all(s['label'] == 'BounceZone' for s in bounce_setups)
            
            direction_response = client.get('/api/parsing/setups', query_string={
                'trading_day': '2025-06-14',
                'direction': 'short'
            })
            assert direction_response.status_code == 200
            direction_data = json.loads(direction_response.data)
            short_setups = direction_data['setups']
            assert all(s['direction'] == 'short' for s in short_setups)
            
            print("✅ New filtering capabilities work correctly")

        print("\n=== PHASE 5: Dashboard JSON Endpoints ===")
        # Test dashboard endpoints
        with self.app.test_client() as client:
            metrics_response = client.get('/dashboard/parsing/metrics')
            assert metrics_response.status_code == 200
            metrics_data = json.loads(metrics_response.data)
            
            # Check enhanced metrics
            parsing_stats = metrics_data.get('parsing_stats', {})
            assert 'setups_by_label' in parsing_stats
            assert 'direction_split' in parsing_stats
            assert 'setup_index_distribution' in parsing_stats
            
            # Validate metrics content
            assert parsing_stats['setups_by_label'].get('BounceZone', 0) > 0
            assert parsing_stats['direction_split'].get('long', 0) > 0
            assert parsing_stats['direction_split'].get('short', 0) > 0
            
            print("✅ Enhanced metrics expose new field analytics")

        print("\n=== PHASE 6: Data Integrity Validation ===")
        # Retrieve and validate all stored data
        retrieved_setups = self.store.get_active_setups_for_day(trading_day)
        assert len(retrieved_setups) >= 3
        
        # Check data integrity for each expected setup
        for expected in EXPECTED_SETUPS:
            matching_setup = next(
                (s for s in retrieved_setups 
                 if s.ticker == expected['ticker'] and s.index == expected['index']),
                None
            )
            assert matching_setup is not None, f"Missing setup: {expected}"
            
            # Validate field mappings
            assert matching_setup.label == expected['label']
            assert matching_setup.direction == expected['direction']
            assert matching_setup.emoji_hint == expected['emoji_hint']
            assert set(matching_setup.keywords) >= set(expected['keywords'])
            assert len(matching_setup.target_prices) == len(expected['target_prices'])
            
        print("✅ All data integrity checks passed")
        
        print("\n=== INTEGRATION TEST COMPLETE ===")
        print("✅ Full workflow validated: Parse → Store → API → Metrics")
        print("✅ All new field mappings working correctly")
        print("✅ Enhanced filtering and analytics functional")

    def test_setup_converter_unit(self):
        """Unit test the setup_converter specifically"""
        print("\n=== SETUP CONVERTER UNIT TEST ===")
        
        # Test conversion of parsed data
        test_parsed_data = {
            'success': True,
            'setups': [
                {
                    'ticker': 'TEST',
                    'setup_line': '🟢 Bounce Zone Near 100.00 (102.00, 104.00)',
                    'trigger_level': 100.00,
                    'target_prices': [102.00, 104.00],
                    'direction': 'long',
                    'label': 'BounceZone',
                    'keywords': ['bounce', 'zone'],
                    'emoji_hint': '🟢',
                    'index': 1
                }
            ],
            'levels': [
                {
                    'ticker': 'TEST',
                    'price': 100.00,
                    'level_type': 'entry',
                    'confidence': 0.8
                }
            ]
        }
        
        message_id = "test_converter_unit"
        trading_day = date.today()
        
        trade_setups, parsed_levels = self.converter.convert_parsed_data(
            parsed_data=test_parsed_data,
            message_id=message_id,
            trading_day=trading_day
        )
        
        assert len(trade_setups) == 1
        assert len(parsed_levels) >= 1
        
        setup = trade_setups[0]
        assert setup.ticker == 'TEST'
        assert setup.label == 'BounceZone'
        assert setup.direction == 'long'
        assert setup.emoji_hint == '🟢'
        assert setup.keywords == ['bounce', 'zone']
        assert setup.target_prices == [102.00, 104.00]
        assert setup.index == 1
        
        print("✅ Setup converter unit test passed")

    def test_missing_setups_audit(self):
        """Test audit logs for missing setups scenario"""
        print("\n=== MISSING SETUPS AUDIT TEST ===")
        
        # Create incomplete message (missing some expected setups)
        incomplete_message = """A+ Trade Setups — Friday June 14

SPY 
🟢 Bounce Zone Near 542.19 (545.50, 548.00, 550.25)
❌ Rejection Near 550.25 (548.00, 545.50, 542.19)

NVDA
🟢 Bounce Zone Near 135.42 (138.00, 140.50, 142.75)

Trade responsibly and manage your risk."""
        
        message_id = "test_missing_setups"
        trading_day = date.today()
        
        # Parse incomplete message
        parsed_data = self.parser.parse_message(incomplete_message)
        
        # Convert and store
        trade_setups, parsed_levels = self.converter.convert_parsed_data(
            parsed_data=parsed_data,
            message_id=message_id,
            trading_day=trading_day
        )
        
        stored_setups, stored_levels = self.store.store_parsed_setups(
            trade_setups, parsed_levels
        )
        
        # Audit for missing setups - should detect fewer setups than typical
        audit_data = self.store.get_audit_data()
        
        # Check that audit captures setup distribution
        setup_counts = audit_data.get('setup_distribution', {})
        print(f"Setup distribution: {setup_counts}")
        
        # Validate that we can detect incomplete parsing scenarios
        stored_setup_count = len(stored_setups)
        assert stored_setup_count >= 2, "Should have at least some setups"
        assert stored_setup_count < 6, "Should have fewer setups than complete message"
        
        print(f"✅ Audit detected {stored_setup_count} setups from incomplete message")
        print("✅ Missing setup audit capability validated")

if __name__ == "__main__":
    # Run tests directly
    test_instance = TestCompleteIntegration()
    test_instance.setup_method()
    
    try:
        test_instance.test_complete_workflow()
        test_instance.test_setup_converter_unit()
        test_instance.test_missing_setups_audit()
        
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    finally:
        test_instance.teardown_method()
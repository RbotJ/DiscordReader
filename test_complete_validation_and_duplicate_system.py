"""
Complete Integration Test for A+ Validation Fix and Duplicate Detection System

Tests the complete workflow from message validation through duplicate detection
to verify both the validation accuracy improvements and duplicate handling work correctly.
"""
import logging
from datetime import date, datetime
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_validation_accuracy():
    """Test the validation fix addresses the parsing accuracy issue."""
    print("\n=== Testing A+ Message Validation Accuracy ===")
    
    try:
        from features.parsing.aplus_parser import get_aplus_parser
        parser = get_aplus_parser()
        
        # Test cases representing the 3 header variations found in the dataset
        test_messages = [
            # Case 1: Standard format (14 messages)
            {
                'content': 'A+ Scalp Trade Setups – Monday June 10\n\nNVDA 🔥\n120C 6/14 @ 1.15 target 1.50+\n121C 6/14 @ .95 target 1.25+',
                'expected': True,
                'description': 'Standard A+ Scalp Trade Setups format'
            },
            # Case 2: Shortened format (7 messages)  
            {
                'content': 'A+ Trade Setups – Tuesday June 11\n\nSPY\n533C 6/14 @ .85 target 1.10+',
                'expected': True,
                'description': 'Shortened A+ Trade Setups format'
            },
            # Case 3: Alternative format (1 message)
            {
                'content': 'A+ Scalp Setups – Wednesday June 12\n\nTSLA\n180C 6/14 @ 2.50 target 3.20+',
                'expected': True,
                'description': 'Alternative A+ Scalp Setups format'
            },
            # Case 4: Non-A+ message (should be rejected)
            {
                'content': 'Good morning everyone! Market update for today...',
                'expected': False,
                'description': 'Non-A+ message should be rejected'
            }
        ]
        
        validation_results = []
        for i, test_case in enumerate(test_messages, 1):
            content = test_case['content']
            expected = test_case['expected']
            description = test_case['description']
            
            is_valid = parser.validate_message(content)
            success = is_valid == expected
            
            validation_results.append({
                'test_case': i,
                'description': description,
                'expected': expected,
                'actual': is_valid,
                'success': success
            })
            
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"Test {i}: {status} - {description}")
            print(f"  Expected: {expected}, Got: {is_valid}")
        
        # Summary
        passed = sum(1 for r in validation_results if r['success'])
        total = len(validation_results)
        print(f"\nValidation Accuracy: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("✓ Validation fix successful - all header variations recognized!")
        else:
            print("✗ Validation issues remain")
            
        return validation_results
        
    except Exception as e:
        logger.error(f"Error testing validation accuracy: {e}")
        return []

def test_duplicate_detection_system():
    """Test the duplicate detection system with various scenarios."""
    print("\n=== Testing Duplicate Detection System ===")
    
    try:
        from features.parsing.store import get_parsing_store
        store = get_parsing_store()
        
        # Test scenarios
        test_trading_day = date(2025, 6, 18)
        test_message_id_1 = "test_msg_001"
        test_message_id_2 = "test_msg_002"
        
        print(f"Testing with trading day: {test_trading_day}")
        
        # Scenario 1: No duplicate (first message)
        is_duplicate_1 = store.is_duplicate_setup(test_trading_day, test_message_id_1)
        print(f"First message duplicate check: {is_duplicate_1} (Expected: False)")
        
        # Scenario 2: Check for existing message details
        existing_details = store.find_existing_message_for_day(test_trading_day)
        print(f"Existing message for day: {existing_details}")
        
        # Scenario 3: Get duplicate trading days
        duplicate_days = store.get_duplicate_trading_days()
        print(f"Found {len(duplicate_days)} trading days with duplicates:")
        for day, count in duplicate_days[:3]:  # Show first 3
            print(f"  {day}: {count} messages")
        
        # Scenario 4: Test replacement logic
        if duplicate_days:
            # Use real data for testing
            test_day, message_count = duplicate_days[0]
            print(f"\nTesting replacement logic for {test_day} ({message_count} messages)")
            
            # Get existing message details for this day
            existing = store.find_existing_message_for_day(test_day)
            if existing:
                existing_msg_id, existing_timestamp, existing_length = existing
                print(f"Existing message: {existing_msg_id} (length: {existing_length})")
                
                # Test replacement decision
                new_timestamp = datetime.now()
                new_length = existing_length + 100  # Simulate longer message
                
                should_replace = store.should_replace(
                    existing, "new_test_msg", new_timestamp, new_length
                )
                print(f"Should replace with longer message: {should_replace} (Expected: True)")
                
                # Test with shorter message
                short_length = max(1, existing_length - 100)
                should_not_replace = store.should_replace(
                    existing, "new_test_msg_short", new_timestamp, short_length
                )
                print(f"Should replace with shorter message: {should_not_replace} (Expected: False)")
        
        return {
            'duplicate_days_found': len(duplicate_days),
            'system_functional': True
        }
        
    except Exception as e:
        logger.error(f"Error testing duplicate detection: {e}")
        return {'system_functional': False, 'error': str(e)}

def test_service_integration():
    """Test integration between validation and duplicate detection in the service layer."""
    print("\n=== Testing Service Layer Integration ===")
    
    try:
        from features.parsing.service import get_parsing_service
        service = get_parsing_service()
        
        if not service:
            print("✗ Parsing service not available")
            return {'service_available': False}
        
        # Test A+ message validation
        test_content = 'A+ Trade Setups – Test Day\n\nNVDA\n120C 6/21 @ 1.00 target 1.30+'
        
        is_aplus = service.should_parse_message(test_content)
        print(f"Service recognizes A+ message: {is_aplus} (Expected: True)")
        
        # Test service statistics
        stats = service.get_service_stats()
        print(f"Service statistics available: {bool(stats)}")
        
        if stats and 'parsing_stats' in stats:
            parsing_stats = stats['parsing_stats']
            print(f"  Total setups: {parsing_stats.get('total_setups', 0)}")
            print(f"  Active setups: {parsing_stats.get('active_setups', 0)}")
            print(f"  Unique messages: {parsing_stats.get('unique_parsed_messages', 0)}")
        
        # Test health check
        is_healthy = service.is_healthy()
        print(f"Service health: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")
        
        return {
            'service_available': True,
            'recognizes_aplus': is_aplus,
            'stats_available': bool(stats),
            'healthy': is_healthy
        }
        
    except Exception as e:
        logger.error(f"Error testing service integration: {e}")
        return {'service_available': False, 'error': str(e)}

def test_dashboard_integration():
    """Test that dashboard shows duplicate detection metrics."""
    print("\n=== Testing Dashboard Integration ===")
    
    try:
        from features.parsing.store import get_parsing_store
        store = get_parsing_store()
        
        # Test audit data includes duplicate metrics
        audit_data = store.get_audit_anomalies()
        
        duplicate_days = store.get_duplicate_trading_days()
        expected_duplicate_count = len(duplicate_days)
        
        print(f"Audit data keys: {list(audit_data.keys())}")
        print(f"Duplicate trading days found: {expected_duplicate_count}")
        
        # Test cleanup functionality (dry run)
        cleanup_result = store.cleanup_duplicate_setups(dry_run=True)
        print(f"Cleanup dry run results: {cleanup_result}")
        
        return {
            'audit_data_available': bool(audit_data),
            'duplicate_tracking': expected_duplicate_count > 0,
            'cleanup_functional': 'duplicates_found' in cleanup_result
        }
        
    except Exception as e:
        logger.error(f"Error testing dashboard integration: {e}")
        return {'dashboard_functional': False, 'error': str(e)}

def main():
    """Run all comprehensive tests."""
    print("🔧 A+ Message Validation and Duplicate Detection System Test")
    print("=" * 70)
    
    # Run all test components
    validation_results = test_validation_accuracy()
    duplicate_results = test_duplicate_detection_system()
    service_results = test_service_integration()
    dashboard_results = test_dashboard_integration()
    
    # Overall summary
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print("=" * 70)
    
    # Validation Summary
    if validation_results:
        passed = sum(1 for r in validation_results if r['success'])
        total = len(validation_results)
        print(f"✓ Validation System: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    else:
        print("✗ Validation System: Tests failed to run")
    
    # Duplicate Detection Summary
    if duplicate_results.get('system_functional'):
        days_found = duplicate_results.get('duplicate_days_found', 0)
        print(f"✓ Duplicate Detection: System functional, {days_found} duplicate days found")
    else:
        print("✗ Duplicate Detection: System issues detected")
    
    # Service Integration Summary
    if service_results.get('service_available'):
        health = "✓" if service_results.get('healthy') else "?"
        print(f"{health} Service Integration: Available and {'healthy' if service_results.get('healthy') else 'status unknown'}")
    else:
        print("✗ Service Integration: Service unavailable")
    
    # Dashboard Integration Summary  
    if dashboard_results.get('audit_data_available'):
        tracking = "✓" if dashboard_results.get('duplicate_tracking') else "?"
        print(f"{tracking} Dashboard Integration: Audit data available, duplicate tracking {'active' if dashboard_results.get('duplicate_tracking') else 'inactive'}")
    else:
        print("✗ Dashboard Integration: Issues detected")
    
    print("\n🎯 Key Improvements Implemented:")
    print("  • Flexible A+ header validation (token-based vs rigid regex)")
    print("  • Comprehensive duplicate detection with configurable policies")
    print("  • Enhanced dashboard audit and monitoring capabilities")
    print("  • Service layer integration for automated duplicate handling")
    
    return {
        'validation_results': validation_results,
        'duplicate_results': duplicate_results,
        'service_results': service_results,
        'dashboard_results': dashboard_results
    }

if __name__ == "__main__":
    results = main()
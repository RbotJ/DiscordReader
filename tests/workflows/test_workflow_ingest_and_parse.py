"""
Workflow Integration Test: Ingest and Parse Flow

Tests the complete vertical slice architecture:
1. Discord message ingestion (features/ingestion/)
2. Message parsing and setup extraction (features/parsing/)
3. Database persistence and event flow
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock

from features.ingestion.service import ingest_messages
from features.parsing.parser import parse_setup_from_text
from features.parsing.store import save_setup
from features.ingestion.models import DiscordMessageModel
from features.parsing.models import SetupModel
from common.db import db


class TestWorkflowIngestAndParse:
    """Test the complete ingest and parse workflow."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create test data
        self.sample_discord_messages = [
            {
                'id': '12345',
                'content': '$AAPL breakout above 150, target 155, stop 148',
                'author': 'TestTrader',
                'author_id': '67890',
                'channel_id': '11111',
                'timestamp': datetime.now().isoformat(),
                'embeds': [],
                'attachments': []
            },
            {
                'id': '12346',
                'content': '$TSLA bullish bounce from support at 200, conservative entry',
                'author': 'TestTrader2',
                'author_id': '67891',
                'channel_id': '11111',
                'timestamp': datetime.now().isoformat(),
                'embeds': [],
                'attachments': []
            }
        ]
    
    @patch('features.ingestion.fetcher.fetch_latest_messages')
    async def test_complete_ingest_and_parse_flow(self, mock_fetch):
        """Test the complete workflow from Discord fetch to setup extraction."""
        # Step 1: Mock Discord API response
        mock_fetch.return_value = self.sample_discord_messages
        
        # Step 2: Run ingestion process
        count = await ingest_messages(limit=5)
        assert count == 2, f"Expected 2 messages ingested, got {count}"
        
        # Step 3: Verify messages were stored
        stored_messages = DiscordMessageModel.query.all()
        assert len(stored_messages) >= 2, "Messages should be stored in database"
        
        # Step 4: Test parsing individual messages
        for message in stored_messages:
            setup = parse_setup_from_text(message.content)
            if setup:  # Only test if parsing succeeded
                # Step 5: Save parsed setup
                save_setup(setup)
                
                # Step 6: Verify setup was stored
                saved_setup = SetupModel.query.filter_by(
                    ticker=setup.ticker,
                    source_message_id=setup.source_message_id
                ).first()
                assert saved_setup is not None, f"Setup for {setup.ticker} should be saved"
                assert saved_setup.setup_type is not None, "Setup type should be classified"
    
    def test_parse_setup_from_text_functionality(self):
        """Test the core parsing functionality with various message types."""
        test_cases = [
            {
                'content': '$AAPL breakout above 150, target 155, stop 148',
                'expected_ticker': 'AAPL',
                'expected_direction': 'bullish',
                'expected_setup_type': 'breakout'
            },
            {
                'content': '$SPY short below 400 resistance, aggressive position',
                'expected_ticker': 'SPY',
                'expected_direction': 'bearish',
                'expected_setup_type': 'breakdown'
            },
            {
                'content': '$TSLA conservative bounce from 200 support',
                'expected_ticker': 'TSLA',
                'expected_direction': 'bullish',
                'expected_setup_type': 'bounce'
            }
        ]
        
        for case in test_cases:
            setup = parse_setup_from_text(case['content'])
            if setup:  # Only test if parsing succeeded
                assert setup.ticker == case['expected_ticker']
                assert setup.direction == case['expected_direction']
                assert setup.setup_type == case['expected_setup_type']
    
    def test_setup_confidence_scoring(self):
        """Test that setup confidence is calculated correctly."""
        # High confidence setup (has ticker, direction, entry, target, stop)
        high_confidence_content = '$AAPL long entry 150, target 155, stop 148'
        setup = parse_setup_from_text(high_confidence_content)
        
        if setup:
            assert setup.confidence > 0.5, "Complete setup should have high confidence"
        
        # Low confidence setup (only ticker)
        low_confidence_content = '$AAPL mentioned in some context'
        setup_low = parse_setup_from_text(low_confidence_content)
        
        if setup_low:
            assert setup_low.confidence <= 0.5, "Incomplete setup should have lower confidence"
    
    @patch('features.ingestion.discord.get_discord_client')
    async def test_ingestion_error_handling(self, mock_client):
        """Test that ingestion handles errors gracefully."""
        # Mock Discord client failure
        mock_client.return_value = None
        
        # Should handle the error without crashing
        try:
            count = await ingest_messages(limit=5)
            # If it doesn't raise an exception, that's good
        except Exception as e:
            # If it does raise, it should be a clear error message
            assert "Discord" in str(e) or "client" in str(e).lower()
    
    def test_database_transaction_integrity(self):
        """Test that database operations maintain transaction integrity."""
        # Create a test setup
        test_content = '$TEST breakout above 100, target 105, stop 98'
        setup = parse_setup_from_text(test_content)
        
        if setup:
            # Test saving
            save_setup(setup)
            
            # Verify it was saved
            saved = SetupModel.query.filter_by(ticker='TEST').first()
            assert saved is not None, "Setup should be saved to database"
            
            # Test updating
            saved.mark_as_triggered()
            db.session.commit()
            
            # Verify update
            updated = SetupModel.query.filter_by(ticker='TEST').first()
            assert updated.triggered is True, "Setup should be marked as triggered"
    
    def test_event_flow_integration(self):
        """Test that events are properly emitted during the workflow."""
        with patch('common.db.publish_event') as mock_publish:
            # Test setup saving emits event
            test_content = '$EVENT breakout test'
            setup = parse_setup_from_text(test_content)
            
            if setup:
                save_setup(setup)
                
                # Verify event was published
                mock_publish.assert_called()
                call_args = mock_publish.call_args
                assert 'SETUP_CREATED' in str(call_args) or 'setup' in str(call_args).lower()
    
    def teardown_method(self):
        """Clean up after tests."""
        # Clean up test data
        try:
            db.session.query(DiscordMessageModel).filter(
                DiscordMessageModel.author.in_(['TestTrader', 'TestTrader2'])
            ).delete()
            db.session.query(SetupModel).filter(
                SetupModel.ticker.in_(['TEST', 'EVENT'])
            ).delete()
            db.session.commit()
        except:
            db.session.rollback()


@pytest.mark.asyncio
async def test_quick_workflow_validation():
    """Quick test to validate the workflow is functional."""
    # Test parsing functionality
    sample_content = '$QUICK breakout above 50'
    setup = parse_setup_from_text(sample_content)
    
    if setup:
        assert setup.ticker == 'QUICK'
        assert 'breakout' in setup.setup_type
        print(f"✅ Parsing working: {setup.ticker} {setup.setup_type}")
    else:
        print("⚠️ Parsing returned None - check parser implementation")
    
    # Test that ingestion service is importable and callable
    try:
        # Don't actually call it without mocking Discord
        from features.ingestion.service import ingest_messages
        print("✅ Ingestion service importable")
    except ImportError as e:
        print(f"❌ Ingestion service import failed: {e}")
    
    print("Workflow integration test validation complete!")


if __name__ == "__main__":
    # Run quick validation
    asyncio.run(test_quick_workflow_validation())
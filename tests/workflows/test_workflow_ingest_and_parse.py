"""
Integration Test for Workflow 1: Ingest and Parse Pipeline

Tests the complete flow:
1. Discord message ingestion → ingestion/service.py
2. Message validation and storage
3. Parse stored messages on MESSAGE_STORED event
4. Emit SETUP_PARSED event
5. Store parsed SetupModel in DB
"""

import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock

from features.ingestion.service import IngestionService
from features.parsing.parser import MessageParser
from features.parsing.models import SetupModel
from common.db import db, publish_event
from common.events.constants import EventChannels


class TestWorkflowIngestAndParse:
    """Test complete ingestion and parsing workflow"""
    
    def setup_method(self):
        """Setup test environment"""
        self.ingestion_service = IngestionService()
        self.parser = MessageParser()
    
    def test_complete_discord_to_setup_workflow(self):
        """Test full workflow from Discord message to parsed setup"""
        
        # Sample Discord message with trading setup
        sample_message = {
            'message_id': 'test_msg_123',
            'channel_id': 'test_channel_456', 
            'author_id': 'test_author_789',
            'content': '$AAPL breakout above $180 resistance. Looking for continuation to $185. Stop at $178.',
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Step 1: Ingest Discord message
        result = self.ingestion_service.ingest_discord_message(sample_message)
        assert result is not None
        assert result.get('status') == 'success'
        
        # Verify message was stored
        stored_message_id = result.get('message_id')
        assert stored_message_id is not None
        
        # Step 2: Parse the stored message
        setups = self.parser.parse_message(
            sample_message['content'], 
            sample_message['message_id']
        )
        
        # Verify parsing results
        assert len(setups) > 0
        setup = setups[0]
        assert isinstance(setup, SetupModel)
        assert setup.ticker == 'AAPL'
        assert 'breakout' in setup.content.lower()
        
        # Step 3: Verify setup can be stored
        with db.session.begin():
            db.session.add(setup)
            db.session.flush()
            setup_id = setup.id
        
        assert setup_id is not None
        
        # Step 4: Verify event publishing works
        event_success = publish_event('setup.parsed', {
            'setup_id': setup_id,
            'ticker': setup.ticker,
            'message_id': sample_message['message_id']
        })
        
        assert event_success is True
    
    def test_multi_ticker_message_parsing(self):
        """Test parsing message with multiple tickers"""
        
        multi_ticker_message = {
            'message_id': 'test_multi_123',
            'channel_id': 'test_channel_456',
            'author_id': 'test_author_789', 
            'content': '$TSLA breaking $250 resistance, target $260. $NVDA pullback to $900 support level.',
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Ingest and parse
        result = self.ingestion_service.ingest_discord_message(multi_ticker_message)
        assert result.get('status') == 'success'
        
        setups = self.parser.parse_message(
            multi_ticker_message['content'],
            multi_ticker_message['message_id']
        )
        
        # Should find multiple setups
        assert len(setups) >= 2
        tickers = [setup.ticker for setup in setups]
        assert 'TSLA' in tickers
        assert 'NVDA' in tickers
    
    def test_invalid_message_handling(self):
        """Test handling of invalid or non-setup messages"""
        
        invalid_message = {
            'message_id': 'test_invalid_123',
            'channel_id': 'test_channel_456',
            'author_id': 'test_author_789',
            'content': 'Just saying hello to everyone!',
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Should still ingest but not parse as setup
        result = self.ingestion_service.ingest_discord_message(invalid_message)
        assert result.get('status') == 'success'
        
        setups = self.parser.parse_message(
            invalid_message['content'],
            invalid_message['message_id']
        )
        
        # Should return empty list for non-trading messages
        assert len(setups) == 0
    
    def test_workflow_error_handling(self):
        """Test error handling in the workflow"""
        
        # Test with malformed message
        malformed_message = {
            'message_id': '',  # Empty message ID
            'content': '$AAPL to the moon!'
        }
        
        # Should handle gracefully
        result = self.ingestion_service.ingest_discord_message(malformed_message)
        
        # Should indicate error but not crash
        assert result is not None
        assert 'error' in result or result.get('status') == 'error'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
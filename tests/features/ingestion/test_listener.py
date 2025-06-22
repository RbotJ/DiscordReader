"""
Unit Tests for Ingestion Listener Event Handling

Tests for the listener's event handling capabilities including message processing,
duplicate detection, and proper integration with the service layer.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from features.ingestion.listener import IngestionListener
from common.models import DiscordMessageDTO


class TestIngestionListener:
    """Test cases for the IngestionListener event handling."""
    
    @pytest.fixture
    def mock_ingestion_service(self):
        """Create a mock ingestion service for testing."""
        service = Mock()
        service.handle_event = AsyncMock(return_value=True)
        return service
    
    @pytest.fixture
    def listener(self, mock_ingestion_service):
        """Create a listener instance with mocked service."""
        return IngestionListener(ingestion_service=mock_ingestion_service)
    
    @pytest.mark.asyncio
    async def test_handle_event_valid_message(self, listener, mock_ingestion_service):
        """Test that valid discord.message.new events are processed correctly."""
        # Arrange
        event_type = "discord.message.new"
        event_data = {
            'message_id': '123456789',
            'channel_id': '987654321',
            'author_id': '555666777',
            'content': 'Test message content',
            'timestamp': '2025-06-22T12:00:00Z'
        }
        
        # Act
        result = await listener._handle_event(event_type, event_data)
        
        # Assert
        assert result is True
        mock_ingestion_service.handle_event.assert_called_once()
        
        # Verify the event passed to service
        call_args = mock_ingestion_service.handle_event.call_args[0][0]
        assert call_args['event_type'] == event_type
        assert call_args['payload'] == event_data
        
        # Verify stats updated
        assert listener.stats['events_received'] == 1
        assert listener.stats['events_processed'] == 1
        assert listener.stats['last_activity'] is not None
    
    @pytest.mark.asyncio
    async def test_handle_event_duplicate_skipped(self, listener, mock_ingestion_service):
        """Test that duplicate messages are properly logged and handled."""
        # Arrange - service returns False indicating duplicate/skip
        mock_ingestion_service.handle_event.return_value = False
        
        event_type = "discord.message.new"
        event_data = {
            'message_id': '123456789',
            'channel_id': '987654321',
            'author_id': '555666777',
            'content': 'Duplicate message content',
            'timestamp': '2025-06-22T12:00:00Z'
        }
        
        # Act
        with patch('features.ingestion.listener.logger') as mock_logger:
            result = await listener._handle_event(event_type, event_data)
        
        # Assert
        assert result is False  # Should return False for skipped/failed processing
        mock_ingestion_service.handle_event.assert_called_once()
        
        # Verify stats - events received but not processed
        assert listener.stats['events_received'] == 1
        assert listener.stats['events_processed'] == 0  # Not incremented for failed processing
    
    @pytest.mark.asyncio
    async def test_handle_discord_message_event_missing_channel_id(self, listener):
        """Test handling of malformed events missing required fields."""
        # Arrange
        event_type = "discord.message.new"
        event_data = {
            'message_id': '123456789',
            # Missing channel_id
            'content': 'Test message'
        }
        
        # Act
        with patch('features.ingestion.listener.logger') as mock_logger:
            result = await listener._handle_discord_message_event(event_type, event_data)
        
        # Assert
        assert result is False
        mock_logger.warning.assert_called_with("No channel_id in discord message event")
        assert listener.stats['errors'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_event_unhandled_type(self, listener):
        """Test handling of unhandled event types."""
        # Arrange
        event_type = "some.other.event"
        event_data = {'data': 'value'}
        
        # Act
        with patch('features.ingestion.listener.logger') as mock_logger:
            result = await listener._handle_event(event_type, event_data)
        
        # Assert
        assert result is True  # Unhandled events return True (no error)
        mock_logger.debug.assert_called_with(f"Unhandled event type: {event_type}")
        assert listener.stats['events_received'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_event_service_exception(self, listener, mock_ingestion_service):
        """Test proper error handling when service raises exception."""
        # Arrange
        mock_ingestion_service.handle_event.side_effect = Exception("Service error")
        
        event_type = "discord.message.new"
        event_data = {'channel_id': '123', 'message_id': '456'}
        
        # Act
        with patch('features.ingestion.listener.logger') as mock_logger:
            result = await listener._handle_event(event_type, event_data)
        
        # Assert
        assert result is False
        mock_logger.error.assert_called()
        assert listener.stats['errors'] == 1
    
    def test_get_stats(self, listener):
        """Test that get_stats returns a copy of current statistics."""
        # Arrange
        listener.stats['custom_field'] = 'test_value'
        
        # Act
        stats = listener.get_stats()
        
        # Assert
        assert 'custom_field' in stats
        assert stats['custom_field'] == 'test_value'
        
        # Verify it's a copy (modifying returned stats doesn't affect original)
        stats['new_field'] = 'new_value'
        assert 'new_field' not in listener.stats
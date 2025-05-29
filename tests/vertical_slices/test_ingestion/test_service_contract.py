"""
Ingestion Service Contract Tests

Tests that verify the ingestion service honors its interface contracts
and properly handles message processing without crossing slice boundaries.
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from features.ingestion.service import IngestionService
from features.ingestion.interfaces import IIngestionService
from common.models import DiscordMessageDTO


class TestIngestionServiceContract:
    """Test ingestion service contract compliance and interface adherence."""

    def test_service_implements_interface(self):
        """Test that IngestionService properly implements IIngestionService."""
        service = IngestionService()
        
        # Verify service implements all required interface methods
        interface_methods = [method for method in dir(IIngestionService) 
                           if not method.startswith('_')]
        
        for method in interface_methods:
            assert hasattr(service, method), f"Service missing interface method: {method}"

    @pytest.mark.asyncio
    async def test_store_discord_message_atomic_operation(self, sample_discord_message_dto, mock_database_session):
        """Test that store_discord_message performs atomic storage operations."""
        service = IngestionService()
        
        with patch('features.ingestion.service.db.session', mock_database_session):
            with patch('features.ingestion.models.DiscordMessageModel') as mock_model:
                mock_instance = MagicMock()
                mock_model.query.filter_by.return_value.first.return_value = None  # No existing message
                mock_model.return_value = mock_instance
                
                result = await service.store_discord_message(sample_discord_message_dto)
                
                assert result is True
                mock_database_session.add.assert_called_once_with(mock_instance)
                mock_database_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_discord_message_deduplication(self, sample_discord_message_dto, mock_database_session):
        """Test that store_discord_message handles duplicate messages correctly."""
        service = IngestionService()
        
        with patch('features.ingestion.service.db.session', mock_database_session):
            with patch('features.ingestion.models.DiscordMessageModel') as mock_model:
                # Simulate existing message
                mock_model.query.filter_by.return_value.first.return_value = MagicMock()
                
                result = await service.store_discord_message(sample_discord_message_dto)
                
                assert result is False  # Should skip duplicate
                mock_database_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_batch_returns_statistics(self, mock_discord_message):
        """Test that process_message_batch returns proper statistics."""
        service = IngestionService()
        messages = [mock_discord_message]
        
        with patch.object(service, '_process_single_message', return_value=True):
            result = await service.process_message_batch(messages)
            
            assert isinstance(result, dict)
            assert 'total' in result
            assert 'stored' in result
            assert 'skipped' in result
            assert 'errors' in result
            assert result['total'] == 1
            assert result['stored'] == 1

    @pytest.mark.asyncio
    async def test_process_message_batch_error_handling(self, mock_discord_message):
        """Test that process_message_batch handles errors gracefully."""
        service = IngestionService()
        messages = [mock_discord_message]
        
        with patch.object(service, '_process_single_message', side_effect=Exception("Test error")):
            result = await service.process_message_batch(messages)
            
            assert result['errors'] == 1
            assert len(result['errors_list']) == 1
            assert 'error' in result['errors_list'][0]

    @pytest.mark.asyncio
    async def test_process_realtime_message_delegates_to_core(self, mock_discord_message):
        """Test that process_realtime_message uses shared processing core."""
        service = IngestionService()
        
        with patch.object(service, '_process_single_message', return_value=True) as mock_process:
            result = await service.process_realtime_message(mock_discord_message)
            
            assert result is True
            mock_process.assert_called_once_with(mock_discord_message)

    @pytest.mark.asyncio
    async def test_ingest_latest_messages_uses_batch_processing(self):
        """Test that ingest_latest_messages uses enhanced batch processing."""
        service = IngestionService()
        channel_id = "123456789"
        
        with patch.object(service, '_fetch_discord_messages', return_value=[]):
            with patch.object(service, 'process_message_batch', return_value={'stored': 0}):
                with patch.object(service, '_emit_batch_completion_event'):
                    result = await service.ingest_latest_messages(channel_id)
                    
                    assert result['status'] == 'completed'
                    assert 'statistics' in result

    @pytest.mark.asyncio
    async def test_ingest_channel_history_delegates_correctly(self):
        """Test that ingest_channel_history properly delegates to core methods."""
        service = IngestionService()
        channel_id = "123456789"
        
        with patch.object(service, 'ingest_latest_messages', return_value={'status': 'completed'}) as mock_ingest:
            result = await service.ingest_channel_history(channel_id, limit=50, source="test")
            
            mock_ingest.assert_called_once_with(channel_id=channel_id, limit=50, since=None)
            assert result['source'] == "test"

    @pytest.mark.asyncio
    async def test_handle_realtime_message_publishes_events(self, mock_discord_message, mock_event_publisher):
        """Test that handle_realtime_message publishes appropriate events."""
        service = IngestionService()
        
        with patch('features.ingestion.service.publish_event') as mock_publish:
            with patch.object(service, 'process_realtime_message', return_value=True):
                await service.handle_realtime_message(mock_discord_message)
                
                mock_publish.assert_called_once()
                call_args = mock_publish.call_args
                assert call_args[1]['event_type'] == "ingestion.message.stored"

    def test_service_does_not_import_discord_directly(self):
        """Test that ingestion service doesn't directly import Discord client modules."""
        import features.ingestion.service as service_module
        import inspect
        
        source = inspect.getsource(service_module)
        
        # Service should not directly import Discord client modules
        forbidden_imports = [
            'import discord.client',
            'from discord.client import',
            'from features.discord_bot import'
        ]
        
        for forbidden in forbidden_imports:
            assert forbidden not in source, f"Ingestion should not directly import: {forbidden}"

    @pytest.mark.parametrize("content,should_store", [
        ("", False),  # Empty content should be rejected
        ("   ", False),  # Whitespace only should be rejected
        ("Valid message content", True),  # Valid content should be stored
        ("Setup: BUY AAPL 150", True),  # Setup message should be stored
    ])
    @pytest.mark.asyncio
    async def test_validation_driven_processing(self, content, should_store, mock_database_session):
        """Test message validation with various content types."""
        service = IngestionService()
        
        message_dto = DiscordMessageDTO(
            message_id="123",
            channel_id="456",
            author_id="789",
            content=content,
            created_at=datetime.utcnow(),
            is_setup=False,
            processed=False,
            embed_data={}
        )
        
        with patch('features.ingestion.service.db.session', mock_database_session):
            with patch('features.ingestion.models.DiscordMessageModel') as mock_model:
                mock_model.query.filter_by.return_value.first.return_value = None
                
                result = await service.store_discord_message(message_dto)
                
                if should_store:
                    assert result is True
                    mock_database_session.add.assert_called()
                else:
                    assert result is False
                    mock_database_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_isolation_and_recovery(self, sample_discord_message_dto, mock_database_session):
        """Test that service handles errors without exposing internal details."""
        service = IngestionService()
        
        # Configure database to raise exception
        mock_database_session.commit.side_effect = Exception("Database error")
        
        with patch('features.ingestion.service.db.session', mock_database_session):
            with patch('features.ingestion.models.DiscordMessageModel'):
                result = await service.store_discord_message(sample_discord_message_dto)
                
                # Should handle error gracefully
                assert result is False
                mock_database_session.rollback.assert_called()
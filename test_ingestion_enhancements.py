"""
Comprehensive Integration Test for Ingestion Feature Enhancements

Tests the complete enhanced ingestion functionality including:
- Structured logging with message ID tracking
- Uptime tracking and metrics
- Duplicate handling with counters
- Enhanced API endpoints
- Event tracing and observability
"""
import asyncio
import pytest
import json
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
from features.ingestion.service import IngestionService
from features.ingestion.listener import IngestionListener
from common.models import DiscordMessageDTO


class TestIngestionEnhancements:
    """Test suite for ingestion feature enhancements."""
    
    @pytest.fixture
    def sample_message_dto(self):
        """Create a sample Discord message DTO for testing."""
        return DiscordMessageDTO(
            message_id="test_message_123",
            channel_id="1372012942848954388",
            content="Test A+ trading message",
            author_id="test_author",
            timestamp=datetime.utcnow(),
            message_type="text"
        )
    
    @pytest.fixture
    def ingestion_service(self):
        """Create ingestion service for testing."""
        service = IngestionService()
        return service
        
    @pytest.fixture
    def ingestion_listener(self, ingestion_service):
        """Create ingestion listener for testing."""
        listener = IngestionListener(ingestion_service=ingestion_service)
        return listener

    @pytest.mark.asyncio
    async def test_structured_logging_after_storage(self, ingestion_service, sample_message_dto):
        """Test that structured logging occurs after successful message storage."""
        # Mock the dependencies
        with patch('features.ingestion.service.logger') as mock_logger, \
             patch.object(ingestion_service, 'validator') as mock_validator, \
             patch.object(ingestion_service, 'store') as mock_store:
            
            # Setup mocks
            mock_validator.validate_message.return_value = True
            mock_store.store_message.return_value = True
            
            # Process message
            result = await ingestion_service.process_message(sample_message_dto)
            
            # Verify structured logging was called
            assert result is True
            mock_logger.info.assert_called_with(
                "[ingestion] Stored message ID: %s (event: message.stored)", 
                sample_message_dto.message_id
            )

    def test_uptime_tracking_metrics(self, ingestion_service):
        """Test uptime tracking functionality."""
        # Get initial metrics
        metrics = ingestion_service.get_metrics()
        
        # Verify uptime tracking is present
        assert 'uptime_seconds' in metrics
        assert isinstance(metrics['uptime_seconds'], int)
        assert metrics['uptime_seconds'] >= 0
        
        # Test uptime calculation method
        uptime = ingestion_service.get_uptime_seconds()
        assert isinstance(uptime, int)
        assert uptime >= 0

    @pytest.mark.asyncio 
    async def test_duplicate_handling_metrics(self, ingestion_service, sample_message_dto):
        """Test duplicate handling and metrics tracking."""
        # Mock dependencies
        with patch.object(ingestion_service, 'validator') as mock_validator, \
             patch.object(ingestion_service, 'store') as mock_store:
            
            mock_validator.validate_message.return_value = True
            mock_store.store_message.return_value = True
            
            # Process same message twice
            await ingestion_service.process_message(sample_message_dto)
            await ingestion_service.process_message(sample_message_dto)  # Duplicate
            
            # Verify duplicate was tracked
            metrics = ingestion_service.get_metrics()
            assert metrics['duplicates_skipped'] >= 1
            assert metrics['duplicates_skipped_today'] >= 1

    @pytest.mark.asyncio
    async def test_listener_error_tracking(self, ingestion_listener):
        """Test that listener properly tracks errors in statistics."""
        # Test malformed event
        event_data = {
            'message_id': '123456789',
            # Missing channel_id
            'content': 'Test message'
        }
        
        result = await ingestion_listener._handle_discord_message_event(
            "discord.message.new", event_data
        )
        
        # Verify error was tracked
        assert result is False
        stats = ingestion_listener.get_stats()
        assert stats['errors'] >= 1

    def test_enhanced_metrics_structure(self, ingestion_service):
        """Test the structure of enhanced metrics."""
        metrics = ingestion_service.get_metrics()
        
        # Core metrics
        assert 'messages_ingested' in metrics
        assert 'ingestion_errors' in metrics
        assert 'validation_success_rate' in metrics
        assert 'service_status' in metrics
        
        # Enhanced metrics
        assert 'uptime_seconds' in metrics
        assert 'duplicates_skipped' in metrics
        assert 'duplicates_skipped_today' in metrics
        assert 'messages_ingested_today' in metrics
        
        # Verify types
        assert isinstance(metrics['uptime_seconds'], int)
        assert isinstance(metrics['duplicates_skipped'], int)
        assert isinstance(metrics['validation_success_rate'], float)

    @pytest.mark.asyncio
    async def test_event_tracing_flow(self, ingestion_service, sample_message_dto):
        """Test complete event tracing from ingestion to storage."""
        with patch('features.ingestion.service.logger') as mock_logger, \
             patch.object(ingestion_service, 'validator') as mock_validator, \
             patch.object(ingestion_service, 'store') as mock_store, \
             patch.object(ingestion_service, 'event_publisher') as mock_publisher:
            
            # Setup mocks
            mock_validator.validate_message.return_value = True
            mock_store.store_message.return_value = True
            
            # Process message
            result = await ingestion_service.process_message(sample_message_dto)
            
            # Verify complete flow
            assert result is True
            
            # Check validation was called
            mock_validator.validate_message.assert_called_once_with(sample_message_dto)
            
            # Check storage was called
            mock_store.store_message.assert_called_once_with(sample_message_dto)
            
            # Check structured logging
            mock_logger.info.assert_called_with(
                "[ingestion] Stored message ID: %s (event: message.stored)", 
                sample_message_dto.message_id
            )
            
            # Check event was published
            mock_publisher.publish_event.assert_called_once()


def test_enhanced_api_endpoint_integration():
    """Test the enhanced metrics API endpoint integration."""
    from flask import Flask
    from features.ingestion.dashboard import ingest_bp
    
    app = Flask(__name__)
    app.register_blueprint(ingest_bp)
    
    with app.test_client() as client:
        # Test enhanced metrics endpoint
        response = client.get('/dashboard/ingestion/enhanced-metrics.json')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        # Verify enhanced structure
        assert 'core_metrics' in data
        assert 'uptime_tracking' in data
        assert 'duplicate_handling' in data
        assert 'daily_metrics' in data
        assert 'timestamp' in data
        
        # Verify core metrics structure
        core = data['core_metrics']
        assert 'messages_ingested' in core
        assert 'ingestion_errors' in core
        assert 'validation_success_rate' in core
        assert 'service_status' in core
        
        # Verify uptime tracking
        uptime = data['uptime_tracking']
        assert 'uptime_seconds' in uptime
        assert 'service_start_time' in uptime
        assert 'last_ingestion' in uptime
        
        # Verify duplicate handling
        duplicates = data['duplicate_handling']
        assert 'duplicates_skipped' in duplicates
        assert 'duplicates_skipped_today' in duplicates
        assert 'total_processing_attempts' in duplicates


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
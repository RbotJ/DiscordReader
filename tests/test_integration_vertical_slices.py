"""
Integration Tests for Vertical Slice Architecture

Tests that verify the complete system behavior while maintaining proper
slice boundaries and service interface compliance.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from features.discord_bot.bot import TradingDiscordBot
from features.ingestion.service import IngestionService
from features.discord_channels.channel_manager import ChannelManager


class TestVerticalSliceIntegration:
    """Integration tests that verify complete system behavior."""

    @pytest.mark.asyncio
    async def test_end_to_end_message_processing(self, mock_discord_message):
        """Test complete message flow from Discord to storage."""
        # Setup components
        bot = TradingDiscordBot()
        ingestion_service = IngestionService()
        bot.ingestion_service = ingestion_service
        
        # Mock database operations
        with patch('features.ingestion.service.db.session') as mock_session:
            with patch('features.ingestion.models.DiscordMessageModel') as mock_model:
                mock_model.query.filter_by.return_value.first.return_value = None
                
                # Process message through bot
                await bot.on_message(mock_discord_message)
                
                # Verify database interaction occurred
                mock_session.add.assert_called()

    def test_service_dependency_injection(self):
        """Test that services can be properly injected without tight coupling."""
        bot = TradingDiscordBot()
        
        # Should be able to replace services with mocks
        mock_ingestion = AsyncMock()
        mock_channel_manager = MagicMock()
        
        bot.ingestion_service = mock_ingestion
        bot.channel_manager = mock_channel_manager
        
        assert bot.ingestion_service is mock_ingestion
        assert bot.channel_manager is mock_channel_manager

    @pytest.mark.asyncio
    async def test_startup_sequence_integration(self):
        """Test that startup sequence properly initializes all components."""
        bot = TradingDiscordBot()
        
        # Mock channel operations
        with patch.object(bot, 'get_channel') as mock_get_channel:
            mock_channel = MagicMock()
            mock_channel.id = 123456789
            mock_get_channel.return_value = mock_channel
            
            bot.aplus_setups_channel_id = "123456789"
            
            # Mock ingestion service
            bot.ingestion_service = AsyncMock()
            
            # Test startup catchup
            await bot._startup_catchup_ingestion()
            
            # Verify ingestion was called
            bot.ingestion_service.ingest_channel_history.assert_awaited_once()

    def test_error_boundary_isolation(self):
        """Test that errors in one slice don't propagate to others."""
        bot = TradingDiscordBot()
        
        # Configure ingestion service to fail
        failing_service = AsyncMock()
        failing_service.process_realtime_message.side_effect = Exception("Service failure")
        bot.ingestion_service = failing_service
        
        # Bot should handle service failures gracefully
        mock_message = MagicMock()
        mock_message.author = MagicMock()
        mock_message.author.id = "user123"  # Not bot user
        
        # Should not raise exception
        try:
            asyncio.run(bot.on_message(mock_message))
        except Exception:
            pytest.fail("Bot should handle service failures gracefully")

    def test_interface_compliance_across_slices(self):
        """Test that all slices comply with their interface contracts."""
        # Test bot uses ingestion interface correctly
        bot = TradingDiscordBot()
        assert hasattr(bot.ingestion_service, 'process_realtime_message')
        assert hasattr(bot.ingestion_service, 'ingest_channel_history')
        
        # Test ingestion service implements interface
        ingestion = IngestionService()
        assert hasattr(ingestion, 'process_realtime_message')
        assert hasattr(ingestion, 'store_discord_message')
        
        # Test channel manager provides expected interface
        channel_manager = ChannelManager()
        assert channel_manager is not None

    @pytest.mark.asyncio
    async def test_message_validation_and_processing_flow(self):
        """Test complete message validation and processing pipeline."""
        ingestion = IngestionService()
        
        # Test with valid message
        valid_message = MagicMock()
        valid_message.id = 123456789
        valid_message.channel = MagicMock()
        valid_message.channel.id = 999888777
        valid_message.author = MagicMock()
        valid_message.author.id = "user123"
        valid_message.content = "Valid trading setup message"
        valid_message.created_at = datetime.utcnow()
        
        with patch.object(ingestion, 'store_discord_message', return_value=True):
            result = await ingestion.process_realtime_message(valid_message)
            assert result is True

    def test_configuration_isolation_between_slices(self):
        """Test that slices maintain independent configurations."""
        bot = TradingDiscordBot()
        ingestion = IngestionService()
        channel_manager = ChannelManager()
        
        # Each slice should be independently configurable
        assert bot is not None
        assert ingestion is not None
        assert channel_manager is not None
        
        # Slices should not share internal state
        assert bot.ingestion_service is not ingestion  # Bot has its own instance

    @pytest.mark.asyncio
    async def test_event_publishing_integration(self):
        """Test that events are properly published across slice boundaries."""
        ingestion = IngestionService()
        
        mock_message = MagicMock()
        mock_message.id = 123456789
        mock_message.channel.id = 999888777
        mock_message.author.id = "user123"
        mock_message.content = "Test message"
        mock_message.created_at = datetime.utcnow()
        
        with patch('features.ingestion.service.publish_event') as mock_publish:
            with patch.object(ingestion, 'store_discord_message', return_value=True):
                await ingestion.handle_realtime_message(mock_message)
                
                # Verify event was published
                mock_publish.assert_called_once()

    def test_slice_boundary_enforcement(self):
        """Test that slices maintain proper boundaries and don't cross-import."""
        # Import all slices and verify no circular dependencies
        try:
            from features.discord_bot.bot import TradingDiscordBot
            from features.ingestion.service import IngestionService
            from features.discord_channels.channel_manager import ChannelManager
            
            # Should be able to instantiate all without issues
            bot = TradingDiscordBot()
            ingestion = IngestionService()
            channel_manager = ChannelManager()
            
            assert all([bot, ingestion, channel_manager])
            
        except ImportError as e:
            pytest.fail(f"Slice boundary violation detected: {e}")

    def test_database_session_isolation(self):
        """Test that database sessions are properly isolated between operations."""
        ingestion = IngestionService()
        
        # Test that service handles database sessions correctly
        with patch('features.ingestion.service.db.session') as mock_session:
            mock_session.commit.side_effect = Exception("DB Error")
            mock_session.rollback = MagicMock()
            
            # Should handle database errors gracefully
            from common.models import DiscordMessageDTO
            test_dto = DiscordMessageDTO(
                message_id="123",
                channel_id="456", 
                author_id="789",
                content="test",
                created_at=datetime.utcnow(),
                is_setup=False,
                processed=False,
                embed_data={}
            )
            
            with patch('features.ingestion.models.DiscordMessageModel'):
                result = asyncio.run(ingestion.store_discord_message(test_dto))
                assert result is False
                mock_session.rollback.assert_called()
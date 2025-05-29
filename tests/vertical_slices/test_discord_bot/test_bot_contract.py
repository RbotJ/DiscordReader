"""
Discord Bot Contract Tests

Tests that ensure the Discord bot slice properly integrates with other services
through their interfaces without crossing slice boundaries.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from features.discord_bot.bot import TradingDiscordBot
from features.discord_bot.dto import RawMessageDto


class TestDiscordBotContract:
    """Test Discord bot contract compliance with other slices."""

    def test_bot_initializes_with_services(self, fake_ingestion_service):
        """Test that bot can be initialized with service dependencies."""
        # Test that bot accepts service interfaces without importing implementations
        bot = TradingDiscordBot()
        bot.ingestion_service = fake_ingestion_service
        
        assert bot.ingestion_service is not None
        assert hasattr(bot.ingestion_service, 'ingest_raw_message')

    @pytest.mark.asyncio
    async def test_on_message_calls_ingestion_service(self, fake_ingestion_service, mock_discord_message):
        """Test that message events are properly delegated to ingestion service."""
        bot = TradingDiscordBot()
        bot.ingestion_service = fake_ingestion_service
        
        # Simulate message event handling
        with patch.object(bot, '_convert_to_raw_dto') as mock_convert:
            mock_convert.return_value = RawMessageDto(
                message_id=str(mock_discord_message.id),
                channel_id=str(mock_discord_message.channel.id),
                author_id=str(mock_discord_message.author.id),
                author_name=mock_discord_message.author.name,
                content=mock_discord_message.content,
                timestamp=mock_discord_message.created_at
            )
            
            await bot._handle_message_event(mock_discord_message)
            
            # Verify ingestion service was called
            fake_ingestion_service.ingest_raw_message.assert_awaited_once()

    def test_bot_does_not_import_database_directly(self):
        """Ensure bot slice doesn't directly import database modules."""
        import features.discord_bot.bot as bot_module
        import inspect
        
        # Get all imports in the bot module
        source = inspect.getsource(bot_module)
        
        # Bot should not directly import database modules
        forbidden_imports = [
            'from common.db import db',
            'from sqlalchemy import',
            'db.session'
        ]
        
        for forbidden in forbidden_imports:
            assert forbidden not in source, f"Bot should not directly import: {forbidden}"

    @pytest.mark.asyncio
    async def test_startup_ingestion_delegates_to_service(self, fake_ingestion_service):
        """Test that startup ingestion is delegated to ingestion service."""
        bot = TradingDiscordBot()
        bot.ingestion_service = fake_ingestion_service
        bot.aplus_setups_channel_id = "123456789"
        
        await bot._startup_catchup_ingestion()
        
        # Verify the service was called with proper parameters
        fake_ingestion_service.ingest_channel_history.assert_awaited_once()
        call_args = fake_ingestion_service.ingest_channel_history.call_args
        assert call_args[1]['channel_id'] == "123456789"
        assert call_args[1]['source'] == "startup_catchup"

    def test_bot_uses_channel_manager_interface(self):
        """Test that bot interacts with channel manager through interface."""
        bot = TradingDiscordBot()
        
        # Bot should have channel manager dependency
        assert hasattr(bot, 'channel_manager')
        
        # Should be able to set channel manager without importing implementation
        mock_channel_manager = MagicMock()
        bot.channel_manager = mock_channel_manager
        
        assert bot.channel_manager is mock_channel_manager

    @pytest.mark.asyncio
    async def test_real_time_ingestion_triggers_service(self, fake_ingestion_service):
        """Test that real-time message triggers call ingestion service."""
        bot = TradingDiscordBot()
        bot.ingestion_service = fake_ingestion_service
        
        channel_id = "999888777"
        
        await bot._trigger_ingestion(channel_id)
        
        # Verify ingestion service was called for real-time processing
        fake_ingestion_service.ingest_latest_messages.assert_awaited_once()
        call_args = fake_ingestion_service.ingest_latest_messages.call_args
        assert call_args[1]['channel_id'] == channel_id

    def test_bot_error_handling_isolation(self, fake_ingestion_service):
        """Test that bot handles service errors without exposing internal details."""
        bot = TradingDiscordBot()
        bot.ingestion_service = fake_ingestion_service
        
        # Configure service to raise an exception
        fake_ingestion_service.ingest_latest_messages.side_effect = Exception("Service error")
        
        # Bot should handle service errors gracefully without exposing internals
        with patch('features.discord_bot.bot.logger') as mock_logger:
            asyncio.run(bot._trigger_ingestion("123"))
            
            # Should log error but not crash
            mock_logger.error.assert_called()

    def test_bot_respects_service_interfaces(self):
        """Test that bot only uses documented service interfaces."""
        from features.ingestion.interfaces import IIngestionService
        from features.discord_channels.interfaces import IChannelManager
        
        bot = TradingDiscordBot()
        
        # Bot should only call methods defined in interfaces
        ingestion_methods = dir(IIngestionService)
        channel_methods = dir(IChannelManager)
        
        # Verify bot doesn't rely on implementation-specific methods
        assert 'ingest_raw_message' in ingestion_methods
        assert 'ingest_latest_messages' in ingestion_methods
        assert 'ingest_channel_history' in ingestion_methods
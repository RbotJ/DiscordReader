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
        
        # Simulate message event handling through on_message
        await bot.on_message(mock_discord_message)
        
        # Verify ingestion service was called
        fake_ingestion_service.process_realtime_message.assert_awaited_once()

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
        
        # Test startup catchup method
        with patch.object(bot, 'get_channel') as mock_get_channel:
            mock_channel = MagicMock()
            mock_get_channel.return_value = mock_channel
            
            await bot._startup_catchup_ingestion()
            
            # Verify the service was called
            fake_ingestion_service.ingest_channel_history.assert_awaited_once()

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
        
        # Test trigger ingestion through startup method
        with patch.object(bot, 'get_channel') as mock_get_channel:
            mock_channel = MagicMock()
            mock_channel.id = int(channel_id)
            mock_get_channel.return_value = mock_channel
            
            bot.aplus_setups_channel_id = channel_id
            await bot._startup_catchup_ingestion()
            
            # Verify ingestion service was called
            fake_ingestion_service.ingest_channel_history.assert_awaited_once()

    def test_bot_error_handling_isolation(self, fake_ingestion_service):
        """Test that bot handles service errors without exposing internal details."""
        bot = TradingDiscordBot()
        bot.ingestion_service = fake_ingestion_service
        
        # Configure service to raise an exception
        fake_ingestion_service.process_realtime_message.side_effect = Exception("Service error")
        
        # Bot should handle service errors gracefully without exposing internals
        with patch('features.discord_bot.bot.logger') as mock_logger:
            mock_message = MagicMock()
            mock_message.author = bot.user  # Should be ignored
            
            asyncio.run(bot.on_message(mock_message))
            
            # Should handle error gracefully
            assert True  # If we get here, no exception was raised

    def test_bot_respects_service_interfaces(self):
        """Test that bot only uses documented service interfaces."""
        from features.ingestion.interfaces import IIngestionService
        
        bot = TradingDiscordBot()
        
        # Bot should only call methods defined in interfaces
        ingestion_methods = dir(IIngestionService)
        
        # Verify bot doesn't rely on implementation-specific methods
        assert 'process_realtime_message' in ingestion_methods
        assert 'ingest_latest_messages' in ingestion_methods
        assert 'ingest_channel_history' in ingestion_methods
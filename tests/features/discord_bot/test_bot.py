"""
Unit tests for Discord Bot Events

Tests the on_ready() and _trigger_ingestion() methods in TradingDiscordBot
without requiring real Discord connectivity.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import logging

# Mock Flask app context for testing
@pytest.fixture
def mock_flask_app():
    """Mock Flask app with necessary config for testing."""
    app = Mock()
    app.config = {
        'DISCORD_BOT': None,
        'TESTING': True
    }
    app.app_context.return_value.__enter__ = Mock(return_value=None)
    app.app_context.return_value.__exit__ = Mock(return_value=None)
    return app

@pytest.fixture
def mock_services():
    """Mock ingestion service and channel manager."""
    ingestion_service = Mock()
    ingestion_service.ingest_latest_messages = AsyncMock()
    
    channel_manager = Mock()
    channel_manager.sync_guild_channels = AsyncMock(return_value={'channels_found': 2, 'channels_added': 0})
    channel_manager.discover_target_channel = Mock(return_value="1372012942848954388")
    channel_manager.mark_channel_for_listening = Mock()
    
    return ingestion_service, channel_manager

@pytest.fixture
def mock_discord_client():
    """Mock Discord client with guild and channel data."""
    client = Mock()
    client.is_ready.return_value = True
    client.latency = 0.038
    
    # Mock user
    user = Mock()
    user.name = "TestBot"
    user.discriminator = "1234"
    client.user = user
    
    # Mock guild
    guild = Mock()
    guild.name = "Test Guild"
    guild.id = 123456789
    
    # Mock channel
    channel = Mock()
    channel.name = "test-channel"
    channel.id = 1372012942848954388
    
    guild.channels = [channel]
    client.guilds = [guild]
    
    return client

@pytest.mark.asyncio
async def test_on_ready_logs_connection(mock_flask_app, mock_services, mock_discord_client, caplog):
    """Test that on_ready logs connection events properly."""
    from features.discord_bot.bot import TradingDiscordBot
    
    ingestion_service, channel_manager = mock_services
    
    # Create bot instance
    with patch('features.discord_bot.bot.discord.Client'):
        bot = TradingDiscordBot(
            ingestion_service=ingestion_service,
            channel_manager=channel_manager,
            flask_app=mock_flask_app
        )
        
        # Mock the client
        bot.client = mock_discord_client
        bot.aplus_setups_channel_id = "1372012942848954388"
    
    # Mock publish_event_async from the correct import path
    with patch('common.events.publisher.publish_event_async') as mock_publish:
        # Trigger on_ready event
        with caplog.at_level(logging.INFO):
            await bot.on_ready()
    
    # Assert log messages
    log_messages = [record.message for record in caplog.records]
    assert any("Discord bot connected as" in msg for msg in log_messages)
    assert any("Target channel configured" in msg for msg in log_messages)
    
    # Verify channel manager methods were called
    channel_manager.sync_guild_channels.assert_called_once()
    channel_manager.discover_target_channel.assert_called_once()
    channel_manager.mark_channel_for_listening.assert_called_once()

@pytest.mark.asyncio
async def test_trigger_ingestion_publishes_event(mock_flask_app, mock_services):
    """Test that _trigger_ingestion publishes the correct event."""
    from features.discord_bot.bot import TradingDiscordBot
    
    ingestion_service, channel_manager = mock_services
    
    # Create bot instance
    with patch('features.discord_bot.bot.discord.Client'):
        bot = TradingDiscordBot(
            ingestion_service=ingestion_service,
            channel_manager=channel_manager,
            flask_app=mock_flask_app
        )
    
    # Mock message
    message = Mock()
    message.id = "123456789"
    message.channel.id = "1372012942848954388"
    message.author.name = "TestUser"
    message.content = "Test message content"
    message.created_at = datetime.utcnow()
    
    # Mock publish_event_async from the correct import path
    with patch('common.events.publisher.publish_event_async') as mock_publish:
        await bot._trigger_ingestion(message)
    
    # Assert publish_event_async was called with correct parameters
    mock_publish.assert_called_once()
    call_args = mock_publish.call_args
    
    # Verify event type
    assert call_args[1]['event_type'] == 'discord.message.new'
    assert call_args[1]['channel'] == 'discord'
    
    # Verify event data contains message information
    event_data = call_args[1]['data']
    assert event_data['message_id'] == "123456789"
    assert event_data['channel_id'] == "1372012942848954388"
    assert event_data['author'] == "TestUser"

@pytest.mark.asyncio
async def test_on_message_flow_logging(mock_flask_app, mock_services, mock_discord_client, caplog):
    """Test that on_message flow includes proper logging."""
    from features.discord_bot.bot import TradingDiscordBot
    
    ingestion_service, channel_manager = mock_services
    
    # Create bot instance
    with patch('features.discord_bot.bot.discord.Client'):
        bot = TradingDiscordBot(
            ingestion_service=ingestion_service,
            channel_manager=channel_manager,
            flask_app=mock_flask_app
        )
        
        bot.client = mock_discord_client
        bot.aplus_setups_channel_id = "1372012942848954388"
    
    # Mock message from target channel
    message = Mock()
    message.id = "123456789"
    message.channel.id = "1372012942848954388"
    message.channel.name = "aplus-setups"
    message.author.name = "TestUser"
    message.author.bot = False
    message.content = "Test A+ setup message"
    message.created_at = datetime.utcnow()
    
    # Mock _trigger_ingestion
    with patch.object(bot, '_trigger_ingestion', new_callable=AsyncMock) as mock_trigger:
        with caplog.at_level(logging.INFO):
            await bot.on_message(message)
    
    # Verify _trigger_ingestion was called
    mock_trigger.assert_called_once_with(message)
    
    # Check that logging includes message reception
    log_messages = [record.message for record in caplog.records]
    assert any("[on_message]" in msg and "Received message" in msg for msg in log_messages)

@pytest.mark.asyncio
async def test_on_message_ignores_wrong_channel(mock_flask_app, mock_services, mock_discord_client, caplog):
    """Test that on_message ignores messages from wrong channels."""
    from features.discord_bot.bot import TradingDiscordBot
    
    ingestion_service, channel_manager = mock_services
    
    # Create bot instance
    with patch('features.discord_bot.bot.discord.Client'):
        bot = TradingDiscordBot(
            ingestion_service=ingestion_service,
            channel_manager=channel_manager,
            flask_app=mock_flask_app
        )
        
        bot.client = mock_discord_client
        bot.aplus_setups_channel_id = "1372012942848954388"
    
    # Mock message from different channel
    message = Mock()
    message.id = "123456789"
    message.channel.id = "9999999999"  # Different channel
    message.channel.name = "general"
    message.author.name = "TestUser"
    message.author.bot = False
    message.content = "Random message"
    
    # Mock _trigger_ingestion to ensure it's not called
    with patch.object(bot, '_trigger_ingestion', new_callable=AsyncMock) as mock_trigger:
        with caplog.at_level(logging.DEBUG):
            await bot.on_message(message)
    
    # Verify _trigger_ingestion was NOT called
    mock_trigger.assert_not_called()
    
    # Check debug log for channel filtering
    log_messages = [record.message for record in caplog.records]
    assert any("Ignored message from channel ID" in msg for msg in log_messages)

def test_bot_uptime_tracking(mock_flask_app, mock_services):
    """Test that bot tracks uptime properly."""
    from features.discord_bot.bot import TradingDiscordBot
    
    ingestion_service, channel_manager = mock_services
    
    # Create bot instance
    with patch('features.discord_bot.bot.discord.Client'):
        bot = TradingDiscordBot(
            ingestion_service=ingestion_service,
            channel_manager=channel_manager,
            flask_app=mock_flask_app
        )
    
    # Verify start time is set
    assert hasattr(bot, '_start_time')
    assert isinstance(bot._start_time, datetime)
    
    # Test uptime calculation
    uptime = bot.get_uptime_seconds()
    assert isinstance(uptime, (int, float))
    assert uptime >= 0

if __name__ == "__main__":
    pytest.main([__file__])
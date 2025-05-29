"""
Centralized Test Fixtures and Utilities

Provides shared fixtures and utilities for all tests to reduce duplication
and enable slice-safe testing with proper isolation.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from features.discord_bot.dto import RawMessageDto
from features.ingestion.service import IngestionService
from features.ingestion.interfaces import IIngestionService
from common.models import DiscordMessageDTO


@pytest.fixture
def sample_raw_message():
    """Sample raw Discord message for testing."""
    return RawMessageDto(
        message_id="123456789",
        channel_id="999888777",
        author_id="abc123def",
        author_name="TestUser",
        content="Sample test message content",
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def sample_discord_message_dto():
    """Sample Discord message DTO for testing."""
    return DiscordMessageDTO(
        message_id="123456789",
        channel_id="999888777", 
        author_id="abc123def",
        content="Sample test message content",
        created_at=datetime.utcnow(),
        is_setup=False,
        processed=False,
        embed_data={}
    )


@pytest.fixture
def fake_ingestion_service():
    """Mock ingestion service for testing Discord bot integration."""
    service = AsyncMock(spec=IIngestionService)
    service.ingest_raw_message = AsyncMock()
    service.ingest_latest_messages = AsyncMock(return_value={
        'status': 'completed',
        'statistics': {'total': 1, 'stored': 1, 'skipped': 0, 'errors': 0}
    })
    service.ingest_channel_history = AsyncMock(return_value={
        'success': True,
        'statistics': {'total': 5, 'stored': 5, 'skipped': 0, 'errors': 0}
    })
    service.get_last_triggered = MagicMock(return_value=None)
    return service


@pytest.fixture
def mock_discord_client():
    """Mock Discord client for testing bot behavior."""
    client = MagicMock()
    client.get_channel = MagicMock()
    client.guilds = []
    client.user = MagicMock()
    client.user.id = "bot_user_id"
    client.user.name = "TestBot"
    return client


@pytest.fixture
def mock_discord_channel():
    """Mock Discord channel for testing."""
    channel = MagicMock()
    channel.id = 999888777
    channel.name = "test-channel"
    channel.guild.id = 111222333
    channel.guild.name = "Test Guild"
    return channel


@pytest.fixture
def mock_discord_message(mock_discord_channel):
    """Mock Discord message for testing."""
    message = MagicMock()
    message.id = 123456789
    message.channel = mock_discord_channel
    message.author.id = "user123"
    message.author.name = "TestUser"
    message.content = "Test message content"
    message.created_at = datetime.utcnow()
    return message


@pytest.fixture
def sample_batch_result():
    """Sample batch processing result for testing."""
    return {
        "total": 10,
        "stored": 8,
        "skipped": 1,
        "errors": 1,
        "errors_list": [
            {
                'message_id': 'error_msg_123',
                'error': 'Validation failed'
            }
        ]
    }


@pytest.fixture
def sample_channel_data():
    """Sample channel data for testing."""
    return {
        'channel_id': '999888777',
        'channel_name': 'test-channel',
        'guild_id': '111222333',
        'guild_name': 'Test Guild',
        'channel_type': 'text',
        'is_active': True
    }


@pytest.fixture
def mock_event_publisher():
    """Mock event publisher for testing event publishing."""
    publisher = MagicMock()
    publisher.publish_event = MagicMock(return_value=True)
    return publisher


@pytest.fixture
def mock_database_session():
    """Mock database session for testing database operations."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.query = MagicMock()
    return session
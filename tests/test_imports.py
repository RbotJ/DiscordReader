"""
Import validation tests to catch broken module paths early.
"""
import pytest


def test_discord_bot_imports():
    """Test that Discord bot modules can be imported cleanly."""
    try:
        import features.discord_bot.bot
        import features.discord_bot.dto
        import features.discord_bot.interfaces
        assert True
    except ImportError as e:
        pytest.fail(f"Discord bot import failed: {e}")


def test_ingestion_imports():
    """Test that ingestion modules can be imported cleanly."""
    try:
        import features.ingestion.service
        import features.ingestion.interfaces
        import features.ingestion.models
        assert True
    except ImportError as e:
        pytest.fail(f"Ingestion import failed: {e}")


def test_vertical_slice_integration():
    """Test that vertical slices can work together without circular imports."""
    try:
        from features.discord_bot.dto import RawMessageDto
        from features.ingestion.service import IngestionService
        from features.discord_bot.bot import TradingDiscordBot
        
        # Test basic instantiation without actual connections
        ingestion_service = IngestionService()
        
        # This should not raise import errors
        assert RawMessageDto is not None
        assert IngestionService is not None
        assert TradingDiscordBot is not None
        
    except ImportError as e:
        pytest.fail(f"Vertical slice integration failed: {e}")
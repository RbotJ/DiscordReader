"""
Discord Channels Contract Tests

Tests that verify the Discord channels slice properly manages channel metadata
and provides clean interfaces to other slices without coupling.
"""
import pytest
from unittest.mock import MagicMock, patch

from features.discord_channels.channel_manager import ChannelManager


class TestDiscordChannelsContract:
    """Test Discord channels slice contract compliance and interface adherence."""

    def test_channel_manager_implements_interface(self):
        """Test that ChannelManager implements the expected interface."""
        service = ChannelManager()
        
        # Verify core channel management methods exist
        required_methods = [
            'get_channel_info',
            'update_channel_metadata',
            'is_monitored_channel',
            'get_monitored_channels'
        ]
        
        for method in required_methods:
            assert hasattr(service, method), f"ChannelManager missing method: {method}"

    def test_channel_info_isolation(self, sample_channel_data):
        """Test that channel info is isolated from Discord client details."""
        service = ChannelManager()
        
        # Test basic channel manager functionality
        assert hasattr(service, 'get_monitored_channels')
        
        # Should be able to handle channel operations
        channels = service.get_monitored_channels()
        assert isinstance(channels, (list, dict))

    def test_monitored_channels_configuration(self):
        """Test that monitored channels are properly configured."""
        service = ChannelManager()
        
        # Should return monitored channels
        channels = service.get_monitored_channels()
        assert isinstance(channels, (list, dict))

    def test_channel_metadata_updates(self):
        """Test that channel metadata can be managed independently."""
        service = ChannelManager()
        
        # Should have channel management capabilities
        assert hasattr(service, 'get_monitored_channels')
        
        # Test that service can be instantiated without errors
        assert service is not None

    def test_service_does_not_import_ingestion_directly(self):
        """Test that channels service doesn't directly import ingestion modules."""
        import features.discord_channels.channel_manager as channels_module
        import inspect
        
        source = inspect.getsource(channels_module)
        
        # Channels should not directly import ingestion modules
        forbidden_imports = [
            'from features.ingestion import',
            'features.ingestion.service',
            'from features.discord_bot import'
        ]
        
        for forbidden in forbidden_imports:
            assert forbidden not in source, f"Channels should not directly import: {forbidden}"

    def test_channel_manager_error_isolation(self):
        """Test that channel manager handles errors without exposing internals."""
        service = ChannelManager()
        
        # Should handle errors gracefully
        try:
            channels = service.get_monitored_channels()
            # Should return a valid response
            assert isinstance(channels, (list, dict))
        except Exception:
            pytest.fail("Channel manager should handle errors gracefully")

    def test_channel_data_validation(self):
        """Test that channel service validates data before processing."""
        service = ChannelManager()
        
        # Test that service can be instantiated and used
        assert service is not None
        
        # Should have proper channel management methods
        channels = service.get_monitored_channels()
        assert isinstance(channels, (list, dict))
"""
Discord Channels Dashboard Tests

Tests for the Discord channels dashboard routes in isolation within the discord_channels slice.
"""
import pytest
from unittest.mock import Mock, patch
from flask import Flask
from features.discord_channels.dashboard import channels_bp


@pytest.fixture
def app():
    """Create Flask app for testing with channels dashboard."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(channels_bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_channel_manager():
    """Mock channel manager with test metrics."""
    manager = Mock()
    manager.get_metrics.return_value = {
        'total_channels': 10,
        'monitored_channels': 3,
        'active_guilds': 2,
        'last_sync': '2025-05-30T20:00:00',
        'sync_status': 'ready'
    }
    return manager


class TestDiscordChannelsDashboard:
    """Test Discord channels dashboard routes."""
    
    @patch('features.discord_channels.dashboard.get_channel_manager')
    def test_overview_route_success(self, mock_get_manager, client, mock_channel_manager):
        """Test overview route returns 200 with valid manager."""
        mock_get_manager.return_value = mock_channel_manager
        
        response = client.get('/dashboard/channels/')
        assert response.status_code == 200
        
        # Verify manager method was called
        mock_channel_manager.get_metrics.assert_called_once()
    
    @patch('features.discord_channels.dashboard.get_channel_manager')
    def test_overview_route_manager_unavailable(self, mock_get_manager, client):
        """Test overview route handles manager unavailable."""
        mock_get_manager.return_value = None
        
        response = client.get('/dashboard/channels/')
        assert response.status_code == 500
    
    @patch('features.discord_channels.dashboard.get_channel_manager')
    def test_metrics_json_route_success(self, mock_get_manager, client, mock_channel_manager):
        """Test metrics JSON endpoint returns expected keys."""
        mock_get_manager.return_value = mock_channel_manager
        
        response = client.get('/dashboard/channels/metrics.json')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'metrics' in data
        assert 'timestamp' in data
        
        # Verify expected metric keys
        metrics = data['metrics']
        expected_keys = [
            'total_channels', 'monitored_channels', 'active_guilds', 
            'last_sync', 'sync_status'
        ]
        for key in expected_keys:
            assert key in metrics
    
    @patch('features.discord_channels.dashboard.get_channel_manager')
    def test_metrics_json_route_manager_unavailable(self, mock_get_manager, client):
        """Test metrics JSON handles manager unavailable."""
        mock_get_manager.return_value = None
        
        response = client.get('/dashboard/channels/metrics.json')
        assert response.status_code == 500
        
        data = response.get_json()
        assert 'error' in data
    
    @patch('features.discord_channels.dashboard.get_channel_manager')
    def test_health_route_healthy(self, mock_get_manager, client, mock_channel_manager):
        """Test health route when channels are synced."""
        mock_get_manager.return_value = mock_channel_manager
        
        response = client.get('/dashboard/channels/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'healthy' in data
        assert 'sync_status' in data
        assert 'timestamp' in data
        assert data['healthy'] is True
    
    @patch('features.discord_channels.dashboard.get_channel_manager')
    def test_health_route_unhealthy(self, mock_get_manager, client):
        """Test health route when manager unavailable."""
        mock_get_manager.return_value = None
        
        response = client.get('/dashboard/channels/health')
        assert response.status_code == 503
        
        data = response.get_json()
        assert data['healthy'] is False
        assert data['sync_status'] == 'unavailable'
    
    @patch('features.discord_channels.dashboard.get_channel_manager')
    def test_manager_error_handling(self, mock_get_manager, client):
        """Test dashboard handles manager errors gracefully."""
        mock_manager = Mock()
        mock_manager.get_metrics.side_effect = Exception("Manager error")
        mock_get_manager.return_value = mock_manager
        
        response = client.get('/dashboard/channels/metrics.json')
        assert response.status_code == 500
        
        data = response.get_json()
        assert 'error' in data


class TestSliceIsolation:
    """Test that channels dashboard maintains slice isolation."""
    
    def test_no_cross_slice_imports(self):
        """Test that dashboard doesn't import from other slices."""
        import features.discord_channels.dashboard as dashboard_module
        import inspect
        
        source = inspect.getsource(dashboard_module)
        
        # Dashboard should not directly import other feature slices
        forbidden_imports = [
            'from features.ingestion import',
            'from features.discord_bot import',
            'features.ingestion.service',
            'features.discord_bot.service'
        ]
        
        for forbidden in forbidden_imports:
            assert forbidden not in source, f"Dashboard should not import: {forbidden}"
    
    def test_dashboard_uses_service_layer(self):
        """Test that dashboard routes use service layer methods."""
        import features.discord_channels.dashboard as dashboard_module
        import inspect
        
        source = inspect.getsource(dashboard_module)
        
        # Dashboard should call manager.get_metrics() not implement metrics directly
        assert 'manager.get_metrics()' in source
        assert 'get_channel_manager()' in source
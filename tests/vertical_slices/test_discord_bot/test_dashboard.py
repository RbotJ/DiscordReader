"""
Discord Bot Dashboard Tests

Tests for the Discord bot dashboard routes in isolation within the discord_bot slice.
"""
import pytest
from unittest.mock import Mock, patch
from flask import Flask
from features.discord_bot.dashboard import discord_bp


@pytest.fixture
def app():
    """Create Flask app for testing with discord bot dashboard."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(discord_bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_bot_service():
    """Mock bot service with test metrics."""
    service = Mock()
    service.get_metrics.return_value = {
        'status': 'connected',
        'uptime_seconds': 3600,
        'messages_processed_today': 42,
        'messages_per_minute': 5,
        'channels_monitored': 3,
        'error_count_last_hour': 0,
        'last_activity': '2025-05-30T20:00:00',
        'connection_attempts': 5,
        'successful_connections': 5,
        'last_ready': '2025-05-30T19:00:00',
        'error_message': None
    }
    return service


class TestDiscordBotDashboard:
    """Test Discord bot dashboard routes."""
    
    @patch('features.discord_bot.dashboard.get_bot_service')
    def test_overview_route_success(self, mock_get_service, client, mock_bot_service):
        """Test overview route returns 200 with valid service."""
        mock_get_service.return_value = mock_bot_service
        
        response = client.get('/dashboard/discord/')
        assert response.status_code == 200
        
        # Verify service method was called
        mock_bot_service.get_metrics.assert_called_once()
    
    @patch('features.discord_bot.dashboard.get_bot_service')
    def test_overview_route_service_unavailable(self, mock_get_service, client):
        """Test overview route handles service unavailable."""
        mock_get_service.return_value = None
        
        response = client.get('/dashboard/discord/')
        assert response.status_code == 500
    
    @patch('features.discord_bot.dashboard.get_bot_service')
    def test_metrics_json_route_success(self, mock_get_service, client, mock_bot_service):
        """Test metrics JSON endpoint returns expected keys."""
        mock_get_service.return_value = mock_bot_service
        
        response = client.get('/dashboard/discord/metrics.json')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'metrics' in data
        assert 'timestamp' in data
        
        # Verify expected metric keys
        metrics = data['metrics']
        expected_keys = [
            'status', 'uptime_seconds', 'messages_processed_today',
            'messages_per_minute', 'channels_monitored', 'error_count_last_hour'
        ]
        for key in expected_keys:
            assert key in metrics
    
    @patch('features.discord_bot.dashboard.get_bot_service')
    def test_metrics_json_route_service_unavailable(self, mock_get_service, client):
        """Test metrics JSON handles service unavailable."""
        mock_get_service.return_value = None
        
        response = client.get('/dashboard/discord/metrics.json')
        assert response.status_code == 500
        
        data = response.get_json()
        assert 'error' in data
    
    @patch('features.discord_bot.dashboard.get_bot_service')
    def test_health_route_healthy(self, mock_get_service, client, mock_bot_service):
        """Test health route when bot is connected."""
        mock_get_service.return_value = mock_bot_service
        
        response = client.get('/dashboard/discord/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'healthy' in data
        assert 'status' in data
        assert 'timestamp' in data
        assert data['healthy'] is True
    
    @patch('features.discord_bot.dashboard.get_bot_service')
    def test_health_route_unhealthy(self, mock_get_service, client):
        """Test health route when bot service unavailable."""
        mock_get_service.return_value = None
        
        response = client.get('/dashboard/discord/health')
        assert response.status_code == 503
        
        data = response.get_json()
        assert data['healthy'] is False
        assert data['status'] == 'unavailable'
    
    @patch('features.discord_bot.dashboard.get_bot_service')
    def test_service_error_handling(self, mock_get_service, client):
        """Test dashboard handles service errors gracefully."""
        mock_service = Mock()
        mock_service.get_metrics.side_effect = Exception("Service error")
        mock_get_service.return_value = mock_service
        
        response = client.get('/dashboard/discord/metrics.json')
        assert response.status_code == 500
        
        data = response.get_json()
        assert 'error' in data


class TestSliceIsolation:
    """Test that Discord bot dashboard maintains slice isolation."""
    
    def test_no_cross_slice_imports(self):
        """Test that dashboard doesn't import from other slices."""
        import features.discord_bot.dashboard as dashboard_module
        import inspect
        
        source = inspect.getsource(dashboard_module)
        
        # Dashboard should not directly import other feature slices
        forbidden_imports = [
            'from features.ingestion import',
            'from features.discord_channels import',
            'features.ingestion.service',
            'features.discord_channels.channel_manager'
        ]
        
        for forbidden in forbidden_imports:
            assert forbidden not in source, f"Dashboard should not import: {forbidden}"
    
    def test_dashboard_uses_service_layer(self):
        """Test that dashboard routes use service layer methods."""
        import features.discord_bot.dashboard as dashboard_module
        import inspect
        
        source = inspect.getsource(dashboard_module)
        
        # Dashboard should call service.get_metrics() not implement metrics directly
        assert 'service.get_metrics()' in source
        assert 'get_bot_service()' in source
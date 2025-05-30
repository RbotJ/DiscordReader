"""
Ingestion Dashboard Tests

Tests for the ingestion dashboard routes in isolation within the ingestion slice.
"""
import pytest
from unittest.mock import Mock, patch
from flask import Flask
from features.ingestion.dashboard import ingest_bp


@pytest.fixture
def app():
    """Create Flask app for testing with ingestion dashboard."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(ingest_bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_ingestion_service():
    """Mock ingestion service with test metrics."""
    service = Mock()
    service.get_metrics.return_value = {
        'messages_processed_today': 150,
        'processing_rate_per_minute': 12,
        'validation_success_rate': 98.5,
        'validation_failures_today': 3,
        'last_processed_message': '2025-05-30T20:00:00',
        'queue_depth': 5,
        'avg_processing_time_ms': 45,
        'status': 'ready'
    }
    return service


class TestIngestionDashboard:
    """Test ingestion dashboard routes."""
    
    @patch('features.ingestion.dashboard.get_ingestion_service')
    def test_overview_route_success(self, mock_get_service, client, mock_ingestion_service):
        """Test overview route returns 200 with valid service."""
        mock_get_service.return_value = mock_ingestion_service
        
        response = client.get('/dashboard/ingestion/')
        assert response.status_code == 200
        
        # Verify service method was called
        mock_ingestion_service.get_metrics.assert_called_once()
    
    @patch('features.ingestion.dashboard.get_ingestion_service')
    def test_overview_route_service_unavailable(self, mock_get_service, client):
        """Test overview route handles service unavailable."""
        mock_get_service.return_value = None
        
        response = client.get('/dashboard/ingestion/')
        assert response.status_code == 500
    
    @patch('features.ingestion.dashboard.get_ingestion_service')
    def test_metrics_json_route_success(self, mock_get_service, client, mock_ingestion_service):
        """Test metrics JSON endpoint returns expected keys."""
        mock_get_service.return_value = mock_ingestion_service
        
        response = client.get('/dashboard/ingestion/metrics.json')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'metrics' in data
        assert 'timestamp' in data
        
        # Verify expected metric keys
        metrics = data['metrics']
        expected_keys = [
            'messages_processed_today', 'processing_rate_per_minute', 
            'validation_success_rate', 'validation_failures_today',
            'last_processed_message', 'queue_depth', 'avg_processing_time_ms', 'status'
        ]
        for key in expected_keys:
            assert key in metrics
    
    @patch('features.ingestion.dashboard.get_ingestion_service')
    def test_metrics_json_route_service_unavailable(self, mock_get_service, client):
        """Test metrics JSON handles service unavailable."""
        mock_get_service.return_value = None
        
        response = client.get('/dashboard/ingestion/metrics.json')
        assert response.status_code == 500
        
        data = response.get_json()
        assert 'error' in data
    
    @patch('features.ingestion.dashboard.get_ingestion_service')
    def test_health_route_healthy(self, mock_get_service, client, mock_ingestion_service):
        """Test health route when ingestion is processing."""
        mock_get_service.return_value = mock_ingestion_service
        
        response = client.get('/dashboard/ingestion/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'healthy' in data
        assert 'status' in data
        assert 'timestamp' in data
        assert data['healthy'] is True
    
    @patch('features.ingestion.dashboard.get_ingestion_service')
    def test_health_route_unhealthy(self, mock_get_service, client):
        """Test health route when service unavailable."""
        mock_get_service.return_value = None
        
        response = client.get('/dashboard/ingestion/health')
        assert response.status_code == 503
        
        data = response.get_json()
        assert data['healthy'] is False
        assert data['status'] == 'unavailable'
    
    @patch('features.ingestion.dashboard.get_ingestion_service')
    def test_service_error_handling(self, mock_get_service, client):
        """Test dashboard handles service errors gracefully."""
        mock_service = Mock()
        mock_service.get_metrics.side_effect = Exception("Service error")
        mock_get_service.return_value = mock_service
        
        response = client.get('/dashboard/ingestion/metrics.json')
        assert response.status_code == 500
        
        data = response.get_json()
        assert 'error' in data


class TestSliceIsolation:
    """Test that ingestion dashboard maintains slice isolation."""
    
    def test_no_cross_slice_imports(self):
        """Test that dashboard doesn't import from other slices."""
        import features.ingestion.dashboard as dashboard_module
        import inspect
        
        source = inspect.getsource(dashboard_module)
        
        # Dashboard should not directly import other feature slices
        forbidden_imports = [
            'from features.discord_bot import',
            'from features.discord_channels import',
            'features.discord_bot.service',
            'features.discord_channels.channel_manager'
        ]
        
        for forbidden in forbidden_imports:
            assert forbidden not in source, f"Dashboard should not import: {forbidden}"
    
    def test_dashboard_uses_service_layer(self):
        """Test that dashboard routes use service layer methods."""
        import features.ingestion.dashboard as dashboard_module
        import inspect
        
        source = inspect.getsource(dashboard_module)
        
        # Dashboard should call service.get_metrics() not implement metrics directly
        assert 'service.get_metrics()' in source
        assert 'get_ingestion_service()' in source
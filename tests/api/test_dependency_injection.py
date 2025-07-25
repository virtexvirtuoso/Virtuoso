"""Integration tests for API dependency injection with Container system."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class TestAPIDependencyInjection:
    """Test suite for API dependency injection patterns."""
    
    @pytest.fixture
    def mock_app_state(self):
        """Create mock app state with all required components."""
        state = MagicMock()
        
        # Mock all required components
        state.config_manager = MagicMock()
        state.exchange_manager = MagicMock()
        state.database_client = MagicMock()
        state.portfolio_analyzer = MagicMock()
        state.confluence_analyzer = MagicMock()
        state.alert_manager = MagicMock()
        state.metrics_manager = MagicMock()
        state.validation_service = MagicMock()
        state.top_symbols_manager = MagicMock()
        state.market_reporter = MagicMock()
        state.market_monitor = MagicMock()
        state.market_data_manager = MagicMock()
        state.container = MagicMock()
        
        return state
    
    def test_dependency_functions_exist(self):
        """Test that all dependency functions are defined."""
        from src.api.core.dependencies import (
            get_config_manager, get_exchange_manager, get_database_client,
            get_confluence_analyzer, get_alert_manager, get_market_reporter,
            get_validation_service, get_top_symbols_manager, get_metrics_manager,
            get_market_monitor, get_market_data_manager, get_container
        )
        
        # If we can import all these, they exist
        assert get_config_manager is not None
        assert get_exchange_manager is not None
        assert get_database_client is not None
        assert get_confluence_analyzer is not None
        assert get_alert_manager is not None
        assert get_market_reporter is not None
        assert get_validation_service is not None
        assert get_top_symbols_manager is not None
        assert get_metrics_manager is not None
        assert get_market_monitor is not None
        assert get_market_data_manager is not None
        assert get_container is not None
    
    @pytest.mark.asyncio
    async def test_dependency_error_handling(self):
        """Test that dependency functions raise HTTPException when components missing."""
        from fastapi import Request, HTTPException
        from src.api.core.dependencies import get_config_manager
        
        # Create mock request with missing component
        mock_request = MagicMock(spec=Request)
        mock_request.app.state = MagicMock()
        mock_request.app.state.config_manager = None
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_config_manager(mock_request)
        
        assert exc_info.value.status_code == 500
        assert "not initialized" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_dependency_returns_component(self, mock_app_state):
        """Test that dependency functions return correct components."""
        from fastapi import Request
            get_config_manager, get_exchange_manager, get_alert_manager
        )
        
        # Create mock request with components
        mock_request = MagicMock(spec=Request)
        mock_request.app.state = mock_app_state
        
        # Test getting components
        config = await get_config_manager(mock_request)
        assert config == mock_app_state.config_manager
        
        exchange = await get_exchange_manager(mock_request)
        assert exchange == mock_app_state.exchange_manager
        
        alerts = await get_alert_manager(mock_request)
        assert alerts == mock_app_state.alert_manager
    
    def test_interactive_reports_no_globals(self):
        """Test that interactive reports route doesn't use global variables."""
        # Read the file to check for globals
        route_file = Path(__file__).parent.parent.parent / "src" / "api" / "routes" / "interactive_reports.py"
        
        with open(route_file, 'r') as f:
            content = f.read()
        
        # Check that problematic globals are removed
        assert "global interactive_generator" not in content
        assert "Depends(get_config_manager)" in content
    
    def test_market_routes_use_centralized_deps(self):
        """Test that market routes use centralized dependencies."""
        route_file = Path(__file__).parent.parent.parent / "src" / "api" / "routes" / "market.py"
        
        with open(route_file, 'r') as f:
            content = f.read()
        
        # Check imports
        assert "from src.api.core.dependencies import" in content
        # Should not define local dependency functions
        assert "async def get_exchange_manager(request: Request)" not in content
    
    def test_alpha_routes_use_centralized_deps(self):
        """Test that alpha routes use centralized dependencies."""
        route_file = Path(__file__).parent.parent.parent / "src" / "api" / "routes" / "alpha.py"
        
        with open(route_file, 'r') as f:
            content = f.read()
        
        # Check imports
        assert "from src.api.core.dependencies import" in content


class TestAPIRouteIntegration:
    """Test API routes work with Container-injected dependencies."""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock components for testing."""
        return {
            'config_manager': MagicMock(),
            'exchange_manager': MagicMock(),
            'market_reporter': MagicMock(),
            'alert_manager': MagicMock()
        }
    
    @pytest.fixture
    def test_client_with_mocks(self, mock_components):
        """Create test client with mocked dependencies."""
        # Import app here to avoid import issues
        with patch('src.main.app_container'):
            from src.main import app
            
            # Mock app state
            for name, component in mock_components.items():
                setattr(app.state, name, component)
            
            # Create test client
            with TestClient(app) as client:
                yield client
    
    def test_health_endpoint(self, test_client_with_mocks):
        """Test health endpoint works with Container system."""
        response = test_client_with_mocks.get("/health")
        
        # May return 200 or 503 depending on component state
        assert response.status_code in [200, 503]
    
    def test_api_endpoints_accessible(self, test_client_with_mocks):
        """Test that API endpoints are accessible."""
        # Test a few key endpoints
        endpoints = [
            "/api/market/exchanges",
            "/api/alerts/recent",
            "/api/signals/latest"
        ]
        
        for endpoint in endpoints:
            response = test_client_with_mocks.get(endpoint)
            # Should not return 404 (route exists)
            assert response.status_code != 404


class TestContainerFastAPIIntegration:
    """Test Container integration with FastAPI lifespan."""
    
    @pytest.mark.asyncio
    async def test_lifespan_creates_container(self):
        """Test that FastAPI lifespan creates Container properly."""
        from src.main import lifespan
        from fastapi import FastAPI
        
        # Create mock app
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        
        # Mock Container creation
        with patch('src.main.Container') as MockContainer:
            with patch('src.main.ConfigManager') as MockConfigManager:
                # Setup mocks
                mock_container = MagicMock()
                mock_container.register_trading_components = MagicMock()
                mock_container.initialize = AsyncMock()
                mock_container.cleanup = AsyncMock()
                mock_container.get_component = MagicMock(return_value=None)
                MockContainer.return_value = mock_container
                
                mock_config = MagicMock()
                MockConfigManager.return_value = mock_config
                
                # Run lifespan
                async with lifespan(mock_app):
                    # Verify Container was created
                    MockContainer.assert_called_once()
                    
                    # Verify trading components registered
                    mock_container.register_trading_components.assert_called_once_with(mock_config)
                    
                    # Verify initialization
                    mock_container.initialize.assert_called_once_with(include_trading_components=True)
                
                # Verify cleanup after context exit
                mock_container.cleanup.assert_called_once_with(cleanup_trading_components=True)
    
    @pytest.mark.asyncio  
    async def test_lifespan_injects_components(self):
        """Test that lifespan injects components into app.state."""
        
        # Create mock app
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        
        # Mock components
        mock_components = {
            'config_manager': MagicMock(),
            'exchange_manager': MagicMock(),
            'alert_manager': MagicMock()
        }
        
        with patch('src.main.Container') as MockContainer:
            with patch('src.main.ConfigManager'):
                # Setup container mock
                mock_container = MagicMock()
                mock_container.register_trading_components = MagicMock()
                mock_container.initialize = AsyncMock()
                mock_container.cleanup = AsyncMock()
                mock_container.get_component = MagicMock(
                    side_effect=lambda name: mock_components.get(name)
                )
                MockContainer.return_value = mock_container
                
                # Run lifespan
                async with lifespan(mock_app):
                    # Verify components injected into app.state
                    assert mock_app.state.config_manager == mock_components['config_manager']
                    assert mock_app.state.exchange_manager == mock_components['exchange_manager']
                    assert mock_app.state.alert_manager == mock_components['alert_manager']
                    assert mock_app.state.container == mock_container


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
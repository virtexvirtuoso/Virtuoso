"""Unit tests for Container integration with trading components."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.container import Container
from src.config.manager import ConfigManager


class TestContainerIntegration:
    """Test suite for Container integration with trading components."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock ConfigManager for testing."""
        config_manager = MagicMock(spec=ConfigManager)
        config_manager.config = {
            'exchanges': {'bybit': {'enabled': True}},
            'monitoring': {'alerts': {'discord': {'enabled': True}}},
            'analysis': {'indicators': {'technical': {'enabled': True}}}
        }
        return config_manager
    
    @pytest.fixture
    def container_settings(self):
        """Default container settings for testing."""
        return {
            'logging': {'level': 'INFO'},
            'resources': {
                'max_memory_mb': 512,
                'max_concurrent_ops': 50
            }
        }
    
    def test_container_creation(self, container_settings):
        """Test that Container can be created with settings."""
        container = Container(settings=container_settings)
        assert container is not None
        assert container.settings == container_settings
        assert hasattr(container, 'logger')
    
    def test_container_has_required_attributes(self, container_settings):
        """Test that Container has all required attributes."""
        container = Container(settings=container_settings)
        
        # Check core attributes
        assert hasattr(container, 'error_handler')
        assert hasattr(container, 'resource_manager')
        assert hasattr(container, 'component_manager')
        assert hasattr(container, '_trading_adapter')
    
    @pytest.mark.asyncio
    async def test_container_base_initialization(self, container_settings):
        """Test Container initialization with base components only."""
        container = Container(settings=container_settings)
        
        # Initialize without trading components
        await container.initialize(include_trading_components=False)
        
        # Verify base initialization completed
        assert container.component_manager is not None
    
    def test_register_trading_components(self, container_settings, mock_config_manager):
        """Test registering trading components with Container."""
        container = Container(settings=container_settings)
        
        # Register trading components
        container.register_trading_components(mock_config_manager)
        
        # Verify trading adapter was created
        assert container._trading_adapter is not None
        assert container._trading_adapter.config_manager == mock_config_manager
    
    @pytest.mark.asyncio
    async def test_container_cleanup(self, container_settings):
        """Test Container cleanup functionality."""
        container = Container(settings=container_settings)
        
        # Initialize and then cleanup
        await container.initialize(include_trading_components=False)
        await container.cleanup(cleanup_trading_components=False)
        
        # Verify cleanup completed without errors
        assert True  # If we get here, cleanup worked
    
    def test_get_component(self, container_settings):
        """Test getting components from Container."""
        container = Container(settings=container_settings)
        
        # Test getting non-existent component
        component = container.get_component('non_existent')
        assert component is None
    
    @pytest.mark.asyncio
    async def test_container_with_trading_components_mock(self, container_settings, mock_config_manager):
        """Test Container with trading components using mocks."""
        container = Container(settings=container_settings)
        
        # Register trading components
        container.register_trading_components(mock_config_manager)
        
        # Mock the trading adapter to avoid real component initialization
        mock_adapter = MagicMock()
        mock_adapter.register_and_initialize_trading_components = AsyncMock()
        mock_adapter.cleanup_trading_components = AsyncMock()
        mock_adapter.get_all_components = MagicMock(return_value={
            'config_manager': mock_config_manager,
            'exchange_manager': MagicMock(),
            'database_client': MagicMock()
        })
        mock_adapter.get_component = MagicMock(side_effect=lambda name: 
            mock_adapter.get_all_components().get(name))
        
        container._trading_adapter = mock_adapter
        
        # Initialize with trading components
        await container.initialize(include_trading_components=True)
        
        # Verify initialization was called
        mock_adapter.register_and_initialize_trading_components.assert_called_once()
        
        # Test getting components
        config = container.get_component('config_manager')
        assert config == mock_config_manager
        
        # Cleanup
        await container.cleanup(cleanup_trading_components=True)
        mock_adapter.cleanup_trading_components.assert_called_once()
    
    def test_get_system_state(self, container_settings):
        """Test getting system state from Container."""
        container = Container(settings=container_settings)
        
        # Get system state
        state = container.get_system_state()
        
        # Verify state structure
        assert isinstance(state, dict)
        assert 'components' in state
        assert 'resources' in state


class TestTradingComponentAdapter:
    """Test suite for TradingComponentAdapter."""
    
    @pytest.fixture
    def mock_container(self):
        """Create a mock Container for testing."""
        return MagicMock(spec=Container)
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock ConfigManager for testing."""
        config_manager = MagicMock(spec=ConfigManager)
        config_manager.config = {'test': True}
        return config_manager
    
    def test_adapter_creation(self, mock_container, mock_config_manager):
        """Test creating TradingComponentAdapter."""
        from src.core.trading_components_adapter import TradingComponentAdapter
        
        adapter = TradingComponentAdapter(mock_container, mock_config_manager)
        assert adapter is not None
        assert adapter.container == mock_container
        assert adapter.config_manager == mock_config_manager
        assert adapter._components == {}
        assert adapter._initialized == {}
    
    @pytest.mark.asyncio
    async def test_adapter_component_initialization(self, mock_container, mock_config_manager):
        """Test adapter component initialization with mocks."""
        
        adapter = TradingComponentAdapter(mock_container, mock_config_manager)
        
        # Mock component
        mock_component = MagicMock()
        mock_component.initialize = AsyncMock()
        
        # Initialize component
        await adapter._initialize_component('test_component', mock_component)
        
        # Verify initialization
        assert adapter._components['test_component'] == mock_component
        assert adapter._initialized['test_component'] is True
        mock_component.initialize.assert_called_once()
    
    def test_adapter_get_component(self, mock_container, mock_config_manager):
        """Test getting components from adapter."""
        
        adapter = TradingComponentAdapter(mock_container, mock_config_manager)
        
        # Add test component
        test_component = MagicMock()
        adapter._components['test'] = test_component
        
        # Get component
        result = adapter.get_component('test')
        assert result == test_component
        
        # Get non-existent component
        result = adapter.get_component('non_existent')
        assert result is None
    
    def test_adapter_initialization_status(self, mock_container, mock_config_manager):
        """Test checking component initialization status."""
        
        adapter = TradingComponentAdapter(mock_container, mock_config_manager)
        
        # Set initialization status
        adapter._initialized['test'] = True
        adapter._initialized['failed'] = False
        
        # Check status
        assert adapter.is_component_initialized('test') is True
        assert adapter.is_component_initialized('failed') is False
        assert adapter.is_component_initialized('unknown') is False


@pytest.mark.asyncio
class TestContainerLifecycle:
    """Test Container lifecycle management."""
    
    async def test_full_lifecycle(self):
        """Test complete Container lifecycle from creation to cleanup."""
        # Create Container
        settings = {
            'logging': {'level': 'INFO'},
            'resources': {'max_memory_mb': 256}
        }
        container = Container(settings=settings)
        
        # Initialize
        await container.initialize(include_trading_components=False)
        
        # Use container
        state = container.get_system_state()
        assert state is not None
        
        # Cleanup
        await container.cleanup(cleanup_trading_components=False)
    
    async def test_error_handling_during_initialization(self):
        """Test Container handles errors during initialization gracefully."""
        container = Container(settings={})
        
        # Mock component manager to raise error
        original_init = container.component_manager.initialize_all
        container.component_manager.initialize_all = AsyncMock(
            side_effect=Exception("Test initialization error")
        )
        
        # Initialize should handle error
        with pytest.raises(Exception) as exc_info:
            await container.initialize(include_trading_components=False)
        
        assert "Test initialization error" in str(exc_info.value)
    
    async def test_cleanup_handles_errors(self):
        """Test Container cleanup handles errors gracefully."""
        container = Container(settings={})
        
        # Mock component manager to raise error during cleanup
        container.component_manager.cleanup_all = AsyncMock(
            side_effect=Exception("Test cleanup error")
        )
        
        # Cleanup should handle error
        with pytest.raises(Exception) as exc_info:
            await container.cleanup(cleanup_trading_components=False)
        
        assert "Test cleanup error" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
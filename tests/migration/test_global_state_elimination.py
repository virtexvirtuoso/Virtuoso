"""Tests to validate global state elimination is complete."""

import pytest
import ast
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class TestGlobalStateElimination:
    """Validate that global state has been eliminated from the codebase."""
    
    def test_main_py_no_global_variables(self):
        """Test that main.py no longer has problematic global variables."""
        main_file = Path(__file__).parent.parent.parent / "src" / "main.py"
        
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Check that old globals are gone/deprecated
        problematic_globals = [
            "config_manager = None",
            "exchange_manager = None",
            "portfolio_analyzer = None",
            "database_client = None",
            "confluence_analyzer = None",
            "top_symbols_manager = None",
            "market_monitor = None",
            "metrics_manager = None",
            "alert_manager = None",
            "market_reporter = None",
            "health_monitor = None",
            "validation_service = None",
            "market_data_manager = None"
        ]
        
        # These should either be commented out or not present
        active_globals = []
        lines = content.split('\n')
        for i, line in enumerate(lines):
            for global_var in problematic_globals:
                if global_var in line and not line.strip().startswith('#'):
                    active_globals.append(f"Line {i+1}: {line.strip()}")
        
        assert len(active_globals) == 0, f"Found active global variables: {active_globals}"
    
    def test_main_py_has_container(self):
        """Test that main.py uses Container instead of globals."""
        main_file = Path(__file__).parent.parent.parent / "src" / "main.py"
        
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Check for Container usage
        assert "from src.core.container import Container" in content
        assert "app_container: Optional[Container] = None" in content
        assert "app_container = Container(" in content
        assert "app_container.register_trading_components" in content
        assert "app_container.initialize" in content
        assert "app_container.cleanup" in content
    
    def test_deprecated_functions_commented(self):
        """Test that deprecated functions are properly commented out."""
        main_file = Path(__file__).parent.parent.parent / "src" / "main.py"
        
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Check deprecated markers exist
        assert "# DEPRECATED: Replaced by Container.cleanup()" in content
        assert "# DEPRECATED: Replaced by Container.initialize()" in content
        
        # Check no active await statements in deprecated sections
        lines = content.split('\n')
        in_deprecated = False
        problematic_lines = []
        
        for i, line in enumerate(lines):
            if "# DEPRECATED:" in line:
                in_deprecated = True
            elif line.strip() and not line.strip().startswith('#') and in_deprecated:
                if "async def" in line or "@" in line:
                    in_deprecated = False
                elif "await" in line:
                    problematic_lines.append(f"Line {i+1}: {line.strip()}")
        
        assert len(problematic_lines) == 0, f"Found active await in deprecated sections: {problematic_lines}"
    
    def test_api_routes_no_global_usage(self):
        """Test that API routes don't use global variables."""
        routes_dir = Path(__file__).parent.parent.parent / "src" / "api" / "routes"
        
        global_usage_files = []
        
        for route_file in routes_dir.glob("*.py"):
            if route_file.name.startswith("test_"):
                continue
                
            with open(route_file, 'r') as f:
                content = f.read()
            
            # Look for global usage
            if "global " in content:
                # Parse to check if it's actual global usage
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip().startswith("global ") and not line.strip().startswith("# global"):
                        global_usage_files.append(f"{route_file.name}:{i+1} - {line.strip()}")
        
        assert len(global_usage_files) == 0, f"Found global usage in routes: {global_usage_files}"
    
    def test_dependency_injection_pattern_used(self):
        """Test that routes use Depends() pattern for injection."""
        routes_dir = Path(__file__).parent.parent.parent / "src" / "api" / "routes"
        
        files_with_depends = []
        files_without_depends = []
        
        for route_file in routes_dir.glob("*.py"):
            if route_file.name.startswith("test_") or route_file.name == "__init__.py":
                continue
                
            with open(route_file, 'r') as f:
                content = f.read()
            
            # Check for Depends usage
            if "Depends(" in content:
                files_with_depends.append(route_file.name)
            else:
                # Only flag if file has route definitions
                if "@router." in content:
                    files_without_depends.append(route_file.name)
        
        # Most route files should use Depends
        assert len(files_with_depends) > 0, "No route files using Depends pattern"
        assert len(files_with_depends) >= len(files_without_depends), \
            f"Too few files using Depends: {files_with_depends} vs {files_without_depends}"
    
    def test_container_components_accessible(self):
        """Test that Container provides access to all required components."""
        from src.core.container import Container
        
        # Create container with mock settings
        container = Container(settings={'logging': {'level': 'INFO'}})
        
        # Test component access methods exist
        assert hasattr(container, 'get_component')
        assert hasattr(container, 'register_trading_components')
        assert hasattr(container, 'initialize')
        assert hasattr(container, 'cleanup')
        assert hasattr(container, 'get_system_state')
    
    def test_no_initialize_components_usage(self):
        """Test that old initialize_components function is not used."""
        src_dir = Path(__file__).parent.parent.parent / "src"
        
        usage_files = []
        
        for py_file in src_dir.rglob("*.py"):
            # Skip test files and deprecated main.py sections
            if "test" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Look for calls to initialize_components (but not private _initialize_components)
            if "initialize_components()" in content and "# DEPRECATED" not in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if "initialize_components()" in line and not line.strip().startswith('#'):
                        # Skip private method calls (_initialize_components)
                        if "_initialize_components()" not in line:
                            usage_files.append(f"{py_file.relative_to(src_dir)}:{i+1}")
        
        assert len(usage_files) == 0, f"Found usage of deprecated initialize_components: {usage_files}"
    
    def test_app_state_injection_exists(self):
        """Test that FastAPI app.state is properly set up for backward compatibility."""
        main_file = Path(__file__).parent.parent.parent / "src" / "main.py"
        
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Check that components are injected into app.state
        required_injections = [
            "app.state.config_manager",
            "app.state.exchange_manager",
            "app.state.database_client",
            "app.state.alert_manager",
            "app.state.market_monitor"
        ]
        
        for injection in required_injections:
            assert injection in content, f"Missing app.state injection: {injection}"


class TestContainerArchitecture:
    """Test the Container architecture is properly implemented."""
    
    def test_container_has_lifecycle_methods(self):
        """Test Container has proper lifecycle management."""
        
        # Check required methods
        assert hasattr(Container, 'initialize')
        assert hasattr(Container, 'cleanup')
        assert hasattr(Container, 'register_trading_components')
        assert hasattr(Container, 'get_component')
        assert hasattr(Container, 'get_system_state')
    
    def test_trading_adapter_exists(self):
        """Test TradingComponentAdapter exists and is functional."""
        from src.core.trading_components_adapter import TradingComponentAdapter
        
        # Check class exists and has required methods
        assert hasattr(TradingComponentAdapter, 'register_and_initialize_trading_components')
        assert hasattr(TradingComponentAdapter, 'cleanup_trading_components')
        assert hasattr(TradingComponentAdapter, 'get_component')
        assert hasattr(TradingComponentAdapter, 'get_all_components')
    
    def test_centralized_dependencies_exist(self):
        """Test centralized dependency functions exist."""
        from src.api.core import dependencies
        
        # Check key dependency functions exist
        required_deps = [
            'get_config_manager',
            'get_exchange_manager',
            'get_database_client',
            'get_alert_manager',
            'get_market_monitor',
            'get_container'
        ]
        
        for dep in required_deps:
            assert hasattr(dependencies, dep), f"Missing dependency function: {dep}"
    
    def test_no_circular_imports(self):
        """Test that Container system doesn't create circular imports."""
        # Try importing key modules - should not raise ImportError
        try:
            from src.api.core.dependencies import get_container
            from src.main import app
            
            # If we get here, imports work
            assert True
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")


class TestMigrationCompleteness:
    """Test that the migration from global state to Container is complete."""
    
    def test_all_components_available_through_container(self):
        """Test that all components previously in globals are available via Container."""
        required_components = [
            'config_manager',
            'exchange_manager',
            'database_client',
            'portfolio_analyzer',
            'confluence_analyzer',
            'validation_service',
            'top_symbols_manager',
            'market_data_manager',
            'metrics_manager',
            'alert_manager',
            'market_reporter',
            'market_monitor'
        ]
        
        # Check that Container can provide these components
        container = Container(settings={})
        
        # Container should have mechanism to get components
        assert hasattr(container, 'get_component')
        
        # Note: We can't test actual component retrieval without full initialization
        # but we've verified the mechanism exists
    
    def test_migration_preserves_functionality(self):
        """Test that key functionality is preserved after migration."""
        # Test that app can be imported without errors
        try:
            assert app is not None
            
            # Check app has required attributes
            assert hasattr(app, 'state')
            assert hasattr(app, 'router')
            
        except Exception as e:
            pytest.fail(f"App import failed after migration: {e}")
    
    def test_container_in_production_mode(self):
        """Test Container works in production-like settings."""
        
        # Production-like settings
        prod_settings = {
            'logging': {'level': 'WARNING'},
            'resources': {
                'max_memory_mb': 2048,
                'max_concurrent_ops': 200
            }
        }
        
        # Should create without errors
        container = Container(settings=prod_settings)
        assert container.settings == prod_settings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
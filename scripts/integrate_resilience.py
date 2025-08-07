#!/usr/bin/env python3
"""
Integrate resilience components into the main application.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def patch_main_py():
    """Add resilience initialization to main.py"""
    
    main_py_path = project_root / "src" / "main.py"
    
    # Read current main.py
    with open(main_py_path, 'r') as f:
        content = f.read()
    
    # Add resilience import after other imports
    resilience_import = """
# Import resilience components
from src.core.resilience import wrap_exchange_manager
from src.core.resilience.patches import patch_dashboard_integration_resilience, patch_api_routes_resilience
"""
    
    # Add after the exchange manager initialization
    resilience_init = """
    # Wrap exchange manager with resilience patterns
    logger.info("Applying resilience patterns to exchange manager...")
    try:
        from src.core.resilience import wrap_exchange_manager
        resilient_exchange_manager = wrap_exchange_manager(exchange_manager)
        # Store both for compatibility
        exchange_manager._resilient_wrapper = resilient_exchange_manager
        logger.info("✅ Exchange manager wrapped with resilience patterns")
    except Exception as e:
        logger.error(f"Failed to wrap exchange manager: {e}")
        logger.warning("Continuing without resilience wrapper")
    
    # Apply resilience patches
    logger.info("Applying resilience patches...")
    try:
        from src.core.resilience.patches import patch_dashboard_integration_resilience, patch_api_routes_resilience
        patch_dashboard_integration_resilience()
        patch_api_routes_resilience()
        logger.info("✅ Resilience patches applied")
    except Exception as e:
        logger.error(f"Failed to apply resilience patches: {e}")
"""
    
    # Find where to insert the import
    import_pos = content.find("from src.monitoring.bandwidth_monitor import bandwidth_monitor")
    if import_pos > 0:
        import_end = content.find('\n', import_pos) + 1
        content = content[:import_end] + resilience_import + content[import_end:]
    
    # Find where to insert the initialization
    init_pos = content.find("logger.info(\"✅ ExchangeManager initialized\")")
    if init_pos > 0:
        init_end = content.find('\n', init_pos) + 1
        content = content[:init_end] + resilience_init + content[init_end:]
    
    # Write back
    with open(main_py_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Patched main.py with resilience initialization")


def patch_api_init():
    """Add health routes to API initialization"""
    
    api_init_path = project_root / "src" / "api" / "__init__.py"
    
    # Read current __init__.py
    with open(api_init_path, 'r') as f:
        content = f.read()
    
    # Add health router import
    if "from .routes import health" not in content:
        # Find the imports section
        import_line = "from .routes import cache"
        if import_line in content:
            content = content.replace(import_line, f"{import_line}\n    from .routes import health")
        
        # Add health router to app
        router_line = 'app.include_router(cache.router, prefix="/api/cache", tags=["cache"])'
        if router_line in content:
            health_router = '\n    app.include_router(health.router, prefix="/api/health", tags=["health"])'
            content = content.replace(router_line, router_line + health_router)
    
    # Write back
    with open(api_init_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Patched API init with health routes")


def patch_dashboard_integration():
    """Update dashboard integration to use fallbacks"""
    
    dashboard_path = project_root / "src" / "dashboard" / "dashboard_integration.py"
    
    # Read current file
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    # Add fallback import
    if "from src.core.resilience.fallback_provider" not in content:
        import_pos = content.find("logger = logging.getLogger(__name__)")
        if import_pos > 0:
            import_line = "\nfrom src.core.resilience.fallback_provider import get_fallback_provider\n"
            content = content[:import_pos] + import_line + content[import_pos:]
    
    # Add error handling to _update_dashboard_data method
    method_start = "async def _update_dashboard_data(self):"
    if method_start in content:
        # Find the method and add try-catch wrapper
        method_pos = content.find(method_start)
        if method_pos > 0:
            # Find the next method definition to know where this one ends
            next_method = content.find("\n    async def ", method_pos + 1)
            if next_method < 0:
                next_method = content.find("\n    def ", method_pos + 1)
            
            # Extract the method
            if next_method > 0:
                method_content = content[method_pos:next_method]
            else:
                method_content = content[method_pos:]
            
            # Check if already has resilience
            if "get_fallback_provider" not in method_content:
                # Add resilience wrapper
                new_method = f'''async def _update_dashboard_data(self):
        """Update dashboard data with fallback support."""
        try:
            # Original update logic
            await self._update_dashboard_data_original()
        except Exception as e:
            self.logger.error(f"Dashboard update failed: {{e}}, using fallback")
            
            # Use fallback data
            try:
                fallback = get_fallback_provider()
                
                self._dashboard_data = {{
                    'signals': (await fallback.get_signals_fallback())['signals'],
                    'alerts': [],
                    'alpha_opportunities': [],
                    'system_status': {{
                        'status': 'degraded',
                        'message': 'External services unavailable - showing cached data',
                        'timestamp': time.time()
                    }},
                    'market_overview': await fallback.get_market_overview_fallback()
                }}
                
                self.logger.info("Dashboard using fallback data")
            except Exception as fallback_error:
                self.logger.error(f"Fallback also failed: {{fallback_error}}")
                # Provide minimal data
                self._dashboard_data = {{
                    'signals': [],
                    'alerts': [],
                    'alpha_opportunities': [],
                    'system_status': {{
                        'status': 'error',
                        'message': 'System unavailable',
                        'timestamp': time.time()
                    }},
                    'market_overview': {{}}
                }}
    
    async def _update_dashboard_data_original(self):'''
                
                # Replace the method signature
                content = content.replace(method_start, new_method)
    
    # Write back
    with open(dashboard_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Patched dashboard integration with fallback support")


def main():
    """Main execution"""
    print("=" * 60)
    print("🔧 Integrating Resilience Components")
    print("=" * 60)
    
    # Apply patches
    patch_main_py()
    patch_api_init()
    patch_dashboard_integration()
    
    print("\n✅ Integration complete!")
    print("\n📝 What was done:")
    print("1. Added resilience wrapper to exchange manager")
    print("2. Added health check endpoints to API")
    print("3. Added fallback support to dashboard integration")
    print("4. Applied circuit breaker patterns")
    
    print("\n🚀 To activate:")
    print("1. Restart the application")
    print("2. Check /api/health/system for system health")
    print("3. Check /api/health/resilience for circuit breaker status")
    print("4. Test with network interruptions to verify fallbacks")


if __name__ == "__main__":
    main()
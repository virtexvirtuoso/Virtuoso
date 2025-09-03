#!/usr/bin/env python3
"""Fix confluence detection in DashboardCacheManager"""

# Create a simple patch for the confluence detection method
patch_code = '''
    def _get_confluence_scores(self) -> Dict[str, Dict[str, Any]]:
        """Get confluence scores from DashboardIntegration service - FIXED VERSION"""
        try:
            # Method 1: Use the global get_dashboard_integration function
            try:
                from src.dashboard.dashboard_integration import get_dashboard_integration
                dashboard_service = get_dashboard_integration()
                if dashboard_service and hasattr(dashboard_service, '_confluence_cache'):
                    confluence_cache = dashboard_service._confluence_cache
                    current_time = time.time()
                    confluence_data = {}
                    
                    # Extract valid confluence scores (not older than 5 minutes)
                    for symbol, data in confluence_cache.items():
                        if isinstance(data, dict) and 'timestamp' in data:
                            age = current_time - data['timestamp']
                            if age < 300:  # 5 minutes
                                confluence_data[symbol] = {
                                    'score': data.get('score', 50),
                                    'components': data.get('components', {}),
                                    'timestamp': data.get('timestamp', current_time),
                                    'age': age
                                }
                    
                    if confluence_data:
                        logger.debug(f"Found {len(confluence_data)} confluence scores from global dashboard integration")
                        return confluence_data
            except ImportError:
                logger.debug("Could not import get_dashboard_integration function")
            except Exception as e:
                logger.debug(f"Error accessing global dashboard integration: {e}")
            
            # Method 2: Search through sys.modules for DashboardIntegration instances
            import sys
            for module_name in list(sys.modules.keys()):
                if 'dashboard' in module_name:
                    try:
                        module = sys.modules[module_name]
                        for attr_name in dir(module):
                            attr_value = getattr(module, attr_name, None)
                            if attr_value and hasattr(attr_value, '_confluence_cache'):
                                confluence_cache = getattr(attr_value, '_confluence_cache', {})
                                if confluence_cache:
                                    current_time = time.time()
                                    confluence_data = {}
                                    
                                    for symbol, data in confluence_cache.items():
                                        if isinstance(data, dict) and 'timestamp' in data:
                                            age = current_time - data['timestamp']
                                            if age < 300:  # 5 minutes
                                                confluence_data[symbol] = {
                                                    'score': data.get('score', 50),
                                                    'components': data.get('components', {}),
                                                    'timestamp': data.get('timestamp', current_time),
                                                    'age': age
                                                }
                                    
                                    if confluence_data:
                                        logger.debug(f"Found {len(confluence_data)} confluence scores from module {module_name}")
                                        return confluence_data
                    except Exception as e:
                        continue
            
            # Method 3: Try to access through main app state
            try:
                if 'src.main' in sys.modules:
                    main_module = sys.modules['src.main']
                    if hasattr(main_module, 'app') and hasattr(main_module.app, 'state'):
                        # Look through all app state attributes
                        for attr_name in dir(main_module.app.state):
                            if 'dashboard' in attr_name.lower():
                                attr_value = getattr(main_module.app.state, attr_name, None)
                                if attr_value and hasattr(attr_value, '_confluence_cache'):
                                    confluence_cache = getattr(attr_value, '_confluence_cache', {})
                                    if confluence_cache:
                                        current_time = time.time()
                                        confluence_data = {}
                                        
                                        for symbol, data in confluence_cache.items():
                                            if isinstance(data, dict) and 'timestamp' in data:
                                                age = current_time - data['timestamp']
                                                if age < 300:  # 5 minutes
                                                    confluence_data[symbol] = {
                                                        'score': data.get('score', 50),
                                                        'components': data.get('components', {}),
                                                        'timestamp': data.get('timestamp', current_time),
                                                        'age': age
                                                    }
                                        
                                        if confluence_data:
                                            logger.debug(f"Found {len(confluence_data)} confluence scores from app.state.{attr_name}")
                                            return confluence_data
            except Exception as e:
                logger.debug(f"Error accessing app state: {e}")
            
            logger.debug("No confluence scores found in any accessible location")
            return {}
            
        except Exception as e:
            logger.debug(f"Could not access confluence scores: {e}")
            return {}
'''

print("Creating fixed confluence detection method...")

# Read the current cache manager
with open('dashboard_cache_manager_enhanced.py', 'r') as f:
    content = f.read()

# Find the old method and replace it
old_method_start = content.find('    def _get_confluence_scores(self)')
if old_method_start == -1:
    print("❌ Could not find _get_confluence_scores method")
    exit(1)

# Find the end of the method (next method or class)
old_method_end = content.find('\n    def ', old_method_start + 1)
if old_method_end == -1:
    old_method_end = content.find('\n    async def ', old_method_start + 1)

if old_method_end == -1:
    print("❌ Could not find end of _get_confluence_scores method")
    exit(1)

# Replace the method
new_content = content[:old_method_start] + patch_code + content[old_method_end:]

# Write the fixed version
with open('dashboard_cache_manager_fixed.py', 'w') as f:
    f.write(new_content)

print("✅ Fixed confluence detection method!")
print("\nKey improvements:")
print("- 🎯 Uses global get_dashboard_integration() function")
print("- 🔍 Enhanced module searching")
print("- 📱 App state inspection")
print("- 🛡️ Better error handling")
print("\nTo deploy:")
print("scp dashboard_cache_manager_fixed.py linuxuser@VPS_HOST_REDACTED:/home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_cache_manager.py")
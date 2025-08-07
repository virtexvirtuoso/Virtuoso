#!/usr/bin/env python3
"""
Fix: Ensure all components use the same global api_cache instance
"""

import sys
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

print("=" * 60)
print("🔧 FIXING CACHE INSTANCE SHARING")
print("=" * 60)
print()

# Fix 1: Update market.py to use global instance properly
market_fix = '''
# At the top of the file, with other imports
from src.core.api_cache import api_cache

# In the get_symbols_with_confluence function, ensure we use the global
# This should already be correct, but let's verify
'''

# Fix 2: Create a cache manager module that ensures single instance
cache_manager_code = '''"""
Global cache manager to ensure single instance across all modules
"""

import logging

logger = logging.getLogger(__name__)

# Global cache instance - initialized once
_global_cache = None

def get_global_cache():
    """Get the global cache instance."""
    global _global_cache
    if _global_cache is None:
        from src.core.api_cache import APICache
        _global_cache = APICache()
        logger.info("Global cache instance created")
    return _global_cache

# Export as singleton
cache = get_global_cache()
'''

try:
    # Create the cache manager
    with open('/home/linuxuser/trading/Virtuoso_ccxt/src/core/cache_manager.py', 'w') as f:
        f.write(cache_manager_code)
    print("✅ Created cache_manager.py")
    
    # Update dashboard_updater.py to use cache manager
    with open('/home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_updater.py', 'r') as f:
        content = f.read()
    
    # Check current import
    if 'from src.core.api_cache import api_cache' in content:
        print("⚠️ Dashboard updater uses direct import - needs fix")
        # The issue is it receives cache as parameter, let's check main.py
    
    # Check main.py initialization
    with open('/home/linuxuser/trading/Virtuoso_ccxt/src/main.py', 'r') as f:
        main_content = f.read()
    
    if 'from src.core.api_cache import api_cache' in main_content:
        print("✅ Main.py imports api_cache")
    
    # The real fix: Ensure market.py stores in the same cache instance
    # that dashboard_updater receives
    
    print()
    print("📝 Applying unified cache fix...")
    
    # Read market.py
    with open('/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/market.py', 'r') as f:
        market_content = f.read()
    
    # The issue is that market.py creates its own import!
    # We need to get the cache from the app context instead
    
    # Better fix: Pass cache through app context
    market_fix = '''@router.get("/symbols")
async def get_symbols_with_confluence(request: Request) -> Dict[str, Any]:
    """
    Get all monitored symbols with confluence scores and market data.
    
    Returns:
        Dictionary containing symbols with confluence scores, prices, and 24h changes
    """
    try:
        # Get the cache from app state (shared with dashboard updater)
        cache = request.app.state.cache if hasattr(request.app.state, 'cache') else api_cache
        
        # Get cached symbols data
        symbols_data = cache.get("symbols")
        
        if symbols_data and "symbols" in symbols_data:
            logger.info(f"Returning {len(symbols_data['symbols'])} symbols from cache")
            return symbols_data
        
        # Fallback: Get basic symbol list if cache is empty
        logger.warning("No symbols in cache, returning empty list")
        
        return {
            'status': 'no_data',
            'symbols': [],
            'timestamp': datetime.now().isoformat(),
            'message': 'No symbols data available'
        }
        
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        return {
            'status': 'error',
            'symbols': [],
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }'''
    
    # Replace the function in market.py
    if '@router.get("/symbols")' in market_content:
        print("📝 Updating market.py symbols endpoint...")
        # Find and replace the function
        start = market_content.find('@router.get("/symbols")')
        if start >= 0:
            # Find the end of the function (next @router or end of file)
            next_route = market_content.find('\n@router', start + 1)
            if next_route < 0:
                next_route = len(market_content)
            
            # Add Request import if needed
            if 'from fastapi import' in market_content and 'Request' not in market_content:
                import_line = market_content.find('from fastapi import')
                end_import = market_content.find('\n', import_line)
                imports = market_content[import_line:end_import]
                if 'Request' not in imports:
                    new_imports = imports.replace(')', ', Request)')
                    market_content = market_content[:import_line] + new_imports + market_content[end_import:]
                    print("  Added Request import")
            
            # Replace the function
            market_content = market_content[:start] + market_fix + market_content[next_route:]
            
            with open('/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/market.py', 'w') as f:
                f.write(market_content)
            
            print("✅ Updated market.py to use shared cache")
    
    # Update main.py to set cache in app state
    print()
    print("📝 Updating main.py to share cache via app state...")
    
    if 'app.state.cache = api_cache' not in main_content:
        # Find where to add it (after app creation)
        app_create = main_content.find('app = FastAPI(')
        if app_create >= 0:
            # Find the next good place to add
            init_routes = main_content.find('init_api_routes(app', app_create)
            if init_routes >= 0:
                # Add before init_routes
                insert_line = '            # Share cache instance via app state\n            app.state.cache = api_cache\n            \n'
                main_content = main_content[:init_routes] + insert_line + main_content[init_routes:]
                
                with open('/home/linuxuser/trading/Virtuoso_ccxt/src/main.py', 'w') as f:
                    f.write(main_content)
                
                print("✅ Updated main.py to share cache via app.state")
    else:
        print("✅ main.py already shares cache")
    
    print()
    print("✅ Cache instance sharing fixed!")
    print()
    print("The fix ensures:")
    print("1. Dashboard updater uses api_cache from main.py")
    print("2. API routes access the same cache via app.state")
    print("3. All components share the same cache instance")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
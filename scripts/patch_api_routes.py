#!/usr/bin/env python3
"""
Patch API routes to use caching
Phase 1 implementation
"""

import os
import sys
import re

def patch_dashboard_routes():
    """Patch the dashboard API routes to use caching."""
    
    dashboard_file = "/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/dashboard.py"
    
    # Read the file
    with open(dashboard_file, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if 'from src.core.api_cache import' in content:
        print("✅ File already patched")
        return
    
    # Add imports at the top
    import_lines = """from src.core.api_cache import api_cache, dashboard_cache
import asyncio
from datetime import datetime
"""
    
    # Find where to insert imports (after existing imports)
    import_pattern = r'(from fastapi import.*?\n)'
    content = re.sub(import_pattern, r'\1' + import_lines, content, count=1)
    
    # Patch the signals endpoint
    signals_patch = '''
@router.get("/signals")
async def get_dashboard_signals():
    """Get trading signals for dashboard with caching."""
    try:
        # Check cache first
        cached = api_cache.get('dashboard:signals')
        if cached:
            logger.info("Serving dashboard signals from cache")
            return cached
        
        # If not cached, return computing status
        # The background task will populate this
        logger.info("Dashboard signals not in cache, computing...")
        return {
            "status": "computing",
            "message": "Data is being computed, please refresh in a few seconds",
            "signals": [],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting dashboard signals: {e}")
        return {
            "status": "error",
            "error": str(e),
            "signals": []
        }
'''
    
    # Replace the existing signals endpoint
    signals_pattern = r'@router\.get\("/signals"\).*?(?=@router\.get|$)'
    content = re.sub(signals_pattern, signals_patch, content, flags=re.DOTALL)
    
    # Patch the overview endpoint
    overview_patch = '''
@router.get("/overview")
async def get_market_overview():
    """Get market overview with caching."""
    try:
        # Check cache first
        cached = api_cache.get('dashboard:overview')
        if cached:
            logger.info("Serving market overview from cache")
            return cached
        
        # If not cached, return computing status
        logger.info("Market overview not in cache, computing...")
        return {
            "status": "computing",
            "message": "Data is being computed, please refresh in a few seconds",
            "data": {},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        return {
            "status": "error",
            "error": str(e),
            "data": {}
        }
'''
    
    # Replace the existing overview endpoint
    overview_pattern = r'@router\.get\("/overview"\).*?(?=@router\.get|$)'
    content = re.sub(overview_pattern, overview_patch, content, flags=re.DOTALL)
    
    # Add cache status endpoint
    cache_status = '''

@router.get("/cache-status")
async def get_cache_status():
    """Get cache statistics and status."""
    return {
        "cache_stats": api_cache.get_stats(),
        "dashboard_cache_status": dashboard_cache.get_status() if hasattr(dashboard_cache, 'get_status') else {},
        "last_update": api_cache.get('dashboard:last_update')
    }
'''
    
    # Add at the end of the file
    content += cache_status
    
    # Write back the patched file
    with open(dashboard_file, 'w') as f:
        f.write(content)
    
    print("✅ Dashboard routes patched successfully")

def patch_main_py():
    """Patch main.py to include the background updater."""
    
    main_file = "/home/linuxuser/trading/Virtuoso_ccxt/src/main.py"
    
    # Read the file
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if 'from src.core.dashboard_updater import' in content:
        print("✅ Main.py already patched")
        return
    
    # Add imports
    import_line = "from src.core.dashboard_updater import DashboardUpdater\nfrom src.core.api_cache import api_cache, cache_cleanup_task\n"
    
    # Find where to add imports (after other src.core imports)
    import_pattern = r'(from src\.core\..*?\n)'
    if re.search(import_pattern, content):
        content = re.sub(import_pattern, r'\1' + import_line, content, count=1)
    else:
        # Add after any import
        content = import_line + content
    
    # Add dashboard updater initialization in __init__
    init_patch = """
        # Initialize dashboard updater
        self.dashboard_updater = None
"""
    
    # Find __init__ method and add the initialization
    init_pattern = r'(def __init__\(self.*?\):.*?)(self\.logger = .*?\n)'
    content = re.sub(init_pattern, r'\1\2' + init_patch, content, flags=re.DOTALL, count=1)
    
    # Add updater start in run method
    run_patch = """
        # Start dashboard updater
        try:
            self.dashboard_updater = DashboardUpdater(self, api_cache, update_interval=30)
            self.dashboard_updater.start()
            logger.info("✅ Dashboard updater started")
        except Exception as e:
            logger.error(f"Failed to start dashboard updater: {e}")
        
        # Start cache cleanup task
        asyncio.create_task(cache_cleanup_task())
        logger.info("✅ Cache cleanup task started")
"""
    
    # Find where to add in run method (after API server start)
    run_pattern = r'(# Start API server.*?logger\.info.*?\n)'
    content = re.sub(run_pattern, r'\1' + run_patch, content, flags=re.DOTALL, count=1)
    
    # Add cleanup in shutdown
    shutdown_patch = """
        # Stop dashboard updater
        if self.dashboard_updater:
            self.dashboard_updater.stop()
            logger.info("Dashboard updater stopped")
"""
    
    # Find shutdown method and add cleanup
    shutdown_pattern = r'(async def shutdown\(self\):.*?)(logger\.info.*?"Initiating.*?\n)'
    content = re.sub(shutdown_pattern, r'\1\2' + shutdown_patch, content, flags=re.DOTALL, count=1)
    
    # Write back the patched file
    with open(main_file, 'w') as f:
        f.write(content)
    
    print("✅ Main.py patched successfully")

if __name__ == "__main__":
    try:
        print("🔧 Patching API routes for caching...")
        patch_dashboard_routes()
        patch_main_py()
        print("✅ All patches applied successfully")
    except Exception as e:
        print(f"❌ Error applying patches: {e}")
        sys.exit(1)
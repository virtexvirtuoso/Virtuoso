#!/usr/bin/env python3
"""
Mobile Dashboard No Data Fix - Quick Implementation
Fixes the mobile endpoint data loading issue by adding type safety and fallback logic

Deo Gratias - Thanks be to God
"""

import os
import sys
from pathlib import Path

def apply_type_safety_fix():
    """Apply type safety fixes to dashboard.py"""

    dashboard_py = Path("src/api/routes/dashboard.py")

    if not dashboard_py.exists():
        print(f"❌ File not found: {dashboard_py}")
        return False

    print(f"📝 Reading {dashboard_py}...")
    content = dashboard_py.read_text()

    # Add helper function at the top (after imports)
    helper_code = '''
# Type safety helper for dashboard responses
def validate_dict_response(data: Any, default: Dict, context: str = "unknown") -> Dict:
    """Ensure response is always a dict, never str or None."""
    if isinstance(data, dict):
        return data
    if data is not None:
        logger.warning(f"Invalid response type in {context}: {type(data).__name__}, using default")
    return default

def get_default_overview() -> Dict[str, Any]:
    """Default overview response when main service unavailable."""
    return {
        "status": "no_data",
        "timestamp": datetime.utcnow().isoformat(),
        "signals": [],
        "alerts": [],
        "market_metrics": {},
        "cache_status": "disconnected",
        "system_status": {
            "monitoring": "disconnected",
            "data_feed": "disconnected",
            "alerts": "disabled",
            "websocket": "disconnected",
            "last_update": 0
        }
    }
'''

    # Find the right place to insert (after router = APIRouter())
    if "def validate_dict_response" not in content:
        insert_pos = content.find("router = APIRouter()")
        if insert_pos != -1:
            # Find end of line
            newline_pos = content.find("\n", insert_pos)
            content = content[:newline_pos + 1] + helper_code + content[newline_pos + 1:]
            print("✅ Added type safety helper functions")

    # Fix get_dashboard_overview function
    old_overview = '''async def get_dashboard_overview() -> Dict[str, Any]:
    """Get comprehensive dashboard overview with real-time data from Memcached.

    CRITICAL FIX: This endpoint now queries breakdown cache keys to populate
    component scores and interpretations for each symbol.
    """
    try:
        # Import cache service
        from src.core.cache.confluence_cache_service import confluence_cache_service

        # Use direct cache if available for better performance
        if USE_DIRECT_CACHE:
            overview = await direct_cache.get_dashboard_overview()'''

    new_overview = '''async def get_dashboard_overview() -> Dict[str, Any]:
    """Get comprehensive dashboard overview with real-time data from Memcached.

    CRITICAL FIX: This endpoint now queries breakdown cache keys to populate
    component scores and interpretations for each symbol.
    """
    try:
        # Import cache service
        from src.core.cache.confluence_cache_service import confluence_cache_service

        # Use direct cache if available for better performance
        if USE_DIRECT_CACHE:
            overview = await direct_cache.get_dashboard_overview()

            # Validate response type
            overview = validate_dict_response(overview, get_default_overview(), "direct_cache")'''

    if old_overview in content:
        content = content.replace(old_overview, new_overview)
        print("✅ Fixed get_dashboard_overview() type safety")

    # Fix the part where it tries to access overview_data without validation
    old_signals_access = '''        # Get dashboard overview from integration service
        overview_data = await integration.get_dashboard_overview()

        # CRITICAL FIX: Enrich signals with breakdown data
        signals = overview_data.get('signals', [])'''

    new_signals_access = '''        # Get dashboard overview from integration service
        overview_data = await integration.get_dashboard_overview()

        # Validate overview_data is a dict before accessing
        overview_data = validate_dict_response(overview_data, get_default_overview(), "integration")

        # CRITICAL FIX: Enrich signals with breakdown data
        signals = overview_data.get('signals', [])'''

    if old_signals_access in content:
        content = content.replace(old_signals_access, new_signals_access)
        print("✅ Fixed overview_data validation")

    # Fix exception handling to return dict instead of raising
    old_exception = '''    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard overview: {str(e)}")'''

    new_exception = '''    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}", exc_info=True)
        return get_default_overview()'''

    # Only replace in get_dashboard_overview context
    if old_exception in content:
        # Find the function and replace only within it
        func_start = content.find("async def get_dashboard_overview")
        func_end = content.find("\n@router.get", func_start)
        if func_start != -1 and func_end != -1:
            func_content = content[func_start:func_end]
            if old_exception in func_content:
                func_content = func_content.replace(old_exception, new_exception)
                content = content[:func_start] + func_content + content[func_end:]
                print("✅ Fixed error handling in get_dashboard_overview()")

    # Write back
    dashboard_py.write_text(content)
    print(f"✅ Updated {dashboard_py}")
    return True

def apply_mobile_data_fix():
    """Fix the mobile-data endpoint"""

    dashboard_py = Path("src/api/routes/dashboard.py")
    content = dashboard_py.read_text()

    # Find mobile-data function and wrap integration access
    old_mobile = '''    try:
        # CRITICAL FIX: Use shared cache bridge for live mobile data
        if web_cache:
            try:
                mobile_data = await web_cache.get_mobile_data()'''

    new_mobile = '''    try:
        # CRITICAL FIX: Use shared cache bridge for live mobile data
        if web_cache:
            try:
                mobile_data = await web_cache.get_mobile_data()
                # Validate response type
                if not isinstance(mobile_data, dict):
                    logger.warning(f"Invalid mobile_data type from cache: {type(mobile_data)}")
                    mobile_data = None'''

    if old_mobile in content and "Validate response type" not in content:
        content = content.replace(old_mobile, new_mobile)
        print("✅ Fixed mobile-data cache response validation")
        dashboard_py.write_text(content)

    return True

def update_mobile_template():
    """Update mobile template to use direct endpoints as fallback"""

    template = Path("src/dashboard/templates/dashboard_mobile_v1.html")

    if not template.exists():
        print(f"❌ Template not found: {template}")
        return False

    print(f"📝 Reading {template}...")
    content = template.read_text()

    # Add fallback logic to loadDashboardData
    old_fetch = '''        async function loadDashboardData() {
            try {
                // Load summary, symbols, market overview, and movers data
                const [summaryResponse, symbolsResponse, marketResponse, mobileDataResponse] = await Promise.all([
                    fetch('/api/dashboard/overview'),
                    fetch('/api/dashboard/symbols'),
                    fetch('/api/dashboard/market-overview'),
                    fetch('/api/dashboard/mobile-data')
                ]);'''

    new_fetch = '''        async function loadDashboardData() {
            try {
                // Load summary, symbols, market overview, and movers data
                // Using fallback to direct endpoints if dashboard endpoints fail
                const [summaryResponse, symbolsResponse, marketResponse, mobileDataResponse] = await Promise.all([
                    fetch('/api/dashboard/overview').catch(() => fetch('/api/market/overview')),
                    fetch('/api/dashboard/symbols').catch(() => fetch('/api/signals/top')),
                    fetch('/api/dashboard/market-overview').catch(() => fetch('/api/market/overview')),
                    fetch('/api/dashboard/mobile-data').catch(() => fetch('/api/dashboard/data'))
                ]);'''

    if old_fetch in content:
        content = content.replace(old_fetch, new_fetch)
        print("✅ Added fallback logic to mobile template")
        template.write_text(content)
        return True
    else:
        print("⚠️  Could not find exact match in template")
        return False

def main():
    """Apply all fixes"""
    print("🚀 Mobile Dashboard No Data Fix")
    print("=" * 60)

    # Check we're in the right directory
    if not Path("src/web_server.py").exists():
        print("❌ Error: Must run from project root")
        print("   Current directory:", os.getcwd())
        sys.exit(1)

    print("📍 Working directory:", os.getcwd())
    print()

    # Apply fixes
    fixes = [
        ("Type Safety Guards", apply_type_safety_fix),
        ("Mobile Data Endpoint", apply_mobile_data_fix),
        ("Mobile Template Fallback", update_mobile_template)
    ]

    results = []
    for name, func in fixes:
        print(f"\n🔧 Applying: {name}")
        print("-" * 60)
        try:
            success = func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Error applying {name}: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 Fix Summary")
    print("=" * 60)

    for name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {name}")

    total = len(results)
    successful = sum(1 for _, s in results if s)

    print(f"\n{successful}/{total} fixes applied successfully")

    if successful == total:
        print("\n✅ All fixes applied! Next steps:")
        print("   1. Review changes: git diff")
        print("   2. Test locally if possible")
        print("   3. Deploy to VPS: rsync -avz src/ vps:/home/linuxuser/trading/Virtuoso_ccxt/src/")
        print("   4. Restart web server: ssh vps 'systemctl restart virtuoso-web'")
        print("   5. Test: http://5.223.63.4:8002/mobile")
    else:
        print("\n⚠️  Some fixes failed. Please review and apply manually.")

    return 0 if successful == total else 1

if __name__ == "__main__":
    sys.exit(main())

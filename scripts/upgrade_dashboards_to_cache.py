#!/usr/bin/env python3
"""
Upgrade existing dashboards to use cache-based endpoints
Creates backup and updates API calls to use cached versions
"""
import os
import re
import shutil
from datetime import datetime

# Dashboards to upgrade
DASHBOARDS = [
    'src/dashboard/templates/dashboard_desktop_v1.html',
    'src/dashboard/templates/dashboard_mobile_v1.html',
    'src/dashboard/templates/dashboard.html',
    'src/dashboard/templates/dashboard_v10.html'
]

# API endpoint mappings (old -> new)
ENDPOINT_MAPPINGS = {
    '/api/dashboard/overview': '/api/dashboard-cached/overview',
    '/api/dashboard/market-overview': '/api/dashboard-cached/market-overview',
    '/api/dashboard/symbols': '/api/dashboard-cached/symbols',
    '/api/dashboard/signals': '/api/dashboard-cached/signals',
    '/api/dashboard/alerts': '/api/dashboard-cached/alerts',
    '/api/dashboard/market-analysis': '/api/dashboard-cached/market-analysis',
    '/api/dashboard/market-movers': '/api/dashboard-cached/market-movers',
    '/api/market/overview': '/api/cache/cache/overview',
    '/api/market/movers': '/api/cache/cache/movers',
    '/api/alpha/opportunities': '/api/dashboard-cached/opportunities'
}

def backup_file(filepath):
    """Create backup of original file"""
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up: {os.path.basename(filepath)} -> {os.path.basename(backup_path)}")
    return backup_path

def upgrade_dashboard(filepath):
    """Upgrade a dashboard file to use cached endpoints"""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    # Read file
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Track changes
    changes_made = 0
    original_content = content
    
    # Replace endpoints
    for old_endpoint, new_endpoint in ENDPOINT_MAPPINGS.items():
        # Count occurrences
        count = content.count(old_endpoint)
        if count > 0:
            content = content.replace(old_endpoint, new_endpoint)
            changes_made += count
            print(f"  📝 Replaced {count} occurrence(s) of {old_endpoint}")
    
    # Add cache status indicator if not present
    if 'cache-status' not in content and changes_made > 0:
        # Add cache status indicator to dashboard
        cache_indicator = """
        <!-- Cache Status Indicator -->
        <div id="cache-status" style="position: fixed; bottom: 20px; right: 20px; padding: 10px; background: rgba(0,0,0,0.8); color: #0f0; border-radius: 5px; font-size: 12px; z-index: 9999; display: none;">
            📦 Cache Mode: <span id="cache-response-time">--</span>ms
        </div>
        <script>
        // Show cache status for cached responses
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const startTime = performance.now();
            return originalFetch.apply(this, args).then(response => {
                const elapsed = (performance.now() - startTime).toFixed(0);
                if (args[0].includes('cache')) {
                    document.getElementById('cache-status').style.display = 'block';
                    document.getElementById('cache-response-time').textContent = elapsed;
                    setTimeout(() => {
                        document.getElementById('cache-status').style.display = 'none';
                    }, 3000);
                }
                return response;
            });
        };
        </script>
        """
        
        # Insert before </body>
        content = content.replace('</body>', cache_indicator + '\n</body>')
        print(f"  ✨ Added cache status indicator")
        changes_made += 1
    
    # Write updated file if changes were made
    if changes_made > 0:
        # Create backup first
        backup_file(filepath)
        
        # Write updated content
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"✅ Upgraded {os.path.basename(filepath)}: {changes_made} changes made")
        return True
    else:
        print(f"ℹ️  No changes needed for {os.path.basename(filepath)}")
        return False

def main():
    print("=" * 60)
    print("DASHBOARD CACHE UPGRADE TOOL")
    print("=" * 60)
    print("\nThis will upgrade existing dashboards to use cached endpoints")
    print("for ultra-fast response times and resilience.\n")
    
    upgraded = 0
    
    for dashboard in DASHBOARDS:
        print(f"\n📋 Processing: {dashboard}")
        if upgrade_dashboard(dashboard):
            upgraded += 1
    
    print("\n" + "=" * 60)
    print(f"UPGRADE COMPLETE: {upgraded}/{len(DASHBOARDS)} dashboards upgraded")
    print("=" * 60)
    
    if upgraded > 0:
        print("\n🎯 Next Steps:")
        print("1. Deploy the cache adapter (src/api/cache_adapter.py)")
        print("2. Deploy the cached routes (src/api/routes/dashboard_cached.py)")
        print("3. Update API initialization to include cached routes")
        print("4. Restart web service")
        print("5. Test dashboards - they should now load in < 10ms!")

if __name__ == "__main__":
    main()
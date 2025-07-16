#!/usr/bin/env python3

import sys
import asyncio
sys.path.append('src')

from dashboard_integration import DashboardIntegrationService, set_dashboard_integration, get_dashboard_integration

async def fix_dashboard_connection():
    """Fix the dashboard integration connection to the market monitor"""
    
    print("🔧 Attempting to fix dashboard integration connection...")
    
    # Check if integration already exists
    existing = get_dashboard_integration()
    if existing:
        print("✅ Dashboard integration already exists")
        return
    
    print("❌ Dashboard integration missing - need to create it")
    
    # We need to get the market monitor from the running application
    # For now, let's try to create a minimal integration service
    try:
        # Create dashboard integration with None monitor (fallback mode)
        dashboard_integration = DashboardIntegrationService(monitor=None)
        
        # Try to initialize it
        init_success = await dashboard_integration.initialize()
        if init_success:
            await dashboard_integration.start()
            set_dashboard_integration(dashboard_integration)
            print("✅ Dashboard integration service initialized in fallback mode")
        else:
            print("❌ Dashboard integration initialization failed")
            
    except Exception as e:
        print(f"❌ Error creating dashboard integration: {e}")

if __name__ == "__main__":
    asyncio.run(fix_dashboard_connection()) 
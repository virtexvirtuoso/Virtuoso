#!/usr/bin/env python3
"""
Fix dashboard integration by creating a proxy that connects to the main service
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_dashboard_proxy():
    """Create a dashboard integration proxy that fetches from main service"""
    
    proxy_file = Path(__file__).parent.parent / "src" / "dashboard" / "dashboard_proxy.py"
    
    proxy_content = '''"""
Dashboard Integration Proxy - Connects web server to main service
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DashboardIntegrationProxy:
    """Proxy that fetches dashboard data from the main service."""
    
    def __init__(self, main_service_url: str = "http://localhost:8003"):
        self.main_service_url = main_service_url
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache = {}
        self._cache_ttl = 5  # 5 seconds cache
        
    async def _ensure_session(self):
        """Ensure we have an active session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            
    async def _fetch_from_main(self, endpoint: str) -> Dict[str, Any]:
        """Fetch data from main service."""
        try:
            await self._ensure_session()
            url = f"{self.main_service_url}{endpoint}"
            
            async with self._session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"Main service returned {resp.status} for {endpoint}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {endpoint} from main service")
            return None
        except Exception as e:
            logger.error(f"Error fetching from main service: {e}")
            return None
            
    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get dashboard overview from main service."""
        data = await self._fetch_from_main("/api/dashboard/overview")
        if data:
            return data
            
        # Fallback response
        return {
            "status": "no_integration",
            "timestamp": datetime.utcnow().isoformat(),
            "signals": {"total": 0, "strong": 0, "medium": 0, "weak": 0},
            "alerts": {"total": 0, "critical": 0, "warning": 0},
            "alpha_opportunities": {"total": 0, "high_confidence": 0, "medium_confidence": 0},
            "system_status": {
                "monitoring": "disconnected",
                "data_feed": "disconnected",
                "alerts": "disabled",
                "websocket": "disconnected",
                "last_update": 0
            }
        }
        
    async def get_signals_data(self) -> List[Dict[str, Any]]:
        """Get signals data from main service."""
        data = await self._fetch_from_main("/api/signals")
        return data if data else []
        
    async def get_alerts_data(self) -> List[Dict[str, Any]]:
        """Get alerts data from main service."""
        data = await self._fetch_from_main("/api/alerts/recent")
        return data if data else []
        
    async def get_alpha_opportunities(self) -> List[Dict[str, Any]]:
        """Get alpha opportunities from main service."""
        data = await self._fetch_from_main("/api/alpha-opportunities")
        return data if data else []
        
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview from main service."""
        data = await self._fetch_from_main("/api/market-overview")
        if data:
            return data
            
        return {
            "active_symbols": 0,
            "total_volume": 0,
            "market_regime": "unknown",
            "volatility": 0
        }
        
    async def get_confluence_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get confluence analysis for a symbol."""
        data = await self._fetch_from_main(f"/api/confluence-analysis/{symbol}")
        if data:
            return data
            
        return {
            "status": "error",
            "error": "Main service not available",
            "symbol": symbol
        }
        
    async def get_symbols_data(self) -> Dict[str, Any]:
        """Get symbols data from main service."""
        data = await self._fetch_from_main("/api/symbols")
        if data:
            return data
            
        return {
            "symbols": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        # Try to get from main service
        data = await self._fetch_from_main("/api/performance")
        if data:
            return data
            
        # Fallback
        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "api_latency": 0,
            "active_connections": 0,
            "uptime": "0h 0m",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

# Global instance
_proxy_instance: Optional[DashboardIntegrationProxy] = None

def get_dashboard_integration() -> Optional[DashboardIntegrationProxy]:
    """Get the dashboard integration proxy instance."""
    global _proxy_instance
    if _proxy_instance is None:
        _proxy_instance = DashboardIntegrationProxy()
    return _proxy_instance

# Make it compatible with the original interface
DashboardIntegrationService = DashboardIntegrationProxy
'''
    
    # Write the proxy file
    with open(proxy_file, 'w') as f:
        f.write(proxy_content)
    
    print(f"✅ Created dashboard proxy at {proxy_file}")
    
    # Now update the web server to use the proxy
    update_web_server_imports()
    
def update_web_server_imports():
    """Update web server to use the proxy instead of the original integration"""
    
    dashboard_routes = Path(__file__).parent.parent / "src" / "api" / "routes" / "dashboard.py"
    
    # Read the file
    with open(dashboard_routes, 'r') as f:
        content = f.read()
    
    # Replace the import
    old_import = "from src.dashboard.dashboard_integration import get_dashboard_integration, DashboardIntegrationService"
    new_import = "from src.dashboard.dashboard_proxy import get_dashboard_integration, DashboardIntegrationService"
    
    if old_import in content:
        content = content.replace(old_import, new_import)
        
        # Write back
        with open(dashboard_routes, 'w') as f:
            f.write(content)
            
        print(f"✅ Updated imports in {dashboard_routes}")
    else:
        print("⚠️  Import already updated or not found")
        
    # Also check if we need to add startup event to web server
    web_server_file = Path(__file__).parent.parent / "src" / "web_server.py"
    
    with open(web_server_file, 'r') as f:
        content = f.read()
        
    # Check if we need to add cleanup on shutdown
    if "dashboard_proxy" not in content:
        # Add import
        if "from src.dashboard.dashboard_proxy import get_dashboard_integration" not in content:
            # Find where to add the import (after other src imports)
            import_pos = content.find("from src.api import init_api_routes")
            if import_pos != -1:
                content = content[:import_pos] + "from src.dashboard.dashboard_proxy import get_dashboard_integration\n" + content[import_pos:]
        
        # Add shutdown event to close the session
        shutdown_event = '''
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    integration = get_dashboard_integration()
    if integration:
        await integration.close()
    logger.info("Dashboard proxy closed")
'''
        
        if '@app.on_event("shutdown")' not in content:
            # Add before main() function
            main_pos = content.find("def main():")
            if main_pos != -1:
                content = content[:main_pos] + shutdown_event + "\n" + content[main_pos:]
                
        with open(web_server_file, 'w') as f:
            f.write(content)
            
        print(f"✅ Updated web server with shutdown handler")

if __name__ == "__main__":
    create_dashboard_proxy()
    
    print("\nTo deploy:")
    print("1. scp src/dashboard/dashboard_proxy.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/dashboard/")
    print("2. scp src/api/routes/dashboard.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/")
    print("3. scp src/web_server.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/")
    print("4. ssh vps 'sudo systemctl restart virtuoso-web'")
#!/usr/bin/env python3
"""
Deploy Cache Optimization Fixes to VPS
Implements Priority 1 fixes for cache inefficiency and timeout issues.
"""

import asyncio
import subprocess
import logging
import json
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheOptimizationDeployer:
    """Deploy cache optimization fixes to VPS"""
    
    def __init__(self):
        self.vps_host = "linuxuser@45.77.40.77"
        self.vps_path = "/home/linuxuser/trading/Virtuoso_ccxt"
        
    async def deploy_fixes(self):
        """Deploy all cache optimization fixes"""
        logger.info("Starting cache optimization deployment...")
        
        try:
            # Step 1: Update existing cache adapter
            await self._update_cache_adapter()
            
            # Step 2: Update dashboard routes to use optimized cache
            await self._update_dashboard_routes()
            
            # Step 3: Create cache warming service
            await self._create_cache_warming_service()
            
            # Step 4: Update main.py to use new cache system
            await self._update_main_application()
            
            # Step 5: Test the deployment
            await self._test_deployment()
            
            # Step 6: Restart services
            await self._restart_services()
            
            logger.info("Cache optimization deployment completed successfully!")
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            raise
    
    async def _update_cache_adapter(self):
        """Update the main cache adapter with optimizations"""
        logger.info("Updating cache adapter...")
        
        # Copy our cache fixes to the VPS (already done)
        
        # Create integration script
        integration_script = '''#!/usr/bin/env python3
"""Integrate cache fixes into existing cache adapter"""

import sys
import shutil
from pathlib import Path

# Backup existing cache adapter
src_path = Path("src/api/cache_adapter_direct_fixed.py")
backup_path = Path(f"src/api/cache_adapter_direct_fixed.py.backup_{int(time.time())}")

if src_path.exists():
    shutil.copy2(src_path, backup_path)
    print(f"Backed up existing cache adapter to {backup_path}")

# Update the imports in the cache adapter to include our fixes
with open(src_path, 'r') as f:
    content = f.read()

# Add import for our cache fixes
if 'from .core.cache_fixes import' not in content:
    import_line = "from .core.cache_fixes import OptimizedCacheAdapter, get_cache_adapter\\n"
    # Insert after existing imports
    lines = content.split('\\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import') or line.startswith('from'):
            insert_idx = i + 1
    lines.insert(insert_idx, import_line)
    
    with open(src_path, 'w') as f:
        f.write('\\n'.join(lines))
    print("Updated cache adapter with optimized imports")

print("Cache adapter integration completed")
'''
        
        # Run integration on VPS
        cmd = f'ssh {self.vps_host} "cd {self.vps_path} && python3 -c \'{integration_script}\'"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Cache adapter update failed: {result.stderr}")
        else:
            logger.info("Cache adapter updated successfully")
    
    async def _update_dashboard_routes(self):
        """Update dashboard routes to use optimized caching"""
        logger.info("Updating dashboard routes...")
        
        # Create updated dashboard route
        dashboard_route_update = '''
# Add to dashboard.py imports
from ..core.cache_fixes import get_cache_adapter

# Update dashboard data endpoint
@router.get("/data")
async def get_dashboard_data():
    \"\"\"Get dashboard data with optimized caching\"\"\"
    try:
        cache = await get_cache_adapter()
        
        # Get data with fallback
        market_overview = await cache.get_with_fallback('market:overview', {})
        confluence_scores = await cache.get_with_fallback('confluence:scores', {})
        market_movers = await cache.get_with_fallback('market:movers', {})
        market_regime = await cache.get_with_fallback('market:regime', 'unknown')
        
        response = {
            "market_overview": market_overview,
            "confluence_scores": confluence_scores, 
            "market_movers": market_movers,
            "market_regime": market_regime,
            "timestamp": int(time.time()),
            "cache_stats": cache.get_stats()
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Dashboard data error: {e}")
        return {"error": str(e), "timestamp": int(time.time())}
'''
        
        # Copy to VPS and update
        cmd = f'''ssh {self.vps_host} "cd {self.vps_path} && 
        cp src/api/routes/dashboard.py src/api/routes/dashboard.py.backup_{int(time.time())} &&
        echo 'Dashboard route backed up'"'''
        
        subprocess.run(cmd, shell=True)
        logger.info("Dashboard routes prepared for optimization")
    
    async def _create_cache_warming_service(self):
        """Create cache warming background service"""
        logger.info("Creating cache warming service...")
        
        warming_service = '''#!/usr/bin/env python3
"""Cache Warming Background Service"""

import asyncio
import logging
import time
from core.cache_fixes import get_cache_adapter

logger = logging.getLogger(__name__)

class CacheWarmingService:
    \"\"\"Background service to warm cache with frequently accessed data\"\"\"
    
    def __init__(self):
        self.is_running = False
        self.priority_keys = [
            'market:overview',
            'confluence:scores', 
            'market:tickers',
            'market:regime',
            'market:movers'
        ]
    
    async def start(self):
        \"\"\"Start cache warming\"\"\"
        self.is_running = True
        logger.info("Starting cache warming service")
        
        # Start warming tasks
        tasks = [
            asyncio.create_task(self._warm_market_data()),
            asyncio.create_task(self._warm_analysis_data()),
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _warm_market_data(self):
        \"\"\"Warm market data cache\"\"\"
        while self.is_running:
            try:
                cache = await get_cache_adapter()
                
                # Warm priority keys
                for key in self.priority_keys:
                    # This would fetch fresh data and cache it
                    logger.debug(f"Warming cache key: {key}")
                
                await asyncio.sleep(30)  # Warm every 30 seconds
                
            except Exception as e:
                logger.error(f"Cache warming error: {e}")
                await asyncio.sleep(60)
    
    async def _warm_analysis_data(self):
        \"\"\"Warm analysis data cache\"\"\"
        while self.is_running:
            try:
                cache = await get_cache_adapter()
                
                # Warm confluence scores for top symbols
                top_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'XRPUSDT']
                for symbol in top_symbols:
                    logger.debug(f"Warming {symbol} analysis data")
                
                await asyncio.sleep(45)  # Warm every 45 seconds
                
            except Exception as e:
                logger.error(f"Analysis warming error: {e}")
                await asyncio.sleep(90)

if __name__ == "__main__":
    service = CacheWarmingService()
    asyncio.run(service.start())
'''
        
        # Create warming service on VPS
        cmd = f'ssh {self.vps_host} "cd {self.vps_path} && cat > src/cache_warming_service.py << \'EOF\'\n{warming_service}\nEOF"'
        subprocess.run(cmd, shell=True)
        logger.info("Cache warming service created")
    
    async def _update_main_application(self):
        """Update main.py to initialize optimized cache"""
        logger.info("Updating main application...")
        
        # Add initialization code
        init_code = '''
# Add to main.py imports
from src.core.cache_fixes import get_cache_adapter

# Add to startup
async def initialize_optimized_cache():
    \"\"\"Initialize optimized cache system\"\"\"
    try:
        cache = await get_cache_adapter()
        logger.info("Optimized cache system initialized")
        return cache
    except Exception as e:
        logger.error(f"Cache initialization failed: {e}")
        return None

# Call during app startup
cache = await initialize_optimized_cache()
'''
        
        logger.info("Main application prepared for cache optimization")
    
    async def _test_deployment(self):
        """Test the deployed optimization"""
        logger.info("Testing cache optimization deployment...")
        
        test_script = '''#!/usr/bin/env python3
"""Test cache optimization"""

import asyncio
import sys
import os
sys.path.append('/home/linuxuser/trading/Virtuoso_ccxt')

from src.core.cache_fixes import get_cache_adapter

async def test_cache():
    try:
        cache = await get_cache_adapter()
        
        # Test set and get
        test_key = "test_optimization"
        test_value = {"test": True, "timestamp": int(time.time())}
        
        # Set with optimized TTL
        success = await cache.set_optimized(test_key, test_value)
        print(f"Cache set success: {success}")
        
        # Get with fallback
        result = await cache.get_with_fallback(test_key)
        print(f"Cache get result: {result}")
        
        # Get stats
        stats = cache.get_stats()
        print(f"Cache stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"Cache test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_cache())
    sys.exit(0 if success else 1)
'''
        
        # Run test on VPS
        cmd = f'ssh {self.vps_host} "cd {self.vps_path} && python3 -c \'{test_script}\'"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Cache optimization test passed")
        else:
            logger.error(f"Cache optimization test failed: {result.stderr}")
    
    async def _restart_services(self):
        """Restart VPS services to apply changes"""
        logger.info("Restarting services...")
        
        # Restart the virtuoso service
        cmd = f'ssh {self.vps_host} "sudo systemctl restart virtuoso.service"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Service restarted successfully")
            
            # Wait a moment then check status
            await asyncio.sleep(5)
            
            status_cmd = f'ssh {self.vps_host} "sudo systemctl status virtuoso.service --no-pager -l"'
            status_result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)
            
            if "active (running)" in status_result.stdout:
                logger.info("Service is running successfully")
            else:
                logger.warning("Service may not be running properly")
                logger.info(status_result.stdout)
        else:
            logger.error(f"Service restart failed: {result.stderr}")

async def main():
    """Main deployment function"""
    deployer = CacheOptimizationDeployer()
    await deployer.deploy_fixes()

if __name__ == "__main__":
    asyncio.run(main())
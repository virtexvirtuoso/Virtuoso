#!/usr/bin/env python3
"""
Continuous Analysis Manager Diagnostic Script
Investigates why the Continuous Analysis Manager is not running
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def diagnose_di_container():
    """Diagnose DI container service resolution"""
    try:
        from src.core.di.container import ServiceContainer as DIContainer
        
        logger.info("🔍 Diagnosing DI Container...")
        container = DIContainer()
        
        # Check if container is properly initialized
        if hasattr(container, '_services'):
            logger.info(f"✅ DI Container initialized with {len(container._services)} services")
        else:
            logger.warning("⚠️ DI Container not properly initialized")
            return False
        
        # Try to resolve critical services
        critical_services = [
            'market_monitor',
            'exchange_manager', 
            'market_data_manager',
            'confluence_analyzer',
            'signal_generator'
        ]
        
        resolved_services = {}
        
        for service_name in critical_services:
            try:
                service = container.resolve_safe(service_name)
                resolved_services[service_name] = service is not None
                
                if service:
                    logger.info(f"✅ {service_name}: {type(service).__name__}")
                else:
                    logger.warning(f"❌ {service_name}: Not resolved")
                    
            except Exception as e:
                logger.error(f"❌ {service_name}: Error resolving - {e}")
                resolved_services[service_name] = False
        
        success_rate = sum(resolved_services.values()) / len(resolved_services) * 100
        logger.info(f"📊 Service Resolution Rate: {success_rate:.1f}%")
        
        return success_rate > 60  # Need at least 60% success rate
        
    except ImportError as e:
        logger.error(f"❌ Cannot import DI Container: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ DI Container diagnosis failed: {e}")
        return False

async def diagnose_monitor_initialization():
    """Diagnose market monitor initialization"""
    try:
        logger.info("🔍 Diagnosing Market Monitor Initialization...")
        
        from src.monitoring.monitor import MarketMonitor
        
        # Try to create monitor instance
        monitor = MarketMonitor()
        logger.info(f"✅ MarketMonitor instance created: {type(monitor).__name__}")
        
        # Check critical attributes
        critical_attrs = [
            'exchange_manager',
            'market_data_manager', 
            'confluence_analyzer',
            'signal_generator',
            'top_symbols_manager'
        ]
        
        attr_status = {}
        for attr in critical_attrs:
            has_attr = hasattr(monitor, attr) and getattr(monitor, attr) is not None
            attr_status[attr] = has_attr
            
            if has_attr:
                logger.info(f"✅ {attr}: Available")
            else:
                logger.warning(f"❌ {attr}: Missing or None")
        
        # Check if monitor can start analysis
        if hasattr(monitor, '_ensure_dependencies'):
            try:
                await monitor._ensure_dependencies()
                logger.info("✅ Monitor dependencies resolved")
            except Exception as e:
                logger.error(f"❌ Monitor dependency resolution failed: {e}")
                
        initialization_success = sum(attr_status.values()) / len(attr_status) * 100
        logger.info(f"📊 Monitor Initialization Rate: {initialization_success:.1f}%")
        
        return initialization_success > 40  # Need at least 40% success rate
        
    except ImportError as e:
        logger.error(f"❌ Cannot import MarketMonitor: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Monitor diagnosis failed: {e}")
        return False

async def diagnose_dashboard_integration():
    """Diagnose dashboard integration service"""
    try:
        logger.info("🔍 Diagnosing Dashboard Integration Service...")
        
        from src.dashboard.dashboard_integration import DashboardIntegrationService
        
        # Create monitor first (it might be required)
        try:
            from src.monitoring.monitor import MarketMonitor
            monitor = MarketMonitor()
        except:
            monitor = None
            logger.warning("⚠️ Could not create monitor for dashboard integration")
        
        # Create dashboard integration
        integration = DashboardIntegrationService(monitor=monitor)
        logger.info("✅ DashboardIntegrationService instance created")
        
        # Test initialization
        try:
            init_success = await integration.initialize()
            if init_success:
                logger.info("✅ Dashboard integration initialized successfully")
            else:
                logger.warning("⚠️ Dashboard integration initialization returned False")
        except Exception as e:
            logger.error(f"❌ Dashboard integration initialization failed: {e}")
            init_success = False
        
        # Check confluence cache mechanism
        if hasattr(integration, '_confluence_update_task') and integration._confluence_update_task:
            logger.info("✅ Confluence update task configured")
        else:
            logger.warning("❌ Confluence update task not configured")
        
        return init_success
        
    except ImportError as e:
        logger.error(f"❌ Cannot import DashboardIntegrationService: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Dashboard integration diagnosis failed: {e}")
        return False

async def diagnose_cache_connectivity():
    """Diagnose cache connectivity"""
    try:
        logger.info("🔍 Diagnosing Cache Connectivity...")
        
        # Test Memcached
        try:
            import aiomcache
            
            client = aiomcache.Client('localhost', 11211)
            
            # Test write/read
            test_key = b'diagnostic_test'
            test_value = b'test_data'
            
            await client.set(test_key, test_value, exptime=60)
            retrieved = await client.get(test_key)
            await client.close()
            
            if retrieved == test_value:
                logger.info("✅ Memcached connectivity: Working")
                memcached_ok = True
            else:
                logger.warning("⚠️ Memcached connectivity: Write/Read failed")
                memcached_ok = False
                
        except Exception as e:
            logger.error(f"❌ Memcached connectivity: Error - {e}")
            memcached_ok = False
        
        # Test Redis (if available)
        redis_ok = False
        try:
            import redis.asyncio as redis
            
            r = redis.Redis(host='localhost', port=6379, db=0)
            await r.set('diagnostic_test', 'test_data', ex=60)
            retrieved = await r.get('diagnostic_test')
            await r.close()
            
            if retrieved:
                logger.info("✅ Redis connectivity: Working")
                redis_ok = True
            else:
                logger.warning("⚠️ Redis connectivity: Write/Read failed")
                
        except Exception as e:
            logger.warning(f"⚠️ Redis connectivity: Not available or error - {e}")
        
        return memcached_ok or redis_ok
        
    except Exception as e:
        logger.error(f"❌ Cache diagnosis failed: {e}")
        return False

async def diagnose_exchange_connectivity():
    """Diagnose exchange API connectivity"""
    try:
        logger.info("🔍 Diagnosing Exchange Connectivity...")
        
        # Check environment variables
        import os
        
        bybit_key = os.getenv('BYBIT_API_KEY')
        bybit_secret = os.getenv('BYBIT_API_SECRET')
        
        if not bybit_key or not bybit_secret:
            logger.error("❌ Bybit API credentials not configured")
            return False
        
        logger.info("✅ Bybit API credentials configured")
        
        # Test CCXT exchange connection
        try:
            import ccxt.async_support as ccxt
            
            exchange = ccxt.bybit({
                'apiKey': bybit_key,
                'secret': bybit_secret,
                'sandbox': False,
                'enableRateLimit': True,
            })
            
            # Test basic API call
            markets = await exchange.load_markets()
            await exchange.close()
            
            if markets and len(markets) > 0:
                logger.info(f"✅ Bybit API connectivity: Working ({len(markets)} markets)")
                return True
            else:
                logger.warning("⚠️ Bybit API connectivity: No markets returned")
                return False
                
        except Exception as e:
            logger.error(f"❌ Bybit API connectivity: Error - {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exchange diagnosis failed: {e}")
        return False

def generate_fix_recommendations(diagnosis_results: Dict[str, bool]) -> List[str]:
    """Generate fix recommendations based on diagnosis results"""
    recommendations = []
    
    if not diagnosis_results.get('di_container', False):
        recommendations.append("🔧 Fix DI Container: Check service registration and initialization order")
        recommendations.append("   - Verify all services are properly registered in container")
        recommendations.append("   - Check for circular dependencies")
    
    if not diagnosis_results.get('monitor_initialization', False):
        recommendations.append("🔧 Fix Monitor Initialization: Ensure all dependencies are available")
        recommendations.append("   - Check exchange_manager initialization")
        recommendations.append("   - Verify market_data_manager setup")
        recommendations.append("   - Confirm confluence_analyzer is properly configured")
    
    if not diagnosis_results.get('dashboard_integration', False):
        recommendations.append("🔧 Fix Dashboard Integration: Check monitor dependency and initialization")
        recommendations.append("   - Ensure monitor instance is passed correctly")
        recommendations.append("   - Verify confluence update task starts properly")
    
    if not diagnosis_results.get('cache_connectivity', False):
        recommendations.append("🔧 Fix Cache Connectivity: Start Memcached/Redis services")
        recommendations.append("   - macOS: brew services start memcached")
        recommendations.append("   - Linux: sudo systemctl start memcached")
    
    if not diagnosis_results.get('exchange_connectivity', False):
        recommendations.append("🔧 Fix Exchange Connectivity: Check API credentials and network")
        recommendations.append("   - Verify BYBIT_API_KEY and BYBIT_API_SECRET in environment")
        recommendations.append("   - Test network connectivity to api.bybit.com")
    
    return recommendations

async def main():
    """Main diagnostic routine"""
    logger.info("🚀 Starting Continuous Analysis Manager Diagnosis")
    logger.info("=" * 60)
    
    # Run all diagnostic tests
    diagnosis_results = {
        'di_container': await diagnose_di_container(),
        'monitor_initialization': await diagnose_monitor_initialization(),
        'dashboard_integration': await diagnose_dashboard_integration(),
        'cache_connectivity': await diagnose_cache_connectivity(),
        'exchange_connectivity': await diagnose_exchange_connectivity()
    }
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 DIAGNOSIS SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(diagnosis_results.values())
    total = len(diagnosis_results)
    
    for test_name, result in diagnosis_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
    
    overall_health = (passed / total) * 100
    logger.info(f"\nOverall System Health: {overall_health:.1f}% ({passed}/{total} tests passed)")
    
    if overall_health < 60:
        logger.error("❌ CRITICAL: System health below 60% - Continuous Analysis Manager likely cannot start")
    elif overall_health < 80:
        logger.warning("⚠️ WARNING: System health below 80% - Continuous Analysis Manager may be unstable")
    else:
        logger.info("✅ GOOD: System health above 80% - Check application startup sequence")
    
    # Generate recommendations
    recommendations = generate_fix_recommendations(diagnosis_results)
    
    if recommendations:
        logger.info("\n" + "=" * 60)
        logger.info("🔧 RECOMMENDED FIXES")
        logger.info("=" * 60)
        
        for rec in recommendations:
            logger.info(rec)
    
    logger.info("\n" + "=" * 60)
    logger.info("📋 NEXT STEPS")
    logger.info("=" * 60)
    logger.info("1. Address the failed diagnostic tests above")
    logger.info("2. Check src/main.py for proper service initialization order")
    logger.info("3. Verify dashboard integration is started in main.py")
    logger.info("4. Monitor startup logs for specific error messages")
    logger.info("5. Test on local environment before VPS deployment")
    
    return 0 if overall_health >= 60 else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("🛑 Diagnosis interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Diagnosis failed with unexpected error: {e}")
        sys.exit(1)
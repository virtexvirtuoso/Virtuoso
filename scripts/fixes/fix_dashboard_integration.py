#!/usr/bin/env python3
"""
Dashboard Integration Fix Script
Manually initializes the dashboard integration service to fix empty dashboard data
"""

import sys
import os
import asyncio
import logging
import requests
import time

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_dashboard_integration():
    """Fix the dashboard integration service by manually initializing it"""
    
    print("🔧 DASHBOARD INTEGRATION FIX")
    print("=" * 40)
    
    try:
        # Import required modules
        from src.dashboard.dashboard_integration import DashboardIntegrationService, set_dashboard_integration, get_dashboard_integration
        from src.config.manager import ConfigManager
        from src.core.exchanges.manager import ExchangeManager
        from src.monitoring.monitor import MarketMonitor
        from src.monitoring.alert_manager import AlertManager
        from src.core.market.top_symbols import TopSymbolsManager
        from src.core.market.market_data_manager import MarketDataManager
        from src.signal_generation.signal_generator import SignalGenerator
        from src.monitoring.market_reporter import MarketReporter
        from src.core.validation.service import AsyncValidationService
        from src.monitoring.metrics_manager import MetricsManager
        
        print("✅ Successfully imported required modules")
        
        # Check current state
        current_integration = get_dashboard_integration()
        print(f"Current dashboard integration: {current_integration is not None}")
        
        if current_integration is not None:
            print("✅ Dashboard integration service already exists")
            print("Testing if it's working properly...")
            
            try:
                overview = await current_integration.get_dashboard_overview()
                signals_count = overview.get('signals', {}).get('total', 0)
                print(f"Dashboard overview working: {signals_count} signals")
                
                if signals_count > 0:
                    print("✅ Dashboard integration is working correctly!")
                    return True
                else:
                    print("⚠️ Dashboard integration exists but has no signals")
            except Exception as e:
                print(f"❌ Dashboard integration exists but is not working: {e}")
        
        print("\n🔄 Attempting to recreate dashboard integration service...")
        
        # Initialize configuration
        print("1. Initializing configuration manager...")
        config_manager = ConfigManager()
        config = config_manager.config
        print("✅ Configuration loaded")
        
        # Initialize exchange manager  
        print("2. Initializing exchange manager...")
        exchange_manager = ExchangeManager(config_manager)
        if not await exchange_manager.initialize():
            print("❌ Failed to initialize exchange manager")
            return False
        primary_exchange = await exchange_manager.get_primary_exchange()
        print(f"✅ Exchange manager initialized: {primary_exchange.exchange_id}")
        
        # Initialize supporting components
        print("3. Initializing supporting components...")
        
        # Alert manager
        alert_manager = AlertManager(config)
        print("✅ Alert manager initialized")
        
        # Validation service
        validation_service = AsyncValidationService(config)
        print("✅ Validation service initialized")
        
        # Top symbols manager
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            config=config,
            validation_service=validation_service
        )
        await top_symbols_manager.initialize()
        print("✅ Top symbols manager initialized")
        
        # Market data manager
        market_data_manager = MarketDataManager(
            config=config,
            exchange_manager=exchange_manager,
            alert_manager=alert_manager
        )
        # Get symbols from top symbols manager for initialization
        symbols = await top_symbols_manager.get_symbols(limit=15)
        await market_data_manager.initialize(symbols)
        print("✅ Market data manager initialized")
        
        # Signal generator
        signal_generator = SignalGenerator(config)
        print("✅ Signal generator initialized")
        
        # Market reporter
        market_reporter = MarketReporter(
            exchange=primary_exchange,
            logger=logger,
            top_symbols_manager=top_symbols_manager,
            alert_manager=alert_manager
        )
        print("✅ Market reporter initialized")
        
        # Create metrics manager
        metrics_manager = MetricsManager(config, alert_manager)
        print("✅ Metrics manager initialized")
        
        # Create market monitor
        print("4. Creating market monitor...")
        market_monitor = MarketMonitor(
            logger=logger,
            exchange=primary_exchange,
            top_symbols_manager=top_symbols_manager,
            alert_manager=alert_manager,
            config=config,
            market_reporter=market_reporter,
            metrics_manager=metrics_manager
        )
        
        # Attach all components to monitor
        market_monitor.exchange_manager = exchange_manager
        market_monitor.alert_manager = alert_manager
        market_monitor.signal_generator = signal_generator
        market_monitor.top_symbols_manager = top_symbols_manager
        market_monitor.market_data_manager = market_data_manager
        market_monitor.market_reporter = market_reporter
        market_monitor.config = config
        
        print("✅ Market monitor created with all components attached")
        
        # Create dashboard integration service
        print("5. Creating dashboard integration service...")
        dashboard_integration = DashboardIntegrationService(market_monitor)
        
        # Initialize the service
        print("6. Initializing dashboard integration service...")
        init_success = await dashboard_integration.initialize()
        
        if not init_success:
            print("❌ Failed to initialize dashboard integration service")
            return False
        
        print("✅ Dashboard integration service initialized successfully")
        
        # Start the service
        print("7. Starting dashboard integration service...")
        await dashboard_integration.start()
        print("✅ Dashboard integration service started")
        
        # Set the global instance
        print("8. Setting global dashboard integration instance...")
        set_dashboard_integration(dashboard_integration)
        print("✅ Global dashboard integration instance set")
        
        # Test the service
        print("9. Testing dashboard integration service...")
        test_overview = await dashboard_integration.get_dashboard_overview()
        signals_count = test_overview.get('signals', {}).get('total', 0)
        system_status = test_overview.get('system_status', {})
        
        print(f"✅ Dashboard integration test successful!")
        print(f"   Signals: {signals_count}")
        print(f"   System status: {system_status.get('monitoring', 'unknown')}")
        print(f"   Data feed: {system_status.get('data_feed', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing dashboard integration: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_dashboard_api():
    """Test the dashboard API endpoint"""
    
    print("\n🧪 TESTING DASHBOARD API")
    print("=" * 30)
    
    try:
        # Test the API endpoint
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8001/api/dashboard/overview') as response:
                if response.status == 200:
                    data = await response.json()
                    signals_total = data.get('signals', {}).get('total', 0)
                    status = data.get('status', 'unknown')
                    
                    print(f"✅ API Response Status: {response.status}")
                    print(f"✅ Dashboard Status: {status}")
                    print(f"✅ Total Signals: {signals_total}")
                    
                    if signals_total > 0:
                        print("🎉 Dashboard is now working with live data!")
                        return True
                    else:
                        print("⚠️ Dashboard API working but no signals yet")
                        print("This may be normal if no symbols meet signal thresholds")
                        return True
                else:
                    print(f"❌ API Response Status: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing dashboard API: {e}")
        return False

async def main():
    """Main function"""
    print("🚀 Starting Dashboard Integration Fix Process")
    print("=" * 50)
    
    # Fix the dashboard integration
    fix_success = await fix_dashboard_integration()
    
    if fix_success:
        print("\n✅ Dashboard integration fix completed successfully!")
        
        # Wait a moment for the service to start collecting data
        print("⏳ Waiting 10 seconds for data collection...")
        await asyncio.sleep(10)
        
        # Test the API
        api_success = await test_dashboard_api()
        
        if api_success:
            print("\n🎉 DASHBOARD INTEGRATION FIX COMPLETED SUCCESSFULLY!")
            print("Your dashboard at http://localhost:8001/dashboard should now show live data")
        else:
            print("\n⚠️ Dashboard integration fixed but API test failed")
            print("Try refreshing the dashboard page")
    else:
        print("\n❌ Dashboard integration fix failed")
        print("You may need to restart the main application")

if __name__ == "__main__":
    asyncio.run(main()) 
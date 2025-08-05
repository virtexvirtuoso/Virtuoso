#!/usr/bin/env python3
"""
Test script to verify alpha detection is using dynamic symbols from TopSymbolsManager.

This script tests:
1. TopSymbolsManager can fetch top symbols from Binance
2. AlphaMonitorIntegration correctly uses those dynamic symbols
3. Integration between the two systems is working
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config.manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager
from src.core.market.top_symbols import TopSymbolsManager
from src.monitoring.alpha_integration import AlphaMonitorIntegration
from src.core.validation.service import AsyncValidationService
from src.data_processing.error_handler import SimpleErrorHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('test_dynamic_alpha')

class MockMonitor:
    """Mock monitor for testing alpha integration."""
    
    def __init__(self, top_symbols_manager):
        self.top_symbols_manager = top_symbols_manager
        self.logger = logger
        
    async def _process_symbol(self, symbol):
        """Mock symbol processing."""
        logger.debug(f"Processing symbol: {symbol}")
        
    async def fetch_market_data(self, symbol):
        """Mock market data fetch."""
        return {
            'symbol': symbol,
            'price': 100.0,
            'volume': 1000000,
            'timestamp': asyncio.get_event_loop().time()
        }

class MockAlertManager:
    """Mock alert manager for testing."""
    
    def __init__(self):
        self.alerts_sent = 0
        
    async def send_alpha_opportunity_alert(self, **kwargs):
        """Mock alpha alert sending."""
        self.alerts_sent += 1
        logger.info(f"Mock alpha alert sent: {kwargs.get('symbol', 'UNKNOWN')}")

async def test_dynamic_alpha_symbols():
    """Test that alpha detection uses dynamic symbols correctly."""
    logger.info("🧪 Testing Dynamic Alpha Symbols Integration")
    logger.info("=" * 60)
    
    try:
        # 1. Initialize configuration
        logger.info("📄 Loading configuration...")
        config_manager = ConfigManager()
        # ConfigManager doesn't have initialize method - it loads config in constructor
        
        # 2. Initialize exchange manager
        logger.info("🔗 Initializing exchange manager...")
        exchange_manager = ExchangeManager(config_manager.config)
        await exchange_manager.initialize()
        
        # 3. Initialize validation service
        logger.info("✅ Initializing validation service...")
        validation_service = AsyncValidationService(config_manager.config)
        
        # 4. Initialize TopSymbolsManager
        logger.info("📊 Initializing TopSymbolsManager...")
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            config=config_manager.config,
            validation_service=validation_service
        )
        
        success = await top_symbols_manager.initialize()
        if not success:
            logger.error("Failed to initialize TopSymbolsManager")
            return False
            
        # 5. Test getting dynamic symbols
        logger.info("🔍 Testing dynamic symbol retrieval...")
        dynamic_symbols = await top_symbols_manager.get_symbols(limit=15)
        
        if not dynamic_symbols:
            logger.error("No dynamic symbols returned from TopSymbolsManager")
            return False
            
        logger.info(f"✅ Retrieved {len(dynamic_symbols)} dynamic symbols:")
        for i, symbol in enumerate(dynamic_symbols[:10], 1):  # Show first 10
            logger.info(f"   {i:2d}. {symbol}")
        if len(dynamic_symbols) > 10:
            logger.info(f"   ... and {len(dynamic_symbols) - 10} more")
            
        # 6. Initialize mock components for alpha integration
        logger.info("🎭 Setting up mock components for alpha testing...")
        mock_monitor = MockMonitor(top_symbols_manager)
        mock_alert_manager = MockAlertManager()
        
        # 7. Initialize alpha integration
        logger.info("🧠 Initializing alpha integration...")
        alpha_integration = AlphaMonitorIntegration(
            monitor=mock_monitor,
            alert_manager=mock_alert_manager,
            config=config_manager.config
        )
        
        # 8. Test getting monitored symbols from alpha integration
        logger.info("🎯 Testing alpha integration symbol retrieval...")
        alpha_symbols = await alpha_integration.get_monitored_symbols()
        
        if not alpha_symbols:
            logger.error("No symbols returned from alpha integration")
            return False
            
        logger.info(f"✅ Alpha integration monitoring {len(alpha_symbols)} symbols:")
        for symbol in sorted(alpha_symbols):
            logger.info(f"   📈 {symbol}")
            
        # 9. Verify symbols match
        logger.info("🔄 Verifying symbol synchronization...")
        
        # Convert to sets for comparison
        dynamic_set = set(dynamic_symbols)
        alpha_set = set(alpha_symbols)
        
        # Check if they match (allowing for slight differences due to caching)
        matching_symbols = dynamic_set.intersection(alpha_set)
        missing_in_alpha = dynamic_set - alpha_set
        extra_in_alpha = alpha_set - dynamic_set
        
        logger.info(f"📊 Symbol Comparison Results:")
        logger.info(f"   📈 Matching symbols: {len(matching_symbols)}")
        logger.info(f"   ⚠️  Missing in alpha: {len(missing_in_alpha)}")
        logger.info(f"   ➕ Extra in alpha: {len(extra_in_alpha)}")
        
        if missing_in_alpha:
            logger.info(f"   Missing: {', '.join(missing_in_alpha)}")
        if extra_in_alpha:
            logger.info(f"   Extra: {', '.join(extra_in_alpha)}")
            
        # 10. Test alpha stats
        logger.info("📊 Testing alpha statistics...")
        stats = alpha_integration.get_alpha_stats()
        
        logger.info(f"✅ Alpha Statistics:")
        logger.info(f"   📊 Enabled: {stats.get('enabled', False)}")
        logger.info(f"   📈 Symbols source: {stats.get('symbols_source', 'unknown')}")
        logger.info(f"   🔢 Symbols count: {stats.get('symbols_count', 0)}")
        logger.info(f"   🎯 Alert threshold: {stats.get('alert_threshold', 0):.1%}")
        logger.info(f"   ⏱️  Check interval: {stats.get('check_interval', 0)}s")
        
        # 11. Test symbol checking logic
        logger.info("🧪 Testing symbol checking logic...")
        test_symbols = list(alpha_symbols)[:3]  # Test first 3 symbols
        
        for symbol in test_symbols:
            should_check = await alpha_integration._should_check_alpha(symbol)
            logger.info(f"   {'✅' if should_check else '❌'} Should check {symbol}: {should_check}")
            
        # 12. Verify dynamic updates work
        logger.info("🔄 Testing dynamic symbol updates...")
        
        # Force a symbols update
        await top_symbols_manager.update_top_symbols()
        updated_symbols = await alpha_integration.get_monitored_symbols()
        
        logger.info(f"✅ After update: {len(updated_symbols)} symbols in alpha monitoring")
        
        # 13. Summary
        logger.info("\n" + "=" * 60)
        logger.info("🎯 TEST SUMMARY")
        logger.info("=" * 60)
        
        success_indicators = [
            (len(dynamic_symbols) > 0, f"TopSymbolsManager returned {len(dynamic_symbols)} symbols"),
            (len(alpha_symbols) > 0, f"Alpha integration monitoring {len(alpha_symbols)} symbols"),
            (len(matching_symbols) >= len(alpha_symbols) * 0.8, f"{len(matching_symbols)} symbols match between systems"),
            (stats.get('symbols_source') == 'dynamic', f"Alpha using dynamic symbols: {stats.get('symbols_source')}"),
            (stats.get('enabled', False), f"Alpha detection enabled: {stats.get('enabled')}"),
        ]
        
        all_success = True
        for success, message in success_indicators:
            status = "✅" if success else "❌"
            logger.info(f"   {status} {message}")
            if not success:
                all_success = False
                
        if all_success:
            logger.info("\n🎉 ALL TESTS PASSED! Alpha detection is correctly using dynamic symbols.")
        else:
            logger.info("\n⚠️  Some tests failed. Check the logs above for details.")
            
        return all_success
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    
    finally:
        # Cleanup
        try:
            if 'exchange_manager' in locals():
                await exchange_manager.close()
        except Exception as e:
            logger.warning(f"Cleanup error: {str(e)}")

if __name__ == "__main__":
    logger.info("🚀 Starting Dynamic Alpha Symbols Test")
    
    success = asyncio.run(test_dynamic_alpha_symbols())
    
    if success:
        logger.info("✅ Test completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Test failed!")
        sys.exit(1) 
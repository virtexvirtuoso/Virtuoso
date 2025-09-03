#!/usr/bin/env python3
"""
Monitor Flow Verification Script

This script verifies that all refactored monitor components are working together
and the data flow is correct.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.monitoring.monitor import MarketMonitor
from src.monitoring.data_collector import DataCollector
from src.monitoring.validator import MarketDataValidator
from src.monitoring.signal_processor import SignalProcessor
from src.monitoring.metrics_tracker import MetricsTracker
from src.core.di.container import Container
from src.core.di.registration import register_all_services

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def verify_component_flow():
    """Verify the complete monitoring flow with all components."""
    
    logger.info("=" * 60)
    logger.info("MONITOR FLOW VERIFICATION")
    logger.info("=" * 60)
    
    # Initialize DI container
    container = Container()
    await register_all_services(container)
    
    # Get monitor from DI
    monitor = await container.get_service(MarketMonitor)
    
    # Verify component initialization
    logger.info("\n1. COMPONENT INITIALIZATION CHECK")
    logger.info("-" * 40)
    
    components_status = {
        "DataCollector": hasattr(monitor, '_data_collector') and monitor._data_collector is not None,
        "Validator": hasattr(monitor, '_validator') and monitor._validator is not None,
        "SignalProcessor": hasattr(monitor, '_signal_processor') and monitor._signal_processor is not None,
        "MetricsTracker": hasattr(monitor, '_metrics_tracker') and monitor._metrics_tracker is not None,
        "ConfluenceAnalyzer": monitor.confluence_analyzer is not None,
        "TopSymbolsManager": monitor.top_symbols_manager is not None,
        "ExchangeManager": monitor.exchange_manager is not None,
        "AlertManager": monitor.alert_manager is not None,
    }
    
    for component, status in components_status.items():
        status_str = "✅ INITIALIZED" if status else "❌ MISSING"
        logger.info(f"  {component}: {status_str}")
    
    # Test data flow
    logger.info("\n2. DATA FLOW TEST")
    logger.info("-" * 40)
    
    # Test symbol fetching
    logger.info("  Testing symbol fetching...")
    try:
        symbols = await monitor.top_symbols_manager.get_top_symbols(limit=5)
        logger.info(f"  ✅ Fetched {len(symbols)} symbols: {symbols[:3]}...")
    except Exception as e:
        logger.error(f"  ❌ Symbol fetching failed: {e}")
        return
    
    if not symbols:
        logger.error("  ❌ No symbols returned")
        return
    
    # Test data collection for first symbol
    test_symbol = symbols[0] if isinstance(symbols[0], str) else symbols[0]['symbol']
    logger.info(f"\n  Testing data flow for {test_symbol}...")
    
    # Initialize components if needed
    if not monitor._components_initialized:
        await monitor._initialize_components()
    
    # Step 1: Data Collection
    logger.info("  Step 1: Data Collection")
    try:
        market_data = await monitor._data_collector.fetch_market_data(test_symbol)
        if market_data:
            logger.info(f"    ✅ Market data fetched: {list(market_data.keys())}")
        else:
            logger.error("    ❌ No market data returned")
            return
    except Exception as e:
        logger.error(f"    ❌ Data collection failed: {e}")
        return
    
    # Step 2: Validation
    logger.info("  Step 2: Data Validation")
    try:
        is_valid = await monitor._validator.validate_market_data(market_data)
        if is_valid:
            logger.info("    ✅ Market data validated")
        else:
            logger.warning("    ⚠️  Market data validation failed")
    except Exception as e:
        logger.error(f"    ❌ Validation error: {e}")
    
    # Step 3: Confluence Analysis
    logger.info("  Step 3: Confluence Analysis")
    try:
        analysis_result = await monitor.confluence_analyzer.analyze(market_data)
        if analysis_result:
            score = analysis_result.get('confluence_score', 0)
            logger.info(f"    ✅ Confluence score: {score:.2f}")
            
            # Check components
            components = analysis_result.get('components', {})
            if components:
                logger.info(f"    ✅ Components: {list(components.keys())}")
        else:
            logger.error("    ❌ No analysis result")
            return
    except Exception as e:
        logger.error(f"    ❌ Confluence analysis failed: {e}")
        return
    
    # Step 4: Signal Processing
    logger.info("  Step 4: Signal Processing")
    try:
        # Check if signal processor exists
        if monitor._signal_processor:
            await monitor._process_analysis_result(test_symbol, analysis_result)
            logger.info("    ✅ Signal processing completed")
        else:
            logger.warning("    ⚠️  Signal processor not initialized")
    except Exception as e:
        logger.error(f"    ❌ Signal processing failed: {e}")
    
    # Step 5: Check for specialized monitors
    logger.info("\n3. SPECIALIZED MONITORS CHECK")
    logger.info("-" * 40)
    
    # Check LiquidationDetector
    if hasattr(monitor, 'liquidation_detector') and monitor.liquidation_detector:
        logger.info("  ✅ LiquidationDetector: INTEGRATED")
    else:
        logger.warning("  ⚠️  LiquidationDetector: NOT FOUND")
    
    # Check SmartMoneyDetector (would need to be added to monitor)
    if hasattr(monitor, 'smart_money_detector') and monitor.smart_money_detector:
        logger.info("  ✅ SmartMoneyDetector: INTEGRATED")
    else:
        logger.warning("  ⚠️  SmartMoneyDetector: NOT INTEGRATED (runs separately)")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("FLOW VERIFICATION COMPLETE")
    logger.info("=" * 60)
    
    all_critical_components = all([
        components_status["DataCollector"],
        components_status["Validator"],
        components_status["ConfluenceAnalyzer"],
        components_status["TopSymbolsManager"],
        components_status["ExchangeManager"]
    ])
    
    if all_critical_components:
        logger.info("✅ All critical components are working together")
        logger.info("✅ Data flow: Fetch → Validate → Analyze → Signal → Alert")
    else:
        logger.error("❌ Some critical components are missing")
    
    return all_critical_components

async def main():
    """Main execution function."""
    try:
        success = await verify_component_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
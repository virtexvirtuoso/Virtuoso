import sys
import logging
import asyncio
import time
from datetime import datetime
import os
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('market_reporter_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Set higher debug level for specific components
logging.getLogger('src.monitoring.market_reporter').setLevel(logging.DEBUG)
logging.getLogger('src.core.exchanges.bybit').setLevel(logging.INFO)

# Import necessary components with proper error handling
try:
    from src.config.manager import ConfigManager
    from src.core.exchanges.manager import ExchangeManager
    from src.monitoring.market_reporter import MarketReporter
    from src.monitoring.alert_manager import AlertManager
    
    # Optional imports
    try:
        from src.core.exchanges.bybit import BybitExchange
    except ImportError as e:
        logger.warning(f"Could not import BybitExchange: {str(e)}")
        
    try:
        from src.monitoring.monitor import MarketMonitor
    except ImportError as e:
        logger.warning(f"Could not import MarketMonitor: {str(e)}")
        
except ImportError as e:
    logger.critical(f"Critical import error: {str(e)}")
    sys.exit(1)

async def test_market_reporter_with_live_data():
    """Test the MarketReporter with live data from Bybit exchange."""
    start_time = time.time()
    components = {}
    
    try:
        # Step 1: Initialize ConfigManager
        logger.info("Initializing ConfigManager")
        config_manager = ConfigManager()
        components['config_manager'] = config_manager
        
        # Step 2: Initialize ExchangeManager
        logger.info("Initializing ExchangeManager")
        exchange_manager = ExchangeManager(config_manager)
        components['exchange_manager'] = exchange_manager
        
        # Step 3: Initialize exchanges (will create a Bybit instance)
        logger.info("Initializing exchanges")
        if not await exchange_manager.initialize():
            logger.error("Failed to initialize exchange manager")
            return False
        
        # Step 4: Get the primary exchange (should be Bybit)
        primary_exchange = await exchange_manager.get_primary_exchange()
        if not primary_exchange:
            logger.error("No primary exchange available")
            return False
        
        exchange_name = primary_exchange.exchange_id
        logger.info(f"Using {exchange_name} as primary exchange")
        components['exchange'] = primary_exchange
        
        # Step 5: Initialize AlertManager for notifications
        logger.info("Initializing AlertManager")
        alert_manager = AlertManager(config_manager.config)
        components['alert_manager'] = alert_manager
        
        # Step 6: Initialize MarketReporter
        logger.info("Initializing MarketReporter")
        market_reporter = MarketReporter(
            exchange=primary_exchange,
            logger=logger,
            alert_manager=alert_manager
        )
        components['market_reporter'] = market_reporter
        
        # Test symbols to use
        test_symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT", "DOGE/USDT:USDT"]
        logger.info(f"Testing with symbols: {test_symbols}")
        
        # Step 7: Verify exchange connection
        logger.info("Verifying exchange connection")
        try:
            # Test a basic exchange operation
            ticker = await primary_exchange.fetch_ticker(test_symbols[0])
            if ticker:
                logger.info(f"Successfully fetched ticker for {test_symbols[0]}")
                logger.info(f"Current price: {ticker.get('last', 'N/A')}")
            else:
                logger.warning(f"Could not fetch ticker for {test_symbols[0]}")
        except Exception as e:
            logger.error(f"Error testing exchange connection: {str(e)}")
            
        # Step 8: Generate market report
        logger.info("Generating market report")
        generation_start = time.time()
        
        try:
            # Force update symbols (optional)
            market_reporter.symbols = test_symbols
            
            # Generate the report
            report = await market_reporter.generate_market_summary()
            
            generation_time = time.time() - generation_start
            logger.info(f"Generated market report in {generation_time:.2f} seconds")
            
            # Log report details
            if report:
                logger.info(f"Report contains {len(report)} sections: {', '.join(report.keys())}")
                
                # Print some stats from the report
                if 'market_overview' in report:
                    market_overview = report['market_overview']
                    logger.info(f"Market overview: {market_overview.get('summary', 'No summary available')}")
                    
                if 'performance_metrics' in report:
                    performance = report['performance_metrics']
                    top_gainers = performance.get('top_gainers', [])
                    if top_gainers:
                        logger.info(f"Top gainer: {top_gainers[0]}")
            else:
                logger.error("Failed to generate report")
                return False
                
            # Step 9: Format the report for Discord
            logger.info("Formatting market report for Discord")
            formatted_report = await market_reporter.format_market_report(
                overview=report.get('market_overview', {}),
                top_pairs=test_symbols,
                market_regime=report.get('market_regime', 'UNKNOWN'),
                smart_money=report.get('smart_money_index', {}),
                whale_activity=report.get('whale_activity', {})
            )
            
            if formatted_report:
                logger.info(f"Formatted report contains {len(formatted_report.get('embeds', []))} embeds")
                
                # Step 10: Send the report (if webhook URL is configured)
                if alert_manager and alert_manager.discord_webhook_url:
                    logger.info("Sending report to Discord")
                    success = await alert_manager.send_discord_webhook_message(formatted_report)
                    if success:
                        logger.info("Successfully sent report to Discord")
                    else:
                        logger.error("Failed to send report to Discord")
                else:
                    logger.info("Skipping Discord sending (no webhook URL configured)")
                    
            else:
                logger.error("Failed to format report for Discord")
                return False
                
            logger.info("Test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during report generation: {str(e)}", exc_info=True)
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False
        
    finally:
        # Cleanup all components
        logger.info("Cleaning up components")
        
        # Close alert manager if it exists
        if 'alert_manager' in components:
            logger.info("Stopping AlertManager")
            if hasattr(components['alert_manager'], 'stop'):
                components['alert_manager'].stop()
            
        # Close exchange connections
        if 'exchange_manager' in components:
            logger.info("Closing exchange connections")
            await components['exchange_manager'].cleanup()
            
        total_time = time.time() - start_time
        logger.info(f"Test completed in {total_time:.2f} seconds")

async def detailed_test():
    """Run tests with detailed logging of each step"""
    logger.info("="*50)
    logger.info("STARTING MARKET REPORTER TEST WITH LIVE DATA")
    logger.info("="*50)
    
    success = await test_market_reporter_with_live_data()
    
    logger.info("="*50)
    logger.info(f"TEST {'PASSED' if success else 'FAILED'}")
    logger.info("="*50)
    
    return success

if __name__ == "__main__":
    result = asyncio.run(detailed_test())
    sys.exit(0 if result else 1) 
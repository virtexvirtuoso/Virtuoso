import asyncio
import logging
import sys
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

# Import with error handling
try:
    from src.monitoring.market_reporter import MarketReporter
    from src.core.exchanges.bybit import BybitExchange
    from src.monitoring.alert_manager import AlertManager
except ImportError as e:
    logger.critical(f"Failed to import critical component: {str(e)}")
    sys.exit(1)

async def test_market_reporter_simple():
    """A simplified test for MarketReporter that works with Python 3.7."""
    start_time = time.time()
    components = {}
    
    try:
        # Create minimal configuration
        logger.info("Creating minimal configuration")
        config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api.bybit.com',
                    'testnet': False,
                    'websocket': {
                        'mainnet_endpoint': 'wss://stream.bybit.com/v5/public'
                    },
                    'api_credentials': {
                        'api_key': os.environ.get('BYBIT_API_KEY', ''),
                        'api_secret': os.environ.get('BYBIT_API_SECRET', '')
                    },
                    'rate_limits': {
                        'requests_per_second': 10,
                        'requests_per_minute': 500
                    }
                }
            },
            'market_data': {
                'update_interval': 1.0,
                'validation': {
                    'volume': {'min_value': 0},
                    'turnover': {'min_value': 0}
                }
            },
            'monitoring': {
                'alerts': {
                    'discord': {
                        'webhook_url': os.environ.get('DISCORD_WEBHOOK_URL', '')
                    }
                }
            }
        }
        
        # Step 1: Create exchange instance
        logger.info("Initializing BybitExchange")
        exchange = BybitExchange(config, None)
        await exchange.initialize()
        logger.info("Exchange initialized successfully")
        components['exchange'] = exchange
        
        # Step 2: Initialize AlertManager (optional)
        alert_manager = None
        try:
            logger.info("Initializing AlertManager")
            alert_manager = AlertManager(config)
            components['alert_manager'] = alert_manager
            logger.info("AlertManager initialized")
        except Exception as e:
            logger.warning(f"Could not initialize AlertManager: {str(e)}")
            logger.info("Continuing without AlertManager")
        
        # Step 3: Initialize MarketReporter
        logger.info("Initializing MarketReporter")
        market_reporter = MarketReporter(
            exchange=exchange,
            logger=logger,
            alert_manager=alert_manager
        )
        components['market_reporter'] = market_reporter
        
        # Test symbols to use
        test_symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]
        logger.info(f"Testing with symbols: {test_symbols}")
        
        # Step 4: Verify exchange connection with a basic operation
        logger.info("Verifying exchange connection")
        try:
            ticker = await exchange.fetch_ticker(test_symbols[0])
            if ticker:
                logger.info(f"Successfully fetched ticker for {test_symbols[0]}")
                logger.info(f"Current price: {ticker.get('last', 'N/A')}")
            else:
                logger.warning(f"Could not fetch ticker for {test_symbols[0]}")
        except Exception as e:
            logger.error(f"Error testing exchange connection: {str(e)}")
        
        # Step 5: Generate market report
        logger.info("Generating market report")
        generation_start = time.time()
        
        # Force update symbols to our test list
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
            
        # Step 6: Format the report for Discord (optional)
        if alert_manager:
            logger.info("Formatting market report for Discord")
            try:
                formatted_report = await market_reporter.format_market_report(
                    overview=report.get('market_overview', {}),
                    top_pairs=test_symbols,
                    market_regime=report.get('market_regime', 'UNKNOWN'),
                    smart_money=report.get('smart_money_index', {}),
                    whale_activity=report.get('whale_activity', {})
                )
                
                if formatted_report:
                    logger.info(f"Formatted report contains {len(formatted_report.get('embeds', []))} embeds")
                    
                    # Step 7: Send the report (if webhook URL is configured)
                    if alert_manager.discord_webhook_url:
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
            except Exception as e:
                logger.error(f"Error formatting/sending report: {str(e)}")
                logger.info("Continuing with test despite formatting error")
                
        logger.info("Test completed successfully")
        return True
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False
        
    finally:
        # Cleanup all components
        logger.info("Cleaning up components")
        
        # Close alert manager if it exists
        if 'alert_manager' in components:
            logger.info("Stopping AlertManager")
            try:
                if hasattr(components['alert_manager'], 'stop'):
                    components['alert_manager'].stop()
            except Exception as e:
                logger.warning(f"Error stopping AlertManager: {str(e)}")
            
        # Close exchange
        if 'exchange' in components:
            logger.info("Closing exchange connection")
            try:
                await components['exchange'].close()
            except Exception as e:
                logger.warning(f"Error closing exchange: {str(e)}")
            
        total_time = time.time() - start_time
        logger.info(f"Test completed in {total_time:.2f} seconds")

async def run_test():
    """Run the test with proper setup and reporting."""
    logger.info("="*50)
    logger.info("STARTING SIMPLIFIED MARKET REPORTER TEST")
    logger.info("="*50)
    
    success = await test_market_reporter_simple()
    
    logger.info("="*50)
    logger.info(f"TEST {'PASSED' if success else 'FAILED'}")
    logger.info("="*50)
    
    return success

if __name__ == "__main__":
    result = asyncio.run(run_test())
    sys.exit(0 if result else 1) 
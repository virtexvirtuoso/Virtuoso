import sys
import logging
import asyncio
import time
from datetime import datetime
import os
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('market_reporter_live.log')
    ]
)
logger = logging.getLogger(__name__)

# Set higher debug level for specific components
logging.getLogger('src.monitoring.market_reporter').setLevel(logging.DEBUG)
logging.getLogger('src.core.exchanges').setLevel(logging.INFO)

# Import necessary components with proper error handling
try:
    from src.config.manager import ConfigManager
    from src.core.exchanges.manager import ExchangeManager
    from src.monitoring.market_reporter import MarketReporter
    from src.monitoring.alert_manager import AlertManager
except ImportError as e:
    logger.critical(f"Critical import error: {str(e)}")
    logger.critical("Make sure you're running this script from the project root directory")
    sys.exit(1)

async def run_market_reporter_live():
    """Run the MarketReporter with live data from the exchange."""
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
        
        # Step 3: Initialize exchanges
        logger.info("Initializing exchanges")
        if not await exchange_manager.initialize():
            logger.error("Failed to initialize exchange manager")
            return False
        
        # Step 4: Get the primary exchange
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
        
        # Test symbols to use - common trading pairs
        test_symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT", "DOGE/USDT:USDT"]
        logger.info(f"Testing with symbols: {test_symbols}")
        
        # Step 7: Verify exchange connection
        logger.info("Verifying exchange connection")
        try:
            ticker = await primary_exchange.fetch_ticker(test_symbols[0])
            if ticker and ticker.get('last'):
                logger.info(f"Successfully fetched ticker for {test_symbols[0]}")
                logger.info(f"Current price: {ticker.get('last', 'N/A')}")
            else:
                logger.warning(f"Could not fetch ticker for {test_symbols[0]}")
                logger.warning("This may indicate an issue with the exchange connection")
        except Exception as e:
            logger.error(f"Error testing exchange connection: {str(e)}")
            logger.error("Will attempt to continue with report generation anyway")
            
        # Step 8: Generate market report
        logger.info("Generating market report")
        generation_start = time.time()
        
        try:
            # Set the symbols for the market reporter
            market_reporter.symbols = test_symbols
            
            # Generate the report
            report = await market_reporter.generate_market_summary()
            
            if not report:
                logger.error("Failed to generate market report")
                return False
                
            generation_time = time.time() - generation_start
            logger.info(f"Generated market report in {generation_time:.2f} seconds")
            
            # Save the raw report for inspection
            try:
                with open('market_report_raw.json', 'w') as f:
                    json.dump(report, f, indent=2)
                logger.info("Raw report saved to market_report_raw.json")
            except Exception as e:
                logger.warning(f"Could not save raw report: {str(e)}")
            
            # Log report sections
            logger.info(f"Report contains {len(report)} sections")
            for section, data in report.items():
                if isinstance(data, dict):
                    logger.info(f"Section '{section}' contains {len(data)} items")
                elif isinstance(data, list):
                    logger.info(f"Section '{section}' contains {len(data)} entries")
                else:
                    logger.info(f"Section '{section}': {str(data)[:100]}...")
                
            # Step 9: Format the report for Discord
            logger.info("Formatting market report for Discord")
            formatted_report = await market_reporter.format_market_report(
                overview=report.get('market_overview', {}),
                top_pairs=test_symbols,
                market_regime=report.get('market_overview', {}).get('regime', 'UNKNOWN'),
                smart_money=report.get('smart_money_index', {}),
                whale_activity=report.get('whale_activity', {})
            )
            
            if not formatted_report:
                logger.error("Failed to format report for Discord")
                return False
                
            logger.info(f"Formatted report contains {len(formatted_report.get('embeds', []))} embeds")
            
            # Save the formatted report for inspection
            try:
                with open('market_report_formatted.json', 'w') as f:
                    json.dump(formatted_report, f, indent=2)
                logger.info("Formatted report saved to market_report_formatted.json")
            except Exception as e:
                logger.warning(f"Could not save formatted report: {str(e)}")
                
            # Step 10: Send the report (if webhook URL is configured)
            discord_webhook_url = config_manager.get_value('discord.market_webhook_url', None)
            if alert_manager and discord_webhook_url:
                logger.info("Sending report to Discord")
                try:
                    await alert_manager.send_discord_webhook_message(formatted_report)
                    logger.info("Successfully sent report to Discord")
                except Exception as e:
                    logger.error(f"Failed to send report to Discord: {str(e)}")
                    logger.debug("Error details:", exc_info=True)
            else:
                logger.info("Skipping Discord sending (no webhook URL configured)")
                
            logger.info("Live market report generation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during report generation: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            return False
            
    except Exception as e:
        logger.error(f"Runtime error: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        return False
        
    finally:
        # Cleanup all components
        logger.info("Cleaning up components")
        cleanup_errors = []
        
        # Close alert manager if it exists
        if 'alert_manager' in components:
            logger.info("Stopping AlertManager")
            if hasattr(components['alert_manager'], 'stop'):
                try:
                    await components['alert_manager'].stop()
                except Exception as e:
                    cleanup_errors.append(f"AlertManager: {str(e)}")
                    logger.error(f"Error stopping AlertManager: {str(e)}")
            
        # Close exchange connections
        if 'exchange_manager' in components:
            logger.info("Closing exchange connections")
            try:
                await components['exchange_manager'].cleanup()
            except Exception as e:
                cleanup_errors.append(f"ExchangeManager: {str(e)}")
                logger.error(f"Error cleaning up exchange manager: {str(e)}")
            
        if cleanup_errors:
            logger.warning(f"Encountered {len(cleanup_errors)} errors during cleanup")
        
        total_time = time.time() - start_time
        logger.info(f"Script completed in {total_time:.2f} seconds")

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("STARTING MARKET REPORTER WITH LIVE DATA")
    logger.info("="*60)
    
    try:
        result = asyncio.run(run_market_reporter_live())
        
        logger.info("="*60)
        logger.info(f"MARKET REPORTER {'SUCCESSFUL' if result else 'FAILED'}")
        logger.info("="*60)
        
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}")
        logger.critical("Stack trace:", exc_info=True)
        sys.exit(1) 
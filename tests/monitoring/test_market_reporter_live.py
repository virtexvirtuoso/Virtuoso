import sys
import logging
import asyncio
import time
from datetime import datetime
from src.config.manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager
from src.monitoring.market_reporter import MarketReporter
from src.monitoring.alert_manager import AlertManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set higher debug level for market reporter
logging.getLogger('src.monitoring.market_reporter').setLevel(logging.DEBUG)

async def test_market_reporter_with_live_data():
    try:
        # Initialize config
        logger.info("Initializing ConfigManager")
        config_manager = ConfigManager()
        
        # Initialize exchange
        logger.info("Initializing ExchangeManager")
        exchange_manager = ExchangeManager(config_manager)
        logger.info("Initializing exchanges")
        exchange_manager.initialize_exchanges()
        
        # Get exchange (Bybit in this case)
        exchange_name = "bybit"
        exchange = exchange_manager.get_exchange(exchange_name)
        if not exchange:
            logger.error(f"No exchange found with name: {exchange_name}")
            return False
        logger.info(f"Using {exchange_name} as primary exchange")
        
        # Initialize AlertManager
        logger.info("Initializing AlertManager")
        alert_manager = AlertManager(config_manager)
        alert_manager.start()
        
        # Initialize market reporter with the real exchange
        logger.info("Initializing MarketReporter with live exchange")
        market_reporter = MarketReporter(exchange=exchange, alert_manager=alert_manager)
        
        # Define known trading pairs to test with
        test_pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT"]
        logger.info(f"Testing with pairs: {test_pairs}")
        
        # Generate market report with live data
        logger.info("Generating market report with live data")
        start_time = time.time()
        
        # This should run a series of calculations in parallel
        logger.info("Running market calculations in parallel")
        report = await market_reporter.generate_market_summary()
        
        # Format the report for Discord
        logger.info("Formatting market report")
        formatted_report = await market_reporter.format_market_report(
            overview=report.get('market_overview', {}),
            top_pairs=test_pairs,
            market_regime=report.get('market_regime', 'UNKNOWN'),
            smart_money=report.get('smart_money_index', {}),
            whale_activity=report.get('whale_activity', {})
        )
        
        end_time = time.time()
        generation_time = end_time - start_time
        logger.info(f"Generated market report in {generation_time:.2f} seconds")
        
        # Log information about the generated report
        if formatted_report:
            logger.info(f"Market report structure: {len(formatted_report.get('embeds', []))} embeds")
            for idx, embed in enumerate(formatted_report.get('embeds', [])):
                logger.info(f"Embed {idx+1}: {embed.get('title')}")
        
        # Send the report to Discord
        logger.info("Sending market report to Discord")
        if hasattr(alert_manager, 'send_discord_webhook_message'):
            logger.info(f"Sending report with {len(formatted_report.get('embeds', []))} embeds to Discord")
            success = await alert_manager.send_discord_webhook_message(formatted_report)
            if success:
                logger.info("Market report sent to Discord successfully")
            else:
                logger.error("Failed to send market report to Discord")
        else:
            logger.error("AlertManager does not have send_discord_webhook_message method")
            
        logger.info("Test passed: Market reporter generated report with live data")
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False
    finally:
        # Clean up
        if alert_manager:
            logger.info("Stopping AlertManager")
            alert_manager.stop()
        
        if exchange_manager:
            logger.info("Closing exchange connections")
            await exchange_manager.close_exchanges()

if __name__ == "__main__":
    result = asyncio.run(test_market_reporter_with_live_data())
    sys.exit(0 if result else 1) 
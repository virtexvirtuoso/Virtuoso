import asyncio
import logging

from src.monitoring.market_reporter import MarketReporter
from src.monitoring.alert_manager import AlertManager

async def test():
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("TestMarketReporter")
    
    # Create a simple config
    config = {}
    
    # Initialize the AlertManager and MarketReporter
    logger.info("Initializing AlertManager and MarketReporter...")
    alert_manager = AlertManager(config)
    market_reporter = MarketReporter(alert_manager=alert_manager, logger=logger)
    
    # Test the send_discord_webhook_message method
    webhook_message = {"content": "Test webhook message"}
    
    logger.info("Testing alert_manager.send_discord_webhook_message...")
    try:
        if hasattr(alert_manager, 'send_discord_webhook_message'):
            logger.info("Method exists!")
            await alert_manager.send_discord_webhook_message(webhook_message)
            logger.info("Method called successfully")
        else:
            logger.warning("Method does not exist!")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    
    # Now test the generate_market_summary method with fallback
    logger.info("Testing MarketReporter.generate_market_summary with fallback mechanism...")
    try:
        # Intentionally set top_symbols_manager to None to test fallback
        result = await market_reporter.generate_market_summary()
        logger.info(f"Market summary generated: {result is not None}")
    except Exception as e:
        logger.error(f"Error generating market summary: {str(e)}")
    
    logger.info("Done testing")

if __name__ == "__main__":
    asyncio.run(test()) 
import asyncio
import logging
from src.monitoring.market_reporter import MarketReporter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_market_reporter():
    try:
        # Initialize reporter
        logger.info("Initializing MarketReporter")
        reporter = MarketReporter()
        
        # Generate a market summary
        logger.info("Generating market summary")
        report = await reporter.generate_market_summary()
        
        # Check if report was generated
        if report:
            logger.info("Market report generated successfully")
            logger.info(f"Report sections: {', '.join(report.keys())}")
        else:
            logger.error("Failed to generate market report")
            
    except Exception as e:
        logger.error(f"Error testing market reporter: {str(e)}")
        logger.exception("Exception details:")

if __name__ == "__main__":
    asyncio.run(test_market_reporter()) 
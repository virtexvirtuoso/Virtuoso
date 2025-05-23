import sys
import os
import asyncio
import logging
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import the MarketReporter
try:
    from src.monitoring.market_reporter import MarketReporter
    logger.info("Successfully imported MarketReporter")
except ImportError as e:
    logger.error(f"Error importing MarketReporter: {str(e)}")
    raise

async def test_market_reporter():
    """Test the market reporter with live data."""
    try:
        logger.info("Initializing MarketReporter")
        reporter = MarketReporter(logger=logger)
        
        logger.info("Generating market summary")
        report = await reporter.generate_market_summary()
        
        if not report:
            logger.error("Failed to generate market report")
            return False
        
        # Check if all required sections are present
        required_sections = [
            'market_overview', 
            'futures_premium', 
            'smart_money_index',
            'whale_activity',
            'performance_metrics'
        ]
        present_sections = {section: section in report and report[section] for section in required_sections}
        
        # Calculate quality score based on present sections
        quality_score = 100 if all(present_sections.values()) else 100 - (len(required_sections) - sum(present_sections.values())) * 20
        
        logger.info(f"Market Report Quality Score: {quality_score}/100")
        logger.info("Section Coverage:")
        for section, present in present_sections.items():
            logger.info(f"- {section}: {'✓' if present else '✗'}")
        
        # Print some sample data from the report
        if 'market_overview' in report:
            market_overview = report['market_overview']
            logger.info(f"Market Regime: {market_overview.get('regime', 'Unknown')}")
            logger.info(f"Trend Strength: {market_overview.get('trend_strength', '0%')}")
        
        logger.info("Market report test completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error testing market reporter: {str(e)}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_market_reporter())
        sys.exit(0 if result else 1)
    except Exception as e:
        logger.error(f"Error running market reporter test: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1) 
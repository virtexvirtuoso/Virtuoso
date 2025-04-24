import asyncio
import logging
import os
import json
import sys
from datetime import datetime

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Set API keys from environment or directly 
BYBIT_API_KEY = os.environ.get('BYBIT_API_KEY', '')
BYBIT_API_SECRET = os.environ.get('BYBIT_API_SECRET', '')

if not BYBIT_API_KEY or not BYBIT_API_SECRET:
    logger.warning("API keys not set in environment variables. Demo mode will be limited.")

async def test_basic_market_reporter():
    """Test basic MarketReporter functionality without depending on TA-Lib."""
    logger.info("Starting basic market reporter test")
    
    # Import the minimum required components
    try:
        # Direct import of MarketReporter to avoid dependency tree issues
        from src.monitoring.market_reporter import MarketReporter
        logger.info("Successfully imported MarketReporter")
    except ImportError as e:
        logger.error(f"Failed to import MarketReporter: {e}")
        return False
    
    try:
        # Create a minimal instance of MarketReporter without exchange
        reporter = MarketReporter(logger=logger)
        logger.info("Successfully created MarketReporter instance")
        
        # Test a basic method that doesn't require exchange connection
        logger.info("Testing _format_number method")
        formatted = reporter._format_number(1234567.89)
        logger.info(f"Result: {formatted}")
        
        # Output success message
        logger.info("Basic MarketReporter test completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error in basic test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(test_basic_market_reporter())
    sys.exit(0 if success else 1) 
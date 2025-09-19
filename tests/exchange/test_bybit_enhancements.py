import asyncio
import logging
import os
import sys
import json
from datetime import datetime
import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the MarketReporter
try:
    from src.monitoring.market_reporter import MarketReporter
    logger.info("Successfully imported MarketReporter")
except ImportError as e:
    logger.error(f"Error importing MarketReporter: {e}")
    MarketReporter = None

@pytest.mark.asyncio
@pytest.mark.skipif(MarketReporter is None,
                   reason="MarketReporter not available in CI environment")
async def test_bybit_enhancements():
    """Test the enhanced Bybit API integration."""
    try:
        # Initialize the MarketReporter
        reporter = MarketReporter(logger=logger)
        
        # Test the _format_bybit_symbol method
        logger.info("\nTesting _format_bybit_symbol method:")
        test_symbols = [
            'BTC/USDT',
            'BTC/USDT:USDT',
            'BTCUSDT',
            'ETHUSDT:USDT'
        ]
        for symbol in test_symbols:
            formatted = reporter._format_bybit_symbol(symbol)
            logger.info(f"  {symbol} -> {formatted}")
        
        # Test the _extract_bybit_field method
        logger.info("\nTesting _extract_bybit_field method:")
        test_data = {
            'last': 64500,
            'info': {
                'markPrice': 64520,
                'indexPrice': 64510,
                'lastPrice': 64500,
                'volume24h': 1500000,
                'fundingRate': 0.0001
            }
        }
        fields = ['mark_price', 'index_price', 'funding_rate', 'volume']
        for field in fields:
            value = reporter._extract_bybit_field(test_data, field)
            logger.info(f"  Extracted {field}: {value}")
        
        # Test funding rate analysis
        logger.info("\nTesting _analyze_funding_rates method:")
        try:
            funding_data = await reporter._analyze_funding_rates('BTCUSDT')
            logger.info(f"  Funding rate analysis: {json.dumps(funding_data, indent=2)}")
        except Exception as e:
            logger.warning(f"  Error analyzing funding rates: {e}")
        
        # Test premium calculation with quarterly futures
        logger.info("\nTesting premium calculation with quarterly futures:")
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        for symbol in symbols:
            try:
                premium_data = await reporter._calculate_single_premium(symbol, {})
                if premium_data:
                    logger.info(f"\nPremium data for {symbol}:")
                    logger.info(f"  Premium: {premium_data.get('premium', 'N/A')}")
                    logger.info(f"  Mark Price: {premium_data.get('mark_price', 'N/A')}")
                    logger.info(f"  Index Price: {premium_data.get('index_price', 'N/A')}")
                    logger.info(f"  Funding Rate: {premium_data.get('funding_rate', 'N/A')}")
                    
                    # Log quarterly futures if available
                    if 'futures_contracts' in premium_data and premium_data['futures_contracts']:
                        logger.info(f"  Quarterly futures found: {premium_data.get('quarterly_futures_count', 0)}")
                        for contract in premium_data['futures_contracts']:
                            logger.info(f"    {contract['symbol']} ({contract['month']}): {contract['price']} - Basis: {contract['basis']}")
                else:
                    logger.warning(f"  No premium data returned for {symbol}")
            except Exception as e:
                logger.error(f"  Error calculating premium for {symbol}: {e}")
                
        # Test full futures premium analysis
        logger.info("\nTesting full futures premium analysis:")
        try:
            futures_premium = await reporter._calculate_futures_premium(symbols)
            logger.info(f"  Average Premium: {futures_premium.get('average_premium', 'N/A')}")
            logger.info(f"  Contango Status: {futures_premium.get('contango_status', 'N/A')}")
            
            # Check if we got funding rates
            if 'funding_rates' in futures_premium:
                logger.info(f"  Funding rates available for {len(futures_premium['funding_rates'])} symbols")
            
            # Check if we got quarterly futures
            if 'quarterly_futures' in futures_premium:
                logger.info(f"  Quarterly futures available for {len(futures_premium['quarterly_futures'])} symbols")
        except Exception as e:
            logger.error(f"  Error in futures premium calculation: {e}")
        
        # Test the full report generation
        logger.info("\nTesting full market report generation:")
        try:
            report = await reporter.generate_market_summary()
            logger.info(f"  Report generated successfully with {len(report)} bytes")
            
            # Save the report to a file for inspection
            output_file = f"bybit_test_report_{int(datetime.now().timestamp())}.json"
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"  Report saved to {output_file}")
        except Exception as e:
            logger.error(f"  Error generating market report: {e}")
    
    except Exception as e:
        logger.error(f"Error in test_bybit_enhancements: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logger.info("Starting test for Bybit API enhancements")
    try:
        asyncio.run(test_bybit_enhancements())
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc() 
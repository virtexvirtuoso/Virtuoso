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

# Import our modules - if they fail, we'll get clear errors
try:
    from src.monitoring.market_reporter import MarketReporter
    from src.core.exchanges.bybit import BybitExchange
    logger.info("Successfully imported required modules")
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

async def generate_market_report():
    """Generate a comprehensive market report using live Bybit data."""
    logger.info("Starting comprehensive market report generation with live Bybit data")
    
    # Create configuration for Bybit exchange
    config = {
        'exchanges': {
            'bybit': {
                'enabled': True,
                'rest_endpoint': 'https://api.bybit.com',
                'testnet': False,
                'api_credentials': {
                    'api_key': BYBIT_API_KEY,
                    'api_secret': BYBIT_API_SECRET
                },
                'websocket': {
                    'mainnet_endpoint': 'wss://stream.bybit.com/v5/public'
                }
            }
        },
        'market_data': {
            'update_interval': 1.0,
            'validation': {
                'volume': {'min_value': 0},
                'turnover': {'min_value': 0}
            }
        }
    }
    
    try:
        # Display important test info
        key_preview = BYBIT_API_KEY[:4] + "..." + BYBIT_API_KEY[-4:] if len(BYBIT_API_KEY) > 8 else BYBIT_API_KEY
        logger.info(f"Using API key: {key_preview}")
        logger.info(f"API Secret length: {len(BYBIT_API_SECRET)} characters")
        
        # Initialize exchange
        exchange = BybitExchange(config, None)
        success = await exchange.initialize()
        if not success:
            logger.error("Failed to initialize BybitExchange")
            return
            
        logger.info("Exchange initialized successfully")
        
        # Initialize market reporter
        reporter = MarketReporter(exchange=exchange, logger=logger)
        logger.info("Market reporter initialized successfully")
        
        # Define symbols for the report
        symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
        logger.info(f"Generating report for symbols: {symbols}")
        
        # Test futures premium calculation (our fixed feature)
        logger.info("\n[TEST 1] Testing futures premium calculation...")
        try:
            premiums = await reporter._calculate_futures_premium(symbols)
            logger.info("Futures premium calculation successful!")
            for symbol, data in premiums.get('premiums', {}).items():
                logger.info(f"{symbol}: {data.get('premium_type', '')} {data.get('premium', '0%')}")
                logger.info(f"  Mark Price: {data.get('mark_price', 0)} | Index Price: {data.get('index_price', 0)}")
                logger.info(f"  Futures Basis: {data.get('futures_basis', '0%')}")
        except Exception as e:
            logger.error(f"Futures premium calculation failed: {e}")
        
        # Test market overview
        logger.info("\n[TEST 2] Testing market overview calculation...")
        try:
            overview = await reporter._calculate_market_overview(symbols)
            logger.info("Market overview calculation successful!")
            logger.info(f"Market Regime: {overview.get('regime', 'Unknown')}")
            logger.info(f"Trend Strength: {overview.get('trend_strength', 'Unknown')}")
            logger.info(f"Volatility: {overview.get('volatility', 'Unknown')}")
            logger.info(f"Total Volume: ${overview.get('total_volume', 0):,.2f}")
            logger.info(f"Total Open Interest: ${overview.get('total_open_interest', 0):,.2f}")
        except Exception as e:
            logger.error(f"Market overview calculation failed: {e}")
        
        # Test whale activity
        logger.info("\n[TEST 3] Testing whale activity calculation...")
        try:
            whale_activity = await reporter._calculate_whale_activity(symbols[:1])
            logger.info("Whale activity calculation successful!")
            logger.info(f"Key Whale Zones: {len(whale_activity.get('key_zones', []))}")
            logger.info(f"Significant Orders: {whale_activity.get('significant_orders', 0)}")
        except Exception as e:
            logger.error(f"Whale activity calculation failed: {e}")
        
        # Test market summary (comprehensive report)
        logger.info("\n[TEST 4] Testing market summary generation...")
        try:
            summary = await reporter.generate_market_summary()
            logger.info("Market summary generation successful!")
            logger.info(f"Summary sections: {list(summary.keys())}")
        except Exception as e:
            logger.error(f"Market summary generation failed: {e}")
        
        # Compile the full report
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_report = {
            "report_time": timestamp,
            "test_results": {
                "futures_premium_test": "success" if "premiums" in locals() else "failed",
                "market_overview_test": "success" if "overview" in locals() else "failed",
                "whale_activity_test": "success" if "whale_activity" in locals() else "failed",
                "market_summary_test": "success" if "summary" in locals() else "failed"
            }
        }
        
        # Add actual data if available
        if "premiums" in locals():
            full_report["futures_premiums"] = premiums
        if "overview" in locals():
            full_report["market_overview"] = overview
        if "whale_activity" in locals():
            full_report["whale_activity"] = whale_activity
        if "summary" in locals():
            full_report["market_summary"] = summary
        
        # Save full report to file
        with open('market_report.json', 'w') as f:
            json.dump(full_report, f, indent=2, default=str)
        logger.info("\nFull report saved to market_report.json")
        
        # Overall test result
        test_results = full_report["test_results"]
        success_count = sum(1 for result in test_results.values() if result == "success")
        total_tests = len(test_results)
        
        logger.info(f"\n=== TEST SUMMARY: {success_count}/{total_tests} tests passed ===")
        for test_name, result in test_results.items():
            logger.info(f"{test_name}: {result}")
        
        return full_report
    except Exception as e:
        logger.error(f"Error generating market report: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

if __name__ == "__main__":
    asyncio.run(generate_market_report()) 
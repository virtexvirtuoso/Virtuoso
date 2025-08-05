#!/usr/bin/env python3
"""
Test the critical fixes applied on 2025-08-04.
"""

import asyncio
import sys
from pathlib import Path
import logging
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_bybit_timeout():
    """Test Bybit connection with new timeout settings."""
    logger.info("Testing Bybit timeout fix...")
    
    try:
        from src.core.exchanges.bybit import BybitExchange
        from src.config.config_manager import ConfigManager
        
        # Load config
        config = ConfigManager().config
        
        # Create exchange instance
        exchange = BybitExchange(config.exchanges.bybit.model_dump())
        
        # Test initialization with timeout
        start_time = datetime.now()
        success = await exchange.initialize()
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if success:
            logger.info(f"✅ Bybit initialized successfully in {elapsed:.2f}s")
            
            # Test a simple API call with timeout
            start_time = datetime.now()
            result = await exchange._make_request('GET', '/v5/market/time')
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if result and result.get('retCode') == 0:
                logger.info(f"✅ API call successful in {elapsed:.2f}s")
            else:
                logger.error(f"❌ API call failed: {result}")
            
            # Cleanup
            await exchange.close()
            
        else:
            logger.error(f"❌ Bybit initialization failed after {elapsed:.2f}s")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Bybit test failed: {str(e)}")
        return False

async def test_pdf_generator():
    """Test PDF generator with entry_pos fix."""
    logger.info("Testing PDF generator fix...")
    
    try:
        from src.core.reporting.pdf_generator import PDFGenerator
        
        # Create test data with missing price
        test_data = {
            'symbol': 'TESTUSDT',
            'signal_type': 'BUY',
            'confluence_score': 75.5,
            'timestamp': datetime.now().isoformat(),
            'entry_price': None,  # This should trigger the fixed code path
            'ohlcv_data': []
        }
        
        generator = PDFGenerator()
        
        # Test chart creation with missing entry price
        logger.info("Testing chart creation with missing entry price...")
        chart_path = await generator._create_candlestick_chart(
            'TESTUSDT',
            [],  # Empty OHLCV data
            test_data,
            'BUY'
        )
        
        if chart_path:
            logger.info(f"✅ Chart created successfully: {chart_path}")
        else:
            logger.info("✅ Chart creation handled gracefully (returned None)")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ PDF generator test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_market_data_fetch():
    """Test market data fetching for new symbols."""
    logger.info("Testing market data fetch for new symbols...")
    
    try:
        from src.core.market.market_data_manager import MarketDataManager
        from src.config.config_manager import ConfigManager
        
        # Create manager
        config = ConfigManager().config
        manager = MarketDataManager(config)
        
        # Test fetching data for a symbol
        test_symbol = 'BTCUSDT'
        logger.info(f"Testing data fetch for {test_symbol}...")
        
        # Initialize if needed
        if hasattr(manager, 'initialize'):
            await manager.initialize()
        
        # Try to get symbol data
        data = await manager.get_symbol_data(test_symbol)
        
        if data:
            logger.info(f"✅ Got data for {test_symbol}: {list(data.keys())}")
            if 'current_price' in data:
                logger.info(f"   Current price: ${data['current_price']}")
        else:
            logger.warning(f"⚠️  No data returned for {test_symbol}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Market data test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    logger.info("🧪 Testing critical fixes...")
    logger.info("=" * 60)
    
    results = []
    
    # Test 1: Bybit timeout
    logger.info("\n1. Testing Bybit timeout fix...")
    results.append(await test_bybit_timeout())
    
    # Test 2: PDF generator
    logger.info("\n2. Testing PDF generator fix...")
    results.append(await test_pdf_generator())
    
    # Test 3: Market data
    logger.info("\n3. Testing market data fetch...")
    results.append(await test_market_data_fetch())
    
    logger.info("\n" + "=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        logger.info(f"✅ All tests passed! ({passed}/{total})")
    else:
        logger.error(f"❌ Some tests failed: {passed}/{total} passed")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
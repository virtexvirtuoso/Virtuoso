#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_specific_symbols():
    """Test specific quarterly futures symbols that might work with Bybit's API."""
    
    # Specific symbols to test, focusing on BTC
    test_symbols = [
        # Format: (symbol, category)
        ("BTCUSDT-29DEC25", "linear"),        # Original hyphenated format
        ("BTCUSDT1229", "linear"),            # MMDD format
        ("BTCUSDTZ25", "linear"),             # Month code format (linear)
        ("BTCUSDZ25", "inverse"),             # Month code format (inverse)
        # Alternative formats for December contract
        ("BTC-29DEC25", "linear"),            # No USDT
        ("BTCUSD-29DEC25", "linear"),         # USD instead of USDT
        # Other months for BTC
        ("BTCUSDT-27SEP25", "linear"),        # September contract
        ("BTCUSDT-31MAR25", "linear"),        # March contract
        ("BTCUSDT-28JUN25", "linear"),        # June contract
        # Testing without dashes or with different separations
        ("BTCUSDT29DEC25", "linear"),         # No hyphen
        ("BTCUSDT_29DEC25", "linear"),        # Underscore
        # Alternative date formats
        ("BTCUSDTDEC25", "linear"),           # Just month and year
        ("BTCUSDTQ425", "linear"),            # Q4 quarter notation
    ]
    
    # URL for tickers endpoint
    url = "https://api.bybit.com/v5/market/tickers"
    
    async with aiohttp.ClientSession() as session:
        for symbol, category in test_symbols:
            try:
                params = {'category': category, 'symbol': symbol}
                logger.info(f"Trying {symbol} ({category})...")
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Response for {symbol}: {result}")
                        
                        if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):
                            data = result['result']['list'][0]
                            price = float(data.get('lastPrice', 0))
                            logger.info(f"✅ SUCCESS for {symbol}: Price = {price}")
                            logger.info(f"Symbol details: {data}")
                        else:
                            logger.info(f"❌ ERROR for {symbol}: {result.get('retMsg', 'Unknown error')}")
                    else:
                        logger.info(f"❌ HTTP Error for {symbol}: {response.status}")
            except Exception as e:
                logger.error(f"Exception for {symbol}: {e}")

    # Also try getting all futures for BTC to see what's available
    logger.info("\n=== LOOKING UP AVAILABLE BTC FUTURES ===")
    try:
        # Try both categories
        categories = ["linear", "inverse"]
        
        for category in categories:
            params = {'category': category}
            async with session.get("https://api.bybit.com/v5/market/instruments-info", params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):
                        futures = [item for item in result['result']['list'] 
                                   if item.get('symbol', '').startswith('BTC') and 
                                   'contractType' in item and item['contractType'] != 'LinearPerpetual']
                        
                        logger.info(f"Found {len(futures)} BTC futures in {category} category:")
                        for future in futures:
                            logger.info(f"Symbol: {future.get('symbol')}, Type: {future.get('contractType')}")
                    else:
                        logger.info(f"No BTC futures found in {category} category: {result.get('retMsg')}")
                else:
                    logger.info(f"HTTP Error getting {category} instruments: {response.status}")
    except Exception as e:
        logger.error(f"Exception getting available futures: {e}")

async def main():
    await test_specific_symbols()

if __name__ == "__main__":
    asyncio.run(main()) 
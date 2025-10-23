#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_bybit_api():
    """Test the Bybit API with the new prioritized formats."""
    
    # Test BTC with the fixed formats in priority order
    url = "https://api.bybit.com/v5/market/tickers"
    
    # Format generators for different patterns
    def get_last_friday(year, month):
        if month == 12:
            last_day = datetime(year, 12, 31)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        offset = (4 - last_day.weekday()) % 7  # Friday is weekday 4
        last_friday = last_day - timedelta(days=offset) if offset != 0 else last_day
        return last_friday
    
    def format_mmdd(base, year, month):
        """MMDD format: BTCUSDT0627"""
        last_friday = get_last_friday(year, month)
        return f"{base}USDT{last_friday.month:02d}{last_friday.day:02d}"
    
    def format_inverse(base, year, month):
        """Month code format for inverse futures: BTCUSDM25"""
        month_codes = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
        return f"{base}USD{month_codes[month]}{year % 100}"
    
    def format_standard(base, year, month):
        """Standard hyphenated format: BTCUSDT-27JUN25"""
        last_friday = get_last_friday(year, month)
        day = last_friday.day
        month_abbr = last_friday.strftime("%b").upper()
        return f"{base}USDT-{day}{month_abbr}{year % 100}"
    
    def format_linear_code(base, year, month):
        """Month code format for linear futures: BTCUSDTM25"""
        month_codes = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
        return f"{base}USDT{month_codes[month]}{year % 100}"
    
    # Current year and month
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Test cases
    test_cases = [
        # BTC with fixed formats
        ("BTC", 6, "MMDD", format_mmdd("BTC", current_year, 6), "linear"),
        ("BTC", 6, "Inverse", format_inverse("BTC", current_year, 6), "inverse"),
        ("BTC", 6, "Standard", format_standard("BTC", current_year, 6), "linear"),
        ("BTC", 6, "Linear Code", format_linear_code("BTC", current_year, 6), "linear"),
        
        # ETH with fixed formats
        ("ETH", 6, "MMDD", format_mmdd("ETH", current_year, 6), "linear"),
        ("ETH", 6, "Inverse", format_inverse("ETH", current_year, 6), "inverse"),
        ("ETH", 6, "Standard", format_standard("ETH", current_year, 6), "linear"),
        ("ETH", 6, "Linear Code", format_linear_code("ETH", current_year, 6), "linear"),
        
        # SOL with fixed formats
        ("SOL", 6, "MMDD", format_mmdd("SOL", current_year, 6), "linear"),
        ("SOL", 6, "Inverse", format_inverse("SOL", current_year, 6), "inverse"),
        ("SOL", 6, "Standard", format_standard("SOL", current_year, 6), "linear"),
        ("SOL", 6, "Linear Code", format_linear_code("SOL", current_year, 6), "linear"),
        
        # Try exact dates from instrument list
        ("BTC", 6, "Exact", "BTCUSDT-27JUN25", "linear"),
        ("ETH", 6, "Exact", "ETHUSDT-27JUN25", "linear"),
        ("SOL", 6, "Exact", "SOLUSDT-27JUN25", "linear"),
        
        # Try explicit BTC contract ID from Bybit
        ("BTC", 0, "Explicit", "BTC-27JUN25", "linear"),
        ("ETH", 0, "Explicit", "ETH-27JUN25", "linear"),
    ]
    
    async with aiohttp.ClientSession() as session:
        for asset, month, format_type, symbol, category in test_cases:
            try:
                params = {'category': category, 'symbol': symbol}
                logger.info(f"Testing {asset} {format_type} format: {symbol} ({category})...")
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Response: {result}")
                        
                        if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):
                            data = result['result']['list'][0]
                            price = float(data.get('lastPrice', 0))
                            logger.info(f"✅ SUCCESS for {symbol}: Price = {price}")
                        else:
                            logger.info(f"❌ ERROR for {symbol}: {result.get('retMsg', 'Unknown error')}")
                    else:
                        logger.info(f"❌ HTTP Error for {symbol}: {response.status}")
            except Exception as e:
                logger.error(f"Exception for {symbol}: {e}")
    
    # Now test fetching all instruments to see the patterns available
    logger.info("\n=== CHECKING AVAILABLE QUARTERLY FUTURES IN BYBIT ===")
    
    try:
        # Fetch instruments info for both categories
        for category in ["linear", "inverse"]:
            url = "https://api.bybit.com/v5/market/instruments-info"
            params = {'category': category}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):
                        instruments = result['result']['list']
                        
                        # Filter for futures contracts
                        futures = [i for i in instruments if i.get('contractType') != 'LinearPerpetual' and i.get('contractType') != 'InversePerpetual']
                        
                        logger.info(f"\nFound {len(futures)} {category} futures contracts")
                        
                        # Print details for selected symbols
                        for symbol in ["BTC", "ETH", "SOL", "XRP", "AVAX"]:
                            symbol_futures = [f for f in futures if f.get('symbol', '').startswith(symbol)]
                            
                            if symbol_futures:
                                logger.info(f"\n{symbol} futures in {category} category:")
                                for contract in symbol_futures:
                                    symbol = contract.get('symbol')
                                    status = contract.get('status')
                                    logger.info(f"Symbol: {symbol}, Status: {status}")
                            else:
                                logger.info(f"No {symbol} futures found in {category} category")
                    else:
                        logger.error(f"Error fetching instruments: {result.get('retMsg')}")
                else:
                    logger.error(f"HTTP Error: {response.status}")
    except Exception as e:
        logger.error(f"Exception checking instruments: {e}")

async def main():
    await test_bybit_api()

if __name__ == "__main__":
    asyncio.run(main()) 
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

async def test_quarterly_futures_with_priority():
    """Test different quarterly futures format with better priority ordering."""
    
    # Base assets to test
    base_assets = ['BTC', 'ETH', 'SOL', 'XRP', 'AVAX']
    
    # Define format generators
    def get_last_friday(year, month):
        if month == 12:
            last_day = datetime(year, 12, 31)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        offset = (4 - last_day.weekday()) % 7  # Friday is weekday 4
        last_friday = last_day - timedelta(days=offset) if offset != 0 else last_day
        return last_friday
    
    # Format generators for different patterns
    def format_mmdd(base, year, month):
        """MMDD format: BTCUSDT0627"""
        last_friday = get_last_friday(year, month)
        return f"{base}USDT{last_friday.month:02d}{last_friday.day:02d}"
    
    def format_inverse(base, year, month):
        """Month code format for inverse futures: BTCUSDM25"""
        month_codes = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
        return f"{base}USD{month_codes[month]}{year % 100}"
    
    def format_linear_code(base, year, month):
        """Month code format for linear futures: BTCUSDTM25"""
        month_codes = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
        return f"{base}USDT{month_codes[month]}{year % 100}"
    
    def format_standard(base, year, month):
        """Standard hyphenated format: BTCUSDT-27JUN25"""
        last_friday = get_last_friday(year, month)
        day = last_friday.day
        month_abbr = last_friday.strftime("%b").upper()
        return f"{base}USDT-{day}{month_abbr}{year % 100}"
    
    def format_base_only(base, year, month):
        """Base only format: BTC-27JUN25"""
        last_friday = get_last_friday(year, month)
        day = last_friday.day
        month_abbr = last_friday.strftime("%b").upper()
        return f"{base}-{day}{month_abbr}{year % 100}"
    
    # Current year and month
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Test each asset with the new priority order
    url = "https://api.bybit.com/v5/market/tickers"
    
    results = {}
    
    async with aiohttp.ClientSession() as session:
        for base_asset in base_assets:
            logger.info(f"\n=== Testing {base_asset} with new priority ===")
            
            # We'll try June, September, and December contracts
            for month in [6, 9, 12]:
                if month < current_month and month != 12:
                    continue  # Skip past contracts except December
                
                # Order of formats to try (in priority order)
                formats_to_try = [
                    (format_mmdd(base_asset, current_year, month), "linear", "MMDD"),
                    (format_inverse(base_asset, current_year, month), "inverse", "Inverse"),
                    (format_standard(base_asset, current_year, month), "linear", "Standard"),
                    (format_linear_code(base_asset, current_year, month), "linear", "Linear Code"),
                    (format_base_only(base_asset, current_year, month), "linear", "Base Only")
                ]
                
                # Try each format in order
                found_working_format = False
                
                for symbol, category, format_type in formats_to_try:
                    if found_working_format:
                        break
                        
                    try:
                        params = {'category': category, 'symbol': symbol}
                        logger.info(f"Trying {format_type} format: {symbol} ({category})...")
                        
                        async with session.get(url, params=params) as response:
                            if response.status == 200:
                                result = await response.json()
                                
                                if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):
                                    price = float(result['result']['list'][0].get('lastPrice', 0))
                                    logger.info(f"✅ SUCCESS for {symbol}: Price = {price}")
                                    
                                    if base_asset not in results:
                                        results[base_asset] = []
                                    
                                    results[base_asset].append({
                                        'symbol': symbol,
                                        'format': format_type,
                                        'category': category,
                                        'price': price,
                                        'month': month
                                    })
                                    
                                    found_working_format = True
                                    break
                                else:
                                    logger.info(f"❌ ERROR for {symbol}: {result.get('retMsg', 'Unknown error')}")
                            else:
                                logger.info(f"❌ HTTP Error for {symbol}: {response.status}")
                    except Exception as e:
                        logger.error(f"Exception for {symbol}: {e}")
    
    # Summary of best formats for each asset
    logger.info("\n=== RECOMMENDED FORMAT BY ASSET ===")
    for asset, contracts in results.items():
        if contracts:
            # Group by format type
            formats = {}
            for contract in contracts:
                format_type = contract['format']
                if format_type not in formats:
                    formats[format_type] = 0
                formats[format_type] += 1
            
            # Find most common format
            best_format = max(formats.items(), key=lambda x: x[1])[0]
            
            logger.info(f"{asset}: Use {best_format} format")
            logger.info(f"  Working symbols: {', '.join([c['symbol'] for c in contracts])}")
        else:
            logger.info(f"{asset}: No working format found")
    
    # Print sample code for market_reporter.py fix
    logger.info("\n=== RECOMMENDED FIX FOR MARKET_REPORTER.PY ===")
    logger.info("""
# Modify the quarterly_symbols list to prioritize formats in this order:
quarterly_symbols = []

# Try formats in priority order for better success rates:

# 1. First try MMDD format without hyphen (e.g., BTCUSDT0627)
quarterly_symbols.append(format_quarterly_symbol_mmdd(base_asset_clean, year, month))

# 2. Then try inverse format for BTC/ETH (e.g., BTCUSDM25)
quarterly_symbols.append((format_quarterly_symbol_code(base_asset_clean, year, month, inverse=True), "inverse"))

# 3. Finally try old format with hyphen as last resort (e.g., BTCUSDT-27JUN25)
quarterly_symbols.append(format_quarterly_symbol_standard(base_asset_clean, year, month))

# 4. Try linear month code format (e.g., BTCUSDTM25)
quarterly_symbols.append(format_quarterly_symbol_code(base_asset_clean, year, month))

# This improves support across all assets:
# - BTC/ETH best with inverse month code format (BTCUSDM25)
# - Other assets may work with MMDD or hyphenated format
# - Trying multiple formats improves reliability
    """)

async def main():
    await test_quarterly_futures_with_priority()

if __name__ == "__main__":
    asyncio.run(main()) 
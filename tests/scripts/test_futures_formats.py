#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import asyncio
import aiohttp
import logging
import sys
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_quarterly_futures_formats():
    """Test different quarterly futures format to see which ones are valid with Bybit's API."""
    
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
    
    # Format 1: Standard format with month abbreviation (Bybit's historical format)
    # Example: BTCUSDT-27JUN25
    def format_quarterly_symbol_standard(base, year, month):
        last_friday = get_last_friday(year, month)
        day = last_friday.day
        month_abbr = last_friday.strftime("%b").upper()
        return f"{base}USDT-{day}{month_abbr}{year % 100}"
    
    # Format 2: MMDD format without hyphen
    # Example: BTCUSDT1229
    def format_quarterly_symbol_mmdd(base, year, month):
        last_friday = get_last_friday(year, month)
        return f"{base}USDT{last_friday.month:02d}{last_friday.day:02d}"
    
    # Format 3: Month code format
    # Example: BTCUSDTM25 for linear or BTCUSDM25 for inverse
    def format_quarterly_symbol_code(base, year, month, inverse=False):
        month_codes = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
        if inverse:
            return f"{base}USD{month_codes[month]}{year % 100}"
        else:
            return f"{base}USDT{month_codes[month]}{year % 100}"
    
    # Current year and month
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Test all formats for each asset
    results = {
        'standard': {},
        'mmdd': {},
        'code': {},
        'inverse_code': {}
    }
    
    url = "https://api.bybit.com/v5/market/tickers"
    
    async with aiohttp.ClientSession() as session:
        for base_asset in base_assets:
            logger.info(f"Testing formats for {base_asset}")
            
            for month in [6, 9, 12]:  # Test June, September, December contracts
                if month < current_month and month != 12:
                    continue  # Skip past contracts except December
                
                # Generate all formats
                standard = format_quarterly_symbol_standard(base_asset, current_year, month)
                mmdd = format_quarterly_symbol_mmdd(base_asset, current_year, month)
                code = format_quarterly_symbol_code(base_asset, current_year, month)
                inverse = format_quarterly_symbol_code(base_asset, current_year, month, inverse=True)
                
                formats = [
                    (standard, "linear", "standard"),
                    (mmdd, "linear", "mmdd"),
                    (code, "linear", "code"),
                    (inverse, "inverse", "inverse_code")
                ]
                
                for symbol, category, format_name in formats:
                    try:
                        params = {'category': category, 'symbol': symbol}
                        logger.info(f"Trying {symbol} ({category})...")
                        
                        async with session.get(url, params=params) as response:
                            if response.status == 200:
                                result = await response.json()
                                if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):
                                    price = float(result['result']['list'][0].get('lastPrice', 0))
                                    results[format_name][symbol] = price
                                    logger.info(f"✅ SUCCESS for {symbol}: Price = {price}")
                                else:
                                    logger.info(f"❌ ERROR for {symbol}: {result.get('retMsg', 'Unknown error')}")
                            else:
                                logger.info(f"❌ HTTP Error for {symbol}: {response.status}")
                    except Exception as e:
                        logger.error(f"Exception for {symbol}: {e}")
    
    # Summary of results
    logger.info("\n=== SUMMARY OF WORKING FORMATS ===")
    for format_name, symbols in results.items():
        if symbols:
            logger.info(f"{format_name.upper()} format - {len(symbols)} valid symbols:")
            for symbol, price in symbols.items():
                logger.info(f"  {symbol}: {price}")
        else:
            logger.info(f"{format_name.upper()} format - No valid symbols found")
    
    # Determine best format for each asset
    logger.info("\n=== RECOMMENDED FORMAT BY ASSET ===")
    for base_asset in base_assets:
        best_format = None
        
        # Check formats in order of preference
        formats_to_check = ["mmdd", "inverse_code", "standard", "code"]
        for format_name in formats_to_check:
            for symbol in results[format_name]:
                if symbol.startswith(base_asset):
                    best_format = format_name
                    break
            if best_format:
                break
        
        if best_format:
            logger.info(f"{base_asset}: Use {best_format.upper()} format")
        else:
            logger.info(f"{base_asset}: No working format found")

async def main():
    await test_quarterly_futures_formats()

if __name__ == "__main__":
    asyncio.run(main()) 
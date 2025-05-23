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

async def verify_tickers():
    """Verify that we can get ticker data for the discovered futures formats."""
    
    # Based on previous script output, we'll test the following formats
    test_symbols = [
        # Linear hyphenated formats
        ("BTCUSDT-26DEC25", "linear"),
        ("BTCUSDT-26SEP25", "linear"),
        ("BTCUSDT-27JUN25", "linear"),
        ("ETHUSDT-26DEC25", "linear"),
        ("ETHUSDT-27JUN25", "linear"),
        ("SOLUSDT-27JUN25", "linear"),
        # Linear with base asset only
        ("BTC-26DEC25", "linear"),
        ("ETH-26DEC25", "linear"),
        # Inverse month code formats
        ("BTCUSDM25", "inverse"),
        ("BTCUSDU25", "inverse"),
        ("ETHUSDM25", "inverse"),
        ("ETHUSDU25", "inverse"),
        # Test non-existent assets with similar formats
        ("AVAXUSDT-26DEC25", "linear"),
        ("XRPUSDT-26DEC25", "linear"),
        ("AVAXUSDM25", "inverse"),
        ("XRPUSDM25", "inverse")
    ]
    
    # URL for tickers endpoint
    url = "https://api.bybit.com/v5/market/tickers"
    
    results = {
        "linear_hyphenated": {},
        "inverse_month_code": {},
        "base_only_hyphenated": {},
        "invalid": []
    }
    
    async with aiohttp.ClientSession() as session:
        for symbol, category in test_symbols:
            try:
                params = {'category': category, 'symbol': symbol}
                logger.info(f"Trying {symbol} ({category})...")
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):
                            data = result['result']['list'][0]
                            price = float(data.get('lastPrice', 0))
                            format_key = None
                            
                            if category == "linear" and "-" in symbol:
                                if symbol.startswith("BTC-") or symbol.startswith("ETH-"):
                                    format_key = "base_only_hyphenated"
                                else:
                                    format_key = "linear_hyphenated"
                            elif category == "inverse" and any(code in symbol for code in ['M', 'U', 'Z', 'H']):
                                format_key = "inverse_month_code"
                            
                            if format_key:
                                results[format_key][symbol] = {
                                    "price": price,
                                    "bid": float(data.get('bid1Price', 0)),
                                    "ask": float(data.get('ask1Price', 0)),
                                    "volume": float(data.get('volume24h', 0)),
                                    "open_interest": float(data.get('openInterest', 0)),
                                    "funding_rate": float(data.get('fundingRate', 0)),
                                    "next_funding": data.get('nextFundingTime', 'N/A')
                                }
                            
                            logger.info(f"✅ SUCCESS for {symbol}: Price = {price}")
                        else:
                            logger.info(f"❌ ERROR for {symbol}: {result.get('retMsg', 'Unknown error')}")
                            results["invalid"].append(symbol)
                    else:
                        logger.info(f"❌ HTTP Error for {symbol}: {response.status}")
                        results["invalid"].append(symbol)
            except Exception as e:
                logger.error(f"Exception for {symbol}: {e}")
                results["invalid"].append(symbol)
    
    # Print summary of working formats
    logger.info("\n=== SUMMARY OF WORKING FORMATS ===")
    
    logger.info("\nLINEAR HYPHENATED FORMAT (e.g., BTCUSDT-26DEC25):")
    for symbol, data in results["linear_hyphenated"].items():
        logger.info(f"- {symbol}: Price={data['price']}, Volume={data['volume']}")
    
    logger.info("\nBASE ONLY HYPHENATED FORMAT (e.g., BTC-26DEC25):")
    for symbol, data in results["base_only_hyphenated"].items():
        logger.info(f"- {symbol}: Price={data['price']}, Volume={data['volume']}")
    
    logger.info("\nINVERSE MONTH CODE FORMAT (e.g., BTCUSDM25):")
    for symbol, data in results["inverse_month_code"].items():
        logger.info(f"- {symbol}: Price={data['price']}, Volume={data['volume']}")
    
    logger.info("\nINVALID SYMBOLS:")
    for symbol in results["invalid"]:
        logger.info(f"- {symbol}")
    
    # Recommendations for format usage by asset
    logger.info("\n=== RECOMMENDED FORMAT BY ASSET ===")
    assets = ["BTC", "ETH", "SOL", "XRP", "AVAX"]
    
    for asset in assets:
        found_formats = []
        
        # Check each format for this asset
        for symbol in results["linear_hyphenated"]:
            if symbol.startswith(asset):
                found_formats.append("linear_hyphenated")
                break
        
        for symbol in results["base_only_hyphenated"]:
            if symbol.startswith(asset):
                found_formats.append("base_only_hyphenated")
                break
                
        for symbol in results["inverse_month_code"]:
            if symbol.startswith(asset):
                found_formats.append("inverse_month_code")
                break
        
        if found_formats:
            # Sort by priority: prefer USDT linear formats, then base-only linear, then inverse
            logger.info(f"{asset}: Found formats: {', '.join(found_formats)}")
            
            if "linear_hyphenated" in found_formats:
                logger.info(f"  Recommendation: Use linear hyphenated format (e.g., {asset}USDT-26DEC25)")
            elif "base_only_hyphenated" in found_formats:
                logger.info(f"  Recommendation: Use base-only hyphenated format (e.g., {asset}-26DEC25)")
            elif "inverse_month_code" in found_formats:
                logger.info(f"  Recommendation: Use inverse month code format (e.g., {asset}USDM25)")
            else:
                logger.info(f"  No recommended format")
        else:
            logger.info(f"{asset}: No working formats found")
            
        # Check if any specific symbols for this asset were invalid
        invalid_for_asset = [s for s in results["invalid"] if s.startswith(asset)]
        if invalid_for_asset:
            logger.info(f"  Invalid formats: {', '.join(invalid_for_asset)}")

async def main():
    await verify_tickers()

if __name__ == "__main__":
    asyncio.run(main()) 
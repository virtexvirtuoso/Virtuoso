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

async def get_available_futures():
    """Get all available futures contracts for major assets on Bybit."""
    
    url = "https://api.bybit.com/v5/market/instruments-info"
    
    # Assets to look for
    assets = ['BTC', 'ETH', 'SOL', 'XRP', 'AVAX']
    
    # Categories to check
    categories = ["linear", "inverse"]
    
    results = {}
    
    async with aiohttp.ClientSession() as session:
        for category in categories:
            logger.info(f"\n=== CHECKING {category.upper()} CATEGORY ===")
            params = {'category': category}
            
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):
                            instruments = result['result']['list']
                            
                            # Filter for futures (non-perpetual) contracts
                            futures = [item for item in instruments 
                                      if item.get('contractType') != 'LinearPerpetual' 
                                      and item.get('contractType') != 'InversePerpetual']
                            
                            logger.info(f"Found {len(futures)} futures contracts in {category} category")
                            
                            # Group by asset
                            for asset in assets:
                                asset_futures = [f for f in futures if f.get('symbol', '').startswith(asset)]
                                
                                if asset_futures:
                                    logger.info(f"\n{asset} futures ({len(asset_futures)}):")
                                    for future in asset_futures:
                                        symbol = future.get('symbol')
                                        contract_type = future.get('contractType')
                                        status = future.get('status')
                                        deliveryDate = future.get('deliveryDate', 'N/A')
                                        if deliveryDate and deliveryDate.isdigit():
                                            delivery_date = datetime.fromtimestamp(int(deliveryDate)/1000).strftime('%Y-%m-%d')
                                        else:
                                            delivery_date = deliveryDate
                                            
                                        logger.info(f"Symbol: {symbol}, Type: {contract_type}, Status: {status}, Delivery: {delivery_date}")
                                        
                                        # Store in results
                                        if asset not in results:
                                            results[asset] = []
                                            
                                        results[asset].append({
                                            'symbol': symbol,
                                            'category': category,
                                            'contract_type': contract_type,
                                            'status': status,
                                            'delivery_date': delivery_date
                                        })
                                else:
                                    logger.info(f"No {asset} futures found in {category} category")
                        else:
                            logger.error(f"API error for {category}: {result.get('retMsg')}")
                    else:
                        logger.error(f"HTTP error getting {category} instruments: {response.status}")
            except Exception as e:
                logger.error(f"Exception with {category}: {str(e)}")
    
    # Print summary of valid symbols by asset
    logger.info("\n=== SUMMARY OF VALID SYMBOLS BY ASSET ===")
    for asset, contracts in results.items():
        logger.info(f"\n{asset}: {len(contracts)} valid futures contracts")
        for contract in contracts:
            logger.info(f"- {contract['symbol']} ({contract['category']}, delivery: {contract['delivery_date']})")
    
    # Check if the presumed quarterly futures format is used
    logger.info("\n=== ANALYZING SYMBOL PATTERNS ===")
    
    patterns = {
        'hyphenated': 0,      # BTCUSDT-29DEC25
        'mmdd': 0,            # BTCUSDT1229
        'month_code': 0,      # BTCUSDTM25 / BTCUSDM25
        'other': 0
    }
    
    pattern_examples = {
        'hyphenated': [],
        'mmdd': [],
        'month_code': [],
        'other': []
    }
    
    for asset, contracts in results.items():
        for contract in contracts:
            symbol = contract['symbol']
            if '-' in symbol:
                patterns['hyphenated'] += 1
                pattern_examples['hyphenated'].append(symbol)
            elif any(code in symbol for code in ['H', 'M', 'U', 'Z']) and symbol[-2:].isdigit():
                patterns['month_code'] += 1
                pattern_examples['month_code'].append(symbol)
            elif len(symbol) >= 4 and symbol[-4:].isdigit():
                patterns['mmdd'] += 1
                pattern_examples['mmdd'].append(symbol)
            else:
                patterns['other'] += 1
                pattern_examples['other'].append(symbol)
    
    # Print pattern analysis
    for pattern, count in patterns.items():
        logger.info(f"{pattern}: {count} contracts")
        if count > 0:
            logger.info(f"  Examples: {', '.join(pattern_examples[pattern][:3])}")

async def main():
    await get_available_futures()

if __name__ == "__main__":
    asyncio.run(main()) 
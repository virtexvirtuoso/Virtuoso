#!/usr/bin/env python3
import asyncio
import logging
import sys
import aiohttp
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Month codes used in futures symbols
MONTH_CODES = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
MONTH_NAMES = {3: 'March', 6: 'June', 9: 'September', 12: 'December'}

def get_last_friday(year, month):
    """Get the last Friday of a given month"""
    if month == 12:
        last_day = datetime(year, 12, 31)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # Find the last Friday (weekday 4)
    offset = (4 - last_day.weekday()) % 7
    last_friday = last_day - timedelta(days=offset) if offset != 0 else last_day
    return last_friday

def format_quarterly_symbol_code(base, year, month, inverse=False):
    """Format month code symbol: BTCUSDTM25 (linear) or BTCUSDM25 (inverse)"""
    if inverse:
        return f"{base}USD{MONTH_CODES[month]}{year % 100}"
    else:
        return f"{base}USDT{MONTH_CODES[month]}{year % 100}"

async def test_bybit_futures():
    """Test our futures premium calculation directly with Bybit API."""
    try:
        logger.info("Starting Bybit futures test...")
        
        # Test assets
        assets = ["BTC", "ETH", "SOL", "XRP", "AVAX"]
        
        # Current year and month
        current_year = datetime.now().year
        current_month = datetime.now().month
        current_year_short = current_year % 100
        
        # Create async HTTP session
        async with aiohttp.ClientSession() as session:
            # Test futures for each asset
            for asset in assets:
                logger.info(f"\nTesting futures for {asset}")
                
                # Get perpetual (spot) price for reference
                perp_symbol = f"{asset}USDT"
                url = "https://api.bybit.com/v5/market/tickers"
                
                # Fetch perpetual ticker
                params = {"category": "linear", "symbol": perp_symbol}
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        perp_data = await response.json()
                        if perp_data.get('retCode') == 0 and perp_data.get('result') and perp_data['result'].get('list'):
                            perp_ticker = perp_data['result']['list'][0]
                            index_price = float(perp_ticker.get('indexPrice', 0))
                            mark_price = float(perp_ticker.get('markPrice', 0))
                            logger.info(f"  {perp_symbol}: Index Price = {index_price}, Mark Price = {mark_price}")
                        else:
                            logger.warning(f"  Could not get price for {perp_symbol}: {perp_data.get('retMsg')}")
                            index_price = 0
                            mark_price = 0
                    else:
                        logger.error(f"  Error fetching {perp_symbol}: {response.status}")
                        index_price = 0
                        mark_price = 0
                
                # Test quarterly futures in inverse category
                futures_found = []
                quarters = [6, 9]  # We know June and September are available
                
                for month in quarters:
                    if month >= current_month or month == 12:
                        # Create inverse symbol
                        symbol = format_quarterly_symbol_code(asset, current_year, month, inverse=True)
                        
                        # Test symbol
                        params = {"category": "inverse", "symbol": symbol}
                        async with session.get(url, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                if data.get('retCode') == 0 and data.get('result') and data['result'].get('list'):
                                    ticker = data['result']['list'][0]
                                    futures_price = float(ticker.get('lastPrice', 0))
                                    futures_index = float(ticker.get('indexPrice', 0))
                                    
                                    # Calculate basis
                                    if futures_index > 0:
                                        # For inverse contracts, the basis is calculated differently
                                        inverse_index = 1/futures_index if futures_index != 0 else 0
                                        inverse_futures = 1/futures_price if futures_price != 0 else 0
                                        basis = ((inverse_futures - inverse_index) / inverse_index) * 100
                                        
                                        # Calculate months to expiry for annualization
                                        current_date = datetime.now()
                                        months_to_expiry = (month - current_month) if month > current_month else (month + 12 - current_month)
                                        months_to_expiry = max(1, months_to_expiry)  # Ensure at least 1 month
                                        
                                        # Annualize basis
                                        annualized_basis = basis * (12 / months_to_expiry)
                                        
                                        # Add to found futures
                                        futures_found.append({
                                            'symbol': symbol,
                                            'category': 'inverse',
                                            'month': MONTH_NAMES[month],
                                            'price': futures_price,
                                            'index': futures_index,
                                            'basis': f"{basis:.4f}%",
                                            'annualized_basis': f"{annualized_basis:.4f}%",
                                            'months_to_expiry': months_to_expiry
                                        })
                                        
                                        logger.info(f"  ✅ Found {symbol} (inverse): Price = {futures_price}, Basis = {basis:.4f}%")
                                    else:
                                        logger.warning(f"  Zero index price for {symbol}")
                                else:
                                    logger.info(f"  ❌ {symbol} not found: {data.get('retMsg')}")
                            else:
                                logger.error(f"  Error fetching {symbol}: {response.status}")
                
                # Print summary for this asset
                if futures_found:
                    logger.info(f"  Found {len(futures_found)} futures contracts for {asset}")
                    # Sort by months to expiry
                    futures_found.sort(key=lambda x: x['months_to_expiry'])
                    for future in futures_found:
                        logger.info(f"    • {future['symbol']} ({future['month']}): Price={future['price']}, Basis={future['basis']}, Annualized={future['annualized_basis']}")
                else:
                    logger.info(f"  No futures contracts found for {asset}")
        
        # Print final summary
        logger.info("\n=== TEST SUMMARY ===")
        logger.info("Bybit futures test completed")
        logger.info("Remember that only BTC and ETH currently have futures contracts in inverse category")
    
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_bybit_futures()) 
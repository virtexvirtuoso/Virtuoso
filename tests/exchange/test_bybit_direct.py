import asyncio
import aiohttp
import logging
import json
from datetime import datetime
import time
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class BybitDirectTester:
    """Test Bybit API integration directly without relying on exchange object."""
    
    def __init__(self):
        self.base_url = "https://api.bybit.com"
        self.headers = {"Content-Type": "application/json"}
        self.session = None
        
        # Bybit field mappings (copied from MarketReporter)
        self.BYBIT_FIELD_MAPPINGS = {
            'mark_price': ['markPrice', 'mark_price'],
            'index_price': ['indexPrice', 'index_price'],
            'funding_rate': ['fundingRate', 'funding_rate'],
            'open_interest': ['openInterest', 'open_interest', 'oi'],
            'turnover': ['turnover24h', 'turnover', 'volume24hValue'],
            'volume': ['volume', 'volume24h']
        }
    
    async def initialize(self):
        """Initialize the HTTP session."""
        self.session = aiohttp.ClientSession()
        
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            
    async def fetch_ticker(self, symbol, category="spot"):
        """Fetch ticker data for a symbol."""
        endpoint = f"/v5/market/tickers?category={category}&symbol={symbol}"
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.get(url, headers=self.headers) as response:
                data = await response.json()
                if data.get("retCode") == 0 and "result" in data and "list" in data["result"]:
                    if len(data["result"]["list"]) > 0:
                        return data["result"]["list"][0]
                return None
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
            
    async def fetch_funding_history(self, symbol, category="linear", limit=10):
        """Fetch funding rate history for a symbol."""
        endpoint = f"/v5/market/funding/history?category={category}&symbol={symbol}&limit={limit}"
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.get(url, headers=self.headers) as response:
                data = await response.json()
                if data.get("retCode") == 0 and "result" in data and "list" in data["result"]:
                    return data["result"]["list"]
                return []
        except Exception as e:
            logger.error(f"Error fetching funding history for {symbol}: {e}")
            return []
            
    async def fetch_open_interest(self, symbol, category="linear", interval="1d", limit=7):
        """Fetch open interest data for a symbol."""
        endpoint = f"/v5/market/open-interest?category={category}&symbol={symbol}&intervalTime={interval}&limit={limit}"
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.get(url, headers=self.headers) as response:
                data = await response.json()
                if data.get("retCode") == 0 and "result" in data and "list" in data["result"]:
                    return data["result"]["list"]
                return []
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            return []
    
    def _extract_field(self, data, field_type, default=0):
        """Extract a field from Bybit data using mappings."""
        if data is None:
            return default
            
        field_names = self.BYBIT_FIELD_MAPPINGS.get(field_type, [field_type])
        
        for name in field_names:
            if name in data:
                try:
                    return float(data[name])
                except (ValueError, TypeError):
                    continue
                
        return default
    
    async def analyze_funding_rates(self, symbol):
        """Analyze funding rate history for a symbol."""
        try:
            funding_data = await self.fetch_funding_history(symbol)
            
            rates = []
            for entry in funding_data:
                if 'fundingRate' in entry:
                    rates.append(float(entry['fundingRate']))
                    
            if not rates:
                return {'average': 0, 'trend': 'neutral', 'latest': 0}
                
            avg_rate = sum(rates) / len(rates)
            
            if len(rates) > 1:
                if rates[0] > avg_rate:
                    trend = 'increasing'
                elif rates[0] < avg_rate:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
            else:
                trend = 'neutral'
                
            if avg_rate > 0.0001:
                sentiment = 'bullish'
            elif avg_rate < -0.0001:
                sentiment = 'bearish'
            else:
                sentiment = 'neutral'
                
            return {
                'average': avg_rate,
                'latest': rates[0] if rates else 0,
                'trend': trend,
                'sentiment': sentiment,
                'historical': rates[:5]
            }
        except Exception as e:
            logger.warning(f"Error analyzing funding rates for {symbol}: {e}")
            return {'average': 0, 'trend': 'neutral', 'latest': 0}
            
    async def calculate_futures_premium(self, base, spot_category="spot", futures_category="linear"):
        """Calculate futures premium for a base asset."""
        try:
            spot_symbol = f"{base}USDT"
            futures_symbol = f"{base}USDT"
            
            # Fetch spot and futures tickers concurrently
            spot_ticker_task = self.fetch_ticker(spot_symbol, spot_category)
            futures_ticker_task = self.fetch_ticker(futures_symbol, futures_category)
            
            spot_ticker, futures_ticker = await asyncio.gather(spot_ticker_task, futures_ticker_task)
            
            if not spot_ticker or not futures_ticker:
                logger.warning(f"Missing ticker data for {base}")
                return None
                
            # Extract prices
            spot_price = self._extract_field(spot_ticker, 'last')
            mark_price = self._extract_field(futures_ticker, 'mark_price')
            index_price = self._extract_field(futures_ticker, 'index_price')
            
            # If index price not found, use spot price
            if not index_price:
                index_price = spot_price
                
            # Calculate premium
            if mark_price > 0 and index_price > 0:
                premium = ((mark_price - index_price) / index_price) * 100
                premium_type = "Backwardation" if premium < 0 else "Contango"
                
                # Get funding rate
                funding_rate = self._extract_field(futures_ticker, 'funding_rate')
                
                # Check for quarterly futures
                current_year = datetime.now().year % 100
                quarterly_patterns = [
                    f"{base}USDM{current_year}",  # June quarterly
                    f"{base}USDU{current_year}",  # September quarterly
                    f"{base}USDZ{current_year}"   # December quarterly
                ]
                
                futures_contracts = []
                
                # Fetch quarterly futures data
                for pattern in quarterly_patterns:
                    try:
                        quarterly_ticker = await self.fetch_ticker(pattern, "inverse")
                        if quarterly_ticker:
                            quarterly_price = self._extract_field(quarterly_ticker, 'last')
                            if quarterly_price > 0:
                                is_june = 'M' in pattern
                                is_sept = 'U' in pattern
                                is_dec = 'Z' in pattern
                                
                                month = "June" if is_june else "September" if is_sept else "December"
                                expiry_month = 6 if is_june else 9 if is_sept else 12
                                months_to_expiry = max(1, expiry_month - datetime.now().month)
                                
                                # For inverse contracts
                                if index_price > 0:
                                    basis = ((1/quarterly_price - 1/index_price) / (1/index_price)) * 100
                                    annualized_basis = basis * (12 / months_to_expiry)
                                    
                                    futures_contracts.append({
                                        'symbol': pattern,
                                        'month': month,
                                        'price': quarterly_price,
                                        'basis': f"{basis:.4f}%",
                                        'annualized_basis': f"{annualized_basis:.4f}%"
                                    })
                    except Exception as e:
                        logger.debug(f"Error fetching quarterly future {pattern}: {e}")
                
                return {
                    'base': base,
                    'spot_price': spot_price,
                    'mark_price': mark_price,
                    'index_price': index_price,
                    'premium': f"{premium:.4f}%",
                    'premium_value': premium,
                    'premium_type': premium_type,
                    'funding_rate': funding_rate,
                    'quarterly_futures': futures_contracts
                }
            else:
                logger.warning(f"Invalid price data for {base}")
                return None
        except Exception as e:
            logger.error(f"Error calculating futures premium for {base}: {e}")
            return None

async def test_bybit_direct():
    """Test direct Bybit API integration."""
    tester = BybitDirectTester()
    
    try:
        await tester.initialize()
        
        # Test symbols
        symbols = ["BTC", "ETH", "SOL", "XRP"]
        
        # Test ticker data
        logger.info("\n===== Testing Ticker Data =====")
        for symbol in symbols:
            ticker = await tester.fetch_ticker(f"{symbol}USDT")
            if ticker:
                logger.info(f"{symbol} Spot Price: {ticker.get('lastPrice')}")
            
            futures_ticker = await tester.fetch_ticker(f"{symbol}USDT", "linear")
            if futures_ticker:
                logger.info(f"{symbol} Futures - Mark: {futures_ticker.get('markPrice')}, Index: {futures_ticker.get('indexPrice')}")
                
        # Test funding rates
        logger.info("\n===== Testing Funding Rates =====")
        for symbol in symbols:
            funding_data = await tester.analyze_funding_rates(f"{symbol}USDT")
            logger.info(f"{symbol} Funding - Average: {funding_data['average']}, Trend: {funding_data['trend']}, Sentiment: {funding_data.get('sentiment', 'neutral')}")
            
        # Test futures premium
        logger.info("\n===== Testing Futures Premium =====")
        for symbol in symbols:
            premium_data = await tester.calculate_futures_premium(symbol)
            if premium_data:
                logger.info(f"{symbol}: Spot: {premium_data['spot_price']}, Mark: {premium_data['mark_price']}")
                logger.info(f"  Premium: {premium_data['premium']} ({premium_data['premium_type']})")
                logger.info(f"  Funding Rate: {premium_data['funding_rate']}")
                
                if premium_data['quarterly_futures']:
                    logger.info(f"  Quarterly Futures:")
                    for contract in premium_data['quarterly_futures']:
                        logger.info(f"    {contract['symbol']} ({contract['month']}): Price: {contract['price']}, Basis: {contract['basis']}")
                        
        # Test open interest
        logger.info("\n===== Testing Open Interest =====")
        for symbol in symbols[:1]:  # Just test BTC
            oi_data = await tester.fetch_open_interest(f"{symbol}USDT")
            if oi_data:
                logger.info(f"{symbol} Open Interest:")
                for entry in oi_data:
                    timestamp = datetime.fromtimestamp(int(entry['timestamp'])/1000).strftime('%Y-%m-%d')
                    oi_value = entry.get('openInterestValue', entry.get('value', 0))
                    logger.info(f"  {timestamp}: {entry.get('openInterest', 0)} contracts, Value: {oi_value}")
                    
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.close()

if __name__ == "__main__":
    logger.info("Starting direct Bybit API test")
    asyncio.run(test_bybit_direct())
    logger.info("Test completed") 
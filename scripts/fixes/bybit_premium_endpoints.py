#!/usr/bin/env python3
"""
Comprehensive Bybit API Endpoints for Futures Premium Data

This script demonstrates all the relevant Bybit API v5 endpoints that should be used
for accurate futures premium calculations, based on the official documentation.

Reference: https://bybit-exchange.github.io/docs/v5/market/instrument
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class BybitPremiumEndpoints:
    """Comprehensive collection of Bybit API endpoints for futures premium data."""
    
    def __init__(self, base_url: str = "https://api.bybit.com"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    # ===========================================
    # 1. INSTRUMENT DISCOVERY ENDPOINTS
    # ===========================================
    
    async def get_instruments_info(self, category: str, base_coin: str = None, symbol: str = None) -> Dict[str, Any]:
        """
        Get Instruments Info - Essential for discovering all available contracts
        
        Endpoint: GET /v5/market/instruments-info
        Documentation: https://bybit-exchange.github.io/docs/v5/market/instrument
        
        This is the PRIMARY endpoint for contract discovery.
        """
        url = f"{self.base_url}/v5/market/instruments-info"
        params = {'category': category}
        
        if base_coin:
            params['baseCoin'] = base_coin
        if symbol:
            params['symbol'] = symbol
        
        # Always request maximum data
        params['limit'] = 1000
        
        logger.info(f"🔍 Discovering instruments: {url} with params: {params}")
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                logger.error(f"Failed to fetch instruments: HTTP {response.status}")
                return {}
    
    # ===========================================
    # 2. PRICING DATA ENDPOINTS  
    # ===========================================
    
    async def get_tickers(self, category: str, symbol: str = None, base_coin: str = None) -> Dict[str, Any]:
        """
        Get Tickers - Contains mark price, index price, and funding rates
        
        Endpoint: GET /v5/market/tickers
        
        Key fields for futures premium:
        - markPrice: Current mark price for perpetuals
        - indexPrice: Underlying index price
        - lastPrice: Last traded price for futures contracts
        - fundingRate: Current funding rate
        """
        url = f"{self.base_url}/v5/market/tickers"
        params = {'category': category}
        
        if symbol:
            params['symbol'] = symbol
        if base_coin:
            params['baseCoin'] = base_coin
            
        logger.info(f"📊 Fetching tickers: {url} with params: {params}")
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch tickers: HTTP {response.status}")
                return {}
    
    async def get_mark_price_kline(self, category: str, symbol: str, interval: str = "1", limit: int = 200) -> Dict[str, Any]:
        """
        Get Mark Price Kline - Historical mark prices
        
        Endpoint: GET /v5/market/mark-price-kline
        
        Useful for analyzing mark price trends and calculating historical premiums.
        """
        url = f"{self.base_url}/v5/market/mark-price-kline"
        params = {
            'category': category,
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        logger.info(f"📈 Fetching mark price kline: {url}")
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch mark price kline: HTTP {response.status}")
                return {}
    
    async def get_index_price_kline(self, category: str, symbol: str, interval: str = "1", limit: int = 200) -> Dict[str, Any]:
        """
        Get Index Price Kline - Historical index prices
        
        Endpoint: GET /v5/market/index-price-kline
        
        Essential for calculating historical premium trends.
        """
        url = f"{self.base_url}/v5/market/index-price-kline"
        params = {
            'category': category,
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        logger.info(f"📉 Fetching index price kline: {url}")
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch index price kline: HTTP {response.status}")
                return {}
    
    async def get_premium_index_price_kline(self, category: str, symbol: str, interval: str = "1", limit: int = 200) -> Dict[str, Any]:
        """
        Get Premium Index Price Kline - Pre-calculated premium data
        
        Endpoint: GET /v5/market/premium-index-price-kline  
        
        This endpoint provides Bybit's own premium calculations!
        Extremely useful for validation and comparison.
        """
        url = f"{self.base_url}/v5/market/premium-index-price-kline"
        params = {
            'category': category,
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        logger.info(f"💎 Fetching premium index kline: {url}")
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch premium index kline: HTTP {response.status}")
                return {}
    
    # ===========================================
    # 3. FUNDING AND RISK ENDPOINTS
    # ===========================================
    
    async def get_funding_rate_history(self, category: str, symbol: str, limit: int = 200) -> Dict[str, Any]:
        """
        Get Funding Rate History
        
        Endpoint: GET /v5/market/funding/history
        
        Essential for understanding funding rate trends that affect perpetual premiums.
        """
        url = f"{self.base_url}/v5/market/funding/history"
        params = {
            'category': category,
            'symbol': symbol,
            'limit': limit
        }
        
        logger.info(f"💰 Fetching funding rate history: {url}")
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch funding rate history: HTTP {response.status}")
                return {}
    
    async def get_open_interest(self, category: str, symbol: str, interval_time: str = "5min", limit: int = 200) -> Dict[str, Any]:
        """
        Get Open Interest
        
        Endpoint: GET /v5/market/open-interest
        
        Open interest affects futures premiums and provides market sentiment insight.
        """
        url = f"{self.base_url}/v5/market/open-interest"
        params = {
            'category': category,
            'symbol': symbol,
            'intervalTime': interval_time,
            'limit': limit
        }
        
        logger.info(f"🎯 Fetching open interest: {url}")
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch open interest: HTTP {response.status}")
                return {}
    
    # ===========================================
    # 4. COMPREHENSIVE PREMIUM CALCULATION
    # ===========================================
    
    async def calculate_complete_premium_data(self, base_coin: str) -> Dict[str, Any]:
        """
        Calculate comprehensive futures premium data using all available endpoints.
        
        This method demonstrates the PROPER way to gather futures premium data
        by leveraging multiple Bybit API endpoints systematically.
        """
        logger.info(f"🚀 Starting comprehensive premium calculation for {base_coin}")
        
        result = {
            'base_coin': base_coin,
            'contracts': {},
            'perpetual_data': {},
            'quarterly_data': {},
            'premium_calculations': {},
            'funding_analysis': {},
            'open_interest_data': {},
            'data_sources': []
        }
        
        # Step 1: Discover all contracts for this base coin
        logger.info("📋 Step 1: Contract Discovery")
        
        # Linear contracts (USDT-margined)
        linear_instruments = await self.get_instruments_info(category="linear", base_coin=base_coin)
        if linear_instruments.get('retCode') == 0:
            linear_contracts = linear_instruments.get('result', {}).get('list', [])
            result['contracts']['linear'] = linear_contracts
            result['data_sources'].append('linear_instruments')
            logger.info(f"   Found {len(linear_contracts)} linear contracts")
        
        # Inverse contracts (Coin-margined)  
        inverse_instruments = await self.get_instruments_info(category="inverse", base_coin=base_coin)
        if inverse_instruments.get('retCode') == 0:
            inverse_contracts = inverse_instruments.get('result', {}).get('list', [])
            result['contracts']['inverse'] = inverse_contracts
            result['data_sources'].append('inverse_instruments')
            logger.info(f"   Found {len(inverse_contracts)} inverse contracts")
        
        # Step 2: Get current pricing data
        logger.info("💹 Step 2: Current Pricing Data")
        
        # Perpetual ticker (USDT-margined)
        perp_symbol = f"{base_coin}USDT"
        linear_tickers = await self.get_tickers(category="linear", symbol=perp_symbol)
        if linear_tickers.get('retCode') == 0:
            ticker_list = linear_tickers.get('result', {}).get('list', [])
            if ticker_list:
                result['perpetual_data'] = ticker_list[0]
                result['data_sources'].append('linear_tickers')
                logger.info(f"   ✅ Perpetual data: mark={result['perpetual_data'].get('markPrice')}, index={result['perpetual_data'].get('indexPrice')}")
        
        # Step 3: Historical premium data (Bybit's own calculations)
        logger.info("📊 Step 3: Historical Premium Data")
        
        premium_kline = await self.get_premium_index_price_kline(category="linear", symbol=perp_symbol, limit=24)
        if premium_kline.get('retCode') == 0:
            result['premium_calculations']['historical'] = premium_kline.get('result', {})
            result['data_sources'].append('premium_index_kline')
            kline_data = premium_kline.get('result', {}).get('list', [])
            logger.info(f"   ✅ Retrieved {len(kline_data)} historical premium data points")
        
        # Step 4: Funding rate analysis
        logger.info("💰 Step 4: Funding Rate Analysis")
        
        funding_history = await self.get_funding_rate_history(category="linear", symbol=perp_symbol, limit=50)
        if funding_history.get('retCode') == 0:
            result['funding_analysis'] = funding_history.get('result', {})
            result['data_sources'].append('funding_history')
            funding_list = funding_history.get('result', {}).get('list', [])
            logger.info(f"   ✅ Retrieved {len(funding_list)} funding rate records")
        
        # Step 5: Open interest data
        logger.info("🎯 Step 5: Open Interest Data")
        
        oi_data = await self.get_open_interest(category="linear", symbol=perp_symbol, limit=24)
        if oi_data.get('retCode') == 0:
            result['open_interest_data'] = oi_data.get('result', {})
            result['data_sources'].append('open_interest')
            oi_list = oi_data.get('result', {}).get('list', [])
            logger.info(f"   ✅ Retrieved {len(oi_list)} open interest data points")
        
        # Step 6: Calculate final premium metrics
        logger.info("🧮 Step 6: Premium Calculations")
        
        if result['perpetual_data']:
            perp_data = result['perpetual_data']
            mark_price = float(perp_data.get('markPrice', 0))
            index_price = float(perp_data.get('indexPrice', 0))
            
            if mark_price > 0 and index_price > 0:
                current_premium = ((mark_price - index_price) / index_price) * 100
                
                result['premium_calculations']['current'] = {
                    'premium_percentage': round(current_premium, 4),
                    'premium_bps': round(current_premium * 100, 2),
                    'mark_price': mark_price,
                    'index_price': index_price,
                    'funding_rate': perp_data.get('fundingRate', 0),
                    'premium_type': 'Contango' if current_premium > 0 else 'Backwardation'
                }
                
                logger.info(f"   ✅ Current premium: {current_premium:.4f}% ({result['premium_calculations']['current']['premium_type']})")
            else:
                logger.warning(f"   ❌ Invalid pricing data: mark={mark_price}, index={index_price}")
        
        logger.info(f"🎉 Comprehensive analysis complete! Data sources used: {', '.join(result['data_sources'])}")
        return result


async def demonstrate_proper_api_usage():
    """Demonstrate the proper way to use Bybit API for futures premium data."""
    
    # Test with the symbols that were missing data
    test_symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'AVAX']
    
    async with BybitPremiumEndpoints() as api:
        for symbol in test_symbols:
            print(f"\n{'='*60}")
            print(f"COMPREHENSIVE ANALYSIS FOR {symbol}")
            print(f"{'='*60}")
            
            premium_data = await api.calculate_complete_premium_data(symbol)
            
            # Display results
            if premium_data.get('premium_calculations', {}).get('current'):
                current = premium_data['premium_calculations']['current']
                print(f"✅ {symbol} PREMIUM DATA FOUND:")
                print(f"   Current Premium: {current['premium_percentage']}% ({current['premium_type']})")
                print(f"   Mark Price: ${current['mark_price']:,.2f}")
                print(f"   Index Price: ${current['index_price']:,.2f}")
                print(f"   Funding Rate: {current['funding_rate']}")
                print(f"   Premium (bps): {current['premium_bps']}")
            else:
                print(f"❌ {symbol}: Unable to calculate current premium")
            
            # Show data sources used
            data_sources = premium_data.get('data_sources', [])
            print(f"   Data Sources: {len(data_sources)} endpoints used")
            for source in data_sources:
                print(f"      ✓ {source}")
            
            # Show contract counts
            linear_count = len(premium_data.get('contracts', {}).get('linear', []))
            inverse_count = len(premium_data.get('contracts', {}).get('inverse', []))
            print(f"   Contracts Found: {linear_count} linear, {inverse_count} inverse")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(demonstrate_proper_api_usage()) 
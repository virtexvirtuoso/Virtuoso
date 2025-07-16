#!/usr/bin/env python3
"""
Improved Futures Premium Data Retrieval Script

This script demonstrates how to properly use Bybit API endpoints to:
1. Discover available quarterly futures contracts
2. Fetch mark prices and index prices
3. Calculate accurate futures premiums

Based on Bybit API v5 documentation:
https://bybit-exchange.github.io/docs/v5/market/instrument
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImprovedFuturesPremiumAPI:
    """Improved API client for futures premium data using proper Bybit endpoints."""
    
    def __init__(self, base_url: str = "https://api.bybit.com"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def discover_futures_contracts(self, base_coin: str) -> List[Dict[str, Any]]:
        """
        Discover all available futures contracts for a base coin using instruments-info endpoint.
        
        Args:
            base_coin: Base coin symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            List of contract information dictionaries
        """
        contracts = []
        
        # Check linear contracts (USDT perpetuals and futures)
        linear_contracts = await self._get_instruments_info(
            category="linear", 
            base_coin=base_coin
        )
        
        # Check inverse contracts (USD futures)  
        inverse_contracts = await self._get_instruments_info(
            category="inverse",
            base_coin=base_coin
        )
        
        contracts.extend(linear_contracts)
        contracts.extend(inverse_contracts)
        
        logger.info(f"Found {len(contracts)} contracts for {base_coin}")
        return contracts
    
    async def _get_instruments_info(self, category: str, base_coin: str) -> List[Dict[str, Any]]:
        """
        Fetch instrument information from Bybit API.
        
        Args:
            category: Contract category ('linear', 'inverse', 'spot', 'option')
            base_coin: Base coin to filter by
            
        Returns:
            List of instrument dictionaries
        """
        url = f"{self.base_url}/v5/market/instruments-info"
        params = {
            'category': category,
            'baseCoin': base_coin,
            'limit': 1000  # Get all contracts
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        instruments = data.get('result', {}).get('list', [])
                        logger.debug(f"Found {len(instruments)} {category} instruments for {base_coin}")
                        return instruments
                    else:
                        logger.error(f"API error: {data.get('retMsg', 'Unknown error')}")
                else:
                    logger.error(f"HTTP {response.status} error fetching {category} instruments")
                    
        except Exception as e:
            logger.error(f"Error fetching {category} instruments for {base_coin}: {e}")
            
        return []
    
    async def get_tickers_for_contracts(self, contracts: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch ticker data for multiple contracts efficiently.
        
        Args:
            contracts: List of contract dictionaries from instruments-info
            
        Returns:
            Dictionary mapping symbol to ticker data
        """
        tickers = {}
        
        # Group contracts by category for efficient batch requests
        by_category = {}
        for contract in contracts:
            category = contract.get('category', 'linear')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(contract['symbol'])
        
        # Fetch tickers for each category
        for category, symbols in by_category.items():
            category_tickers = await self._get_category_tickers(category, symbols)
            tickers.update(category_tickers)
            
        return tickers
    
    async def _get_category_tickers(self, category: str, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch tickers for a specific category.
        
        Args:
            category: Contract category
            symbols: List of symbols to fetch
            
        Returns:
            Dictionary mapping symbol to ticker data
        """
        url = f"{self.base_url}/v5/market/tickers"
        params = {'category': category}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        tickers_list = data.get('result', {}).get('list', [])
                        
                        # Filter to requested symbols and convert to dict
                        tickers = {}
                        for ticker in tickers_list:
                            symbol = ticker.get('symbol')
                            if symbol in symbols:
                                tickers[symbol] = ticker
                                
                        logger.debug(f"Fetched {len(tickers)} tickers for {category}")
                        return tickers
                    else:
                        logger.error(f"API error fetching {category} tickers: {data.get('retMsg')}")
                else:
                    logger.error(f"HTTP {response.status} error fetching {category} tickers")
                    
        except Exception as e:
            logger.error(f"Error fetching {category} tickers: {e}")
            
        return {}
    
    async def calculate_futures_premium_comprehensive(self, base_coin: str) -> Dict[str, Any]:
        """
        Calculate comprehensive futures premium data for a base coin.
        
        Args:
            base_coin: Base coin symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            Dictionary with premium calculations and contract details
        """
        logger.info(f"Calculating comprehensive futures premium for {base_coin}")
        
        # Step 1: Discover all contracts
        contracts = await self.discover_futures_contracts(base_coin)
        
        if not contracts:
            logger.warning(f"No contracts found for {base_coin}")
            return {}
        
        # Step 2: Categorize contracts
        perpetual_contracts = []
        quarterly_contracts = []
        spot_contracts = []
        
        for contract in contracts:
            contract_type = contract.get('contractType', '')
            symbol = contract.get('symbol', '')
            
            if contract_type == 'LinearPerpetual':
                perpetual_contracts.append(contract)
            elif contract_type in ['LinearFutures', 'InverseFutures']:
                # Check if it has a delivery date (quarterly)
                delivery_time = contract.get('deliveryTime', '0')
                if delivery_time != '0':
                    quarterly_contracts.append(contract)
            elif 'USDT' in symbol and not ':' in symbol:
                spot_contracts.append(contract)
        
        logger.info(f"Found {len(perpetual_contracts)} perpetual, {len(quarterly_contracts)} quarterly, {len(spot_contracts)} spot contracts")
        
        # Step 3: Get ticker data for all contracts
        all_contracts = perpetual_contracts + quarterly_contracts + spot_contracts
        tickers = await self.get_tickers_for_contracts(all_contracts)
        
        # Step 4: Calculate premiums
        premium_data = {
            'base_coin': base_coin,
            'timestamp': int(datetime.now().timestamp() * 1000),
            'perpetual_premium': None,
            'quarterly_premiums': [],
            'mark_price': None,
            'index_price': None,
            'spot_price': None,
            'contracts_found': len(all_contracts),
            'data_quality': 'high' if len(tickers) > 0 else 'low'
        }
        
        # Get perpetual data
        perp_symbol = f"{base_coin}USDT"
        if perp_symbol in tickers:
            perp_ticker = tickers[perp_symbol]
            mark_price = float(perp_ticker.get('markPrice', 0))
            index_price = float(perp_ticker.get('indexPrice', 0))
            
            premium_data['mark_price'] = mark_price
            premium_data['index_price'] = index_price
            
            if mark_price > 0 and index_price > 0:
                perp_premium = ((mark_price - index_price) / index_price) * 100
                premium_data['perpetual_premium'] = {
                    'value': round(perp_premium, 4),
                    'percentage': f"{perp_premium:.4f}%",
                    'type': 'Contango' if perp_premium > 0 else 'Backwardation',
                    'funding_rate': perp_ticker.get('fundingRate', 'N/A')
                }
        
        # Calculate quarterly premiums
        for contract in quarterly_contracts:
            symbol = contract['symbol']
            if symbol in tickers:
                ticker = tickers[symbol]
                futures_price = float(ticker.get('lastPrice', 0))
                
                if futures_price > 0 and premium_data['index_price'] and premium_data['index_price'] > 0:
                    quarterly_premium = ((futures_price - premium_data['index_price']) / premium_data['index_price']) * 100
                    
                    # Calculate annualized basis
                    delivery_time = int(contract.get('deliveryTime', 0))
                    if delivery_time > 0:
                        delivery_date = datetime.fromtimestamp(delivery_time / 1000)
                        days_to_expiry = (delivery_date - datetime.now()).days
                        months_to_expiry = max(1, days_to_expiry / 30.44)  # Average days per month
                        annualized_basis = quarterly_premium * (12 / months_to_expiry)
                    else:
                        annualized_basis = quarterly_premium
                    
                    premium_data['quarterly_premiums'].append({
                        'symbol': symbol,
                        'contract_type': contract.get('contractType'),
                        'delivery_date': delivery_date.strftime('%Y-%m-%d') if delivery_time > 0 else 'N/A',
                        'days_to_expiry': days_to_expiry if delivery_time > 0 else 0,
                        'futures_price': futures_price,
                        'premium': round(quarterly_premium, 4),
                        'annualized_basis': round(annualized_basis, 4),
                        'volume_24h': ticker.get('volume24h', 0)
                    })
        
        return premium_data


async def test_improved_api():
    """Test the improved API with major symbols that were missing data."""
    
    # Test symbols that were showing missing data in logs
    test_symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'AVAX']
    
    async with ImprovedFuturesPremiumAPI() as api:
        for symbol in test_symbols:
            logger.info(f"\n{'='*50}")
            logger.info(f"Testing improved API for {symbol}")
            logger.info(f"{'='*50}")
            
            premium_data = await api.calculate_futures_premium_comprehensive(symbol)
            
            if premium_data:
                logger.info(f"✅ {symbol} Premium Data Retrieved:")
                logger.info(f"   Mark Price: {premium_data.get('mark_price', 'N/A')}")
                logger.info(f"   Index Price: {premium_data.get('index_price', 'N/A')}")
                logger.info(f"   Data Quality: {premium_data.get('data_quality', 'unknown')}")
                
                if premium_data.get('perpetual_premium'):
                    perp = premium_data['perpetual_premium']
                    logger.info(f"   Perpetual Premium: {perp['percentage']} ({perp['type']})")
                    logger.info(f"   Funding Rate: {perp['funding_rate']}")
                
                if premium_data.get('quarterly_premiums'):
                    logger.info(f"   Quarterly Contracts Found: {len(premium_data['quarterly_premiums'])}")
                    for q in premium_data['quarterly_premiums']:
                        logger.info(f"      {q['symbol']}: {q['premium']:.4f}% (expires: {q['delivery_date']})")
                else:
                    logger.info(f"   No quarterly contracts found")
                    
                logger.info(f"   Total Contracts: {premium_data.get('contracts_found', 0)}")
            else:
                logger.error(f"❌ Failed to retrieve data for {symbol}")


if __name__ == "__main__":
    asyncio.run(test_improved_api()) 
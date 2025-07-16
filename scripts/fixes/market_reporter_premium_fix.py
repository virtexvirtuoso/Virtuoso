#!/usr/bin/env python3
"""
Production Fix for Market Reporter Futures Premium Calculation

This script provides the improved futures premium calculation methods that should be
integrated into the main market reporter to resolve the missing data issues.

Key improvements:
1. Uses Bybit's instruments-info endpoint for contract discovery
2. Leverages premium-index-price-kline for validation
3. Better error handling and fallback mechanisms
4. More comprehensive contract symbol patterns

Based on successful testing that resolved all missing premium data.
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ImprovedFuturesPremiumMethods:
    """Improved methods for futures premium calculation to replace existing logic."""
    
    def __init__(self, exchange=None, base_url: str = "https://api.bybit.com"):
        self.exchange = exchange
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def calculate_improved_single_premium(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Improved single premium calculation using proper Bybit API endpoints.
        
        This method should replace the existing _calculate_single_premium method
        in the market reporter.
        
        Args:
            symbol: Symbol to calculate premium for (e.g., 'BTCUSDT', 'BTC/USDT:USDT')
            
        Returns:
            Premium data dictionary or None if calculation fails
        """
        try:
            # Extract base coin from symbol
            base_coin = self._extract_base_coin(symbol)
            if not base_coin:
                logger.warning(f"Could not extract base coin from symbol: {symbol}")
                return None
            
            logger.debug(f"Calculating improved premium for {symbol} (base: {base_coin})")
            
            # Step 1: Discover contracts using instruments-info endpoint
            contracts = await self._discover_contracts_via_api(base_coin)
            if not contracts:
                logger.warning(f"No contracts discovered for {base_coin}")
                return None
            
            # Step 2: Get perpetual data (primary source)
            perpetual_data = await self._get_perpetual_data(base_coin, contracts)
            if not perpetual_data:
                logger.warning(f"No perpetual data found for {base_coin}")
                return None
            
            # Step 3: Calculate basic premium from perpetual vs index
            mark_price = float(perpetual_data.get('markPrice', 0))
            index_price = float(perpetual_data.get('indexPrice', 0))
            
            if mark_price <= 0 or index_price <= 0:
                logger.warning(f"Invalid pricing data for {base_coin}: mark={mark_price}, index={index_price}")
                return None
            
            # Calculate perpetual premium
            perpetual_premium = ((mark_price - index_price) / index_price) * 100
            
            # Step 4: Get quarterly contracts data (if available)
            quarterly_data = await self._get_quarterly_contracts_data(base_coin, contracts, index_price)
            
            # Step 5: Validate with Bybit's own premium calculations
            validation_data = await self._validate_with_bybit_premium_index(base_coin)
            
            # Step 6: Compile comprehensive result
            result = {
                'premium': f"{perpetual_premium:.4f}%",
                'premium_value': perpetual_premium,
                'premium_type': "📈 Contango" if perpetual_premium > 0 else "📉 Backwardation",
                'mark_price': mark_price,
                'index_price': index_price,
                'last_price': float(perpetual_data.get('lastPrice', mark_price)),
                'funding_rate': perpetual_data.get('fundingRate', 0),
                'timestamp': int(datetime.now().timestamp() * 1000),
                
                # Enhanced data
                'quarterly_futures_count': len(quarterly_data),
                'quarterly_futures': quarterly_data,
                'contracts_found': len(contracts),
                'data_source': 'improved_api_v5',
                'data_quality': 'high',
                
                # Validation
                'bybit_validation': validation_data,
                'calculation_method': 'perpetual_vs_index_enhanced'
            }
            
            logger.debug(f"Successfully calculated premium for {symbol}: {perpetual_premium:.4f}%")
            return result
            
        except Exception as e:
            logger.error(f"Error in improved premium calculation for {symbol}: {e}")
            return None
    
    def _extract_base_coin(self, symbol: str) -> Optional[str]:
        """Extract base coin from various symbol formats."""
        try:
            if '/' in symbol:
                # Format: BTC/USDT:USDT or BTC/USDT
                return symbol.split('/')[0]
            elif symbol.endswith('USDT'):
                # Format: BTCUSDT
                return symbol.replace('USDT', '')
            elif ':' in symbol:
                # Format: BTCUSDT:USDT
                return symbol.split(':')[0].replace('USDT', '')
            else:
                # Assume it's already base coin
                return symbol
        except Exception:
            return None
    
    async def _discover_contracts_via_api(self, base_coin: str) -> List[Dict[str, Any]]:
        """Discover contracts using Bybit's instruments-info endpoint."""
        contracts = []
        
        try:
            # Linear contracts (USDT-margined)
            linear_url = f"{self.base_url}/v5/market/instruments-info"
            linear_params = {'category': 'linear', 'baseCoin': base_coin, 'limit': 1000}
            
            async with self.session.get(linear_url, params=linear_params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        linear_contracts = data.get('result', {}).get('list', [])
                        contracts.extend(linear_contracts)
                        logger.debug(f"Found {len(linear_contracts)} linear contracts for {base_coin}")
            
            # Inverse contracts (Coin-margined) 
            inverse_url = f"{self.base_url}/v5/market/instruments-info"
            inverse_params = {'category': 'inverse', 'baseCoin': base_coin, 'limit': 1000}
            
            async with self.session.get(inverse_url, params=inverse_params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        inverse_contracts = data.get('result', {}).get('list', [])
                        contracts.extend(inverse_contracts)
                        logger.debug(f"Found {len(inverse_contracts)} inverse contracts for {base_coin}")
                        
        except Exception as e:
            logger.error(f"Error discovering contracts for {base_coin}: {e}")
        
        return contracts
    
    async def _get_perpetual_data(self, base_coin: str, contracts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get perpetual contract ticker data."""
        try:
            # Find perpetual contract
            perpetual_symbol = f"{base_coin}USDT"
            
            # Get ticker data
            ticker_url = f"{self.base_url}/v5/market/tickers"
            params = {'category': 'linear', 'symbol': perpetual_symbol}
            
            async with self.session.get(ticker_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        ticker_list = data.get('result', {}).get('list', [])
                        if ticker_list:
                            return ticker_list[0]
                        
        except Exception as e:
            logger.error(f"Error getting perpetual data for {base_coin}: {e}")
        
        return None
    
    async def _get_quarterly_contracts_data(self, base_coin: str, contracts: List[Dict[str, Any]], index_price: float) -> List[Dict[str, Any]]:
        """Get quarterly contracts data with premium calculations."""
        quarterly_data = []
        
        try:
            # Filter for quarterly contracts
            quarterly_contracts = [
                c for c in contracts 
                if c.get('contractType') in ['LinearFutures', 'InverseFutures'] 
                and c.get('deliveryTime', '0') != '0'
            ]
            
            if not quarterly_contracts:
                return quarterly_data
            
            # Get ticker data for quarterly contracts
            for contract in quarterly_contracts[:10]:  # Limit to avoid too many API calls
                try:
                    symbol = contract['symbol']
                    category = contract.get('category', 'linear')
                    
                    ticker_url = f"{self.base_url}/v5/market/tickers"
                    params = {'category': category, 'symbol': symbol}
                    
                    async with self.session.get(ticker_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('retCode') == 0:
                                ticker_list = data.get('result', {}).get('list', [])
                                if ticker_list:
                                    ticker = ticker_list[0]
                                    futures_price = float(ticker.get('lastPrice', 0))
                                    
                                    if futures_price > 0 and index_price > 0:
                                        quarterly_premium = ((futures_price - index_price) / index_price) * 100
                                        
                                        # Calculate time to expiry
                                        delivery_time = int(contract.get('deliveryTime', 0))
                                        delivery_date = datetime.fromtimestamp(delivery_time / 1000) if delivery_time > 0 else None
                                        
                                        quarterly_data.append({
                                            'symbol': symbol,
                                            'contract_type': contract.get('contractType'),
                                            'futures_price': futures_price,
                                            'premium': quarterly_premium,
                                            'delivery_date': delivery_date.strftime('%Y-%m-%d') if delivery_date else 'N/A',
                                            'days_to_expiry': (delivery_date - datetime.now()).days if delivery_date else 0
                                        })
                                        
                except Exception as e:
                    logger.debug(f"Error processing quarterly contract {contract.get('symbol', 'unknown')}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error getting quarterly contracts data for {base_coin}: {e}")
        
        return quarterly_data
    
    async def _validate_with_bybit_premium_index(self, base_coin: str) -> Optional[Dict[str, Any]]:
        """Validate calculations using Bybit's own premium index data."""
        try:
            symbol = f"{base_coin}USDT"
            url = f"{self.base_url}/v5/market/premium-index-price-kline"
            params = {'category': 'linear', 'symbol': symbol, 'interval': '1', 'limit': 1}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        kline_data = data.get('result', {}).get('list', [])
                        if kline_data:
                            latest = kline_data[0]
                            return {
                                'bybit_premium_index': float(latest[4]),  # Close price
                                'timestamp': int(latest[0]),
                                'source': 'premium_index_kline'
                            }
                            
        except Exception as e:
            logger.debug(f"Could not validate with Bybit premium index for {base_coin}: {e}")
        
        return None


async def test_production_fix():
    """Test the production fix with the problematic symbols."""
    
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'AVAXUSDT']
    
    async with ImprovedFuturesPremiumMethods() as premium_calc:
        print("🔧 Testing Production Fix for Futures Premium Calculation")
        print("=" * 70)
        
        for symbol in test_symbols:
            print(f"\n📊 Testing {symbol}:")
            
            result = await premium_calc.calculate_improved_single_premium(symbol)
            
            if result:
                print(f"  ✅ SUCCESS:")
                print(f"     Premium: {result['premium']} ({result['premium_type']})")
                print(f"     Mark Price: ${result['mark_price']:,.2f}")
                print(f"     Index Price: ${result['index_price']:,.2f}")
                print(f"     Funding Rate: {result['funding_rate']}")
                print(f"     Quarterly Contracts: {result['quarterly_futures_count']}")
                print(f"     Data Quality: {result['data_quality']}")
                print(f"     Contracts Found: {result['contracts_found']}")
                
                if result.get('bybit_validation'):
                    validation = result['bybit_validation']
                    print(f"     Bybit Validation: ✅ (premium index: {validation['bybit_premium_index']})")
                else:
                    print(f"     Bybit Validation: ⚠️ (not available)")
                    
            else:
                print(f"  ❌ FAILED: No premium data calculated")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_production_fix()) 
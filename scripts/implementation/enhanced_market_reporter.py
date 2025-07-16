#!/usr/bin/env python3
"""
Enhanced Market Reporter Implementation

This script shows how to integrate the improved futures premium calculation
into the existing market reporter system. It includes:

1. Backward-compatible implementation
2. Enhanced validation features
3. Fallback mechanisms 
4. Performance monitoring
5. Step-by-step integration guide
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from timedelta import timedelta
import time

class EnhancedFuturesPremiumMixin:
    """
    Mixin class that can be added to the existing MarketReporter
    to provide enhanced futures premium calculation capabilities.
    """
    
    def __init__(self):
        """Initialize enhanced premium calculation capabilities."""
        self._aiohttp_session = None
        self._premium_api_base_url = "https://api.bybit.com"  # Configurable
        self._enable_enhanced_premium = True  # Feature flag
        self._enable_premium_validation = True  # Validation flag
        self._premium_calculation_stats = {
            'improved_success': 0,
            'improved_failures': 0,
            'fallback_usage': 0,
            'validation_matches': 0,
            'validation_mismatches': 0
        }
    
    async def _get_aiohttp_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session for direct API calls."""
        if self._aiohttp_session is None:
            self._aiohttp_session = aiohttp.ClientSession()
        return self._aiohttp_session
    
    async def _close_aiohttp_session(self):
        """Close aiohttp session on cleanup."""
        if self._aiohttp_session:
            await self._aiohttp_session.close()
            self._aiohttp_session = None
    
    async def _calculate_single_premium_enhanced(self, symbol: str, all_markets: Dict = None) -> Optional[Dict[str, Any]]:
        """
        Enhanced single premium calculation that replaces the existing method.
        
        This method provides:
        1. Improved contract discovery via instruments-info API
        2. Enhanced data validation via premium-index-price-kline
        3. Better error handling and fallback mechanisms
        4. Performance monitoring and statistics
        
        Args:
            symbol: Symbol to calculate premium for
            all_markets: Market data (for backward compatibility)
            
        Returns:
            Premium data dictionary or None if calculation fails
        """
        if not self._enable_enhanced_premium:
            # Feature flag disabled, use original method
            return await self._calculate_single_premium_original(symbol, all_markets)
        
        start_time = time.time()
        
        try:
            # Extract base coin from symbol
            base_coin = self._extract_base_coin_enhanced(symbol)
            if not base_coin:
                self.logger.warning(f"Could not extract base coin from symbol: {symbol}")
                self._premium_calculation_stats['improved_failures'] += 1
                return await self._fallback_to_original_method(symbol, all_markets)
            
            self.logger.debug(f"Enhanced premium calculation for {symbol} (base: {base_coin})")
            
            # Step 1: Discover contracts via instruments-info API
            contracts = await self._discover_contracts_enhanced(base_coin)
            if not contracts:
                self.logger.warning(f"No contracts discovered via enhanced method for {base_coin}")
                self._premium_calculation_stats['improved_failures'] += 1
                return await self._fallback_to_original_method(symbol, all_markets)
            
            # Step 2: Get perpetual data using enhanced method
            perpetual_data = await self._get_perpetual_data_enhanced(base_coin)
            if not perpetual_data:
                self.logger.warning(f"No perpetual data found via enhanced method for {base_coin}")
                self._premium_calculation_stats['improved_failures'] += 1
                return await self._fallback_to_original_method(symbol, all_markets)
            
            # Step 3: Extract pricing data
            mark_price = float(perpetual_data.get('markPrice', 0))
            index_price = float(perpetual_data.get('indexPrice', 0))
            
            if mark_price <= 0 or index_price <= 0:
                self.logger.warning(f"Invalid pricing data for {base_coin}: mark={mark_price}, index={index_price}")
                self._premium_calculation_stats['improved_failures'] += 1
                return await self._fallback_to_original_method(symbol, all_markets)
            
            # Step 4: Calculate perpetual premium
            perpetual_premium = ((mark_price - index_price) / index_price) * 100
            
            # Step 5: Get quarterly contracts data
            quarterly_data = await self._get_quarterly_contracts_enhanced(base_coin, contracts, index_price)
            
            # Step 6: Validate with Bybit's premium index (if enabled)
            validation_data = None
            if self._enable_premium_validation:
                validation_data = await self._validate_with_bybit_premium_index(base_coin)
                if validation_data:
                    # Check if our calculation matches Bybit's (within 5 basis points)
                    bybit_premium = validation_data.get('bybit_premium_index', 0) * 100  # Convert to percentage
                    if abs(perpetual_premium - bybit_premium) < 0.05:  # 5 basis points tolerance
                        self._premium_calculation_stats['validation_matches'] += 1
                    else:
                        self._premium_calculation_stats['validation_mismatches'] += 1
                        self.logger.warning(f"Premium validation mismatch for {base_coin}: "
                                          f"calculated={perpetual_premium:.4f}%, bybit={bybit_premium:.4f}%")
            
            # Step 7: Compile enhanced result
            result = {
                # Standard fields (backward compatibility)
                'premium': f"{perpetual_premium:.4f}%",
                'premium_value': perpetual_premium,
                'premium_type': "📈 Contango" if perpetual_premium > 0 else "📉 Backwardation",
                'mark_price': mark_price,
                'index_price': index_price,
                'last_price': float(perpetual_data.get('lastPrice', mark_price)),
                'funding_rate': perpetual_data.get('fundingRate', 0),
                'timestamp': int(datetime.now().timestamp() * 1000),
                
                # Enhanced fields
                'quarterly_futures_count': len(quarterly_data),
                'quarterly_futures': quarterly_data,
                'contracts_found': len(contracts),
                'data_source': 'enhanced_api_v5',
                'data_quality': 'high',
                'calculation_method': 'enhanced_perpetual_vs_index',
                'processing_time_ms': round((time.time() - start_time) * 1000, 2),
                
                # Validation data (if available)
                'bybit_validation': validation_data,
                'validation_status': 'validated' if validation_data else 'not_validated',
                
                # Legacy compatibility fields
                'weekly_futures_count': 0,  # Not used in enhanced method
                'futures_price': quarterly_data[0]['futures_price'] if quarterly_data else 0,
                'futures_basis': f"{quarterly_data[0]['premium']:.4f}%" if quarterly_data else "0.00%",
                'futures_contracts': quarterly_data  # For backward compatibility
            }
            
            self._premium_calculation_stats['improved_success'] += 1
            self.logger.debug(f"Enhanced premium calculation successful for {symbol}: {perpetual_premium:.4f}%")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in enhanced premium calculation for {symbol}: {e}")
            self._premium_calculation_stats['improved_failures'] += 1
            return await self._fallback_to_original_method(symbol, all_markets)
    
    def _extract_base_coin_enhanced(self, symbol: str) -> Optional[str]:
        """Enhanced base coin extraction with better pattern matching."""
        try:
            if '/' in symbol:
                # Format: BTC/USDT:USDT or BTC/USDT
                return symbol.split('/')[0].upper()
            elif symbol.endswith('USDT'):
                # Format: BTCUSDT
                return symbol.replace('USDT', '').upper()
            elif ':' in symbol:
                # Format: BTCUSDT:USDT
                return symbol.split(':')[0].replace('USDT', '').upper()
            else:
                # Assume it's already base coin
                return symbol.upper()
        except Exception:
            return None
    
    async def _discover_contracts_enhanced(self, base_coin: str) -> List[Dict[str, Any]]:
        """Discover contracts using Bybit's instruments-info endpoint."""
        contracts = []
        session = await self._get_aiohttp_session()
        
        try:
            # Linear contracts (USDT-margined)
            linear_url = f"{self._premium_api_base_url}/v5/market/instruments-info"
            linear_params = {'category': 'linear', 'baseCoin': base_coin, 'limit': 1000}
            
            async with session.get(linear_url, params=linear_params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        linear_contracts = data.get('result', {}).get('list', [])
                        contracts.extend(linear_contracts)
                        self.logger.debug(f"Enhanced discovery: Found {len(linear_contracts)} linear contracts for {base_coin}")
            
            # Inverse contracts (Coin-margined)
            inverse_params = {'category': 'inverse', 'baseCoin': base_coin, 'limit': 1000}
            
            async with session.get(linear_url, params=inverse_params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        inverse_contracts = data.get('result', {}).get('list', [])
                        contracts.extend(inverse_contracts)
                        self.logger.debug(f"Enhanced discovery: Found {len(inverse_contracts)} inverse contracts for {base_coin}")
                        
        except Exception as e:
            self.logger.error(f"Error in enhanced contract discovery for {base_coin}: {e}")
        
        return contracts
    
    async def _get_perpetual_data_enhanced(self, base_coin: str) -> Optional[Dict[str, Any]]:
        """Get perpetual contract data using enhanced API method."""
        session = await self._get_aiohttp_session()
        
        try:
            perpetual_symbol = f"{base_coin}USDT"
            ticker_url = f"{self._premium_api_base_url}/v5/market/tickers"
            params = {'category': 'linear', 'symbol': perpetual_symbol}
            
            async with session.get(ticker_url, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        ticker_list = data.get('result', {}).get('list', [])
                        if ticker_list:
                            return ticker_list[0]
                        
        except Exception as e:
            self.logger.error(f"Error getting enhanced perpetual data for {base_coin}: {e}")
        
        return None
    
    async def _get_quarterly_contracts_enhanced(self, base_coin: str, contracts: List[Dict[str, Any]], index_price: float) -> List[Dict[str, Any]]:
        """Get quarterly contracts data using enhanced discovery."""
        quarterly_data = []
        session = await self._get_aiohttp_session()
        
        try:
            # Filter for quarterly contracts
            quarterly_contracts = [
                c for c in contracts 
                if c.get('contractType') in ['LinearFutures', 'InverseFutures'] 
                and c.get('deliveryTime', '0') != '0'
            ]
            
            if not quarterly_contracts:
                return quarterly_data
            
            # Process up to 10 quarterly contracts
            for contract in quarterly_contracts[:10]:
                try:
                    symbol = contract['symbol']
                    category = contract.get('category', 'linear')
                    
                    ticker_url = f"{self._premium_api_base_url}/v5/market/tickers"
                    params = {'category': category, 'symbol': symbol}
                    
                    async with session.get(ticker_url, params=params, timeout=3) as response:
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
                                            'days_to_expiry': (delivery_date - datetime.now()).days if delivery_date else 0,
                                            'category': category,
                                            'basis': f"{quarterly_premium:.4f}%",  # For legacy compatibility
                                            'price': futures_price,  # For legacy compatibility
                                            'month': delivery_date.strftime('%B') if delivery_date else 'Unknown'
                                        })
                                        
                except Exception as e:
                    self.logger.debug(f"Error processing enhanced quarterly contract {contract.get('symbol', 'unknown')}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error getting enhanced quarterly contracts data for {base_coin}: {e}")
        
        return quarterly_data
    
    async def _validate_with_bybit_premium_index(self, base_coin: str) -> Optional[Dict[str, Any]]:
        """Validate calculations using Bybit's own premium index data."""
        session = await self._get_aiohttp_session()
        
        try:
            symbol = f"{base_coin}USDT"
            url = f"{self._premium_api_base_url}/v5/market/premium-index-price-kline"
            params = {'category': 'linear', 'symbol': symbol, 'interval': '1', 'limit': 1}
            
            async with session.get(url, params=params, timeout=3) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        kline_data = data.get('result', {}).get('list', [])
                        if kline_data:
                            latest = kline_data[0]
                            return {
                                'bybit_premium_index': float(latest[4]),  # Close price
                                'timestamp': int(latest[0]),
                                'source': 'premium_index_kline',
                                'validation_method': 'enhanced'
                            }
                            
        except Exception as e:
            self.logger.debug(f"Could not validate with Bybit premium index for {base_coin}: {e}")
        
        return None
    
    async def _fallback_to_original_method(self, symbol: str, all_markets: Dict = None) -> Optional[Dict[str, Any]]:
        """Fallback to the original _calculate_single_premium method."""
        self._premium_calculation_stats['fallback_usage'] += 1
        self.logger.info(f"Falling back to original premium calculation method for {symbol}")
        
        try:
            # Call the original method (renamed to avoid conflict)
            return await self._calculate_single_premium_original(symbol, all_markets)
        except Exception as e:
            self.logger.error(f"Error in fallback premium calculation for {symbol}: {e}")
            return None
    
    def get_premium_calculation_stats(self) -> Dict[str, Any]:
        """Get statistics about premium calculation performance."""
        total_attempts = (self._premium_calculation_stats['improved_success'] + 
                         self._premium_calculation_stats['improved_failures'])
        
        return {
            'enhanced_method': {
                'success_count': self._premium_calculation_stats['improved_success'],
                'failure_count': self._premium_calculation_stats['improved_failures'],
                'success_rate': (self._premium_calculation_stats['improved_success'] / max(total_attempts, 1)) * 100,
                'total_attempts': total_attempts
            },
            'fallback_usage': {
                'count': self._premium_calculation_stats['fallback_usage'],
                'percentage': (self._premium_calculation_stats['fallback_usage'] / max(total_attempts, 1)) * 100
            },
            'validation': {
                'matches': self._premium_calculation_stats['validation_matches'],
                'mismatches': self._premium_calculation_stats['validation_mismatches'],
                'match_rate': (self._premium_calculation_stats['validation_matches'] / 
                              max(self._premium_calculation_stats['validation_matches'] + 
                                  self._premium_calculation_stats['validation_mismatches'], 1)) * 100
            }
        }
    
    async def _log_premium_performance_metrics(self):
        """Log performance metrics for premium calculations."""
        stats = self.get_premium_calculation_stats()
        
        self.logger.info("=== Enhanced Premium Calculation Performance ===")
        self.logger.info(f"Enhanced method success rate: {stats['enhanced_method']['success_rate']:.1f}%")
        self.logger.info(f"Fallback usage: {stats['fallback_usage']['percentage']:.1f}%")
        self.logger.info(f"Validation match rate: {stats['validation']['match_rate']:.1f}%")
        self.logger.info(f"Total attempts: {stats['enhanced_method']['total_attempts']}")


# ==============================================
# IMPLEMENTATION INTEGRATION INSTRUCTIONS
# ==============================================

INTEGRATION_INSTRUCTIONS = """
# Enhanced Futures Premium Integration Guide

## Step 1: Backup Current Implementation
1. Create backup of current market_reporter.py:
   ```bash
   cp src/monitoring/market_reporter.py src/monitoring/market_reporter.py.backup
   ```

## Step 2: Add Enhanced Capabilities to MarketReporter Class

### 2.1: Add Mixin to Class Definition
```python
# In src/monitoring/market_reporter.py
class MarketReporter(EnhancedFuturesPremiumMixin):
    def __init__(self, exchange: Any = None, logger: Optional[logging.Logger] = None, 
                 top_symbols_manager: Any = None, alert_manager: Any = None):
        # Existing initialization
        super().__init__(exchange, logger, top_symbols_manager, alert_manager)
        
        # Add enhanced premium initialization
        EnhancedFuturesPremiumMixin.__init__(self)
```

### 2.2: Rename Existing Method
```python
# Rename current method to preserve as fallback
async def _calculate_single_premium_original(self, symbol: str, all_markets: Dict) -> Optional[Dict[str, Any]]:
    # [Move all existing _calculate_single_premium code here]
```

### 2.3: Replace Main Method
```python
async def _calculate_single_premium(self, symbol: str, all_markets: Dict) -> Optional[Dict[str, Any]]:
    \"\"\"Calculate futures premium with enhanced capabilities and fallback.\"\"\"
    return await self._calculate_single_premium_enhanced(symbol, all_markets)
```

## Step 3: Add Required Imports
```python
import aiohttp
from timedelta import timedelta
```

## Step 4: Add Configuration Options
```python
# In config files or environment variables
ENABLE_ENHANCED_PREMIUM_CALCULATION = True
ENABLE_PREMIUM_VALIDATION = True
PREMIUM_API_BASE_URL = "https://api.bybit.com"
```

## Step 5: Add Cleanup in Destructor
```python
async def __del__(self):
    await self._close_aiohttp_session()
```

## Step 6: Add Performance Monitoring
```python
# Add to existing _log_performance_metrics method
async def _log_performance_metrics(self):
    # [existing code]
    await self._log_premium_performance_metrics()
```

## Step 7: Testing Deployment Strategy

### Phase 1: Canary Testing (Feature Flag Off)
- Deploy with enhanced_premium = False
- Monitor system stability
- Verify no regressions

### Phase 2: A/B Testing (Gradual Rollout)
- Enable enhanced_premium = True for subset of symbols
- Compare results between old and new methods
- Monitor success rates and validation matches

### Phase 3: Full Deployment
- Enable enhanced_premium = True for all symbols
- Monitor performance metrics
- Keep original method as fallback

## Step 8: Monitoring & Alerts

### Success Metrics to Track:
- Enhanced method success rate (target: >95%)
- Fallback usage rate (target: <5%)
- Validation match rate (target: >90%)
- Processing time improvements

### Alert Thresholds:
- Enhanced method success rate < 80%
- Validation mismatch rate > 20%
- Fallback usage > 25%

## Step 9: Rollback Plan
If issues occur:
1. Set enhanced_premium = False (immediate fallback)
2. Restore from backup if needed
3. Investigate issues in isolated environment

This approach ensures zero-downtime deployment with full rollback capabilities.
"""

def print_integration_guide():
    """Print the integration guide for implementing enhanced premium calculation."""
    print(INTEGRATION_INSTRUCTIONS)

if __name__ == "__main__":
    print_integration_guide() 
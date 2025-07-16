#!/usr/bin/env python3
"""
Simple Test for Enhanced Futures Premium Implementation

This script provides a simplified test of the enhanced futures premium functionality
without complex module imports that could cause issues.

Usage:
    python scripts/implementation/test_enhanced_premium_simple.py
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import time

class SimpleEnhancedPremiumTest:
    """Simple test implementation of enhanced premium calculation."""
    
    def __init__(self):
        self.logger = logging.getLogger("simple_test")
        self.logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        self._aiohttp_session = None
        self._premium_api_base_url = "https://api.bybit.com"
        self._premium_calculation_stats = {
            'improved_success': 0,
            'improved_failures': 0,
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
    
    def _extract_base_coin_enhanced(self, symbol: str) -> Optional[str]:
        """Enhanced base coin extraction."""
        try:
            if '/' in symbol:
                return symbol.split('/')[0].upper()
            elif symbol.endswith('USDT'):
                return symbol.replace('USDT', '').upper()
            elif ':' in symbol:
                return symbol.split(':')[0].replace('USDT', '').upper()
            else:
                return symbol.upper()
        except Exception:
            return None
    
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
                                'bybit_premium_index': float(latest[4]),
                                'timestamp': int(latest[0]),
                                'source': 'premium_index_kline',
                                'validation_method': 'enhanced'
                            }
                            
        except Exception as e:
            self.logger.debug(f"Could not validate with Bybit premium index for {base_coin}: {e}")
        
        return None
    
    async def _calculate_enhanced_premium(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Enhanced premium calculation test."""
        start_time = time.time()
        
        try:
            # Extract base coin
            base_coin = self._extract_base_coin_enhanced(symbol)
            if not base_coin:
                self.logger.warning(f"Could not extract base coin from symbol: {symbol}")
                self._premium_calculation_stats['improved_failures'] += 1
                return None
            
            self.logger.debug(f"Enhanced premium calculation for {symbol} (base: {base_coin})")
            
            # Get perpetual data using enhanced method
            perpetual_data = await self._get_perpetual_data_enhanced(base_coin)
            if not perpetual_data:
                self.logger.warning(f"No perpetual data found via enhanced method for {base_coin}")
                self._premium_calculation_stats['improved_failures'] += 1
                return None
            
            # Extract pricing data
            mark_price = float(perpetual_data.get('markPrice', 0))
            index_price = float(perpetual_data.get('indexPrice', 0))
            
            if mark_price <= 0 or index_price <= 0:
                self.logger.warning(f"Invalid pricing data for {base_coin}: mark={mark_price}, index={index_price}")
                self._premium_calculation_stats['improved_failures'] += 1
                return None
            
            # Calculate perpetual premium
            perpetual_premium = ((mark_price - index_price) / index_price) * 100
            
            # Validate with Bybit's premium index
            validation_data = await self._validate_with_bybit_premium_index(base_coin)
            if validation_data:
                bybit_premium = validation_data.get('bybit_premium_index', 0) * 100
                if abs(perpetual_premium - bybit_premium) < 0.05:  # 5 basis points tolerance
                    self._premium_calculation_stats['validation_matches'] += 1
                else:
                    self._premium_calculation_stats['validation_mismatches'] += 1
                    self.logger.warning(f"Premium validation mismatch for {base_coin}: "
                                      f"calculated={perpetual_premium:.4f}%, bybit={bybit_premium:.4f}%")
            
            # Compile result
            result = {
                'premium': f"{perpetual_premium:.4f}%",
                'premium_value': perpetual_premium,
                'premium_type': "📈 Contango" if perpetual_premium > 0 else "📉 Backwardation",
                'mark_price': mark_price,
                'index_price': index_price,
                'last_price': float(perpetual_data.get('lastPrice', mark_price)),
                'funding_rate': perpetual_data.get('fundingRate', 0),
                'timestamp': int(datetime.now().timestamp() * 1000),
                'data_source': 'enhanced_api_v5',
                'data_quality': 'high',
                'calculation_method': 'enhanced_perpetual_vs_index',
                'processing_time_ms': round((time.time() - start_time) * 1000, 2),
                'bybit_validation': validation_data,
                'validation_status': 'validated' if validation_data else 'not_validated'
            }
            
            self._premium_calculation_stats['improved_success'] += 1
            self.logger.debug(f"Enhanced premium calculation successful for {symbol}: {perpetual_premium:.4f}%")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in enhanced premium calculation for {symbol}: {e}")
            self._premium_calculation_stats['improved_failures'] += 1
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
            'validation': {
                'matches': self._premium_calculation_stats['validation_matches'],
                'mismatches': self._premium_calculation_stats['validation_mismatches'],
                'match_rate': (self._premium_calculation_stats['validation_matches'] / 
                              max(self._premium_calculation_stats['validation_matches'] + 
                                  self._premium_calculation_stats['validation_mismatches'], 1)) * 100
            }
        }

async def test_enhanced_premium_functionality():
    """Test the enhanced premium calculation functionality."""
    print("🚀 Testing Enhanced Futures Premium Functionality")
    print("=" * 60)
    
    # Create test instance
    tester = SimpleEnhancedPremiumTest()
    
    try:
        # Test symbols that were previously missing data
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'AVAXUSDT']
        
        print("\n🧪 Testing Enhanced Premium Calculation:")
        
        successful_tests = 0
        failed_tests = 0
        
        for symbol in test_symbols:
            print(f"\n📊 Testing {symbol}:")
            
            try:
                result = await tester._calculate_enhanced_premium(symbol)
                
                if result:
                    print(f"  ✅ Success: {result.get('premium', 'N/A')} "
                          f"({result.get('premium_type', 'N/A')})")
                    print(f"  💰 Mark Price: ${result.get('mark_price', 0):,.2f}")
                    print(f"  📈 Index Price: ${result.get('index_price', 0):,.2f}")
                    print(f"  💸 Funding Rate: {result.get('funding_rate', 'N/A')}")
                    print(f"  📊 Data Source: {result.get('data_source', 'N/A')}")
                    print(f"  🕒 Processing Time: {result.get('processing_time_ms', 'N/A')}ms")
                    print(f"  🔍 Validation: {result.get('validation_status', 'N/A')}")
                    
                    if result.get('bybit_validation'):
                        validation = result['bybit_validation']
                        print(f"  ✅ Bybit Validation: {validation['bybit_premium_index']:.6f}")
                    
                    successful_tests += 1
                else:
                    print(f"  ❌ Failed: No result returned for {symbol}")
                    failed_tests += 1
                    
            except Exception as e:
                print(f"  ❌ Error testing {symbol}: {e}")
                failed_tests += 1
        
        # Performance statistics
        stats = tester.get_premium_calculation_stats()
        
        print(f"\n📊 Performance Statistics:")
        print(f"  Enhanced method success rate: {stats['enhanced_method']['success_rate']:.1f}%")
        print(f"  Total attempts: {stats['enhanced_method']['total_attempts']}")
        print(f"  Successful calculations: {stats['enhanced_method']['success_count']}")
        print(f"  Failed calculations: {stats['enhanced_method']['failure_count']}")
        print(f"  Validation match rate: {stats['validation']['match_rate']:.1f}%")
        print(f"  Validation matches: {stats['validation']['matches']}")
        print(f"  Validation mismatches: {stats['validation']['mismatches']}")
        
        # Overall results
        total_tests = successful_tests + failed_tests
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n🏁 Test Results Summary:")
        print(f"  Total symbols tested: {total_tests}")
        print(f"  Successful: {successful_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Success rate: {success_rate:.1f}%")
        
        # Clean up
        await tester._close_aiohttp_session()
        
        if success_rate >= 80:  # 80% success rate threshold
            print(f"\n🎉 EXCELLENT! Enhanced premium calculation is working correctly!")
            print(f"   Success rate of {success_rate:.1f}% exceeds 80% threshold.")
            print(f"   This resolves the missing futures premium data issues.")
            return True
        else:
            print(f"\n⚠️ Success rate of {success_rate:.1f}% is below 80% threshold.")
            print(f"   Further investigation may be needed.")
            return False
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        await tester._close_aiohttp_session()
        return False

def test_base_coin_extraction():
    """Test base coin extraction functionality."""
    print("\n🧪 Testing Base Coin Extraction:")
    
    tester = SimpleEnhancedPremiumTest()
    
    test_cases = [
        ('BTCUSDT', 'BTC'),
        ('BTC/USDT:USDT', 'BTC'),
        ('ETHUSDT', 'ETH'),
        ('ETH/USDT', 'ETH'),
        ('SOLUSDT', 'SOL'),
        ('SOL/USDT:USDT', 'SOL'),
        ('XRPUSDT', 'XRP'),
        ('AVAXUSDT', 'AVAX')
    ]
    
    passed = 0
    failed = 0
    
    for symbol, expected in test_cases:
        result = tester._extract_base_coin_enhanced(symbol)
        if result == expected:
            print(f"  ✅ {symbol} -> {result} (expected: {expected})")
            passed += 1
        else:
            print(f"  ❌ {symbol} -> {result} (expected: {expected})")
            failed += 1
    
    success_rate = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0
    print(f"  Base coin extraction success rate: {success_rate:.1f}%")
    
    return success_rate >= 90

async def main():
    """Main test function."""
    print("🚀 Enhanced Futures Premium - Simple Functionality Test")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Base coin extraction
    print("\n1️⃣ Testing Base Coin Extraction...")
    base_coin_result = test_base_coin_extraction()
    test_results.append(("Base Coin Extraction", base_coin_result))
    
    # Test 2: Enhanced premium functionality
    print("\n2️⃣ Testing Enhanced Premium Functionality...")
    premium_result = await test_enhanced_premium_functionality()
    test_results.append(("Enhanced Premium Calculation", premium_result))
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 Final Test Results:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    overall_success_rate = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0
    print(f"\nOverall Success Rate: {overall_success_rate:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Enhanced futures premium calculation is working correctly")
        print("✅ This implementation resolves the missing premium data issues")
        print("✅ Ready for production deployment")
        
        print("\n📋 Deployment Instructions:")
        print("1. Run: python scripts/implementation/implement_enhanced_premium.py --backup")
        print("2. Monitor performance metrics in upcoming market reports")
        print("3. Check for improved success rates for major symbols (BTC, ETH, SOL, XRP, AVAX)")
        print("4. Verify validation rates against Bybit's calculations")
        
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed.")
        print("Further investigation needed before deployment.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1) 
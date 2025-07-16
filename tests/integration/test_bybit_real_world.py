#!/usr/bin/env python3
"""
Real-World Bybit Market Data Test

Validates that our KeyError fixes work correctly with actual API calls.
This test focuses on the specific scenarios that were causing issues.
"""

import asyncio
import sys
import os
import time
import json
import traceback
from typing import Dict, Any
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BybitRealWorldTester:
    """Test Bybit market data fetching in real-world conditions."""
    
    def __init__(self):
        self.test_symbols = ['BTCUSDT', 'ETHUSDT']  # Conservative symbol list
        self.exchange = None
        
    def initialize_exchange(self) -> bool:
        """Initialize Bybit exchange for testing."""
        try:
            from src.core.exchanges.bybit import BybitExchange
            
            # Use testnet for safe testing
            config = {
                'exchanges': {
                    'bybit': {
                        'rest_endpoint': 'https://api-testnet.bybit.com',
                        'websocket': {
                            'mainnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public/linear',
                            'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public/linear'
                        },
                        'api_key': 'test_key',
                        'api_secret': 'test_secret',
                        'sandbox': True,
                        'rate_limit': {
                            'requests_per_second': 1,  # Very conservative
                            'burst_limit': 3
                        }
                    }
                }
            }
            
            self.exchange = BybitExchange(config)
            self.exchange.logger = logger
            
            logger.info("✅ Bybit exchange initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Exchange initialization failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def test_ticker_fetching(self) -> Dict[str, Any]:
        """Test ticker fetching - the core functionality."""
        logger.info("🧪 Testing ticker data fetching...")
        
        results = {}
        
        for symbol in self.test_symbols:
            logger.info(f"  Fetching ticker for {symbol}...")
            
            try:
                start_time = time.time()
                
                # This should work without KeyErrors now
                ticker_data = await self.exchange.fetch_ticker(symbol)
                
                fetch_time = time.time() - start_time
                
                if ticker_data:
                    # Validate structure
                    has_price = any(key in ticker_data for key in ['lastPrice', 'last', 'price', 'close'])
                    has_volume = any(key in ticker_data for key in ['volume24h', 'volume', 'quoteVolume'])
                    
                    sample_data = {
                        'symbol': ticker_data.get('symbol'),
                        'price': (ticker_data.get('lastPrice') or 
                                ticker_data.get('last') or 
                                ticker_data.get('price') or 
                                ticker_data.get('close')),
                        'volume': (ticker_data.get('volume24h') or 
                                 ticker_data.get('volume') or 
                                 ticker_data.get('quoteVolume'))
                    }
                    
                    results[symbol] = {
                        'status': 'success',
                        'fetch_time': fetch_time,
                        'has_price': has_price,
                        'has_volume': has_volume,
                        'sample_data': sample_data,
                        'no_keyerror': True
                    }
                    
                    logger.info(f"    ✅ {symbol}: {fetch_time:.3f}s")
                    logger.info(f"      Price: {sample_data['price']}")
                    logger.info(f"      Volume: {sample_data['volume']}")
                else:
                    results[symbol] = {
                        'status': 'no_data',
                        'fetch_time': fetch_time,
                        'no_keyerror': True
                    }
                    logger.warning(f"    ⚠️ {symbol}: No data returned")
                
                # Rate limiting
                await asyncio.sleep(1.0)
                
            except Exception as e:
                error_msg = str(e)
                is_keyerror = 'KeyError' in error_msg
                
                results[symbol] = {
                    'status': 'error',
                    'error': error_msg,
                    'is_keyerror': is_keyerror,
                    'no_keyerror': not is_keyerror
                }
                
                if is_keyerror:
                    logger.error(f"    ❌ {symbol}: KeyError occurred: {e}")
                else:
                    logger.warning(f"    ⚠️ {symbol}: Other error: {e}")
        
        # Calculate metrics
        successful_fetches = sum(1 for r in results.values() if r['status'] == 'success')
        keyerror_free = all(r.get('no_keyerror', False) for r in results.values())
        
        return {
            'test_name': 'ticker_fetching',
            'successful_fetches': successful_fetches,
            'total_symbols': len(self.test_symbols),
            'success_rate': successful_fetches / len(self.test_symbols),
            'keyerror_free': keyerror_free,
            'results': results
        }
    
    async def test_comprehensive_data_fetching(self) -> Dict[str, Any]:
        """Test the comprehensive market data method that was causing KeyErrors."""
        logger.info("🧪 Testing comprehensive market data fetching...")
        
        # Test with one symbol to avoid rate limits
        symbol = 'BTCUSDT'
        logger.info(f"  Fetching comprehensive data for {symbol}...")
        
        try:
            start_time = time.time()
            
            # This was the problematic method - should work now
            market_data = await self.exchange.fetch_market_data(symbol)
            
            fetch_time = time.time() - start_time
            
            if market_data:
                # Analyze data completeness
                sections = ['ticker', 'orderbook', 'trades', 'sentiment', 'ohlcv', 'metadata']
                present_sections = [section for section in sections if section in market_data]
                
                # Check sentiment data (was causing KeyErrors)
                sentiment = market_data.get('sentiment', {})
                sentiment_components = ['long_short_ratio', 'open_interest', 'funding_rate']
                present_sentiment = [comp for comp in sentiment_components if comp in sentiment]
                
                # Check metadata success indicators
                metadata = market_data.get('metadata', {})
                success_indicators = [k for k, v in metadata.items() if k.endswith('_success') and v]
                
                # Sample key data points
                sample_data = {}
                
                if market_data.get('ticker'):
                    ticker = market_data['ticker']
                    sample_data['price'] = (ticker.get('lastPrice') or 
                                          ticker.get('last') or 
                                          ticker.get('price'))
                
                if sentiment.get('long_short_ratio'):
                    lsr = sentiment['long_short_ratio']
                    sample_data['lsr'] = f"L:{lsr.get('long', 'N/A')} S:{lsr.get('short', 'N/A')}"
                
                if sentiment.get('open_interest'):
                    oi = sentiment['open_interest']
                    sample_data['oi'] = oi.get('current', 'N/A')
                
                logger.info(f"    ✅ {symbol}: {fetch_time:.3f}s")
                logger.info(f"      Sections: {len(present_sections)}/6")
                logger.info(f"      Sentiment: {len(present_sentiment)}/3")
                logger.info(f"      Success indicators: {len(success_indicators)}")
                if sample_data.get('price'):
                    logger.info(f"      Price: {sample_data['price']}")
                if sample_data.get('lsr'):
                    logger.info(f"      LSR: {sample_data['lsr']}")
                if sample_data.get('oi'):
                    logger.info(f"      OI: {sample_data['oi']}")
                
                return {
                    'test_name': 'comprehensive_data',
                    'status': 'success',
                    'fetch_time': fetch_time,
                    'sections_present': len(present_sections),
                    'sentiment_components': len(present_sentiment),
                    'success_indicators': len(success_indicators),
                    'sample_data': sample_data,
                    'no_keyerror': True
                }
            else:
                logger.warning(f"    ⚠️ {symbol}: No data returned")
                return {
                    'test_name': 'comprehensive_data',
                    'status': 'no_data',
                    'fetch_time': fetch_time,
                    'no_keyerror': True
                }
            
        except Exception as e:
            error_msg = str(e)
            is_keyerror = 'KeyError' in error_msg
            
            if is_keyerror:
                logger.error(f"    ❌ {symbol}: KeyError in comprehensive data: {e}")
            else:
                logger.warning(f"    ⚠️ {symbol}: Other error in comprehensive data: {e}")
            
            return {
                'test_name': 'comprehensive_data',
                'status': 'error',
                'error': error_msg,
                'is_keyerror': is_keyerror,
                'no_keyerror': not is_keyerror
            }
    
    async def test_error_conditions(self) -> Dict[str, Any]:
        """Test error handling scenarios."""
        logger.info("🧪 Testing error condition handling...")
        
        error_scenarios = [
            {'name': 'Invalid Symbol', 'symbol': 'INVALIDUSDT'},
            {'name': 'Non-existent Pair', 'symbol': 'TESTCOINUSDT'}
        ]
        
        scenario_results = {}
        
        for scenario in error_scenarios:
            name = scenario['name']
            symbol = scenario['symbol']
            
            logger.info(f"  Testing: {name} ({symbol})")
            
            try:
                start_time = time.time()
                
                # Should handle gracefully without KeyErrors
                result = await self.exchange.fetch_ticker(symbol)
                
                fetch_time = time.time() - start_time
                
                if result is None:
                    scenario_results[name] = {
                        'status': 'graceful_failure',
                        'fetch_time': fetch_time,
                        'no_keyerror': True
                    }
                    logger.info(f"    ✅ {name}: Handled gracefully (returned None)")
                else:
                    scenario_results[name] = {
                        'status': 'unexpected_success',
                        'fetch_time': fetch_time,
                        'no_keyerror': True
                    }
                    logger.info(f"    ⚠️ {name}: Unexpected success")
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                error_msg = str(e)
                is_keyerror = 'KeyError' in error_msg
                
                scenario_results[name] = {
                    'status': 'error',
                    'error': error_msg,
                    'is_keyerror': is_keyerror,
                    'no_keyerror': not is_keyerror
                }
                
                if is_keyerror:
                    logger.error(f"    ❌ {name}: KeyError occurred: {e}")
                else:
                    logger.info(f"    ✅ {name}: Non-KeyError (acceptable): {e}")
        
        # Check if all scenarios handled without KeyErrors
        all_keyerror_free = all(r.get('no_keyerror', False) for r in scenario_results.values())
        
        return {
            'test_name': 'error_conditions',
            'scenario_results': scenario_results,
            'all_keyerror_free': all_keyerror_free,
            'scenarios_tested': len(error_scenarios)
        }
    
    async def run_complete_test(self) -> Dict[str, Any]:
        """Run the complete real-world test suite."""
        logger.info("🚀 Starting Real-World Bybit Market Data Test")
        logger.info("=" * 60)
        
        if not self.initialize_exchange():
            return {
                'status': 'initialization_failed',
                'error': 'Could not initialize Bybit exchange'
            }
        
        # Run all tests
        test_results = {}
        
        tests = [
            ('ticker_fetching', self.test_ticker_fetching),
            ('comprehensive_data', self.test_comprehensive_data_fetching),
            ('error_handling', self.test_error_conditions)
        ]
        
        all_keyerror_free = True
        overall_success = True
        
        for test_name, test_func in tests:
            logger.info(f"\n📋 Running {test_name}...")
            
            try:
                result = await test_func()
                test_results[test_name] = result
                
                # Check for KeyErrors
                if not result.get('keyerror_free', result.get('no_keyerror', result.get('all_keyerror_free', True))):
                    all_keyerror_free = False
                
                # Check for success
                if result.get('status') not in ['success', 'no_data'] and result.get('success_rate', 1) < 0.5:
                    overall_success = False
                
                logger.info(f"✅ Completed {test_name}")
                
            except Exception as e:
                logger.error(f"❌ Failed {test_name}: {e}")
                test_results[test_name] = {
                    'status': 'crashed',
                    'error': str(e),
                    'no_keyerror': 'KeyError' not in str(e)
                }
                if 'KeyError' in str(e):
                    all_keyerror_free = False
                overall_success = False
        
        # Calculate final assessment
        ticker_test = test_results.get('ticker_fetching', {})
        ticker_success = ticker_test.get('success_rate', 0)
        
        comprehensive_test = test_results.get('comprehensive_data', {})
        comprehensive_working = comprehensive_test.get('status') == 'success'
        
        error_test = test_results.get('error_handling', {})
        error_handling_good = error_test.get('all_keyerror_free', False)
        
        # Final verdict
        production_ready = (
            all_keyerror_free and
            ticker_success >= 0.5 and  # At least 50% ticker success
            error_handling_good
        )
        
        final_results = {
            'test_timestamp': time.time(),
            'test_results': test_results,
            'summary': {
                'all_keyerror_free': all_keyerror_free,
                'overall_success': overall_success,
                'ticker_success_rate': ticker_success,
                'comprehensive_working': comprehensive_working,
                'error_handling_good': error_handling_good,
                'production_ready': production_ready
            }
        }
        
        # Print final summary
        logger.info(f"\n{'='*60}")
        logger.info("📊 REAL-WORLD TEST SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"KeyError Issues Resolved: {'✅ YES' if all_keyerror_free else '❌ NO'}")
        logger.info(f"Ticker Success Rate: {ticker_success*100:.1f}%")
        logger.info(f"Comprehensive Data Working: {'✅ YES' if comprehensive_working else '❌ NO'}")
        logger.info(f"Error Handling Good: {'✅ YES' if error_handling_good else '❌ NO'}")
        logger.info(f"Production Ready: {'✅ YES' if production_ready else '❌ NO'}")
        
        if production_ready:
            logger.info("🎉 Market data fetching system is ready for production use!")
        elif all_keyerror_free:
            logger.info("✅ KeyError fixes successful - system stable but may need tuning")
        else:
            logger.warning("⚠️ KeyError issues still present - additional work needed")
        
        return final_results

def run_test():
    """Run the test when executed directly."""
    async def main():
        tester = BybitRealWorldTester()
        return await tester.run_complete_test()
    
    return asyncio.run(main())

if __name__ == "__main__":
    try:
        results = run_test()
        
        # Print detailed results
        print(f"\n{'='*60}")
        print("📄 DETAILED RESULTS")
        print(f"{'='*60}")
        print(json.dumps(results, indent=2, default=str))
        
        # Exit with appropriate code
        exit(0 if results.get('summary', {}).get('all_keyerror_free', False) else 1)
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        print(traceback.format_exc())
        exit(1)

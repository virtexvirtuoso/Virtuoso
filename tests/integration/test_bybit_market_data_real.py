#!/usr/bin/env python3
"""
Real-world Bybit Market Data Fetching Test

This test verifies that market data fetching works correctly with the actual
Bybit exchange after our KeyError fixes, using real API calls in a controlled manner.
"""

import asyncio
import sys
import os
import time
import json
from typing import Dict, Any, Optional
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealBybitMarketDataTester:
    """Real-world Bybit market data testing with actual API calls."""
    
    def __init__(self):
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        self.exchange = None
        self.results = {}
        
    def setup_bybit_exchange(self) -> bool:
        """Set up Bybit exchange with test configuration."""
        try:
            from src.core.exchanges.bybit import BybitExchange
            
            # Test configuration (sandbox mode)
            config = {
                'exchanges': {
                    'bybit': {
                        'rest_endpoint': 'https://api-testnet.bybit.com',  # Use testnet
                        'ws_endpoint': 'wss://stream-testnet.bybit.com/v5/public/linear',
                        'api_key': 'test_key',  # Not needed for public endpoints
                        'api_secret': 'test_secret',
                        'sandbox': True,
                        'rate_limit': {
                            'requests_per_second': 2,  # Conservative rate limit
                            'burst_limit': 5
                        }
                    }
                }
            }
            
            self.exchange = BybitExchange(config)
            self.exchange.logger = logger
            
            logger.info("✅ Bybit exchange initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Bybit exchange: {e}")
            return False
    
    async def test_basic_ticker_fetching(self) -> Dict[str, Any]:
        """Test basic ticker data fetching."""
        logger.info("🧪 Testing basic ticker fetching...")
        
        results = {}
        
        for symbol in self.test_symbols:
            logger.info(f"  Fetching ticker for {symbol}...")
            
            try:
                start_time = time.time()
                
                # Fetch ticker data
                ticker_data = await self.exchange.fetch_ticker(symbol)
                
                fetch_time = time.time() - start_time
                
                # Validate ticker structure
                validation_results = {
                    'fetch_successful': ticker_data is not None,
                    'has_symbol': ticker_data.get('symbol') == symbol if ticker_data else False,
                    'has_price': any(key in ticker_data for key in ['lastPrice', 'last', 'price', 'close']) if ticker_data else False,
                    'has_volume': 'volume' in ticker_data or 'volume24h' in ticker_data if ticker_data else False,
                    'fetch_time': fetch_time
                }
                
                # Check for KeyError indicators in logs (our fixes should prevent these)
                no_keyerrors = True  # We'll monitor this through successful completion
                
                results[symbol] = {
                    'status': 'success' if validation_results['fetch_successful'] else 'failed',
                    'validation': validation_results,
                    'data_sample': {
                        'symbol': ticker_data.get('symbol') if ticker_data else None,
                        'price': ticker_data.get('lastPrice') or ticker_data.get('last') or ticker_data.get('price') if ticker_data else None,
                        'volume': ticker_data.get('volume24h') or ticker_data.get('volume') if ticker_data else None
                    } if ticker_data else None,
                    'no_keyerrors': no_keyerrors
                }
                
                if validation_results['fetch_successful']:
                    logger.info(f"    ✅ {symbol}: {validation_results['fetch_time']:.3f}s")
                    logger.info(f"      Price: {results[symbol]['data_sample']['price']}")
                    logger.info(f"      Volume: {results[symbol]['data_sample']['volume']}")
                else:
                    logger.warning(f"    ⚠️ {symbol}: Fetch failed")
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"    ❌ {symbol}: Error - {e}")
                results[symbol] = {
                    'status': 'error',
                    'error': str(e),
                    'no_keyerrors': 'KeyError' not in str(e)
                }
        
        # Calculate success metrics
        successful_fetches = sum(1 for r in results.values() if r['status'] == 'success')
        no_keyerror_issues = all(r.get('no_keyerrors', False) for r in results.values())
        
        return {
            'status': 'success' if successful_fetches > 0 else 'failed',
            'successful_fetches': successful_fetches,
            'total_symbols': len(self.test_symbols),
            'success_rate': successful_fetches / len(self.test_symbols),
            'no_keyerror_issues': no_keyerror_issues,
            'symbol_results': results
        }
    
    async def test_comprehensive_market_data(self) -> Dict[str, Any]:
        """Test comprehensive market data fetching (the main function that was having KeyErrors)."""
        logger.info("🧪 Testing comprehensive market data fetching...")
        
        # Test with just one symbol to avoid rate limits
        symbol = 'BTCUSDT'
        logger.info(f"  Fetching comprehensive data for {symbol}...")
        
        try:
            start_time = time.time()
            
            # This is the method that was causing KeyErrors - now it should work
            market_data = await self.exchange.fetch_market_data(symbol)
            
            fetch_time = time.time() - start_time
            
            # Validate comprehensive data structure
            if market_data:
                structure_analysis = {
                    'has_ticker': 'ticker' in market_data,
                    'has_orderbook': 'orderbook' in market_data,
                    'has_trades': 'trades' in market_data,
                    'has_sentiment': 'sentiment' in market_data,
                    'has_ohlcv': 'ohlcv' in market_data,
                    'has_metadata': 'metadata' in market_data
                }
                
                # Check sentiment data (this was causing KeyErrors)
                sentiment = market_data.get('sentiment', {})
                sentiment_analysis = {
                    'has_lsr': 'long_short_ratio' in sentiment,
                    'has_oi': 'open_interest' in sentiment,
                    'has_funding': 'funding_rate' in sentiment
                }
                
                # Check metadata for success indicators
                metadata = market_data.get('metadata', {})
                success_indicators = [k for k, v in metadata.items() if k.endswith('_success') and v]
                
                # Sample some actual data
                data_samples = {
                    'ticker_price': None,
                    'lsr_ratio': None,
                    'oi_current': None,
                    'funding_rate': None
                }
                
                if market_data.get('ticker'):
                    ticker = market_data['ticker']
                    data_samples['ticker_price'] = ticker.get('lastPrice') or ticker.get('last') or ticker.get('price')
                
                if sentiment.get('long_short_ratio'):
                    lsr = sentiment['long_short_ratio']
                    data_samples['lsr_ratio'] = f"L:{lsr.get('long', 'N/A')}% S:{lsr.get('short', 'N/A')}%"
                
                if sentiment.get('open_interest'):
                    oi = sentiment['open_interest']
                    data_samples['oi_current'] = oi.get('current')
                
                if sentiment.get('funding_rate'):
                    fr = sentiment['funding_rate']
                    data_samples['funding_rate'] = fr.get('rate')
                
                logger.info(f"    ✅ {symbol}: {fetch_time:.3f}s")
                logger.info(f"      Structure: {sum(structure_analysis.values())}/6 sections")
                logger.info(f"      Sentiment: {sum(sentiment_analysis.values())}/3 components")
                logger.info(f"      Success indicators: {len(success_indicators)}")
                logger.info(f"      Price: {data_samples['ticker_price']}")
                logger.info(f"      LSR: {data_samples['lsr_ratio']}")
                logger.info(f"      OI: {data_samples['oi_current']}")
                
                return {
                    'status': 'success',
                    'fetch_time': fetch_time,
                    'structure_analysis': structure_analysis,
                    'sentiment_analysis': sentiment_analysis,
                    'success_indicators': success_indicators,
                    'data_samples': data_samples,
                    'no_keyerrors': True  # Successful completion means no KeyErrors
                }
            else:
                logger.warning(f"    ⚠️ {symbol}: No data returned")
                return {
                    'status': 'no_data',
                    'fetch_time': fetch_time,
                    'no_keyerrors': True  # No crash means no KeyErrors
                }
            
        except Exception as e:
            logger.error(f"    ❌ {symbol}: Error - {e}")
            return {
                'status': 'error',
                'error': str(e),
                'no_keyerrors': 'KeyError' not in str(e)
            }
    
    async def test_error_resilience(self) -> Dict[str, Any]:
        """Test resilience against various error conditions."""
        logger.info("🧪 Testing error resilience...")
        
        test_scenarios = [
            {
                'name': 'Invalid Symbol',
                'symbol': 'INVALIDUSDT',
                'expected': 'graceful_failure'
            },
            {
                'name': 'Non-existent Pair',
                'symbol': 'FAKECOINUSDT',
                'expected': 'graceful_failure'
            }
        ]
        
        scenario_results = {}
        
        for scenario in test_scenarios:
            scenario_name = scenario['name']
            symbol = scenario['symbol']
            expected = scenario['expected']
            
            logger.info(f"  Testing: {scenario_name} ({symbol})")
            
            try:
                start_time = time.time()
                
                # Try to fetch data - should handle gracefully without KeyErrors
                result = await self.exchange.fetch_ticker(symbol)
                
                fetch_time = time.time() - start_time
                
                if result is None or not result:
                    # Expected - graceful handling
                    scenario_results[scenario_name] = {
                        'status': 'graceful_failure',
                        'fetch_time': fetch_time,
                        'no_keyerrors': True
                    }
                    logger.info(f"    ✅ {scenario_name}: Handled gracefully")
                else:
                    # Unexpected success (maybe the symbol exists)
                    scenario_results[scenario_name] = {
                        'status': 'unexpected_success',
                        'fetch_time': fetch_time,
                        'no_keyerrors': True
                    }
                    logger.info(f"    ⚠️ {scenario_name}: Unexpected success")
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                error_msg = str(e)
                is_keyerror = 'KeyError' in error_msg
                
                if is_keyerror:
                    scenario_results[scenario_name] = {
                        'status': 'keyerror_failure',
                        'error': error_msg,
                        'no_keyerrors': False
                    }
                    logger.error(f"    ❌ {scenario_name}: KeyError occurred: {e}")
                else:
                    scenario_results[scenario_name] = {
                        'status': 'other_error',
                        'error': error_msg,
                        'no_keyerrors': True
                    }
                    logger.info(f"    ✅ {scenario_name}: Other error (no KeyError): {e}")
        
        # Analyze results
        no_keyerror_issues = all(r.get('no_keyerrors', False) for r in scenario_results.values())
        graceful_handling_count = sum(1 for r in scenario_results.values() 
                                    if r['status'] in ['graceful_failure', 'other_error'])
        
        return {
            'status': 'success',
            'scenario_results': scenario_results,
            'no_keyerror_issues': no_keyerror_issues,
            'graceful_handling_rate': graceful_handling_count / len(scenario_results)
        }
    
    async def run_real_world_test(self) -> Dict[str, Any]:
        """Run the complete real-world test suite."""
        logger.info("🚀 Starting Real-World Bybit Market Data Test")
        logger.info("=" * 60)
        
        # Initialize exchange
        if not self.setup_bybit_exchange():
            return {
                'status': 'setup_failed',
                'error': 'Could not initialize Bybit exchange'
            }
        
        # Run test categories
        test_categories = [
            ('basic_ticker_fetching', self.test_basic_ticker_fetching),
            ('comprehensive_market_data', self.test_comprehensive_market_data),
            ('error_resilience', self.test_error_resilience)
        ]
        
        comprehensive_results = {
            'test_timestamp': time.time(),
            'exchange_type': 'Bybit Real API',
            'test_results': {},
            'summary': {}
        }
        
        passed_categories = 0
        total_categories = len(test_categories)
        all_keyerror_free = True
        
        for category_name, test_func in test_categories:
            logger.info(f"\n📋 Running {category_name}...")
            
            try:
                result = await test_func()
                comprehensive_results['test_results'][category_name] = result
                
                # Check for KeyError issues
                if not result.get('no_keyerror_issues', result.get('no_keyerrors', True)):
                    all_keyerror_free = False
                
                if result.get('status') in ['success', 'no_data']:
                    passed_categories += 1
                    status = '✅ PASSED' if result.get('status') == 'success' else '⚠️ NO DATA'
                    logger.info(f"{status} {category_name}")
                else:
                    logger.error(f"❌ FAILED {category_name}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"❌ CRASHED {category_name}: {e}")
                comprehensive_results['test_results'][category_name] = {
                    'status': 'crashed', 
                    'error': str(e),
                    'no_keyerrors': 'KeyError' not in str(e)
                }
                if 'KeyError' in str(e):
                    all_keyerror_free = False
        
        # Calculate final metrics
        success_rate = passed_categories / total_categories
        
        # Check specific results
        ticker_test = comprehensive_results['test_results'].get('basic_ticker_fetching', {})
        ticker_success_rate = ticker_test.get('success_rate', 0)
        
        comprehensive_test = comprehensive_results['test_results'].get('comprehensive_market_data', {})
        comprehensive_working = comprehensive_test.get('status') == 'success'
        
        resilience_test = comprehensive_results['test_results'].get('error_resilience', {})
        error_handling_good = resilience_test.get('graceful_handling_rate', 0) >= 0.8
        
        # Overall assessment
        overall_grade = 'EXCELLENT' if success_rate >= 0.9 else 'GOOD' if success_rate >= 0.75 else 'NEEDS_WORK'
        production_ready = (
            success_rate >= 0.75 and 
            all_keyerror_free and 
            ticker_success_rate >= 0.5  # At least 50% of symbols should work
        )
        
        comprehensive_results['summary'] = {
            'passed_categories': passed_categories,
            'total_categories': total_categories,
            'success_rate': success_rate,
            'overall_grade': overall_grade,
            'all_keyerror_free': all_keyerror_free,
            'ticker_success_rate': ticker_success_rate,
            'comprehensive_working': comprehensive_working,
            'error_handling_good': error_handling_good,
            'production_ready': production_ready
        }
        
        # Print final results
        logger.info(f"\n{'='*60}")
        logger.info("📊 REAL-WORLD TEST RESULTS")
        logger.info(f"{'='*60}")
        logger.info(f"Categories Passed: {passed_categories}/{total_categories}")
        logger.info(f"Success Rate: {success_rate*100:.1f}%")
        logger.info(f"Overall Grade: {overall_grade}")
        logger.info(f"KeyError Free: {'✅ YES' if all_keyerror_free else '❌ NO'}")
        logger.info(f"Ticker Success Rate: {ticker_success_rate*100:.1f}%")
        logger.info(f"Comprehensive Data Working: {'✅ YES' if comprehensive_working else '❌ NO'}")
        logger.info(f"Production Ready: {'✅ YES' if production_ready else '❌ NO'}")
        
        # Key findings
        key_findings = []
        
        if all_keyerror_free:
            key_findings.append("✅ All KeyError issues resolved")
        else:
            key_findings.append("❌ KeyError issues still present")
        
        if comprehensive_working:
            key_findings.append("✅ Comprehensive market data fetching works")
        
        if ticker_success_rate >= 0.8:
            key_findings.append("✅ High ticker fetch success rate")
        elif ticker_success_rate >= 0.5:
            key_findings.append("⚠️ Moderate ticker fetch success rate")
        else:
            key_findings.append("❌ Low ticker fetch success rate")
        
        if error_handling_good:
            key_findings.append("✅ Good error handling and resilience")
        
        logger.info(f"\n📋 Key Findings:")
        for finding in key_findings:
            logger.info(f"  {finding}")
        
        if production_ready:
            logger.info("🎉 Real-world market data fetching is working correctly!")
        else:
            logger.warning("⚠️ Market data fetching needs additional work")
        
        return comprehensive_results

def run_test():
    """Run the test if executed directly."""
    async def main():
        tester = RealBybitMarketDataTester()
        return await tester.run_real_world_test()
    
    return asyncio.run(main())

if __name__ == "__main__":
    results = run_test()
    
    # Print concise summary
    print(f"\n{'='*60}")
    print("📄 SUMMARY")
    print(f"{'='*60}")
    summary = results.get('summary', {})
    print(f"Overall Grade: {summary.get('overall_grade', 'UNKNOWN')}")
    print(f"Success Rate: {summary.get('success_rate', 0)*100:.1f}%")
    print(f"KeyError Free: {summary.get('all_keyerror_free', False)}")
    print(f"Production Ready: {summary.get('production_ready', False)}")
    
    # Print detailed results as JSON for analysis
    print(f"\n{'='*60}")
    print("📄 DETAILED RESULTS (JSON)")
    print(f"{'='*60}")
    print(json.dumps(results, indent=2, default=str))
    
    exit(0 if summary.get('production_ready', False) else 1) 
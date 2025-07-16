#!/usr/bin/env python3
"""
Comprehensive Confluence Analysis Test

This test runs a complete confluence analysis loop to ensure our KeyError fixes
work correctly in the full trading pipeline, from market data fetching through
signal generation and analysis.
"""

import asyncio
import sys
import os
import time
import json
import traceback
from typing import Dict, Any, List, Optional
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveMarketDataTester:
    """Comprehensive tester for market data pipeline with confluence analysis."""
    
    def __init__(self):
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        self.exchange = None
        self.keyerror_count = 0
        self.successful_fetches = 0
        self.failed_fetches = 0
        
    async def initialize_exchange(self) -> bool:
        """Initialize the exchange for testing."""
        try:
            from src.core.exchanges.bybit import BybitExchange
            
            config = {
                'exchanges': {
                    'bybit': {
                        'rest_endpoint': 'https://api.bybit.com',
                        'websocket': {
                            'mainnet_endpoint': 'wss://stream.bybit.com/v5/public/linear',
                            'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public/linear'
                        },
                        'api_key': 'test_key',
                        'api_secret': 'test_secret',
                        'sandbox': False,
                        'rate_limit': {
                            'requests_per_second': 2,
                            'burst_limit': 5
                        }
                    }
                }
            }
            
            self.exchange = BybitExchange(config)
            self.exchange.logger = logger
            logger.info("✅ Exchange initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Exchange initialization failed: {e}")
            return False
    
    async def test_comprehensive_market_data_fetching(self) -> Dict[str, Any]:
        """Test comprehensive market data fetching with full analysis."""
        logger.info("📊 Testing comprehensive market data fetching...")
        
        test_results = {
            'symbols_tested': [],
            'fetch_results': {},
            'confluence_analysis': {},
            'keyerror_incidents': [],
            'performance_metrics': {}
        }
        
        for symbol in self.test_symbols:
            logger.info(f"  📈 Analyzing {symbol}...")
            
            try:
                start_time = time.time()
                
                # Step 1: Fetch comprehensive market data
                market_data = await self.exchange.fetch_market_data(symbol)
                fetch_time = time.time() - start_time
                
                if market_data:
                    # Step 2: Analyze data completeness
                    data_analysis = self.analyze_market_data_completeness(market_data)
                    
                    # Step 3: Run confluence analysis
                    confluence_result = self.perform_confluence_analysis(symbol, market_data)
                    
                    # Step 4: Generate trading signals
                    signal_result = self.generate_trading_signals(symbol, confluence_result, market_data)
                    
                    # Store results
                    test_results['fetch_results'][symbol] = {
                        'success': True,
                        'fetch_time': fetch_time,
                        'data_analysis': data_analysis,
                        'has_keyerror_recovery': self.detect_recovery_patterns(market_data)
                    }
                    
                    test_results['confluence_analysis'][symbol] = {
                        'confluence_score': confluence_result['overall_score'],
                        'signal': signal_result['signal'],
                        'confidence': signal_result['confidence'],
                        'risk_level': signal_result['risk_level']
                    }
                    
                    self.successful_fetches += 1
                    
                    logger.info(f"    ✅ {symbol}: {fetch_time:.3f}s")
                    logger.info(f"      Data completeness: {data_analysis['completeness_score']:.1%}")
                    logger.info(f"      Confluence score: {confluence_result['overall_score']:.3f}")
                    logger.info(f"      Signal: {signal_result['signal']} ({signal_result['confidence']:.1%})")
                else:
                    test_results['fetch_results'][symbol] = {
                        'success': False,
                        'error': 'No data returned'
                    }
                    self.failed_fetches += 1
                    logger.warning(f"    ⚠️ {symbol}: No data returned")
                
                test_results['symbols_tested'].append(symbol)
                
                # Rate limiting for API
                await asyncio.sleep(1.5)
                
            except KeyError as e:
                self.keyerror_count += 1
                test_results['keyerror_incidents'].append(f"{symbol}: {str(e)}")
                test_results['fetch_results'][symbol] = {
                    'success': False,
                    'error': f'KeyError: {e}',
                    'is_keyerror': True
                }
                logger.error(f"    ❌ {symbol}: KeyError detected: {e}")
                
            except Exception as e:
                self.failed_fetches += 1
                test_results['fetch_results'][symbol] = {
                    'success': False,
                    'error': str(e),
                    'is_keyerror': False
                }
                logger.error(f"    ❌ {symbol}: Other error: {e}")
        
        # Calculate performance metrics
        total_symbols = len(self.test_symbols)
        test_results['performance_metrics'] = {
            'total_symbols': total_symbols,
            'successful_fetches': self.successful_fetches,
            'failed_fetches': self.failed_fetches,
            'success_rate': self.successful_fetches / total_symbols,
            'keyerror_count': self.keyerror_count,
            'keyerror_free': self.keyerror_count == 0
        }
        
        return test_results
    
    def analyze_market_data_completeness(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the completeness and quality of market data."""
        
        required_sections = ['ticker', 'orderbook', 'trades', 'sentiment', 'ohlcv', 'metadata']
        present_sections = []
        section_quality = {}
        
        for section in required_sections:
            if section in market_data and market_data[section]:
                present_sections.append(section)
                
                # Analyze section quality
                if section == 'ticker':
                    ticker = market_data[section]
                    section_quality[section] = {
                        'has_price': any(key in ticker for key in ['lastPrice', 'last', 'price', 'close']),
                        'has_volume': any(key in ticker for key in ['volume24h', 'volume', 'quoteVolume']),
                        'field_count': len(ticker)
                    }
                
                elif section == 'sentiment':
                    sentiment = market_data[section]
                    components = ['long_short_ratio', 'open_interest', 'funding_rate']
                    present_components = sum(1 for comp in components if comp in sentiment and sentiment[comp])
                    section_quality[section] = {
                        'component_count': present_components,
                        'completeness': present_components / len(components),
                        'has_lsr': 'long_short_ratio' in sentiment,
                        'has_oi': 'open_interest' in sentiment,
                        'has_funding': 'funding_rate' in sentiment
                    }
                
                elif section == 'metadata':
                    metadata = market_data[section]
                    success_indicators = [k for k, v in metadata.items() if k.endswith('_success') and v]
                    section_quality[section] = {
                        'success_indicators': len(success_indicators),
                        'total_indicators': len([k for k in metadata.keys() if k.endswith('_success')]),
                        'success_rate': len(success_indicators) / max(1, len([k for k in metadata.keys() if k.endswith('_success')]))
                    }
        
        completeness_score = len(present_sections) / len(required_sections)
        
        return {
            'completeness_score': completeness_score,
            'present_sections': present_sections,
            'missing_sections': [s for s in required_sections if s not in present_sections],
            'section_quality': section_quality,
            'grade': 'EXCELLENT' if completeness_score >= 0.9 else 'GOOD' if completeness_score >= 0.7 else 'FAIR' if completeness_score >= 0.5 else 'POOR'
        }
    
    def perform_confluence_analysis(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform confluence analysis on the market data."""
        
        confluence_factors = {
            'price_momentum': 0.0,
            'volume_profile': 0.0,
            'sentiment_alignment': 0.0,
            'market_structure': 0.0,
            'technical_strength': 0.0
        }
        
        # Price momentum analysis
        ticker = market_data.get('ticker', {})
        if ticker:
            try:
                price = float(ticker.get('lastPrice', ticker.get('last', ticker.get('price', 0))))
                volume = float(ticker.get('volume24h', ticker.get('volume', 0)))
                
                # Price momentum (simplified)
                if price > 0:
                    confluence_factors['price_momentum'] = min(1.0, price / 50000)
                
                # Volume analysis
                if volume > 0:
                    confluence_factors['volume_profile'] = min(1.0, volume / 10000)
                    
            except (ValueError, TypeError):
                logger.warning(f"Could not parse price/volume data for {symbol}")
        
        # Sentiment analysis (area that had KeyErrors)
        sentiment = market_data.get('sentiment', {})
        if sentiment:
            sentiment_score = 0.0
            
            # Long/Short Ratio analysis
            lsr = sentiment.get('long_short_ratio', {})
            if lsr and isinstance(lsr, dict):
                try:
                    long_ratio = float(lsr.get('long', 50))
                    if long_ratio > 60:
                        sentiment_score += 0.4
                    elif long_ratio < 40:
                        sentiment_score -= 0.4
                    else:
                        sentiment_score += 0.1  # Neutral is slightly positive
                except (ValueError, TypeError):
                    pass
            
            # Open Interest analysis
            oi = sentiment.get('open_interest', {})
            if oi and isinstance(oi, dict):
                try:
                    current_oi = float(oi.get('current', 0))
                    if current_oi > 10000:
                        sentiment_score += 0.3
                except (ValueError, TypeError):
                    pass
            
            # Funding Rate analysis
            funding = sentiment.get('funding_rate', {})
            if funding and isinstance(funding, dict):
                try:
                    rate = float(funding.get('rate', 0))
                    if abs(rate) < 0.01:  # Low funding suggests stability
                        sentiment_score += 0.2
                except (ValueError, TypeError):
                    pass
            
            confluence_factors['sentiment_alignment'] = max(-1.0, min(1.0, sentiment_score))
        
        # Market structure analysis
        orderbook = market_data.get('orderbook', {})
        if orderbook:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if bids and asks and len(bids) > 0 and len(asks) > 0:
                try:
                    bid_price = float(bids[0][0])
                    ask_price = float(asks[0][0])
                    spread = ask_price - bid_price
                    spread_pct = spread / bid_price if bid_price > 0 else 1
                    
                    # Tighter spreads indicate better market structure
                    confluence_factors['market_structure'] = max(0.0, min(1.0, 1 - (spread_pct * 1000)))
                except (ValueError, TypeError, IndexError):
                    pass
        
        # Technical strength (based on OHLCV availability)
        ohlcv = market_data.get('ohlcv', {})
        if ohlcv:
            timeframes_available = sum(1 for tf, data in ohlcv.items() if data is not None)
            confluence_factors['technical_strength'] = min(1.0, timeframes_available / 4)
        
        # Calculate overall confluence score
        overall_score = sum(confluence_factors.values()) / len(confluence_factors)
        
        return {
            'symbol': symbol,
            'overall_score': overall_score,
            'factor_scores': confluence_factors,
            'timestamp': time.time()
        }
    
    def generate_trading_signals(self, symbol: str, confluence: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signals based on confluence analysis."""
        
        score = confluence['overall_score']
        
        # Signal generation logic
        if score >= 0.8:
            signal = 'STRONG_BUY'
            strength = 'strong'
        elif score >= 0.6:
            signal = 'BUY'
            strength = 'moderate'
        elif score >= 0.4:
            signal = 'WEAK_BUY'
            strength = 'weak'
        elif score <= -0.4:
            signal = 'SELL'
            strength = 'moderate'
        elif score <= -0.6:
            signal = 'STRONG_SELL'
            strength = 'strong'
        else:
            signal = 'NEUTRAL'
            strength = 'none'
        
        # Calculate confidence based on data quality
        data_analysis = self.analyze_market_data_completeness(market_data)
        confidence = data_analysis['completeness_score']
        
        # Risk assessment
        if confidence >= 0.8 and abs(score) >= 0.6:
            risk_level = 'LOW'
        elif confidence >= 0.6 and abs(score) >= 0.4:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'HIGH'
        
        return {
            'symbol': symbol,
            'signal': signal,
            'strength': strength,
            'confidence': confidence,
            'risk_level': risk_level,
            'confluence_score': score,
            'timestamp': time.time()
        }
    
    def detect_recovery_patterns(self, market_data: Dict[str, Any]) -> bool:
        """Detect if KeyError recovery patterns are present."""
        recovery_indicators = []
        
        # Check sentiment data for recovery patterns
        sentiment = market_data.get('sentiment', {})
        
        # LSR default pattern (50/50 suggests fallback)
        lsr = sentiment.get('long_short_ratio', {})
        if isinstance(lsr, dict) and lsr.get('long') == 50.0 and lsr.get('short') == 50.0:
            recovery_indicators.append('lsr_default')
        
        # OI empty history pattern
        oi = sentiment.get('open_interest', {})
        if isinstance(oi, dict) and 'history' in oi and len(oi.get('history', [])) == 0:
            recovery_indicators.append('oi_empty_history')
        
        # Metadata partial success pattern
        metadata = market_data.get('metadata', {})
        if metadata:
            success_indicators = [k for k, v in metadata.items() if k.endswith('_success')]
            if success_indicators:
                success_count = sum(1 for k in success_indicators if metadata.get(k))
                if 0 < success_count < len(success_indicators):
                    recovery_indicators.append('partial_success')
        
        return len(recovery_indicators) > 0
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run the comprehensive confluence analysis test."""
        logger.info("🚀 Starting Comprehensive Confluence Analysis Test")
        logger.info("=" * 70)
        
        if not await self.initialize_exchange():
            return {
                'status': 'initialization_failed',
                'error': 'Could not initialize exchange'
            }
        
        # Run comprehensive market data test
        test_start_time = time.time()
        test_results = await self.test_comprehensive_market_data_fetching()
        total_test_time = time.time() - test_start_time
        
        # Calculate final assessment
        performance = test_results['performance_metrics']
        
        final_assessment = {
            'test_duration': total_test_time,
            'symbols_tested': performance['total_symbols'],
            'successful_fetches': performance['successful_fetches'],
            'success_rate': performance['success_rate'],
            'keyerror_count': performance['keyerror_count'],
            'keyerror_free': performance['keyerror_free'],
            'confluence_working': len(test_results['confluence_analysis']) > 0,
            'production_ready': (
                performance['keyerror_free'] and 
                performance['success_rate'] >= 0.7 and
                len(test_results['confluence_analysis']) > 0
            )
        }
        
        # Generate final report
        self.log_final_report(test_results, final_assessment)
        
        return {
            'test_results': test_results,
            'final_assessment': final_assessment,
            'timestamp': time.time()
        }
    
    def log_final_report(self, test_results: Dict[str, Any], assessment: Dict[str, Any]):
        """Log the final comprehensive report."""
        
        logger.info(f"\n{'='*70}")
        logger.info("📊 COMPREHENSIVE CONFLUENCE ANALYSIS RESULTS")
        logger.info(f"{'='*70}")
        
        # Test Summary
        logger.info(f"🔍 Test Summary:")
        logger.info(f"   Test Duration: {assessment['test_duration']:.2f}s")
        logger.info(f"   Symbols Tested: {assessment['symbols_tested']}")
        logger.info(f"   Successful Fetches: {assessment['successful_fetches']}")
        logger.info(f"   Success Rate: {assessment['success_rate']*100:.1f}%")
        
        # KeyError Analysis
        logger.info(f"\n🔧 KeyError Analysis:")
        logger.info(f"   KeyError Count: {assessment['keyerror_count']}")
        logger.info(f"   KeyError Free: {'✅ YES' if assessment['keyerror_free'] else '❌ NO'}")
        
        if test_results.get('keyerror_incidents'):
            logger.info(f"   KeyError Incidents:")
            for incident in test_results['keyerror_incidents']:
                logger.info(f"     - {incident}")
        
        # Confluence Analysis Results
        logger.info(f"\n📈 Confluence Analysis:")
        logger.info(f"   Confluence Working: {'✅ YES' if assessment['confluence_working'] else '❌ NO'}")
        
        if test_results.get('confluence_analysis'):
            logger.info(f"   Analysis Results:")
            for symbol, analysis in test_results['confluence_analysis'].items():
                logger.info(f"     {symbol}: Score={analysis['confluence_score']:.3f}, Signal={analysis['signal']}, Confidence={analysis['confidence']*100:.0f}%")
        
        # Data Quality Assessment
        logger.info(f"\n📊 Data Quality:")
        for symbol, fetch_result in test_results['fetch_results'].items():
            if fetch_result.get('success') and 'data_analysis' in fetch_result:
                data_analysis = fetch_result['data_analysis']
                logger.info(f"   {symbol}: {data_analysis['grade']} ({data_analysis['completeness_score']*100:.0f}% complete)")
        
        # Final Verdict
        logger.info(f"\n🎯 Final Verdict:")
        logger.info(f"   Production Ready: {'✅ YES' if assessment['production_ready'] else '❌ NO'}")
        
        if assessment['production_ready']:
            logger.info("🎉 Comprehensive confluence analysis system is fully operational!")
        elif assessment['keyerror_free']:
            logger.info("✅ KeyError fixes successful - system stable")
        else:
            logger.warning("⚠️ KeyError issues detected - fixes needed")

def run_test():
    """Run the comprehensive confluence analysis test."""
    async def main():
        tester = ComprehensiveMarketDataTester()
        return await tester.run_comprehensive_test()
    
    return asyncio.run(main())

if __name__ == "__main__":
    try:
        results = run_test()
        
        # Print summary
        assessment = results.get('final_assessment', {})
        print(f"\n{'='*70}")
        print("📄 TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Success Rate: {assessment.get('success_rate', 0)*100:.1f}%")
        print(f"KeyError Free: {assessment.get('keyerror_free', False)}")
        print(f"Production Ready: {assessment.get('production_ready', False)}")
        
        # Print detailed JSON results
        print(f"\n{'='*70}")
        print("📄 DETAILED RESULTS (JSON)")
        print(f"{'='*70}")
        print(json.dumps(results, indent=2, default=str))
        
        # Exit with appropriate code
        exit(0 if assessment.get('keyerror_free', False) else 1)
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        print(traceback.format_exc())
        exit(1) 
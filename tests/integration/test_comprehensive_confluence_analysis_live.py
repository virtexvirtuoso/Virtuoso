#!/usr/bin/env python3
"""
Comprehensive Confluence Analysis Test - LIVE DATA

This test runs a complete confluence analysis loop using LIVE MARKET DATA
to ensure our KeyError fixes work correctly with real trading conditions.
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

class LiveMarketDataTester:
    """Live market data tester for comprehensive confluence analysis."""
    
    def __init__(self):
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        self.exchange = None
        self.keyerror_count = 0
        self.successful_fetches = 0
        self.failed_fetches = 0
        
    async def initialize_live_exchange(self) -> bool:
        """Initialize the exchange for LIVE data testing."""
        try:
            from src.core.exchanges.bybit import BybitExchange
            
            # Configuration for LIVE market data
            config = {
                'exchanges': {
                    'bybit': {
                        'rest_endpoint': 'https://api.bybit.com',  # LIVE endpoint
                        'websocket': {
                            'mainnet_endpoint': 'wss://stream.bybit.com/v5/public/linear',
                            'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public/linear'
                        },
                        'api_key': '',  # No credentials needed for public data
                        'api_secret': '',
                        'sandbox': False,  # LIVE mode
                        'testnet': False,  # Explicitly disable testnet
                        'rate_limit': {
                            'requests_per_second': 1,  # Conservative for live data
                            'burst_limit': 3
                        }
                    }
                }
            }
            
            self.exchange = BybitExchange(config)
            self.exchange.logger = logger
            
            logger.info("🌐 LIVE DATA MODE - Using real market data")
            logger.info(f"📡 REST Endpoint: {config['exchanges']['bybit']['rest_endpoint']}")
            logger.info("✅ Live exchange initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Live exchange initialization failed: {e}")
            return False
    
    async def test_live_market_data_comprehensive(self) -> Dict[str, Any]:
        """Test comprehensive live market data fetching and analysis."""
        logger.info("🌐 Testing LIVE market data comprehensive analysis...")
        
        test_results = {
            'test_type': 'LIVE_DATA',
            'symbols_tested': [],
            'live_analysis': {},
            'keyerror_incidents': [],
            'performance_metrics': {}
        }
        
        current_time = time.time()
        
        for symbol in self.test_symbols:
            logger.info(f"\n🔴 LIVE ANALYSIS: {symbol}")
            
            try:
                start_time = time.time()
                
                # Fetch LIVE market data
                market_data = await self.exchange.fetch_market_data(symbol)
                fetch_time = time.time() - start_time
                
                if market_data:
                    # Analyze live data
                    live_analysis = self.analyze_live_market_data(symbol, market_data)
                    
                    # Perform confluence analysis
                    confluence_result = self.perform_live_confluence_analysis(symbol, market_data)
                    
                    # Generate trading signals
                    signal_result = self.generate_live_trading_signals(symbol, confluence_result)
                    
                    # Store results
                    test_results['live_analysis'][symbol] = {
                        'fetch_time': fetch_time,
                        'data_analysis': live_analysis,
                        'confluence_analysis': confluence_result,
                        'trading_signals': signal_result,
                        'keyerror_recovery_detected': self.detect_live_recovery_patterns(market_data)
                    }
                    
                    self.successful_fetches += 1
                    
                    # Extract key metrics
                    price = self.extract_live_price(market_data)
                    volume = self.extract_live_volume(market_data)
                    
                    logger.info(f"  💰 LIVE Price: ${price:,.2f}")
                    logger.info(f"  📊 24h Volume: {volume:,.0f}")
                    logger.info(f"  🎯 Quality: {live_analysis['data_quality_score']:.1%}")
                    logger.info(f"  📈 Confluence: {confluence_result['overall_score']:.3f}")
                    logger.info(f"  🚦 Signal: {signal_result['signal']} ({signal_result['confidence']:.1%})")
                    
                else:
                    self.failed_fetches += 1
                    logger.warning(f"  ⚠️ No live data returned for {symbol}")
                
                test_results['symbols_tested'].append(symbol)
                await asyncio.sleep(2.0)  # Rate limiting
                
            except KeyError as e:
                self.keyerror_count += 1
                test_results['keyerror_incidents'].append(f"{symbol}: {str(e)}")
                logger.error(f"  ❌ KeyError in live data for {symbol}: {e}")
                
            except Exception as e:
                self.failed_fetches += 1
                logger.error(f"  ❌ Live data error for {symbol}: {e}")
        
        # Calculate metrics
        total_test_time = time.time() - current_time
        total_symbols = len(self.test_symbols)
        
        test_results['performance_metrics'] = {
            'test_duration': total_test_time,
            'total_symbols': total_symbols,
            'successful_fetches': self.successful_fetches,
            'success_rate': self.successful_fetches / total_symbols if total_symbols > 0 else 0,
            'keyerror_count': self.keyerror_count,
            'keyerror_free': self.keyerror_count == 0
        }
        
        return test_results
    
    def analyze_live_market_data(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze live market data quality."""
        
        analysis = {
            'symbol': symbol,
            'data_quality_score': 0.0,
            'market_conditions': {},
            'live_indicators': {}
        }
        
        # Market conditions from ticker
        ticker = market_data.get('ticker', {})
        if ticker:
            try:
                price = float(ticker.get('lastPrice', ticker.get('last', ticker.get('price', 0))))
                volume_24h = float(ticker.get('volume24h', ticker.get('volume', 0)))
                price_change_pct = float(ticker.get('price24hPcnt', ticker.get('priceChangePercent', 0)))
                
                analysis['live_indicators'] = {
                    'current_price': price,
                    'volume_24h': volume_24h,
                    'price_change_24h': price_change_pct,
                    'volatility_level': 'high' if abs(price_change_pct) > 5 else 'medium' if abs(price_change_pct) > 2 else 'low',
                    'trend_direction': 'bullish' if price_change_pct > 1 else 'bearish' if price_change_pct < -1 else 'sideways'
                }
                
                analysis['market_conditions'] = {
                    'price_trend': analysis['live_indicators']['trend_direction'],
                    'volatility': analysis['live_indicators']['volatility_level']
                }
                
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing live data for {symbol}: {e}")
        
        # Data quality scoring
        required_sections = ['ticker', 'orderbook', 'trades', 'sentiment', 'metadata']
        present_sections = sum(1 for section in required_sections if section in market_data and market_data[section])
        analysis['data_quality_score'] = present_sections / len(required_sections)
        
        return analysis
    
    def perform_live_confluence_analysis(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform confluence analysis on live data."""
        
        confluence_factors = {
            'live_price_momentum': 0.0,
            'live_sentiment_alignment': 0.0,
            'live_market_structure': 0.0
        }
        
        # Price momentum
        ticker = market_data.get('ticker', {})
        if ticker:
            try:
                price_change = float(ticker.get('price24hPcnt', ticker.get('priceChangePercent', 0)))
                confluence_factors['live_price_momentum'] = max(-1.0, min(1.0, price_change / 10.0))
            except (ValueError, TypeError):
                pass
        
        # Sentiment alignment
        sentiment = market_data.get('sentiment', {})
        if sentiment:
            sentiment_score = 0.0
            
            lsr = sentiment.get('long_short_ratio', {})
            if lsr and isinstance(lsr, dict):
                try:
                    long_ratio = float(lsr.get('long', 50))
                    sentiment_bias = (long_ratio - 50) / 50
                    sentiment_score += sentiment_bias * 0.5
                except (ValueError, TypeError):
                    pass
            
            confluence_factors['live_sentiment_alignment'] = max(-1.0, min(1.0, sentiment_score))
        
        # Market structure
        orderbook = market_data.get('orderbook', {})
        if orderbook:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if bids and asks and len(bids) > 0 and len(asks) > 0:
                try:
                    bid_price = float(bids[0][0])
                    ask_price = float(asks[0][0])
                    spread_pct = (ask_price - bid_price) / bid_price * 100
                    
                    spread_quality = max(0.0, min(1.0, 1 - (spread_pct / 0.5)))
                    confluence_factors['live_market_structure'] = spread_quality
                except (ValueError, TypeError, IndexError):
                    pass
        
        overall_score = sum(confluence_factors.values()) / len(confluence_factors)
        
        return {
            'symbol': symbol,
            'overall_score': overall_score,
            'factor_scores': confluence_factors,
            'timestamp': time.time()
        }
    
    def generate_live_trading_signals(self, symbol: str, confluence: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signals."""
        
        score = confluence['overall_score']
        
        if score >= 0.6:
            signal = 'BUY'
            strength = 'strong'
        elif score >= 0.3:
            signal = 'WEAK_BUY'
            strength = 'weak'
        elif score <= -0.3:
            signal = 'SELL'
            strength = 'moderate'
        else:
            signal = 'NEUTRAL'
            strength = 'none'
        
        confidence = min(1.0, abs(score) + 0.5)
        
        return {
            'symbol': symbol,
            'signal': signal,
            'strength': strength,
            'confidence': confidence,
            'confluence_score': score,
            'timestamp': time.time()
        }
    
    def detect_live_recovery_patterns(self, market_data: Dict[str, Any]) -> bool:
        """Detect KeyError recovery patterns."""
        recovery_indicators = []
        
        sentiment = market_data.get('sentiment', {})
        
        # Check for fallback patterns
        lsr = sentiment.get('long_short_ratio', {})
        if isinstance(lsr, dict) and lsr.get('long') == 50.0 and lsr.get('short') == 50.0:
            recovery_indicators.append('lsr_default_fallback')
        
        metadata = market_data.get('metadata', {})
        if metadata:
            success_indicators = [k for k, v in metadata.items() if k.endswith('_success')]
            if success_indicators:
                success_count = sum(1 for k in success_indicators if metadata.get(k))
                if 0 < success_count < len(success_indicators):
                    recovery_indicators.append('partial_metadata_success')
        
        return len(recovery_indicators) > 0
    
    def extract_live_price(self, market_data: Dict[str, Any]) -> float:
        """Extract current price."""
        ticker = market_data.get('ticker', {})
        if ticker:
            return float(ticker.get('lastPrice', ticker.get('last', ticker.get('price', 0))))
        return 0.0
    
    def extract_live_volume(self, market_data: Dict[str, Any]) -> float:
        """Extract 24h volume."""
        ticker = market_data.get('ticker', {})
        if ticker:
            return float(ticker.get('volume24h', ticker.get('volume', 0)))
        return 0.0
    
    async def run_live_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive live data test."""
        logger.info("🌐 Starting LIVE DATA Comprehensive Test")
        logger.info("=" * 80)
        
        if not await self.initialize_live_exchange():
            return {
                'status': 'initialization_failed',
                'error': 'Could not initialize live exchange'
            }
        
        test_results = await self.test_live_market_data_comprehensive()
        
        # Final assessment
        performance = test_results['performance_metrics']
        final_assessment = {
            'test_type': 'LIVE_DATA',
            'success_rate': performance['success_rate'],
            'keyerror_free': performance['keyerror_free'],
            'production_ready_live': (
                performance['keyerror_free'] and 
                performance['success_rate'] >= 0.8 and
                len(test_results.get('live_analysis', {})) > 0
            )
        }
        
        self.log_live_test_results(test_results, final_assessment)
        
        return {
            'test_results': test_results,
            'final_assessment': final_assessment,
            'timestamp': time.time()
        }
    
    def log_live_test_results(self, test_results: Dict[str, Any], assessment: Dict[str, Any]):
        """Log live test results."""
        
        logger.info(f"\n{'='*80}")
        logger.info("🌐 LIVE DATA TEST RESULTS")
        logger.info(f"{'='*80}")
        
        performance = test_results['performance_metrics']
        logger.info(f"📊 Test Summary:")
        logger.info(f"   Duration: {performance['test_duration']:.2f}s")
        logger.info(f"   Success Rate: {performance['success_rate']*100:.1f}%")
        logger.info(f"   KeyError Free: {'✅ YES' if performance['keyerror_free'] else '❌ NO'}")
        
        # Live analysis results
        live_analyses = test_results.get('live_analysis', {})
        if live_analyses:
            logger.info(f"\n📈 Live Analysis Results:")
            for symbol, analysis in live_analyses.items():
                signals = analysis.get('trading_signals', {})
                confluence = analysis.get('confluence_analysis', {})
                
                logger.info(f"   {symbol}:")
                logger.info(f"     Score: {confluence.get('overall_score', 0):.3f}")
                logger.info(f"     Signal: {signals.get('signal', 'UNKNOWN')}")
                logger.info(f"     Confidence: {signals.get('confidence', 0)*100:.0f}%")
        
        logger.info(f"\n🎯 Final Verdict:")
        logger.info(f"   Production Ready (Live): {'✅ YES' if assessment['production_ready_live'] else '❌ NO'}")
        
        if assessment['production_ready_live']:
            logger.info("🎉 Live data system is fully operational!")
        else:
            logger.warning("⚠️ Live data issues detected")

def run_live_test():
    """Run the live data test."""
    async def main():
        tester = LiveMarketDataTester()
        return await tester.run_live_comprehensive_test()
    
    return asyncio.run(main())

if __name__ == "__main__":
    try:
        print("🌐 STARTING LIVE DATA TEST")
        print("=" * 80)
        print("⚠️  Using REAL MARKET DATA from live exchanges")
        print("=" * 80)
        
        results = run_live_test()
        
        assessment = results.get('final_assessment', {})
        print(f"\n{'='*80}")
        print("📄 LIVE DATA TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Success Rate: {assessment.get('success_rate', 0)*100:.1f}%")
        print(f"KeyError Free: {assessment.get('keyerror_free', False)}")
        print(f"Production Ready (Live): {assessment.get('production_ready_live', False)}")
        
        exit(0 if assessment.get('keyerror_free', False) else 1)
        
    except Exception as e:
        print(f"❌ Live test failed: {e}")
        exit(1) 
#!/usr/bin/env python3
"""
Enhanced Indicator Scoring Bybit Live Data Test

This test uses the Bybit exchange implementation directly to fetch LIVE market data
and verifies the enhanced indicator scoring implementation with actual trading conditions.

Test Coverage:
- Real market data from Bybit exchange
- All enhanced transform methods with live data
- Unified scoring framework integration
- Market regime detection with real conditions
- Performance metrics with actual data
"""

import asyncio
import sys
import os
import time
import json
import traceback
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/enhanced_scoring_bybit_live_test.log')
    ]
)
logger = logging.getLogger('enhanced_scoring_bybit_live_test')

class EnhancedScoringBybitLiveTest:
    """Comprehensive live data test for enhanced indicator scoring using Bybit exchange."""
    
    def __init__(self):
        self.bybit_exchange = None
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        self.results = {}
        
    async def initialize_bybit_exchange(self):
        """Initialize Bybit exchange connection."""
        logger.info("🚀 Initializing Bybit exchange for live data...")
        
        try:
            # Import the Bybit exchange implementation
            from src.core.exchanges.bybit import BybitExchange
            
            # Load configuration
            from src.config.manager import ConfigManager
            config_manager = ConfigManager()
            config = config_manager.config
            
            # Initialize Bybit exchange
            self.bybit_exchange = BybitExchange(config, error_handler=None)
            
            # Initialize the exchange
            if not await self.bybit_exchange.initialize():
                logger.error("❌ Failed to initialize Bybit exchange")
                return False
            
            logger.info("✅ Bybit exchange initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing Bybit exchange: {e}")
            traceback.print_exc()
            return False
    
    async def fetch_live_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch live market data from Bybit exchange."""
        try:
            logger.info(f"🔍 Fetching live market data for {symbol}")
            
            # Fetch comprehensive market data using the Bybit implementation
            market_data = await self.bybit_exchange.fetch_market_data(symbol)
            
            if not market_data:
                logger.warning(f"⚠️ No market data returned for {symbol}")
                return None
            
            # Validate the market data structure
            if not self.bybit_exchange.validate_market_data(market_data):
                logger.warning(f"⚠️ Market data validation failed for {symbol}")
                return None
            
            logger.info(f"✅ Successfully fetched market data for {symbol}")
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Error fetching market data for {symbol}: {e}")
            return None
    
    async def test_enhanced_scoring_with_live_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test enhanced scoring methods with live market data."""
        logger.info(f"🧪 Testing enhanced scoring for {market_data['symbol']}")
        
        test_results = {
            'symbol': market_data['symbol'],
            'exchange': 'bybit',
            'data_points': 0,
            'enhanced_methods': {},
            'unified_scoring': {},
            'market_regime': {},
            'performance': {}
        }
        
        try:
            # Import indicator classes
            from src.indicators.technical_indicators import TechnicalIndicators
            from src.indicators.volume_indicators import VolumeIndicators
            from src.indicators.orderbook_indicators import OrderbookIndicators
            from src.indicators.orderflow_indicators import OrderflowIndicators
            
            # Load configuration
            config_manager = ConfigManager()
            config = config_manager.config
            
            # Initialize indicators
            tech_indicators = TechnicalIndicators(config)
            volume_indicators = VolumeIndicators(config)
            ob_indicators = OrderbookIndicators(config)
            of_indicators = OrderflowIndicators(config)
            
            # Get OHLCV data from market_data
            ohlcv_data = market_data.get('ohlcv', {})
            
            # Test enhanced transforms with each timeframe
            for timeframe, df in ohlcv_data.items():
                if df is None or df.empty:
                    continue
                
                logger.info(f"📊 Testing {timeframe} timeframe with {len(df)} data points")
                test_results['data_points'] = len(df)
                
                # Test enhanced RSI transforms
                if len(df) >= 14:
                    try:
                        rsi_values = tech_indicators.rsi(df['close'], period=14)
                        if rsi_values is not None and not rsi_values.empty:
                            enhanced_rsi = tech_indicators._enhanced_rsi_transform(rsi_values)
                            test_results['enhanced_methods'][f'{timeframe}_enhanced_rsi'] = {
                                'original_mean': float(rsi_values.mean()),
                                'enhanced_mean': float(enhanced_rsi.mean()),
                                'transform_applied': True,
                                'data_points': len(rsi_values)
                            }
                    except Exception as e:
                        logger.warning(f"⚠️ RSI transform failed for {timeframe}: {e}")
                
                # Test enhanced volume transforms
                if len(df) >= 20:
                    try:
                        # ADL transform
                        adl_values = volume_indicators.adl(df)
                        if adl_values is not None and not adl_values.empty:
                            enhanced_adl = volume_indicators._enhanced_adl_transform(adl_values)
                            test_results['enhanced_methods'][f'{timeframe}_enhanced_adl'] = {
                                'original_mean': float(adl_values.mean()),
                                'enhanced_mean': float(enhanced_adl.mean()),
                                'transform_applied': True,
                                'data_points': len(adl_values)
                            }
                    except Exception as e:
                        logger.warning(f"⚠️ ADL transform failed for {timeframe}: {e}")
                    
                    try:
                        # CMF transform
                        cmf_values = volume_indicators.cmf(df, period=20)
                        if cmf_values is not None and not cmf_values.empty:
                            enhanced_cmf = volume_indicators._enhanced_cmf_transform(cmf_values)
                            test_results['enhanced_methods'][f'{timeframe}_enhanced_cmf'] = {
                                'original_mean': float(cmf_values.mean()),
                                'enhanced_mean': float(enhanced_cmf.mean()),
                                'transform_applied': True,
                                'data_points': len(cmf_values)
                            }
                    except Exception as e:
                        logger.warning(f"⚠️ CMF transform failed for {timeframe}: {e}")
                
                # Test additional enhanced transforms
                try:
                    # MACD transform
                    macd_values = tech_indicators.macd(df['close'])
                    if macd_values is not None and not macd_values.empty:
                        enhanced_macd = tech_indicators._enhanced_macd_transform(macd_values)
                        test_results['enhanced_methods'][f'{timeframe}_enhanced_macd'] = {
                            'original_mean': float(macd_values.mean()),
                            'enhanced_mean': float(enhanced_macd.mean()),
                            'transform_applied': True,
                            'data_points': len(macd_values)
                        }
                except Exception as e:
                    logger.warning(f"⚠️ MACD transform failed for {timeframe}: {e}")
                
                try:
                    # Stochastic transform
                    stoch_values = tech_indicators.stochastic(df)
                    if stoch_values is not None and not stoch_values.empty:
                        enhanced_stoch = tech_indicators._enhanced_stochastic_transform(stoch_values)
                        test_results['enhanced_methods'][f'{timeframe}_enhanced_stochastic'] = {
                            'original_mean': float(stoch_values.mean()),
                            'enhanced_mean': float(enhanced_stoch.mean()),
                            'transform_applied': True,
                            'data_points': len(stoch_values)
                        }
                except Exception as e:
                    logger.warning(f"⚠️ Stochastic transform failed for {timeframe}: {e}")
            
            # Test unified scoring framework
            from src.core.scoring.unified_scoring_framework import UnifiedScoringFramework
            scoring_framework = UnifiedScoringFramework()
            
            # Test with different scoring modes
            scoring_modes = ['auto_detect', 'enhanced', 'hybrid', 'traditional']
            
            for mode in scoring_modes:
                try:
                    # Use actual price data for testing
                    if 'base' in ohlcv_data and not ohlcv_data['base'].empty:
                        price_values = ohlcv_data['base']['close'].values
                        
                        unified_score = scoring_framework.transform_score(
                            values=price_values,
                            scoring_mode=mode,
                            market_regime='trending'  # Assume trending for testing
                        )
                        
                        test_results['unified_scoring'][mode] = {
                            'score_mean': float(np.mean(unified_score)),
                            'score_std': float(np.std(unified_score)),
                            'score_range': [float(np.min(unified_score)), float(np.max(unified_score))],
                            'success': True,
                            'data_points': len(unified_score)
                        }
                    else:
                        # Fallback to sample data
                        sample_values = np.random.randn(100) * 0.5 + 50
                        unified_score = scoring_framework.transform_score(
                            values=sample_values,
                            scoring_mode=mode,
                            market_regime='trending'
                        )
                        
                        test_results['unified_scoring'][mode] = {
                            'score_mean': float(np.mean(unified_score)),
                            'score_std': float(np.std(unified_score)),
                            'score_range': [float(np.min(unified_score)), float(np.max(unified_score))],
                            'success': True,
                            'data_points': len(unified_score),
                            'note': 'used_sample_data'
                        }
                    
                except Exception as e:
                    test_results['unified_scoring'][mode] = {
                        'error': str(e),
                        'success': False
                    }
            
            # Test market regime detection
            try:
                from src.core.market_regime.market_regime_detector import MarketRegimeDetector
                regime_detector = MarketRegimeDetector()
                
                # Use recent price data for regime detection
                if 'base' in ohlcv_data and not ohlcv_data['base'].empty:
                    recent_prices = ohlcv_data['base']['close'].tail(100).values
                    
                    regime_result = regime_detector.detect_regime(
                        prices=recent_prices,
                        method='hmm'  # Use HMM method
                    )
                    
                    test_results['market_regime'] = {
                        'detected_regime': regime_result.get('regime', 'unknown'),
                        'confidence': regime_result.get('confidence', 0.0),
                        'method': 'hmm',
                        'success': True,
                        'data_points': len(recent_prices)
                    }
                else:
                    test_results['market_regime'] = {
                        'error': 'No price data available for regime detection',
                        'success': False
                    }
                
            except Exception as e:
                test_results['market_regime'] = {
                    'error': str(e),
                    'success': False
                }
            
            # Performance metrics
            test_results['performance'] = {
                'data_quality': 'live',
                'data_points_used': test_results['data_points'],
                'timeframes_available': list(ohlcv_data.keys()),
                'sentiment_data_available': bool(market_data.get('sentiment')),
                'orderbook_data_available': bool(market_data.get('orderbook')),
                'trades_data_available': bool(market_data.get('trades')),
                'test_timestamp': datetime.now().isoformat()
            }
            
            # Add sentiment analysis if available
            sentiment = market_data.get('sentiment', {})
            if sentiment:
                test_results['sentiment_analysis'] = {
                    'long_short_ratio': sentiment.get('long_short_ratio', {}),
                    'funding_rate': sentiment.get('funding_rate', {}),
                    'open_interest': sentiment.get('open_interest', {}),
                    'volatility': sentiment.get('volatility', {}),
                    'market_mood': sentiment.get('market_mood', {})
                }
            
            logger.info(f"✅ Enhanced scoring test completed for {market_data['symbol']}")
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced scoring test for {market_data['symbol']}: {e}")
            test_results['error'] = str(e)
        
        return test_results
    
    async def run_comprehensive_live_test(self):
        """Run comprehensive live data test."""
        logger.info("🚀 Starting Enhanced Indicator Scoring Bybit Live Data Test")
        logger.info("=" * 70)
        
        # Initialize Bybit exchange
        if not await self.initialize_bybit_exchange():
            logger.error("❌ Cannot proceed without Bybit exchange initialization")
            return
        
        # Test each symbol
        for symbol in self.test_symbols:
            logger.info(f"\n📊 Testing {symbol}")
            logger.info("-" * 50)
            
            try:
                # Fetch live market data
                market_data = await self.fetch_live_market_data(symbol)
                
                if market_data:
                    # Test enhanced scoring methods
                    test_result = await self.test_enhanced_scoring_with_live_data(market_data)
                    self.results[symbol] = test_result
                    
                    # Log summary
                    enhanced_methods = test_result.get('enhanced_methods', {})
                    unified_scoring = test_result.get('unified_scoring', {})
                    
                    logger.info(f"✅ {symbol}: {len(enhanced_methods)} enhanced methods, {len(unified_scoring)} scoring modes")
                    
                    if 'market_regime' in test_result and test_result['market_regime'].get('success'):
                        regime = test_result['market_regime']['detected_regime']
                        confidence = test_result['market_regime']['confidence']
                        logger.info(f"   Market regime: {regime} (confidence: {confidence:.2f})")
                    
                else:
                    logger.warning(f"⚠️ No data available for {symbol}")
                    self.results[symbol] = {'error': 'No market data available'}
                    
            except Exception as e:
                logger.error(f"❌ Error testing {symbol}: {e}")
                self.results[symbol] = {'error': str(e)}
        
        # Generate comprehensive report
        await self.generate_live_test_report()
        
        # Cleanup
        await self.cleanup()
    
    async def generate_live_test_report(self):
        """Generate comprehensive live test report."""
        logger.info("\n📋 Generating Bybit Live Test Report")
        logger.info("=" * 70)
        
        report = {
            'test_info': {
                'test_name': 'Enhanced Indicator Scoring Bybit Live Data Test',
                'timestamp': datetime.now().isoformat(),
                'exchange': 'bybit',
                'symbols_tested': self.test_symbols,
                'exchange_implementation': 'src.core.exchanges.bybit.BybitExchange'
            },
            'summary': {
                'total_symbols': len(self.results),
                'successful_tests': 0,
                'failed_tests': 0,
                'total_enhanced_methods': 0,
                'total_scoring_modes': 0
            },
            'detailed_results': self.results
        }
        
        # Calculate summary statistics
        for symbol, test_result in self.results.items():
            if 'error' not in test_result:
                report['summary']['successful_tests'] += 1
                report['summary']['total_enhanced_methods'] += len(test_result.get('enhanced_methods', {}))
                report['summary']['total_scoring_modes'] += len(test_result.get('unified_scoring', {}))
            else:
                report['summary']['failed_tests'] += 1
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"test_output/enhanced_scoring_bybit_live_test_{timestamp}.json"
        
        os.makedirs('test_output', exist_ok=True)
        
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Report saved to: {report_filename}")
        
        # Print summary
        logger.info(f"\n📊 Test Summary:")
        logger.info(f"   Exchange: Bybit")
        logger.info(f"   Symbols tested: {report['summary']['total_symbols']}")
        logger.info(f"   Successful tests: {report['summary']['successful_tests']}")
        logger.info(f"   Failed tests: {report['summary']['failed_tests']}")
        logger.info(f"   Total enhanced methods tested: {report['summary']['total_enhanced_methods']}")
        logger.info(f"   Total scoring modes tested: {report['summary']['total_scoring_modes']}")
        
        # Print detailed results for successful tests
        logger.info(f"\n🔍 Detailed Results:")
        for symbol, test_result in self.results.items():
            if 'error' not in test_result:
                enhanced_methods = test_result.get('enhanced_methods', {})
                unified_scoring = test_result.get('unified_scoring', {})
                performance = test_result.get('performance', {})
                
                logger.info(f"\n📊 {symbol}:")
                logger.info(f"   Enhanced methods: {list(enhanced_methods.keys())}")
                logger.info(f"   Unified scoring modes: {list(unified_scoring.keys())}")
                logger.info(f"   Data points: {performance.get('data_points_used', 0)}")
                logger.info(f"   Timeframes: {performance.get('timeframes_available', [])}")
                
                if 'market_regime' in test_result and test_result['market_regime'].get('success'):
                    regime = test_result['market_regime']['detected_regime']
                    confidence = test_result['market_regime']['confidence']
                    logger.info(f"   Market regime: {regime} (confidence: {confidence:.2f})")
                
                # Show sentiment data if available
                if 'sentiment_analysis' in test_result:
                    sentiment = test_result['sentiment_analysis']
                    if sentiment.get('long_short_ratio'):
                        lsr = sentiment['long_short_ratio']
                        logger.info(f"   LSR: Long={lsr.get('long', 0):.1f}%, Short={lsr.get('short', 0):.1f}%")
                    
                    if sentiment.get('funding_rate'):
                        fr = sentiment['funding_rate']
                        logger.info(f"   Funding rate: {fr.get('rate', 0):.6f}")
    
    async def cleanup(self):
        """Cleanup exchange connections."""
        logger.info("🧹 Cleaning up Bybit exchange connections...")
        
        if self.bybit_exchange:
            try:
                await self.bybit_exchange.close()
                logger.info("✅ Bybit exchange connection closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing Bybit exchange: {e}")

async def main():
    """Main test execution."""
    try:
        test = EnhancedScoringBybitLiveTest()
        await test.run_comprehensive_live_test()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 
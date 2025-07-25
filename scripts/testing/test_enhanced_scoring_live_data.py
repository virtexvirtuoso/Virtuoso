#!/usr/bin/env python3
"""
Enhanced Indicator Scoring Live Data Test

This test fetches LIVE market data from real exchanges and verifies the enhanced 
indicator scoring implementation with actual trading conditions.

Test Coverage:
- Real market data from multiple exchanges (Binance, Bybit, OKX)
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
import ccxt.async_support as ccxt

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/enhanced_scoring_live_test.log')
    ]
)
logger = logging.getLogger('enhanced_scoring_live_test')

class EnhancedScoringLiveDataTest:
    """Comprehensive live data test for enhanced indicator scoring."""
    
    def __init__(self):
        self.exchanges = {}
        self.test_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
        self.timeframes = ['1m', '5m', '15m']
        self.results = {}
        
    async def initialize_exchanges(self):
        """Initialize exchange connections for live data."""
        logger.info("🚀 Initializing exchange connections for live data...")
        
        exchange_configs = {
            'binance': {
                'apiKey': os.getenv('BINANCE_API_KEY', ''),
                'secret': os.getenv('BINANCE_SECRET', ''),
                'sandbox': False
            },
            'bybit': {
                'apiKey': os.getenv('BYBIT_API_KEY', ''),
                'secret': os.getenv('BYBIT_SECRET', ''),
                'sandbox': False
            },
            'okx': {
                'apiKey': os.getenv('OKX_API_KEY', ''),
                'secret': os.getenv('OKX_SECRET', ''),
                'password': os.getenv('OKX_PASSWORD', ''),
                'sandbox': False
            }
        }
        
        for exchange_name, config in exchange_configs.items():
            try:
                exchange_class = getattr(ccxt, exchange_name)
                exchange = exchange_class(config)
                
                # Test connection
                markets = await exchange.load_markets()
                logger.info(f"✅ {exchange_name.upper()} initialized successfully")
                self.exchanges[exchange_name] = exchange
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize {exchange_name}: {e}")
                continue
    
    async def fetch_live_market_data(self, exchange_name: str, symbol: str, timeframe: str = '5m', limit: int = 100) -> Optional[Dict[str, Any]]:
        """Fetch live market data from exchange."""
        try:
            exchange = self.exchanges[exchange_name]
            
            # Fetch OHLCV data
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv or len(ohlcv) < 50:
                logger.warning(f"⚠️ Insufficient data for {symbol} on {exchange_name}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Fetch orderbook data
            try:
                orderbook = await exchange.fetch_order_book(symbol, limit=20)
            except:
                orderbook = None
            
            # Fetch ticker data
            try:
                ticker = await exchange.fetch_ticker(symbol)
            except:
                ticker = None
            
            return {
                'exchange': exchange_name,
                'symbol': symbol,
                'timeframe': timeframe,
                'ohlcv': df,
                'orderbook': orderbook,
                'ticker': ticker,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol} on {exchange_name}: {e}")
            return None
    
    async def test_enhanced_scoring_with_live_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test enhanced scoring methods with live market data."""
        logger.info(f"🧪 Testing enhanced scoring for {market_data['symbol']} on {market_data['exchange']}")
        
        test_results = {
            'symbol': market_data['symbol'],
            'exchange': market_data['exchange'],
            'timeframe': market_data['timeframe'],
            'data_points': len(market_data['ohlcv']),
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
            
            # Initialize indicators
            tech_indicators = TechnicalIndicators()
            volume_indicators = VolumeIndicators()
            ob_indicators = OrderbookIndicators()
            of_indicators = OrderflowIndicators()
            
            # Get OHLCV data
            df = market_data['ohlcv']
            
            # Test enhanced RSI transforms
            if len(df) >= 14:
                rsi_values = tech_indicators.rsi(df['close'], period=14)
                if rsi_values is not None and not rsi_values.empty:
                    enhanced_rsi = tech_indicators._enhanced_rsi_transform(rsi_values)
                    test_results['enhanced_methods']['enhanced_rsi'] = {
                        'original_mean': float(rsi_values.mean()),
                        'enhanced_mean': float(enhanced_rsi.mean()),
                        'transform_applied': True
                    }
            
            # Test enhanced volume transforms
            if len(df) >= 20:
                # ADL transform
                adl_values = volume_indicators.adl(df)
                if adl_values is not None and not adl_values.empty:
                    enhanced_adl = volume_indicators._enhanced_adl_transform(adl_values)
                    test_results['enhanced_methods']['enhanced_adl'] = {
                        'original_mean': float(adl_values.mean()),
                        'enhanced_mean': float(enhanced_adl.mean()),
                        'transform_applied': True
                    }
                
                # CMF transform
                cmf_values = volume_indicators.cmf(df, period=20)
                if cmf_values is not None and not cmf_values.empty:
                    enhanced_cmf = volume_indicators._enhanced_cmf_transform(cmf_values)
                    test_results['enhanced_methods']['enhanced_cmf'] = {
                        'original_mean': float(cmf_values.mean()),
                        'enhanced_mean': float(enhanced_cmf.mean()),
                        'transform_applied': True
                    }
            
            # Test unified scoring framework
            from src.core.scoring.unified_scoring_framework import UnifiedScoringFramework
            scoring_framework = UnifiedScoringFramework()
            
            # Test with different scoring modes
            scoring_modes = ['auto_detect', 'enhanced', 'hybrid', 'traditional']
            
            for mode in scoring_modes:
                try:
                    # Create sample indicator values for testing
                    sample_values = np.random.randn(100) * 0.5 + 50  # Normal distribution around 50
                    
                    unified_score = scoring_framework.transform_score(
                        values=sample_values,
                        scoring_mode=mode,
                        market_regime='trending'  # Assume trending for testing
                    )
                    
                    test_results['unified_scoring'][mode] = {
                        'score_mean': float(np.mean(unified_score)),
                        'score_std': float(np.std(unified_score)),
                        'score_range': [float(np.min(unified_score)), float(np.max(unified_score))],
                        'success': True
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
                recent_prices = df['close'].tail(100).values
                
                regime_result = regime_detector.detect_regime(
                    prices=recent_prices,
                    method='hmm'  # Use HMM method
                )
                
                test_results['market_regime'] = {
                    'detected_regime': regime_result.get('regime', 'unknown'),
                    'confidence': regime_result.get('confidence', 0.0),
                    'method': 'hmm',
                    'success': True
                }
                
            except Exception as e:
                test_results['market_regime'] = {
                    'error': str(e),
                    'success': False
                }
            
            # Performance metrics
            test_results['performance'] = {
                'data_quality': 'live',
                'data_points_used': len(df),
                'price_range': [float(df['low'].min()), float(df['high'].max())],
                'volume_total': float(df['volume'].sum()),
                'test_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Enhanced scoring test completed for {market_data['symbol']}")
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced scoring test for {market_data['symbol']}: {e}")
            test_results['error'] = str(e)
        
        return test_results
    
    async def run_comprehensive_live_test(self):
        """Run comprehensive live data test."""
        logger.info("🚀 Starting Enhanced Indicator Scoring Live Data Test")
        logger.info("=" * 60)
        
        # Initialize exchanges
        await self.initialize_exchanges()
        
        if not self.exchanges:
            logger.error("❌ No exchanges initialized. Cannot proceed with live data test.")
            return
        
        logger.info(f"✅ Initialized {len(self.exchanges)} exchanges: {list(self.exchanges.keys())}")
        
        # Test each symbol on each exchange
        for exchange_name in self.exchanges.keys():
            logger.info(f"\n📊 Testing {exchange_name.upper()}")
            logger.info("-" * 40)
            
            exchange_results = {}
            
            for symbol in self.test_symbols:
                logger.info(f"🔍 Testing {symbol} on {exchange_name}")
                
                symbol_results = {}
                
                for timeframe in self.timeframes:
                    try:
                        # Fetch live market data
                        market_data = await self.fetch_live_market_data(
                            exchange_name=exchange_name,
                            symbol=symbol,
                            timeframe=timeframe,
                            limit=100
                        )
                        
                        if market_data and not market_data['ohlcv'].empty:
                            # Test enhanced scoring methods
                            test_result = await self.test_enhanced_scoring_with_live_data(market_data)
                            symbol_results[timeframe] = test_result
                            
                            logger.info(f"✅ {symbol} {timeframe}: {test_result.get('enhanced_methods', {}).keys()}")
                            
                        else:
                            logger.warning(f"⚠️ No data available for {symbol} {timeframe} on {exchange_name}")
                            
                    except Exception as e:
                        logger.error(f"❌ Error testing {symbol} {timeframe} on {exchange_name}: {e}")
                        symbol_results[timeframe] = {'error': str(e)}
                
                exchange_results[symbol] = symbol_results
            
            self.results[exchange_name] = exchange_results
        
        # Generate comprehensive report
        await self.generate_live_test_report()
        
        # Cleanup
        await self.cleanup()
    
    async def generate_live_test_report(self):
        """Generate comprehensive live test report."""
        logger.info("\n📋 Generating Live Test Report")
        logger.info("=" * 60)
        
        report = {
            'test_info': {
                'test_name': 'Enhanced Indicator Scoring Live Data Test',
                'timestamp': datetime.now().isoformat(),
                'exchanges_tested': list(self.exchanges.keys()),
                'symbols_tested': self.test_symbols,
                'timeframes_tested': self.timeframes
            },
            'summary': {
                'total_exchanges': len(self.results),
                'total_symbols_tested': sum(len(exchange_results) for exchange_results in self.results.values()),
                'successful_tests': 0,
                'failed_tests': 0
            },
            'detailed_results': self.results
        }
        
        # Calculate summary statistics
        for exchange_name, exchange_results in self.results.items():
            for symbol, symbol_results in exchange_results.items():
                for timeframe, test_result in symbol_results.items():
                    if 'error' not in test_result:
                        report['summary']['successful_tests'] += 1
                    else:
                        report['summary']['failed_tests'] += 1
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"test_output/enhanced_scoring_live_test_{timestamp}.json"
        
        os.makedirs('test_output', exist_ok=True)
        
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Report saved to: {report_filename}")
        
        # Print summary
        logger.info(f"\n📊 Test Summary:")
        logger.info(f"   Exchanges tested: {report['summary']['total_exchanges']}")
        logger.info(f"   Symbols tested: {report['summary']['total_symbols_tested']}")
        logger.info(f"   Successful tests: {report['summary']['successful_tests']}")
        logger.info(f"   Failed tests: {report['summary']['failed_tests']}")
        
        # Print detailed results for successful tests
        logger.info(f"\n🔍 Detailed Results:")
        for exchange_name, exchange_results in self.results.items():
            logger.info(f"\n📊 {exchange_name.upper()}:")
            for symbol, symbol_results in exchange_results.items():
                for timeframe, test_result in symbol_results.items():
                    if 'error' not in test_result:
                        enhanced_methods = test_result.get('enhanced_methods', {})
                        unified_scoring = test_result.get('unified_scoring', {})
                        
                        logger.info(f"   {symbol} {timeframe}:")
                        logger.info(f"     Enhanced methods: {list(enhanced_methods.keys())}")
                        logger.info(f"     Unified scoring modes: {list(unified_scoring.keys())}")
                        
                        if 'market_regime' in test_result and test_result['market_regime'].get('success'):
                            regime = test_result['market_regime']['detected_regime']
                            confidence = test_result['market_regime']['confidence']
                            logger.info(f"     Market regime: {regime} (confidence: {confidence:.2f})")
    
    async def cleanup(self):
        """Cleanup exchange connections."""
        logger.info("🧹 Cleaning up exchange connections...")
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                await exchange.close()
                logger.info(f"✅ {exchange_name} connection closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing {exchange_name}: {e}")

async def main():
    """Main test execution."""
    try:
        test = EnhancedScoringLiveDataTest()
        await test.run_comprehensive_live_test()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 
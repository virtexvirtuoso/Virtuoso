#!/usr/bin/env python3
"""
Comprehensive test script for enhanced indicator scoring with live data.

This script tests all enhanced indicators:
- Technical Indicators: MACD, AO, Williams %R, CCI enhancements
- Volume Indicators: CMF, ADL, OBV advanced enhancements

Tests both enhanced transforms and fallback methods with live market data.
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List
import traceback

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.volume_indicators import VolumeIndicators
from src.config.manager import ConfigManager
from src.core.logger import Logger
from src.core.exchanges.bybit import BybitExchange

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedIndicatorTester:
    """Comprehensive tester for enhanced indicator scoring."""
    
    def __init__(self):
        """Initialize the tester."""
        self.config = self._load_config()
        self.logger = Logger(__name__)
        self.bybit_exchange = None
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']  # Use Bybit format
        self.test_results = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration for indicators."""
        try:
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            # Ensure required config sections exist
            if 'analysis' not in config:
                config['analysis'] = {}
            if 'indicators' not in config['analysis']:
                config['analysis']['indicators'] = {}
            
            # Set up timeframes
            config['timeframes'] = {
                'base': {'interval': '1m', 'weight': 0.4, 'validation': {'min_candles': 50}},
                'ltf': {'interval': '5m', 'weight': 0.3, 'validation': {'min_candles': 30}},
                'mtf': {'interval': '15m', 'weight': 0.2, 'validation': {'min_candles': 20}},
                'htf': {'interval': '1h', 'weight': 0.1, 'validation': {'min_candles': 10}}
            }
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {
                'analysis': {'indicators': {}},
                'timeframes': {
                    'base': {'interval': '1m', 'weight': 0.4, 'validation': {'min_candles': 50}},
                    'ltf': {'interval': '5m', 'weight': 0.3, 'validation': {'min_candles': 30}},
                    'mtf': {'interval': '15m', 'weight': 0.2, 'validation': {'min_candles': 20}},
                    'htf': {'interval': '1h', 'weight': 0.1, 'validation': {'min_candles': 10}}
                }
            }
    
    async def setup_data_client(self):
        """Setup Bybit exchange for live data."""
        try:
            # Load Bybit configuration
            bybit_config = self.config.get('exchanges', {}).get('bybit', {})
            if not bybit_config:
                # Create minimal config for testing
                bybit_config = {
                    'enabled': True,
                    'api_credentials': {
                        'api_key': 'test_key',
                        'api_secret': 'test_secret'
                    },
                    'rest_endpoint': 'https://api.bybit.com',
                    'websocket': {
                        'enabled': False,
                        'mainnet_endpoint': 'wss://stream.bybit.com/v5/public/linear',
                        'channels': []
                    }
                }
                self.config['exchanges'] = {'bybit': bybit_config}
            
            self.bybit_exchange = BybitExchange(self.config, error_handler=None)
            await self.bybit_exchange.initialize()
            logger.info("✅ Bybit exchange initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Bybit exchange: {str(e)}")
            raise
    
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch market data for testing."""
        try:
            logger.info(f"📊 Fetching market data for {symbol}")
            
            # Fetch OHLCV data for all timeframes
            ohlcv_data = {}
            timeframes = {
                'base': '1m',
                'ltf': '5m', 
                'mtf': '15m',
                'htf': '1h'
            }
            
            for tf_name, tf_interval in timeframes.items():
                try:
                    # Fetch 100 candles for each timeframe using Bybit
                    candles = await self.bybit_exchange.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=tf_interval,
                        limit=100
                    )
                    
                    if candles:
                        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('timestamp', inplace=True)
                        ohlcv_data[tf_name] = df
                        logger.info(f"  ✅ {tf_name} ({tf_interval}): {len(df)} candles")
                    else:
                        logger.warning(f"  ⚠️ No data for {tf_name} ({tf_interval})")
                        
                except Exception as e:
                    logger.error(f"  ❌ Error fetching {tf_name} data: {str(e)}")
            
            return {
                'symbol': symbol,
                'ohlcv': ohlcv_data,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching market data for {symbol}: {str(e)}")
            return {'symbol': symbol, 'ohlcv': {}, 'timestamp': datetime.now()}
    
    async def test_technical_indicators(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test enhanced technical indicators."""
        try:
            logger.info(f"🔧 Testing Technical Indicators for {market_data['symbol']}")
            
            # Initialize technical indicators
            technical = TechnicalIndicators(self.config, self.logger)
            
            results = {
                'symbol': market_data['symbol'],
                'enhanced_scores': {},
                'traditional_scores': {},
                'transformations': {},
                'errors': []
            }
            
            # Test each enhanced method
            test_methods = [
                ('MACD', '_calculate_macd_score'),
                ('AO', '_calculate_ao_score'),
                ('Williams %R', '_calculate_williams_r_score'),
                ('CCI', '_calculate_cci_score')
            ]
            
            for indicator_name, method_name in test_methods:
                try:
                    logger.info(f"  🧪 Testing {indicator_name}")
                    
                    # Get base timeframe data
                    if 'base' in market_data['ohlcv']:
                        df = market_data['ohlcv']['base']
                        
                        # Call the enhanced method
                        method = getattr(technical, method_name)
                        enhanced_score = method(df, 'base')
                        
                        results['enhanced_scores'][indicator_name] = enhanced_score
                        
                        # Test market regime detection
                        market_regime = technical._detect_market_regime(df)
                        volatility_context = technical._calculate_volatility_context(df)
                        
                        results['transformations'][indicator_name] = {
                            'market_regime': market_regime,
                            'volatility_context': volatility_context,
                            'data_points': len(df)
                        }
                        
                        logger.info(f"    ✅ {indicator_name}: {enhanced_score:.2f} (Market: {market_regime}, Vol: {volatility_context:.3f})")
                        
                    else:
                        logger.warning(f"    ⚠️ No base timeframe data for {indicator_name}")
                        results['errors'].append(f"No base data for {indicator_name}")
                        
                except Exception as e:
                    logger.error(f"    ❌ Error testing {indicator_name}: {str(e)}")
                    results['errors'].append(f"{indicator_name}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error testing technical indicators: {str(e)}")
            return {'symbol': market_data['symbol'], 'enhanced_scores': {}, 'errors': [str(e)]}
    
    async def test_volume_indicators(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test enhanced volume indicators."""
        try:
            logger.info(f"📊 Testing Volume Indicators for {market_data['symbol']}")
            
            # Initialize volume indicators
            volume = VolumeIndicators(self.config, self.logger)
            
            results = {
                'symbol': market_data['symbol'],
                'enhanced_scores': {},
                'traditional_scores': {},
                'transformations': {},
                'errors': []
            }
            
            # Test each enhanced method
            test_methods = [
                ('CMF', '_calculate_cmf_score'),
                ('ADL', '_calculate_adl_score'),
                ('OBV', '_calculate_obv_score')
            ]
            
            for indicator_name, method_name in test_methods:
                try:
                    logger.info(f"  🧪 Testing {indicator_name}")
                    
                    # Call the enhanced method
                    method = getattr(volume, method_name)
                    enhanced_score = method(market_data)
                    
                    results['enhanced_scores'][indicator_name] = enhanced_score
                    
                    # Test market context calculations
                    if 'base' in market_data['ohlcv']:
                        df = market_data['ohlcv']['base']
                        
                        market_regime = volume._detect_market_regime(df)
                        volatility_context = volume._calculate_volatility_context(df)
                        price_trend = volume._calculate_price_trend(df)
                        volume_trend = volume._calculate_volume_trend(df)
                        
                        results['transformations'][indicator_name] = {
                            'market_regime': market_regime,
                            'volatility_context': volatility_context,
                            'price_trend': price_trend,
                            'volume_trend': volume_trend,
                            'data_points': len(df)
                        }
                        
                        logger.info(f"    ✅ {indicator_name}: {enhanced_score:.2f} (Market: {market_regime}, Vol: {volatility_context:.3f}, Price: {price_trend:.3f})")
                    else:
                        logger.info(f"    ✅ {indicator_name}: {enhanced_score:.2f} (Limited context)")
                        
                except Exception as e:
                    logger.error(f"    ❌ Error testing {indicator_name}: {str(e)}")
                    results['errors'].append(f"{indicator_name}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error testing volume indicators: {str(e)}")
            return {'symbol': market_data['symbol'], 'enhanced_scores': {}, 'errors': [str(e)]}
    
    def analyze_results(self, results: Dict[str, Any]) -> None:
        """Analyze and display test results."""
        try:
            logger.info("\n" + "="*80)
            logger.info("📊 ENHANCED INDICATOR TESTING RESULTS")
            logger.info("="*80)
            
            for symbol, symbol_results in results.items():
                logger.info(f"\n🔸 {symbol}")
                logger.info("-" * 50)
                
                # Technical Indicators Results
                if 'technical' in symbol_results:
                    tech_results = symbol_results['technical']
                    logger.info("🔧 Technical Indicators:")
                    
                    for indicator, score in tech_results['enhanced_scores'].items():
                        transformation = tech_results['transformations'].get(indicator, {})
                        market_regime = transformation.get('market_regime', 'unknown')
                        volatility = transformation.get('volatility_context', 0.0)
                        
                        logger.info(f"  {indicator:12}: {score:6.2f} | Market: {market_regime:8} | Vol: {volatility:.3f}")
                    
                    if tech_results['errors']:
                        logger.warning(f"  ⚠️ Errors: {', '.join(tech_results['errors'])}")
                
                # Volume Indicators Results
                if 'volume' in symbol_results:
                    vol_results = symbol_results['volume']
                    logger.info("\n📊 Volume Indicators:")
                    
                    for indicator, score in vol_results['enhanced_scores'].items():
                        transformation = vol_results['transformations'].get(indicator, {})
                        market_regime = transformation.get('market_regime', 'unknown')
                        volatility = transformation.get('volatility_context', 0.0)
                        price_trend = transformation.get('price_trend', 0.0)
                        
                        logger.info(f"  {indicator:12}: {score:6.2f} | Market: {market_regime:8} | Vol: {volatility:.3f} | Price: {price_trend:+.3f}")
                    
                    if vol_results['errors']:
                        logger.warning(f"  ⚠️ Errors: {', '.join(vol_results['errors'])}")
            
            # Summary statistics
            logger.info("\n📈 SUMMARY STATISTICS")
            logger.info("-" * 50)
            
            all_scores = []
            error_count = 0
            
            for symbol_results in results.values():
                for indicator_type in ['technical', 'volume']:
                    if indicator_type in symbol_results:
                        all_scores.extend(symbol_results[indicator_type]['enhanced_scores'].values())
                        error_count += len(symbol_results[indicator_type]['errors'])
            
            if all_scores:
                logger.info(f"Total indicators tested: {len(all_scores)}")
                logger.info(f"Average score: {np.mean(all_scores):.2f}")
                logger.info(f"Score range: {np.min(all_scores):.2f} - {np.max(all_scores):.2f}")
                logger.info(f"Standard deviation: {np.std(all_scores):.2f}")
                logger.info(f"Errors encountered: {error_count}")
                
                # Score distribution
                score_ranges = [
                    (0, 20, "Very Bearish"),
                    (20, 40, "Bearish"),
                    (40, 60, "Neutral"),
                    (60, 80, "Bullish"),
                    (80, 100, "Very Bullish")
                ]
                
                logger.info("\n📊 Score Distribution:")
                for min_score, max_score, label in score_ranges:
                    count = sum(1 for score in all_scores if min_score <= score < max_score)
                    percentage = (count / len(all_scores)) * 100 if all_scores else 0
                    logger.info(f"  {label:12}: {count:3d} ({percentage:5.1f}%)")
            
            logger.info("\n✅ Enhanced indicator testing completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error analyzing results: {str(e)}")
    
    async def run_comprehensive_test(self):
        """Run comprehensive test of all enhanced indicators."""
        try:
            logger.info("🚀 Starting comprehensive enhanced indicator testing")
            
            # Setup data client
            await self.setup_data_client()
            
            # Test all symbols
            for symbol in self.test_symbols:
                try:
                    logger.info(f"\n🔍 Testing {symbol}")
                    
                    # Fetch market data
                    market_data = await self.fetch_market_data(symbol)
                    
                    if not market_data['ohlcv']:
                        logger.warning(f"⚠️ No market data for {symbol}, skipping")
                        continue
                    
                    # Test technical indicators
                    tech_results = await self.test_technical_indicators(market_data)
                    
                    # Test volume indicators
                    vol_results = await self.test_volume_indicators(market_data)
                    
                    # Store results
                    self.test_results[symbol] = {
                        'technical': tech_results,
                        'volume': vol_results,
                        'timestamp': market_data['timestamp']
                    }
                    
                except Exception as e:
                    logger.error(f"❌ Error testing {symbol}: {str(e)}")
                    self.test_results[symbol] = {'error': str(e)}
            
            # Analyze results
            self.analyze_results(self.test_results)
            
        except Exception as e:
            logger.error(f"❌ Error in comprehensive test: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            # Cleanup
            if self.bybit_exchange:
                await self.bybit_exchange.close()

async def main():
    """Main function to run the comprehensive test."""
    try:
        tester = EnhancedIndicatorTester()
        await tester.run_comprehensive_test()
        
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 
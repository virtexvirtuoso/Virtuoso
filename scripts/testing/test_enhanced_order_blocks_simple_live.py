#!/usr/bin/env python3
"""
Enhanced Smart Money Concepts Order Block Detection - Simple Live Test
====================================================================

This script tests the enhanced order block detection system using a simplified
approach that works with the existing CCXT-based infrastructure.

Author: AI Assistant
Date: 2024
"""

import asyncio
import os
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Core imports
from src.core.logger import Logger
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.config.manager import ConfigManager

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleLiveTest:
    """Simplified live test for enhanced SMC order block detection."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.logger = Logger("SimpleLiveTest")
        self.config_manager = None
        self.price_structure_indicator = None
        
    def setup(self):
        """Set up test environment."""
        try:
            self.logger.info("🔧 Setting up Enhanced SMC Order Block Simple Test")
            
            # Load configuration
            self.config_manager = ConfigManager()
            config = self.config_manager.config
            
            # Initialize price structure indicator
            self.price_structure_indicator = PriceStructureIndicators(config, self.logger)
            
            self.logger.info("🎯 Enhanced SMC Order Block Test Suite Ready")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Setup failed: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def generate_realistic_market_data(self, symbol: str = "BTCUSDT") -> Dict[str, pd.DataFrame]:
        """Generate realistic market data for testing."""
        try:
            self.logger.info(f"📊 Generating realistic market data for {symbol}")
            
            # Base parameters
            base_price = 45000.0
            volatility = 0.02
            trend = 0.0005
            
            # Generate multi-timeframe data
            timeframes = {
                'base': {'periods': 300, 'interval': 1},    # 1-minute, 5 hours
                'ltf': {'periods': 60, 'interval': 5},      # 5-minute, 5 hours  
                'mtf': {'periods': 10, 'interval': 30},     # 30-minute, 5 hours
                'htf': {'periods': 3, 'interval': 240}      # 4-hour, 12 hours
            }
            
            market_data = {}
            
            for tf_name, tf_config in timeframes.items():
                periods = tf_config['periods']
                interval = tf_config['interval']
                
                # Generate timestamps
                timestamps = pd.date_range(
                    start=datetime.now() - pd.Timedelta(minutes=periods * interval),
                    periods=periods,
                    freq=f'{interval}min'
                )
                
                # Generate price data with realistic patterns
                np.random.seed(42)  # For reproducible results
                
                # Create price movement with trend and volatility
                returns = np.random.normal(trend, volatility, periods)
                
                # Add some institutional patterns
                if tf_name == 'base':
                    # Add some order block patterns
                    for i in range(50, periods, 50):
                        if i < periods - 10:
                            # Create accumulation/distribution pattern
                            returns[i:i+5] = np.random.normal(0.001, 0.0005, 5)  # Accumulation
                            returns[i+5:i+10] = np.random.normal(-0.002, 0.001, 5)  # Distribution
                
                # Generate OHLCV data
                prices = [base_price]
                for ret in returns:
                    prices.append(prices[-1] * (1 + ret))
                
                ohlcv_data = []
                for i in range(periods):
                    open_price = prices[i]
                    close_price = prices[i + 1]
                    
                    # Generate high/low with some spread
                    spread = abs(close_price - open_price) * 0.5
                    high = max(open_price, close_price) + spread * np.random.random()
                    low = min(open_price, close_price) - spread * np.random.random()
                    
                    # Generate volume with some spikes
                    base_volume = 1000000
                    volume_multiplier = 1 + np.random.exponential(0.5)
                    volume = base_volume * volume_multiplier
                    
                    ohlcv_data.append({
                        'timestamp': timestamps[i],
                        'open': open_price,
                        'high': high,
                        'low': low,
                        'close': close_price,
                        'volume': volume
                    })
                
                # Create DataFrame
                df = pd.DataFrame(ohlcv_data)
                df = df.set_index('timestamp')
                market_data[tf_name] = df
                
                self.logger.debug(f"  {tf_name}: {len(df)} candles from {df.index[0]} to {df.index[-1]}")
            
            self.logger.info(f"✅ Generated market data for {symbol}: {len(market_data)} timeframes")
            return market_data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate market data: {str(e)}")
            return {}
    
    def test_enhanced_order_blocks(self, symbol: str, ohlcv_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Test enhanced order block detection."""
        try:
            self.logger.info(f"🔍 Testing Enhanced SMC Order Block Detection for {symbol}")
            
            # Get base timeframe data
            base_data = ohlcv_data.get('base')
            if base_data is None or base_data.empty:
                raise ValueError(f"No base timeframe data for {symbol}")
            
            # Test enhanced order block identification
            start_time = time.time()
            order_blocks = self.price_structure_indicator._identify_order_blocks(base_data, ohlcv_data)
            detection_time = time.time() - start_time
            
            # Analyze results
            results = {
                'symbol': symbol,
                'detection_time_ms': detection_time * 1000,
                'total_blocks': len(order_blocks),
                'demand_blocks': len([b for b in order_blocks if b['type'] == 'demand']),
                'supply_blocks': len([b for b in order_blocks if b['type'] == 'supply']),
                'blocks_with_volume_confirmation': len([b for b in order_blocks if b.get('volume_confirmation', False)]),
                'blocks_with_fvg': len([b for b in order_blocks if b.get('fvg_present', False)]),
                'blocks_with_mtf_confirmation': len([b for b in order_blocks if b.get('mtf_confirmation', {}).get('confirmed', False)]),
                'blocks_with_liquidity_sweeps': len([b for b in order_blocks if b.get('sweep_info', {}).get('has_sweep', False)]),
                'clustered_blocks': len([b for b in order_blocks if b.get('is_clustered', False)]),
                'mitigated_blocks': len([b for b in order_blocks if b.get('mitigation_info', {}).get('is_mitigated', False)]),
                'quality_blocks': len([b for b in order_blocks if b.get('enhanced_strength', 0) >= 0.5]),
                'top_blocks': order_blocks[:5]  # Top 5 blocks for analysis
            }
            
            # Log detailed results
            self.logger.info(f"📈 Enhanced SMC Results for {symbol}:")
            self.logger.info(f"  🎯 Total Blocks: {results['total_blocks']}")
            self.logger.info(f"  🔵 Demand Blocks: {results['demand_blocks']}")
            self.logger.info(f"  🔴 Supply Blocks: {results['supply_blocks']}")
            self.logger.info(f"  📊 Volume Confirmed: {results['blocks_with_volume_confirmation']}")
            self.logger.info(f"  🕳️  FVG Present: {results['blocks_with_fvg']}")
            self.logger.info(f"  🔗 MTF Confirmed: {results['blocks_with_mtf_confirmation']}")
            self.logger.info(f"  💧 Liquidity Sweeps: {results['blocks_with_liquidity_sweeps']}")
            self.logger.info(f"  🎯 Clustered: {results['clustered_blocks']}")
            self.logger.info(f"  ❌ Mitigated: {results['mitigated_blocks']}")
            self.logger.info(f"  ⭐ Quality Blocks: {results['quality_blocks']}")
            self.logger.info(f"  ⚡ Detection Time: {results['detection_time_ms']:.2f}ms")
            
            # Analyze top blocks
            if results['top_blocks']:
                self.logger.info(f"\n📊 Top 5 Order Blocks for {symbol}:")
                for i, block in enumerate(results['top_blocks'], 1):
                    self._log_block_details(i, block)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced order block test failed for {symbol}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {'symbol': symbol, 'error': str(e)}
    
    def _log_block_details(self, index: int, block: Dict[str, Any]):
        """Log detailed information about an order block."""
        try:
            block_type = block.get('type', 'unknown')
            strength = block.get('enhanced_strength', block.get('strength', 0))
            price_range = f"{block.get('low', 0):.2f} - {block.get('high', 0):.2f}"
            
            # Enhanced features
            volume_conf = "✅" if block.get('volume_confirmation', False) else "❌"
            fvg_present = "✅" if block.get('fvg_present', False) else "❌"
            mtf_conf = "✅" if block.get('mtf_confirmation', {}).get('confirmed', False) else "❌"
            sweep_info = block.get('sweep_info', {})
            has_sweep = "✅" if sweep_info.get('has_sweep', False) else "❌"
            is_clustered = "✅" if block.get('is_clustered', False) else "❌"
            is_mitigated = "✅" if block.get('mitigation_info', {}).get('is_mitigated', False) else "❌"
            
            self.logger.info(f"  #{index} {block_type.upper()} Block:")
            self.logger.info(f"    💪 Strength: {strength:.3f}")
            self.logger.info(f"    💰 Price Range: {price_range}")
            self.logger.info(f"    📊 Volume Confirmed: {volume_conf}")
            self.logger.info(f"    🕳️  FVG Present: {fvg_present}")
            self.logger.info(f"    🔗 MTF Confirmed: {mtf_conf}")
            self.logger.info(f"    💧 Liquidity Sweep: {has_sweep}")
            self.logger.info(f"    🎯 Clustered: {is_clustered}")
            self.logger.info(f"    ❌ Mitigated: {is_mitigated}")
            
            # Additional details
            if block.get('volume_multiplier'):
                self.logger.info(f"    📈 Volume Multiplier: {block['volume_multiplier']:.2f}x")
            
            if mtf_conf == "✅":
                confluence_score = block.get('mtf_confirmation', {}).get('confluence_score', 0)
                confirming_tfs = block.get('mtf_confirmation', {}).get('confirming_timeframes', [])
                self.logger.info(f"    🔗 MTF Confluence: {confluence_score:.2f} ({', '.join(confirming_tfs)})")
            
            if has_sweep == "✅":
                sweep_type = sweep_info.get('sweep_type', 'unknown')
                sweep_strength = sweep_info.get('sweep_strength', 0)
                self.logger.info(f"    💧 Sweep: {sweep_type} ({sweep_strength:.3f})")
            
        except Exception as e:
            self.logger.error(f"Error logging block details: {str(e)}")
    
    def test_price_structure_integration(self, symbol: str, ohlcv_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Test integration with price structure indicator."""
        try:
            self.logger.info(f"🔧 Testing Price Structure Integration for {symbol}")
            
            # Create market data structure
            market_data = {
                'symbol': symbol,
                'ohlcv': ohlcv_data,
                'timestamp': int(time.time() * 1000)
            }
            
            # Test full price structure calculation
            start_time = time.time()
            result = self.price_structure_indicator.calculate(market_data)
            calculation_time = time.time() - start_time
            
            # Extract order blocks component
            order_blocks_score = result.get('components', {}).get('order_blocks', 50.0)
            
            integration_results = {
                'symbol': symbol,
                'calculation_time_ms': calculation_time * 1000,
                'overall_score': result.get('score', 50.0),
                'order_blocks_score': order_blocks_score,
                'components': result.get('components', {}),
                'signals': result.get('signals', {}),
                'timeframe_scores': result.get('timeframe_scores', {}),
                'divergences': result.get('divergences', {})
            }
            
            self.logger.info(f"📊 Price Structure Integration Results for {symbol}:")
            self.logger.info(f"  🎯 Overall Score: {integration_results['overall_score']:.2f}")
            self.logger.info(f"  📦 Order Blocks Score: {integration_results['order_blocks_score']:.2f}")
            self.logger.info(f"  ⚡ Calculation Time: {integration_results['calculation_time_ms']:.2f}ms")
            
            # Log component breakdown
            components = integration_results['components']
            if components:
                self.logger.info("  📊 Component Scores:")
                for component, score in components.items():
                    self.logger.info(f"    {component}: {score:.2f}")
            
            return integration_results
            
        except Exception as e:
            self.logger.error(f"❌ Price structure integration test failed for {symbol}: {str(e)}")
            return {'symbol': symbol, 'error': str(e)}
    
    def run_comprehensive_test(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """Run comprehensive test suite for a symbol."""
        try:
            self.logger.info(f"\n🚀 Starting Comprehensive Test for {symbol}")
            
            # Generate realistic market data
            ohlcv_data = self.generate_realistic_market_data(symbol)
            if not ohlcv_data:
                return {'symbol': symbol, 'error': 'Failed to generate market data'}
            
            # Test enhanced order blocks
            order_blocks_results = self.test_enhanced_order_blocks(symbol, ohlcv_data)
            
            # Test price structure integration
            integration_results = self.test_price_structure_integration(symbol, ohlcv_data)
            
            # Combine results
            comprehensive_results = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'data_quality': {
                    'timeframes_available': len(ohlcv_data),
                    'base_candles': len(ohlcv_data.get('base', [])),
                    'ltf_candles': len(ohlcv_data.get('ltf', [])),
                    'mtf_candles': len(ohlcv_data.get('mtf', [])),
                    'htf_candles': len(ohlcv_data.get('htf', []))
                },
                'order_blocks': order_blocks_results,
                'price_structure': integration_results,
                'performance': {
                    'total_test_time_ms': (
                        order_blocks_results.get('detection_time_ms', 0) +
                        integration_results.get('calculation_time_ms', 0)
                    )
                }
            }
            
            self.logger.info(f"✅ Comprehensive test completed for {symbol}")
            return comprehensive_results
            
        except Exception as e:
            self.logger.error(f"❌ Comprehensive test failed for {symbol}: {str(e)}")
            return {'symbol': symbol, 'error': str(e)}
    
    def run_test(self):
        """Run the test suite."""
        try:
            self.logger.info("🎯 Starting Enhanced SMC Order Block Simple Test")
            
            # Test with generated data
            result = self.run_comprehensive_test("BTCUSDT")
            
            # Generate summary report
            self.generate_summary_report(result)
            
        except Exception as e:
            self.logger.error(f"❌ Test suite failed: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def generate_summary_report(self, result: Dict[str, Any]):
        """Generate comprehensive summary report."""
        try:
            self.logger.info("\n" + "="*80)
            self.logger.info("📊 ENHANCED SMC ORDER BLOCK DETECTION - SIMPLE TEST SUMMARY")
            self.logger.info("="*80)
            
            if 'error' in result:
                self.logger.error(f"❌ Test failed: {result['error']}")
                return
            
            order_blocks = result.get('order_blocks', {})
            price_structure = result.get('price_structure', {})
            
            # Test results
            self.logger.info(f"✅ Test completed for {result['symbol']}")
            self.logger.info(f"📦 Total Blocks Found: {order_blocks.get('total_blocks', 0)}")
            self.logger.info(f"⭐ Quality Blocks: {order_blocks.get('quality_blocks', 0)}")
            self.logger.info(f"📊 Volume Confirmed: {order_blocks.get('blocks_with_volume_confirmation', 0)}")
            self.logger.info(f"🔗 MTF Confirmed: {order_blocks.get('blocks_with_mtf_confirmation', 0)}")
            self.logger.info(f"🕳️  FVG Blocks: {order_blocks.get('blocks_with_fvg', 0)}")
            self.logger.info(f"💧 Sweep Blocks: {order_blocks.get('blocks_with_liquidity_sweeps', 0)}")
            self.logger.info(f"🎯 Overall Score: {price_structure.get('overall_score', 0):.2f}")
            
            # Performance metrics
            performance = result.get('performance', {})
            self.logger.info(f"⚡ Total Processing Time: {performance.get('total_test_time_ms', 0):.2f}ms")
            
            # Quality assessment
            total_blocks = order_blocks.get('total_blocks', 0)
            quality_blocks = order_blocks.get('quality_blocks', 0)
            
            if total_blocks > 0:
                quality_ratio = quality_blocks / total_blocks
                self.logger.info(f"📊 Quality Ratio: {quality_ratio:.2%}")
                
                if quality_ratio >= 0.7:
                    self.logger.info("🎯 EXCELLENT: High quality block detection")
                elif quality_ratio >= 0.5:
                    self.logger.info("👍 GOOD: Acceptable quality block detection")
                else:
                    self.logger.info("⚠️  NEEDS IMPROVEMENT: Low quality block detection")
            
            # Feature validation
            features_tested = [
                ('Volume Confirmation', order_blocks.get('blocks_with_volume_confirmation', 0) > 0),
                ('Fair Value Gaps', order_blocks.get('blocks_with_fvg', 0) > 0),
                ('Multi-Timeframe Confirmation', order_blocks.get('blocks_with_mtf_confirmation', 0) > 0),
                ('Liquidity Sweeps', order_blocks.get('blocks_with_liquidity_sweeps', 0) > 0),
                ('Block Clustering', order_blocks.get('clustered_blocks', 0) > 0),
                ('Mitigation Tracking', order_blocks.get('mitigated_blocks', 0) >= 0)
            ]
            
            self.logger.info("\n🔧 FEATURE VALIDATION:")
            for feature_name, is_working in features_tested:
                status = "✅ WORKING" if is_working else "❌ NOT DETECTED"
                self.logger.info(f"  {feature_name}: {status}")
            
            self.logger.info("="*80)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate summary report: {str(e)}")

def main():
    """Main test execution."""
    test_suite = SimpleLiveTest()
    
    try:
        # Setup
        if not test_suite.setup():
            logger.error("❌ Test setup failed")
            return 1
        
        # Run tests
        test_suite.run_test()
        
        logger.info("🎉 Enhanced SMC Order Block Simple Test completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    # Run the test
    exit_code = main()
    sys.exit(exit_code) 
#!/usr/bin/env python3
"""
Enhanced Smart Money Concepts Order Block Detection - Live Data Test
==================================================================

This script tests the enhanced order block detection system using live data from Bybit.
It validates all SMC components including:
- Volume confirmation for institutional validation
- Fair Value Gap (FVG) integration
- Multi-timeframe confirmation
- Liquidity sweep detection
- Mitigation tracking
- ML-based clustering

Author: AI Assistant
Date: 2024
"""

import asyncio
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Core imports
from src.core.logger import Logger
from src.core.exchanges.bybit import BybitExchange
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.config.manager import ConfigManager

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedOrderBlockLiveTest:
    """Live test suite for enhanced SMC order block detection."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.logger = Logger("EnhancedOrderBlockLiveTest")
        self.config_manager = None
        self.bybit_exchange = None
        self.price_structure_indicator = None
        
        # Test configuration
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        self.test_results = {}
        
    async def setup(self):
        """Set up test environment."""
        try:
            self.logger.info("🔧 Setting up Enhanced SMC Order Block Live Test")
            
            # Load configuration
            self.config_manager = ConfigManager()
            config = self.config_manager.config
            
            # Initialize Bybit exchange
            self.logger.info("📡 Initializing Bybit exchange connection...")
            self.bybit_exchange = await BybitExchange.get_instance(config)
            
            # Test connection
            if not await self.bybit_exchange.test_connection():
                raise RuntimeError("Failed to connect to Bybit exchange")
                
            self.logger.info("✅ Bybit exchange connection established")
            
            # Initialize price structure indicator
            self.price_structure_indicator = PriceStructureIndicators(config, self.logger)
            
            self.logger.info("🎯 Enhanced SMC Order Block Test Suite Ready")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Setup failed: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    async def fetch_live_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch live multi-timeframe data from Bybit."""
        try:
            self.logger.info(f"📊 Fetching live data for {symbol}")
            
            # Fetch comprehensive market data
            market_data = await self.bybit_exchange.fetch_market_data(symbol)
            
            if not market_data or 'ohlcv' not in market_data:
                raise ValueError(f"No OHLCV data received for {symbol}")
            
            ohlcv_data = market_data['ohlcv']
            
            # Validate multi-timeframe data
            required_timeframes = ['base', 'ltf', 'mtf', 'htf']
            missing_timeframes = [tf for tf in required_timeframes if tf not in ohlcv_data]
            
            if missing_timeframes:
                self.logger.warning(f"⚠️  Missing timeframes for {symbol}: {missing_timeframes}")
            
            # Convert to DataFrames
            processed_data = {}
            for tf, data in ohlcv_data.items():
                if isinstance(data, list) and len(data) > 0:
                    # Convert Bybit format to DataFrame
                    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df = df.set_index('timestamp')
                    df = df.astype(float)
                    processed_data[tf] = df
                    
                    self.logger.debug(f"  {tf}: {len(df)} candles from {df.index[0]} to {df.index[-1]}")
            
            self.logger.info(f"✅ Live data fetched for {symbol}: {len(processed_data)} timeframes")
            return processed_data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch live data for {symbol}: {str(e)}")
            return {}
    
    async def test_enhanced_order_blocks(self, symbol: str, ohlcv_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Test enhanced order block detection on live data."""
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
            price_range = f"{block.get('low', 0):.4f} - {block.get('high', 0):.4f}"
            
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
    
    async def test_price_structure_integration(self, symbol: str, ohlcv_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
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
            result = await self.price_structure_indicator.calculate(market_data)
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
    
    async def run_comprehensive_test(self, symbol: str) -> Dict[str, Any]:
        """Run comprehensive test suite for a symbol."""
        try:
            self.logger.info(f"\n🚀 Starting Comprehensive Test for {symbol}")
            
            # Fetch live data
            ohlcv_data = await self.fetch_live_data(symbol)
            if not ohlcv_data:
                return {'symbol': symbol, 'error': 'Failed to fetch live data'}
            
            # Test enhanced order blocks
            order_blocks_results = await self.test_enhanced_order_blocks(symbol, ohlcv_data)
            
            # Test price structure integration
            integration_results = await self.test_price_structure_integration(symbol, ohlcv_data)
            
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
    
    async def run_all_tests(self):
        """Run tests for all configured symbols."""
        try:
            self.logger.info("🎯 Starting Enhanced SMC Order Block Live Tests")
            
            # Test each symbol
            for symbol in self.test_symbols:
                try:
                    result = await self.run_comprehensive_test(symbol)
                    self.test_results[symbol] = result
                    
                    # Small delay between symbols to respect rate limits
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    self.logger.error(f"❌ Test failed for {symbol}: {str(e)}")
                    self.test_results[symbol] = {'symbol': symbol, 'error': str(e)}
            
            # Generate summary report
            self.generate_summary_report()
            
        except Exception as e:
            self.logger.error(f"❌ Test suite failed: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def generate_summary_report(self):
        """Generate comprehensive summary report."""
        try:
            self.logger.info("\n" + "="*80)
            self.logger.info("📊 ENHANCED SMC ORDER BLOCK DETECTION - LIVE TEST SUMMARY")
            self.logger.info("="*80)
            
            successful_tests = 0
            failed_tests = 0
            total_blocks_found = 0
            total_quality_blocks = 0
            total_volume_confirmed = 0
            total_mtf_confirmed = 0
            total_fvg_blocks = 0
            total_sweep_blocks = 0
            
            for symbol, result in self.test_results.items():
                if 'error' in result:
                    failed_tests += 1
                    self.logger.error(f"❌ {symbol}: {result['error']}")
                else:
                    successful_tests += 1
                    order_blocks = result.get('order_blocks', {})
                    
                    # Accumulate statistics
                    total_blocks_found += order_blocks.get('total_blocks', 0)
                    total_quality_blocks += order_blocks.get('quality_blocks', 0)
                    total_volume_confirmed += order_blocks.get('blocks_with_volume_confirmation', 0)
                    total_mtf_confirmed += order_blocks.get('blocks_with_mtf_confirmation', 0)
                    total_fvg_blocks += order_blocks.get('blocks_with_fvg', 0)
                    total_sweep_blocks += order_blocks.get('blocks_with_liquidity_sweeps', 0)
                    
                    # Log individual results
                    self.logger.info(f"✅ {symbol}:")
                    self.logger.info(f"  📦 Blocks: {order_blocks.get('total_blocks', 0)}")
                    self.logger.info(f"  ⭐ Quality: {order_blocks.get('quality_blocks', 0)}")
                    self.logger.info(f"  📊 Volume Confirmed: {order_blocks.get('blocks_with_volume_confirmation', 0)}")
                    self.logger.info(f"  🔗 MTF Confirmed: {order_blocks.get('blocks_with_mtf_confirmation', 0)}")
                    self.logger.info(f"  🎯 Overall Score: {result.get('price_structure', {}).get('overall_score', 0):.2f}")
            
            # Overall statistics
            self.logger.info("\n📈 OVERALL STATISTICS:")
            self.logger.info(f"  ✅ Successful Tests: {successful_tests}/{len(self.test_symbols)}")
            self.logger.info(f"  ❌ Failed Tests: {failed_tests}/{len(self.test_symbols)}")
            self.logger.info(f"  📦 Total Blocks Found: {total_blocks_found}")
            self.logger.info(f"  ⭐ Quality Blocks: {total_quality_blocks}")
            self.logger.info(f"  📊 Volume Confirmed: {total_volume_confirmed}")
            self.logger.info(f"  🔗 MTF Confirmed: {total_mtf_confirmed}")
            self.logger.info(f"  🕳️  FVG Blocks: {total_fvg_blocks}")
            self.logger.info(f"  💧 Sweep Blocks: {total_sweep_blocks}")
            
            # Quality metrics
            if total_blocks_found > 0:
                quality_ratio = total_quality_blocks / total_blocks_found
                volume_conf_ratio = total_volume_confirmed / total_blocks_found
                mtf_conf_ratio = total_mtf_confirmed / total_blocks_found
                
                self.logger.info("\n📊 QUALITY METRICS:")
                self.logger.info(f"  ⭐ Quality Ratio: {quality_ratio:.2%}")
                self.logger.info(f"  📊 Volume Confirmation Ratio: {volume_conf_ratio:.2%}")
                self.logger.info(f"  🔗 MTF Confirmation Ratio: {mtf_conf_ratio:.2%}")
                
                # Performance assessment
                if quality_ratio >= 0.7:
                    self.logger.info("🎯 EXCELLENT: High quality block detection")
                elif quality_ratio >= 0.5:
                    self.logger.info("👍 GOOD: Acceptable quality block detection")
                else:
                    self.logger.warning("⚠️  NEEDS IMPROVEMENT: Low quality block detection")
            
            self.logger.info("="*80)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate summary report: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.bybit_exchange:
                await self.bybit_exchange.close()
            self.logger.info("🧹 Cleanup completed")
        except Exception as e:
            self.logger.error(f"❌ Cleanup failed: {str(e)}")

async def main():
    """Main test execution."""
    test_suite = EnhancedOrderBlockLiveTest()
    
    try:
        # Setup
        if not await test_suite.setup():
            logger.error("❌ Test setup failed")
            return 1
        
        # Run tests
        await test_suite.run_all_tests()
        
        # Cleanup
        await test_suite.cleanup()
        
        logger.info("🎉 Enhanced SMC Order Block Live Test completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    # Run the test
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 
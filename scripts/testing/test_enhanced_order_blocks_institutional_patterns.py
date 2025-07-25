#!/usr/bin/env python3
"""
Enhanced SMC Order Block Detection - Institutional Patterns Test
==============================================================

This script creates strong institutional patterns to test the enhanced
Smart Money Concepts order block detection system across multiple symbols.

Author: AI Assistant
Date: 2024
"""

import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import Logger
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.config.manager import ConfigManager

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InstitutionalPatternsTest:
    """Test enhanced SMC detection with strong institutional patterns across multiple symbols."""
    
    def __init__(self):
        self.logger = Logger("InstitutionalPatternsTest")
        self.config_manager = ConfigManager()
        self.price_structure_indicator = PriceStructureIndicators(
            self.config_manager.config, self.logger
        )
        
        # Test symbols with realistic base prices
        self.test_symbols = {
            'BTCUSDT': 45000.0,    # Bitcoin
            'ETHUSDT': 2800.0,     # Ethereum
            'SOLUSDT': 95.0        # Solana
        }
        
        self.test_results = {}
        
    def generate_institutional_patterns(self, symbol: str, base_price: float) -> Dict[str, pd.DataFrame]:
        """Generate data with strong institutional patterns for a specific symbol."""
        try:
            self.logger.info(f"🏦 Generating institutional patterns for {symbol}")
            
            periods = 300
            
            # Create timestamps
            timestamps = pd.date_range(
                start=datetime.now() - pd.Timedelta(minutes=periods),
                periods=periods,
                freq='1min'
            )
            
            # Generate base price movement with symbol-specific characteristics
            np.random.seed(hash(symbol) % 1000)  # Different seed per symbol
            prices = [base_price]
            volumes = []
            
            # Symbol-specific volatility
            if symbol == 'BTCUSDT':
                volatility = 0.008  # 0.8% std
                volume_base = 1000000
            elif symbol == 'ETHUSDT':
                volatility = 0.012  # 1.2% std (more volatile)
                volume_base = 800000
            elif symbol == 'SOLUSDT':
                volatility = 0.015  # 1.5% std (most volatile)
                volume_base = 500000
            else:
                volatility = 0.010
                volume_base = 750000
            
            for i in range(periods):
                current_price = prices[-1]
                
                # Create institutional accumulation zones every 40-60 candles
                institutional_frequency = 45 if symbol == 'BTCUSDT' else 50
                
                if i % institutional_frequency == 0 and i > 0:
                    # Institutional accumulation pattern
                    # 1. High volume spike (institutional entry)
                    volume_spike = volume_base * 5  # 5x normal volume
                    
                    # 2. Strong price move (symbol-specific)
                    if symbol == 'BTCUSDT':
                        price_move_magnitude = 0.025  # 2.5% move
                    elif symbol == 'ETHUSDT':
                        price_move_magnitude = 0.030  # 3.0% move
                    elif symbol == 'SOLUSDT':
                        price_move_magnitude = 0.035  # 3.5% move
                    else:
                        price_move_magnitude = 0.025
                    
                    if np.random.random() > 0.5:
                        # Bullish order block
                        new_price = current_price * (1 + price_move_magnitude)
                    else:
                        # Bearish order block  
                        new_price = current_price * (1 - price_move_magnitude)
                    
                    prices.append(new_price)
                    volumes.append(volume_spike)
                    
                    # 3. Consolidation after institutional move (next 5-10 candles)
                    consolidation_candles = 8
                    for j in range(min(consolidation_candles, periods - i - 1)):
                        # Small price movements during consolidation
                        consolidation_move = np.random.normal(0, volatility * 0.3)
                        consolidation_price = prices[-1] * (1 + consolidation_move)
                        prices.append(consolidation_price)
                        
                        # Lower volume during consolidation
                        consolidation_volume = volume_base * 0.8 + np.random.normal(0, volume_base * 0.1)
                        volumes.append(max(volume_base * 0.5, consolidation_volume))
                        
                        if len(prices) >= periods + 1:
                            break
                else:
                    # Normal price movement
                    normal_move = np.random.normal(0, volatility)
                    new_price = current_price * (1 + normal_move)
                    prices.append(new_price)
                    
                    # Normal volume
                    normal_volume = volume_base + np.random.normal(0, volume_base * 0.2)
                    volumes.append(max(volume_base * 0.5, normal_volume))
                
                if len(prices) >= periods + 1:
                    break
            
            # Ensure we have the right number of data points
            prices = prices[:periods + 1]
            volumes = volumes[:periods]
            
            # Create OHLCV data with institutional patterns
            ohlcv_data = []
            for i in range(periods):
                open_price = prices[i]
                close_price = prices[i + 1]
                
                # Create realistic high/low with institutional footprint
                price_range = abs(close_price - open_price)
                
                # Institutional candles have wider ranges
                if volumes[i] > volume_base * 2:  # High volume candle
                    range_multiplier = 1.5
                else:
                    range_multiplier = 1.0
                
                high = max(open_price, close_price) + price_range * range_multiplier * 0.3
                low = min(open_price, close_price) - price_range * range_multiplier * 0.3
                
                ohlcv_data.append({
                    'timestamp': timestamps[i],
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close_price,
                    'volume': volumes[i]
                })
            
            # Create base DataFrame
            base_df = pd.DataFrame(ohlcv_data)
            base_df = base_df.set_index('timestamp')
            
            # Create multi-timeframe data
            market_data = {
                'base': base_df,
                'ltf': base_df.iloc[::5].copy(),    # 5-minute data
                'mtf': base_df.iloc[::30].copy(),   # 30-minute data  
                'htf': base_df.iloc[::240].copy()   # 4-hour data
            }
            
            # Add Fair Value Gaps to base data
            self._add_fair_value_gaps(market_data['base'], symbol)
            
            # Add liquidity sweeps
            self._add_liquidity_sweeps(market_data['base'], symbol)
            
            self.logger.info(f"✅ Generated institutional patterns for {symbol}:")
            self.logger.info(f"  📊 Base timeframe: {len(market_data['base'])} candles")
            self.logger.info(f"  📈 High volume candles: {len(market_data['base'][market_data['base']['volume'] > volume_base * 2])}")
            self.logger.info(f"  💰 Price range: {market_data['base']['close'].min():.2f} - {market_data['base']['close'].max():.2f}")
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate institutional patterns for {symbol}: {str(e)}")
            return {}
    
    def _add_fair_value_gaps(self, df: pd.DataFrame, symbol: str):
        """Add Fair Value Gaps to the data."""
        try:
            # Add 3-5 FVGs throughout the data
            fvg_indices = [50, 100, 150, 200, 250]
            
            # Symbol-specific gap sizes
            if symbol == 'BTCUSDT':
                gap_size = 50
            elif symbol == 'ETHUSDT':
                gap_size = 5
            elif symbol == 'SOLUSDT':
                gap_size = 1
            else:
                gap_size = 10
            
            for idx in fvg_indices:
                if idx + 2 < len(df):
                    # Create bullish FVG: candle[i-1].high < candle[i+1].low
                    if np.random.random() > 0.5:
                        # Bullish FVG
                        df.iloc[idx - 1, df.columns.get_loc('high')] = df.iloc[idx + 1, df.columns.get_loc('low')] - gap_size
                    else:
                        # Bearish FVG: candle[i-1].low > candle[i+1].high
                        df.iloc[idx - 1, df.columns.get_loc('low')] = df.iloc[idx + 1, df.columns.get_loc('high')] + gap_size
                        
        except Exception as e:
            self.logger.error(f"Error adding FVGs to {symbol}: {str(e)}")
    
    def _add_liquidity_sweeps(self, df: pd.DataFrame, symbol: str):
        """Add liquidity sweep patterns."""
        try:
            # Add liquidity sweeps at key levels
            sweep_indices = [75, 125, 175, 225]
            
            for idx in sweep_indices:
                if idx + 5 < len(df):
                    # Find recent swing high/low
                    lookback = 20
                    start_idx = max(0, idx - lookback)
                    recent_high = df.iloc[start_idx:idx]['high'].max()
                    recent_low = df.iloc[start_idx:idx]['low'].min()
                    
                    if np.random.random() > 0.5:
                        # Bullish sweep (sweep low then reverse)
                        df.iloc[idx, df.columns.get_loc('low')] = recent_low * 0.998  # Sweep below
                        df.iloc[idx, df.columns.get_loc('close')] = df.iloc[idx, df.columns.get_loc('open')] * 1.005  # Close higher
                        df.iloc[idx, df.columns.get_loc('volume')] *= 2  # Volume spike
                    else:
                        # Bearish sweep (sweep high then reverse)
                        df.iloc[idx, df.columns.get_loc('high')] = recent_high * 1.002  # Sweep above
                        df.iloc[idx, df.columns.get_loc('close')] = df.iloc[idx, df.columns.get_loc('open')] * 0.995  # Close lower
                        df.iloc[idx, df.columns.get_loc('volume')] *= 2  # Volume spike
                        
        except Exception as e:
            self.logger.error(f"Error adding liquidity sweeps to {symbol}: {str(e)}")
    
    def test_symbol(self, symbol: str, base_price: float) -> Dict[str, Any]:
        """Test enhanced SMC detection for a single symbol."""
        try:
            self.logger.info(f"\n🚀 Testing Enhanced SMC Detection for {symbol}")
            
            # Generate institutional data
            market_data = self.generate_institutional_patterns(symbol, base_price)
            if not market_data:
                return {'symbol': symbol, 'error': 'Failed to generate market data'}
            
            # Test enhanced order block detection
            base_data = market_data['base']
            
            self.logger.info(f"🔍 Running Enhanced SMC Detection for {symbol}")
            start_time = time.time()
            order_blocks = self.price_structure_indicator._identify_order_blocks(base_data, market_data)
            detection_time = time.time() - start_time
            
            # Analyze results
            results = {
                'symbol': symbol,
                'detection_time_ms': detection_time * 1000,
                'total_blocks': len(order_blocks),
                'demand_blocks': len([b for b in order_blocks if b['type'] == 'demand']),
                'supply_blocks': len([b for b in order_blocks if b['type'] == 'supply']),
                'volume_confirmed': len([b for b in order_blocks if b.get('volume_confirmation', False)]),
                'fvg_blocks': len([b for b in order_blocks if b.get('fvg_present', False)]),
                'mtf_confirmed': len([b for b in order_blocks if b.get('mtf_confirmation', {}).get('confirmed', False)]),
                'sweep_blocks': len([b for b in order_blocks if b.get('sweep_info', {}).get('has_sweep', False)]),
                'clustered_blocks': len([b for b in order_blocks if b.get('is_clustered', False)]),
                'mitigated_blocks': len([b for b in order_blocks if b.get('mitigation_info', {}).get('is_mitigated', False)]),
                'quality_blocks': len([b for b in order_blocks if b.get('enhanced_strength', 0) >= 0.3]),
                'top_blocks': order_blocks[:3],  # Top 3 blocks for analysis
                'price_range': {
                    'min': float(base_data['close'].min()),
                    'max': float(base_data['close'].max()),
                    'range_percent': ((base_data['close'].max() - base_data['close'].min()) / base_data['close'].min()) * 100
                }
            }
            
            # Log results
            self.logger.info(f"📊 Enhanced SMC Results for {symbol}:")
            self.logger.info(f"  ⚡ Detection Time: {results['detection_time_ms']:.2f}ms")
            self.logger.info(f"  🎯 Total Blocks: {results['total_blocks']}")
            self.logger.info(f"  🔵 Demand Blocks: {results['demand_blocks']}")
            self.logger.info(f"  🔴 Supply Blocks: {results['supply_blocks']}")
            self.logger.info(f"  📊 Volume Confirmed: {results['volume_confirmed']}")
            self.logger.info(f"  🕳️  FVG Present: {results['fvg_blocks']}")
            self.logger.info(f"  🔗 MTF Confirmed: {results['mtf_confirmed']}")
            self.logger.info(f"  💧 Liquidity Sweeps: {results['sweep_blocks']}")
            self.logger.info(f"  🎯 Clustered: {results['clustered_blocks']}")
            self.logger.info(f"  ❌ Mitigated: {results['mitigated_blocks']}")
            self.logger.info(f"  ⭐ Quality Blocks: {results['quality_blocks']}")
            self.logger.info(f"  💰 Price Range: {results['price_range']['range_percent']:.1f}%")
            
            # Show top blocks if any
            if results['top_blocks']:
                self.logger.info(f"\n🏆 TOP 3 ORDER BLOCKS FOR {symbol}:")
                for i, block in enumerate(results['top_blocks'], 1):
                    self._log_block_details(i, block, symbol)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Test failed for {symbol}: {str(e)}")
            return {'symbol': symbol, 'error': str(e)}
    
    def run_institutional_test(self):
        """Run test with institutional patterns across all symbols."""
        try:
            self.logger.info("🏦 Starting Multi-Symbol Institutional Patterns Test")
            self.logger.info(f"📊 Testing symbols: {', '.join(self.test_symbols.keys())}")
            
            # Test each symbol
            for symbol, base_price in self.test_symbols.items():
                try:
                    result = self.test_symbol(symbol, base_price)
                    self.test_results[symbol] = result
                    
                    # Small delay between symbols
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.logger.error(f"❌ Test failed for {symbol}: {str(e)}")
                    self.test_results[symbol] = {'symbol': symbol, 'error': str(e)}
            
            # Generate comprehensive summary
            self.generate_multi_symbol_summary()
            
        except Exception as e:
            self.logger.error(f"❌ Multi-symbol test failed: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def generate_multi_symbol_summary(self):
        """Generate comprehensive summary across all symbols."""
        try:
            self.logger.info("\n" + "="*80)
            self.logger.info("📊 MULTI-SYMBOL ENHANCED SMC DETECTION - TEST SUMMARY")
            self.logger.info("="*80)
            
            successful_tests = 0
            failed_tests = 0
            total_blocks = 0
            total_quality_blocks = 0
            total_volume_confirmed = 0
            total_mtf_confirmed = 0
            total_fvg_blocks = 0
            total_sweep_blocks = 0
            total_detection_time = 0
            
            # Process results for each symbol
            for symbol, result in self.test_results.items():
                if 'error' in result:
                    failed_tests += 1
                    self.logger.error(f"❌ {symbol}: {result['error']}")
                else:
                    successful_tests += 1
                    total_blocks += result.get('total_blocks', 0)
                    total_quality_blocks += result.get('quality_blocks', 0)
                    total_volume_confirmed += result.get('volume_confirmed', 0)
                    total_mtf_confirmed += result.get('mtf_confirmed', 0)
                    total_fvg_blocks += result.get('fvg_blocks', 0)
                    total_sweep_blocks += result.get('sweep_blocks', 0)
                    total_detection_time += result.get('detection_time_ms', 0)
                    
                    # Log individual symbol results
                    self.logger.info(f"✅ {symbol}:")
                    self.logger.info(f"  📦 Blocks: {result.get('total_blocks', 0)}")
                    self.logger.info(f"  ⭐ Quality: {result.get('quality_blocks', 0)}")
                    self.logger.info(f"  📊 Volume Confirmed: {result.get('volume_confirmed', 0)}")
                    self.logger.info(f"  🔗 MTF Confirmed: {result.get('mtf_confirmed', 0)}")
                    self.logger.info(f"  ⚡ Detection Time: {result.get('detection_time_ms', 0):.2f}ms")
                    self.logger.info(f"  💰 Price Range: {result.get('price_range', {}).get('range_percent', 0):.1f}%")
            
            # Overall statistics
            self.logger.info(f"\n📈 OVERALL STATISTICS:")
            self.logger.info(f"  ✅ Successful Tests: {successful_tests}/{len(self.test_symbols)}")
            self.logger.info(f"  ❌ Failed Tests: {failed_tests}/{len(self.test_symbols)}")
            self.logger.info(f"  📦 Total Blocks Found: {total_blocks}")
            self.logger.info(f"  ⭐ Quality Blocks: {total_quality_blocks}")
            self.logger.info(f"  📊 Volume Confirmed: {total_volume_confirmed}")
            self.logger.info(f"  🔗 MTF Confirmed: {total_mtf_confirmed}")
            self.logger.info(f"  🕳️  FVG Blocks: {total_fvg_blocks}")
            self.logger.info(f"  💧 Sweep Blocks: {total_sweep_blocks}")
            self.logger.info(f"  ⚡ Avg Detection Time: {total_detection_time/max(1, successful_tests):.2f}ms")
            
            # Performance assessment
            if successful_tests > 0:
                avg_blocks_per_symbol = total_blocks / successful_tests
                avg_quality_per_symbol = total_quality_blocks / successful_tests
                
                self.logger.info(f"\n🎯 PERFORMANCE METRICS:")
                self.logger.info(f"  📊 Avg Blocks per Symbol: {avg_blocks_per_symbol:.1f}")
                self.logger.info(f"  ⭐ Avg Quality Blocks per Symbol: {avg_quality_per_symbol:.1f}")
                
                # Success assessment
                success_rate = successful_tests / len(self.test_symbols)
                detection_quality = total_quality_blocks / max(1, total_blocks)
                
                self.logger.info(f"  📈 Test Success Rate: {success_rate:.1%}")
                self.logger.info(f"  🎯 Detection Quality: {detection_quality:.1%}")
                
                if success_rate >= 0.8 and detection_quality >= 0.3:
                    self.logger.info("🎉 EXCELLENT: Multi-symbol SMC system performing well!")
                elif success_rate >= 0.6:
                    self.logger.info("👍 GOOD: Multi-symbol SMC system is functional")
                else:
                    self.logger.info("⚠️  NEEDS IMPROVEMENT: Multi-symbol SMC system needs tuning")
            
            # Feature validation across symbols
            self.logger.info(f"\n🔧 FEATURE VALIDATION ACROSS SYMBOLS:")
            features = ['volume_confirmed', 'fvg_blocks', 'mtf_confirmed', 'sweep_blocks']
            for feature in features:
                total_feature = sum(result.get(feature, 0) for result in self.test_results.values() if 'error' not in result)
                status = "✅ WORKING" if total_feature > 0 else "❌ NOT DETECTED"
                feature_name = feature.replace('_', ' ').title()
                self.logger.info(f"  {feature_name}: {status} ({total_feature} total)")
            
            self.logger.info("="*80)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate multi-symbol summary: {str(e)}")
    
    def _log_block_details(self, index: int, block: Dict[str, Any], symbol: str):
        """Log detailed block information."""
        try:
            block_type = block.get('type', 'unknown')
            strength = block.get('enhanced_strength', block.get('strength', 0))
            
            # Format price range based on symbol
            if symbol == 'BTCUSDT':
                price_format = ":.2f"
            elif symbol == 'ETHUSDT':
                price_format = ":.2f"
            elif symbol == 'SOLUSDT':
                price_format = ":.3f"
            else:
                price_format = ":.4f"
            
            price_range = f"{block.get('low', 0):{price_format}} - {block.get('high', 0):{price_format}}"
            
            self.logger.info(f"  #{index} {block_type.upper()} Block:")
            self.logger.info(f"    💪 Enhanced Strength: {strength:.3f}")
            self.logger.info(f"    💰 Price Range: {price_range}")
            
            # Enhanced features
            if block.get('volume_confirmation', False):
                vol_mult = block.get('volume_multiplier', 1.0)
                self.logger.info(f"    📊 Volume Confirmed: ✅ ({vol_mult:.2f}x)")
            
            if block.get('fvg_present', False):
                fvg_strength = block.get('fvg_strength', 1.0)
                self.logger.info(f"    🕳️  FVG Present: ✅ ({fvg_strength:.2f})")
            
            if block.get('mtf_confirmation', {}).get('confirmed', False):
                confluence = block.get('mtf_confirmation', {}).get('confluence_score', 0)
                self.logger.info(f"    🔗 MTF Confirmed: ✅ ({confluence:.2f})")
            
            if block.get('sweep_info', {}).get('has_sweep', False):
                sweep_type = block.get('sweep_info', {}).get('sweep_type', 'unknown')
                sweep_strength = block.get('sweep_info', {}).get('sweep_strength', 0)
                self.logger.info(f"    💧 Liquidity Sweep: ✅ {sweep_type} ({sweep_strength:.3f})")
            
            if block.get('is_clustered', False):
                cluster_size = block.get('cluster_size', 1)
                self.logger.info(f"    🎯 Clustered: ✅ ({cluster_size} blocks)")
            
        except Exception as e:
            self.logger.error(f"Error logging block details for {symbol}: {str(e)}")

def main():
    """Main test execution."""
    try:
        test = InstitutionalPatternsTest()
        test.run_institutional_test()
        return 0
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 
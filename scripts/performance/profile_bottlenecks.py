#!/usr/bin/env python3
"""
Performance Bottleneck Profiler

This script uses cProfile and other profiling tools to identify performance bottlenecks
in the trading system codebase.
"""

import cProfile
import pstats
import io
import sys
import os
import time
import asyncio
import tracemalloc
import gc
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
import logging
from contextlib import asynccontextmanager

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import key modules to profile
try:
    from src.monitoring.monitor import MarketMonitor
    from src.analysis.core.confluence import ConfluenceAnalyzer
    from src.indicators.technical_indicators import TechnicalIndicators
    from src.indicators.volume_indicators import VolumeIndicators
    from src.core.exchanges.bybit import BybitExchange
    from src.core.market.market_data_manager import MarketDataManager
    from src.signal_generation.signal_generator import SignalGenerator
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

logger = logging.getLogger(__name__)

class PerformanceProfiler:
    """Comprehensive performance profiler for the trading system."""
    
    def __init__(self, output_dir: str = "performance_analysis"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
        
    def profile_function(self, func, *args, **kwargs):
        """Profile a single function call."""
        profiler = cProfile.Profile()
        
        # Start profiling
        profiler.enable()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            logger.error(f"Error profiling {func.__name__}: {e}")
        
        end_time = time.time()
        profiler.disable()
        
        # Analyze results
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        
        return {
            'function': func.__name__,
            'duration': end_time - start_time,
            'success': success,
            'result': result,
            'profile_stats': s.getvalue()
        }
    
    async def profile_async_function(self, func, *args, **kwargs):
        """Profile an async function call."""
        # Start memory tracking
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()
        
        profiler = cProfile.Profile()
        profiler.enable()
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            logger.error(f"Error profiling async {func.__name__}: {e}")
        
        end_time = time.time()
        profiler.disable()
        
        # Memory analysis
        snapshot_after = tracemalloc.take_snapshot()
        top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')
        memory_usage = sum(stat.size_diff for stat in top_stats) / 1024 / 1024  # MB
        
        # Profile analysis
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)
        
        tracemalloc.stop()
        
        return {
            'function': func.__name__,
            'duration': end_time - start_time,
            'memory_change_mb': memory_usage,
            'success': success,
            'result': result,
            'profile_stats': s.getvalue(),
            'top_memory_allocations': top_stats[:5]
        }

    def create_mock_market_data(self):
        """Create mock market data for testing."""
        import numpy as np
        
        # Create OHLCV data
        dates = pd.date_range(start='2024-01-01', periods=1000, freq='1min')
        base_price = 50000
        
        ohlcv_data = []
        for i in range(len(dates)):
            price = base_price + np.random.normal(0, 100) + np.sin(i/50) * 500
            high = price + abs(np.random.normal(0, 50))
            low = price - abs(np.random.normal(0, 50))
            close = price + np.random.normal(0, 20)
            volume = abs(np.random.normal(1000, 200))
            
            ohlcv_data.append({
                'timestamp': dates[i],
                'open': price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(ohlcv_data)
        df.set_index('timestamp', inplace=True)
        
        # Create mock market data structure
        market_data = {
            'symbol': 'BTCUSDT',
            'ohlcv': {
                'base': df,
                '1m': df,
                '5m': df.resample('5min').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                })
            },
            'ticker': {
                'symbol': 'BTCUSDT',
                'last': df['close'].iloc[-1],
                'bid': df['close'].iloc[-1] - 0.5,
                'ask': df['close'].iloc[-1] + 0.5,
                'volume': df['volume'].sum()
            },
            'orderbook': {
                'symbol': 'BTCUSDT',
                'bids': [[df['close'].iloc[-1] - i, 10.0] for i in range(1, 21)],
                'asks': [[df['close'].iloc[-1] + i, 10.0] for i in range(1, 21)]
            },
            'trades': [
                {
                    'price': df['close'].iloc[-1] + np.random.normal(0, 1),
                    'amount': abs(np.random.normal(1, 0.5)),
                    'side': 'buy' if i % 2 == 0 else 'sell',
                    'timestamp': time.time() * 1000 - i * 1000
                } for i in range(100)
            ]
        }
        
        return market_data

    async def profile_key_components(self):
        """Profile key system components."""
        print("Starting comprehensive performance profiling...")
        
        # Create mock data
        market_data = self.create_mock_market_data()
        
        results = {}
        
        # 1. Profile Technical Indicators
        print("Profiling Technical Indicators...")
        tech_indicators = TechnicalIndicators()
        results['technical_indicators'] = await self.profile_async_function(
            tech_indicators.calculate,
            market_data
        )
        
        # 2. Profile Volume Indicators
        print("Profiling Volume Indicators...")
        vol_indicators = VolumeIndicators()
        results['volume_indicators'] = await self.profile_async_function(
            vol_indicators.calculate,
            market_data
        )
        
        # 3. Profile Confluence Analysis
        print("Profiling Confluence Analysis...")
        try:
            confluence = ConfluenceAnalyzer()
            results['confluence_analysis'] = await self.profile_async_function(
                confluence.analyze,
                market_data
            )
        except Exception as e:
            print(f"Could not profile confluence analysis: {e}")
        
        # 4. Profile Signal Generation
        print("Profiling Signal Generation...")
        try:
            signal_gen = SignalGenerator()
            # Create mock indicators
            mock_indicators = {
                'symbol': 'BTCUSDT',
                'current_price': 50000,
                'momentum_score': 65.0,
                'volume_score': 70.0,
                'orderflow_score': 60.0,
                'sentiment_score': 55.0,
                'confluence_score': 62.5
            }
            results['signal_generation'] = await self.profile_async_function(
                signal_gen.generate_signal,
                mock_indicators
            )
        except Exception as e:
            print(f"Could not profile signal generation: {e}")
        
        return results

    def analyze_bottlenecks(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze profiling results to identify bottlenecks."""
        bottlenecks = []
        
        for component, data in results.items():
            if not data.get('success', False):
                continue
                
            duration = data.get('duration', 0)
            memory_change = data.get('memory_change_mb', 0)
            
            # Identify slow components (>100ms)
            if duration > 0.1:
                bottlenecks.append({
                    'component': component,
                    'type': 'slow_execution',
                    'duration': duration,
                    'severity': 'high' if duration > 1.0 else 'medium',
                    'recommendation': f"Optimize {component} - takes {duration:.3f}s"
                })
            
            # Identify memory-heavy components (>10MB)
            if memory_change > 10:
                bottlenecks.append({
                    'component': component,
                    'type': 'memory_usage',
                    'memory_mb': memory_change,
                    'severity': 'high' if memory_change > 50 else 'medium',
                    'recommendation': f"Reduce memory usage in {component} - uses {memory_change:.1f}MB"
                })
        
        return bottlenecks

    def generate_report(self, results: Dict[str, Any], bottlenecks: List[Dict[str, Any]]):
        """Generate a comprehensive performance report."""
        report_path = self.output_dir / "performance_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# Performance Analysis Report\n\n")
            f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary
            f.write("## Executive Summary\n\n")
            total_components = len(results)
            successful_components = sum(1 for r in results.values() if r.get('success', False))
            high_severity_issues = sum(1 for b in bottlenecks if b.get('severity') == 'high')
            
            f.write(f"- **Components Profiled**: {total_components}\n")
            f.write(f"- **Successful Profiles**: {successful_components}\n")
            f.write(f"- **High Severity Issues**: {high_severity_issues}\n\n")
            
            # Bottlenecks
            f.write("## Performance Bottlenecks\n\n")
            if bottlenecks:
                for bottleneck in sorted(bottlenecks, key=lambda x: x.get('duration', 0), reverse=True):
                    severity_emoji = "🔴" if bottleneck['severity'] == 'high' else "🟡"
                    f.write(f"{severity_emoji} **{bottleneck['component']}**\n")
                    f.write(f"- Type: {bottleneck['type']}\n")
                    if 'duration' in bottleneck:
                        f.write(f"- Duration: {bottleneck['duration']:.3f}s\n")
                    if 'memory_mb' in bottleneck:
                        f.write(f"- Memory Usage: {bottleneck['memory_mb']:.1f}MB\n")
                    f.write(f"- Recommendation: {bottleneck['recommendation']}\n\n")
            else:
                f.write("✅ No significant bottlenecks identified!\n\n")
            
            # Detailed Results
            f.write("## Detailed Profiling Results\n\n")
            for component, data in results.items():
                f.write(f"### {component}\n\n")
                f.write(f"- **Status**: {'✅ Success' if data.get('success') else '❌ Failed'}\n")
                f.write(f"- **Duration**: {data.get('duration', 0):.3f}s\n")
                if 'memory_change_mb' in data:
                    f.write(f"- **Memory Change**: {data['memory_change_mb']:.1f}MB\n")
                f.write("\n")
                
                # Top functions from profile
                if 'profile_stats' in data:
                    f.write("**Top Functions:**\n```\n")
                    # Extract first 10 lines of profile stats
                    lines = data['profile_stats'].split('\n')
                    for line in lines[:15]:
                        if line.strip():
                            f.write(line + '\n')
                    f.write("```\n\n")
        
        return report_path

    async def run_comprehensive_analysis(self):
        """Run the complete performance analysis."""
        print("🔍 Starting comprehensive performance analysis...")
        
        # Profile components
        results = await self.profile_key_components()
        
        # Analyze bottlenecks
        bottlenecks = self.analyze_bottlenecks(results)
        
        # Generate report
        report_path = self.generate_report(results, bottlenecks)
        
        # Save raw results
        import json
        with open(self.output_dir / "raw_results.json", 'w') as f:
            # Convert non-serializable data
            serializable_results = {}
            for k, v in results.items():
                serializable_results[k] = {
                    'function': v.get('function'),
                    'duration': v.get('duration'),
                    'memory_change_mb': v.get('memory_change_mb'),
                    'success': v.get('success')
                }
            json.dump(serializable_results, f, indent=2)
        
        print(f"✅ Analysis complete! Report saved to: {report_path}")
        print(f"📊 Raw data saved to: {self.output_dir / 'raw_results.json'}")
        
        # Print summary
        print("\n" + "="*60)
        print("PERFORMANCE SUMMARY")
        print("="*60)
        
        for component, data in results.items():
            status = "✅" if data.get('success') else "❌"
            duration = data.get('duration', 0)
            memory = data.get('memory_change_mb', 0)
            print(f"{status} {component}: {duration:.3f}s, {memory:.1f}MB")
        
        if bottlenecks:
            print(f"\n🔴 Found {len(bottlenecks)} performance issues")
            for bottleneck in bottlenecks[:3]:  # Top 3
                print(f"   - {bottleneck['component']}: {bottleneck['recommendation']}")
        else:
            print("\n✅ No significant performance issues found!")
        
        return results, bottlenecks

async def main():
    """Main entry point."""
    logging.basicConfig(level=logging.INFO)
    
    profiler = PerformanceProfiler()
    
    try:
        await profiler.run_comprehensive_analysis()
    except KeyboardInterrupt:
        print("\n⚠️ Analysis interrupted by user")
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
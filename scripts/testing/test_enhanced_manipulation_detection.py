"""Test Enhanced Manipulation Detection Features

This script tests the Week 3-4 enhancements including:
- Trade correlation analysis
- Enhanced wash trading detection
- Fake liquidity detection
- Iceberg order detection
- Performance optimization with caching
"""

import asyncio
import ccxt.async_support as ccxt
import logging
import sys
import os
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.enhanced_manipulation_detector import EnhancedManipulationDetector
from src.indicators.cached_manipulation_detector import CachedManipulationDetector, ManipulationDetectorPool
from src.core.logger import setup_logger

console = Console()


class EnhancedManipulationTester:
    """Test enhanced manipulation detection features"""
    
    def __init__(self, exchange_id: str = 'bybit', symbols: list = None):
        self.exchange_id = exchange_id
        self.symbols = symbols or ['BTC/USDT', 'ETH/USDT']
        self.exchange = None
        self.logger = setup_logger('EnhancedManipulationTester')
        
        # Detection components
        self.detector_pool = None
        self.detection_results = {}
        
    async def initialize(self):
        """Initialize exchange and detector pool"""
        # Initialize exchange
        self.exchange = getattr(ccxt, self.exchange_id)({
            'enableRateLimit': True,
            'options': {'defaultType': 'linear'}
        })
        
        await self.exchange.load_markets()
        
        # Initialize detector pool
        config = {
            'manipulation_detection': {
                'enabled': True,
                'history': {'max_snapshots': 100},
                'spoofing': {'enabled': True},
                'layering': {'enabled': True},
                'wash_trading': {'enabled': True},
                'fake_liquidity': {'enabled': True},
                'iceberg': {'enabled': True},
                'trade_correlation': {'enabled': True}
            }
        }
        
        self.detector_pool = ManipulationDetectorPool(config, self.logger, pool_size=3)
        
        console.print(f"[green]Initialized {self.exchange_id} with detector pool[/green]")
    
    async def fetch_market_data(self, symbol: str) -> dict:
        """Fetch orderbook and trades for a symbol"""
        try:
            # Fetch data in parallel
            orderbook_task = self.exchange.fetch_order_book(symbol, limit=25)
            trades_task = self.exchange.fetch_trades(symbol, limit=100)
            
            orderbook, trades = await asyncio.gather(orderbook_task, trades_task)
            
            return {
                'symbol': symbol,
                'orderbook': {
                    'bids': orderbook['bids'],
                    'asks': orderbook['asks'],
                    'timestamp': orderbook['timestamp']
                },
                'trades': [
                    {
                        'id': trade['id'],
                        'price': trade['price'],
                        'size': trade['amount'],
                        'side': trade['side'],
                        'timestamp': trade['timestamp']
                    }
                    for trade in trades
                ]
            }
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None
    
    def create_enhanced_display(self, symbol: str, result: dict) -> Panel:
        """Create enhanced display with all detection types"""
        # Create main table
        table = Table(title=f"{symbol} - Enhanced Manipulation Analysis")
        table.add_column("Detection Type", style="cyan", width=25)
        table.add_column("Likelihood", style="white", width=15)
        table.add_column("Status", style="white", width=15)
        table.add_column("Key Indicators", style="white", width=40)
        
        # Overall status
        overall = result.get('overall_likelihood', 0)
        severity = result.get('severity', 'NONE')
        severity_color = {
            'NONE': 'green',
            'LOW': 'yellow',
            'MEDIUM': 'orange1',
            'HIGH': 'red',
            'CRITICAL': 'red bold'
        }.get(severity, 'white')
        
        table.add_row(
            "OVERALL",
            f"{overall:.1%}",
            f"[{severity_color}]{severity}[/{severity_color}]",
            f"Type: {result.get('manipulation_type', 'none').upper()}"
        )
        table.add_section()
        
        # Spoofing
        spoofing = result.get('spoofing', {})
        table.add_row(
            "Spoofing",
            f"{spoofing.get('likelihood', 0):.1%}",
            "🚨" if spoofing.get('detected', False) else "✓",
            f"Volatility: {spoofing.get('volatility_ratio', 0):.2f}, "
            f"Phantoms: {spoofing.get('phantom_orders', {}).get('count', 0)}"
        )
        
        # Layering
        layering = result.get('layering', {})
        table.add_row(
            "Layering",
            f"{layering.get('likelihood', 0):.1%}",
            "🚨" if layering.get('detected', False) else "✓",
            f"Bid: {layering.get('bid_side', {}).get('likelihood', 0):.0%}, "
            f"Ask: {layering.get('ask_side', {}).get('likelihood', 0):.0%}"
        )
        
        # Wash Trading
        wash = result.get('wash_trading', {})
        table.add_row(
            "Wash Trading",
            f"{wash.get('likelihood', 0):.1%}",
            "🚨" if wash.get('detected', False) else "✓",
            f"Patterns: {wash.get('pattern_count', 0)}, "
            f"Groups: {wash.get('fingerprint_groups', 0)}"
        )
        
        # Fake Liquidity
        fake_liq = result.get('fake_liquidity', {})
        table.add_row(
            "Fake Liquidity",
            f"{fake_liq.get('likelihood', 0):.1%}",
            "🚨" if fake_liq.get('detected', False) else "✓",
            f"Withdrawals: {fake_liq.get('withdrawal_events', 0)}, "
            f"Phantom Ratio: {fake_liq.get('phantom_ratio', 0):.1%}"
        )
        
        # Iceberg Orders
        iceberg = result.get('iceberg_orders', {})
        table.add_row(
            "Iceberg Orders",
            f"{iceberg.get('likelihood', 0):.1%}",
            "🚨" if iceberg.get('detected', False) else "✓",
            f"Candidates: {iceberg.get('candidate_count', 0)}, "
            f"Refills: {iceberg.get('total_refills', 0)}"
        )
        
        table.add_section()
        
        # Trade Correlation
        correlation = result.get('trade_correlation', {})
        table.add_row(
            "Trade Correlation",
            f"{correlation.get('correlation_score', 0):.1%}",
            "📊",
            f"Matched: {correlation.get('matched_trades', 0)}, "
            f"Accuracy: {correlation.get('accuracy_trend', 0):.1%}"
        )
        
        # Trade Patterns
        patterns = result.get('trade_patterns', {})
        table.add_row(
            "Trade Patterns",
            f"{patterns.get('pattern_score', 0):.1%}",
            "🔥" if patterns.get('burst_detected', False) else "📈",
            f"Velocity: {patterns.get('velocity', 0):.1f}/s, "
            f"Clusters: {len(patterns.get('clusters', []))}"
        )
        
        # Advanced Metrics
        metrics = result.get('advanced_metrics', {})
        table.add_section()
        table.add_row(
            "Tracking",
            "-",
            "📍",
            f"Orders: {metrics.get('tracked_orders', 0)}, "
            f"Phantoms: {metrics.get('phantom_orders', 0)}"
        )
        
        # Performance
        perf = result.get('performance', {})
        if perf:
            table.add_row(
                "Performance",
                "-",
                "⚡",
                f"Time: {perf.get('analysis_time_ms', 0):.1f}ms, "
                f"Cache: {perf.get('cache_hit_rate', 0):.0%}"
            )
        
        return Panel(table, border_style="green" if overall < 0.5 else "red")
    
    async def run_continuous_analysis(self, duration_seconds: int = 60):
        """Run continuous analysis on multiple symbols"""
        console.print(f"[yellow]Starting enhanced analysis for {duration_seconds} seconds...[/yellow]")
        
        start_time = datetime.now()
        analysis_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task(
                f"Analyzing {len(self.symbols)} symbols", 
                total=duration_seconds
            )
            
            while (datetime.now() - start_time).seconds < duration_seconds:
                # Fetch data for all symbols
                market_data_tasks = [
                    self.fetch_market_data(symbol) for symbol in self.symbols
                ]
                market_data_list = await asyncio.gather(*market_data_tasks)
                
                # Analyze each symbol
                for i, (symbol, data) in enumerate(zip(self.symbols, market_data_list)):
                    if data:
                        result = await self.detector_pool.analyze_symbol(
                            symbol,
                            data['orderbook'],
                            data['trades']
                        )
                        
                        self.detection_results[symbol] = result
                        analysis_count += 1
                        
                        # Display results
                        console.print(self.create_enhanced_display(symbol, result))
                
                # Update progress
                elapsed = (datetime.now() - start_time).seconds
                progress.update(task, completed=elapsed)
                
                # Show pool statistics periodically
                if analysis_count % 10 == 0:
                    self._show_pool_stats()
                
                await asyncio.sleep(1)
        
        # Final statistics
        self._show_final_stats(analysis_count, duration_seconds)
    
    def _show_pool_stats(self):
        """Display detector pool statistics"""
        stats = self.detector_pool.get_pool_stats()
        
        table = Table(title="Detector Pool Statistics")
        table.add_column("Detector", style="cyan")
        table.add_column("Symbols", style="white")
        table.add_column("Cache Hit Rate", style="green")
        table.add_column("Avg Time", style="yellow")
        
        for detector_stats in stats['detectors']:
            symbols = ", ".join(detector_stats['assigned_symbols'])
            table.add_row(
                f"#{detector_stats['detector_id']}",
                symbols or "None",
                f"{detector_stats.get('cache_hit_rate', 0):.1%}",
                f"{detector_stats.get('avg_analysis_time_ms', 0):.1f}ms"
            )
        
        console.print(table)
    
    def _show_final_stats(self, analysis_count: int, duration: int):
        """Show final analysis statistics"""
        console.print("\n[bold cyan]Final Analysis Statistics[/bold cyan]")
        
        # Detection summary
        total_detections = 0
        detection_types = {}
        
        for symbol, results in self.detection_results.items():
            if results.get('overall_likelihood', 0) > 0.5:
                total_detections += 1
                mtype = results.get('manipulation_type', 'unknown')
                detection_types[mtype] = detection_types.get(mtype, 0) + 1
        
        table = Table(title="Detection Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Total Analyses", str(analysis_count))
        table.add_row("Analysis Rate", f"{analysis_count/duration:.1f}/s")
        table.add_row("Symbols Monitored", str(len(self.symbols)))
        table.add_row("Total Detections", str(total_detections))
        table.add_row("Detection Rate", f"{total_detections/analysis_count*100:.1f}%")
        
        table.add_section()
        for mtype, count in detection_types.items():
            table.add_row(f"{mtype.title()} Detections", str(count))
        
        console.print(table)
        
        # Pool performance
        pool_stats = self.detector_pool.get_pool_stats()
        console.print(f"\n[cyan]Pool Size:[/cyan] {pool_stats['pool_size']} detectors")
        
        total_cache_hits = sum(d['cache_hits'] for d in pool_stats['detectors'])
        total_cache_misses = sum(d['cache_misses'] for d in pool_stats['detectors'])
        overall_hit_rate = total_cache_hits / (total_cache_hits + total_cache_misses) if (total_cache_hits + total_cache_misses) > 0 else 0
        
        console.print(f"[green]Overall Cache Hit Rate:[/green] {overall_hit_rate:.1%}")
    
    async def test_specific_patterns(self):
        """Test specific manipulation patterns"""
        console.print("\n[bold yellow]Testing Specific Manipulation Patterns[/bold yellow]")
        
        # Test data for different patterns
        test_cases = [
            {
                'name': 'Spoofing Pattern',
                'orderbook': {
                    'bids': [[100.0, 1000.0]] + [[99.9 - i*0.1, 10.0] for i in range(24)],
                    'asks': [[100.1 + i*0.1, 10.0] for i in range(25)],
                    'timestamp': datetime.now().timestamp() * 1000
                },
                'trades': []
            },
            {
                'name': 'Layering Pattern',
                'orderbook': {
                    'bids': [[100.0 - i*0.01, 50.0] for i in range(25)],
                    'asks': [[100.1 + i*0.01, 50.0] for i in range(25)],
                    'timestamp': datetime.now().timestamp() * 1000
                },
                'trades': []
            },
            {
                'name': 'Wash Trading Pattern',
                'orderbook': {
                    'bids': [[100.0 - i*0.1, 10.0] for i in range(25)],
                    'asks': [[100.1 + i*0.1, 10.0] for i in range(25)],
                    'timestamp': datetime.now().timestamp() * 1000
                },
                'trades': [
                    {
                        'id': f'trade_{i}',
                        'price': 100.0,
                        'size': 10.0,
                        'side': 'buy' if i % 2 == 0 else 'sell',
                        'timestamp': (datetime.now().timestamp() - i) * 1000
                    }
                    for i in range(10)
                ]
            }
        ]
        
        for test_case in test_cases:
            console.print(f"\n[cyan]Testing: {test_case['name']}[/cyan]")
            
            detector = self.detector_pool.get_detector('TEST')
            result = await detector.analyze_manipulation(
                test_case['orderbook'],
                test_case['trades']
            )
            
            console.print(self.create_enhanced_display('TEST', result))
    
    async def close(self):
        """Close exchange connection"""
        if self.exchange:
            await self.exchange.close()


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test enhanced manipulation detection')
    parser.add_argument('--symbols', nargs='+', default=['BTC/USDT', 'ETH/USDT'], 
                       help='Symbols to monitor')
    parser.add_argument('--exchange', default='bybit', help='Exchange to use')
    parser.add_argument('--duration', type=int, default=30, 
                       help='Analysis duration in seconds')
    parser.add_argument('--test-patterns', action='store_true', 
                       help='Test specific manipulation patterns')
    
    args = parser.parse_args()
    
    tester = EnhancedManipulationTester(args.exchange, args.symbols)
    
    try:
        await tester.initialize()
        
        if args.test_patterns:
            await tester.test_specific_patterns()
        else:
            await tester.run_continuous_analysis(args.duration)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        await tester.close()


if __name__ == '__main__':
    asyncio.run(main())
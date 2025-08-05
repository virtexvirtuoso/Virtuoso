"""Test Order Book Manipulation Detection with Live Market Data

This script connects to a live exchange (Bybit) and monitors orderbook
data for manipulation patterns like spoofing and layering.
"""

import asyncio
import ccxt.async_support as ccxt
import logging
import sys
import os
from datetime import datetime
import json
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.orderbook_indicators import OrderbookIndicators
from src.core.logger import Logger
import logging

console = Console()

class ManipulationMonitor:
    """Monitor live orderbook data for manipulation patterns"""
    
    def __init__(self, exchange_id: str = 'bybit', symbol: str = 'BTC/USDT'):
        self.exchange_id = exchange_id
        self.symbol = symbol
        self.exchange = None
        self.orderbook_indicators = None
        self.logger = logging.getLogger('ManipulationMonitor')
        self.logger.setLevel(logging.INFO)
        self.detection_history = []
        
    async def initialize(self):
        """Initialize exchange connection and indicators"""
        # Initialize exchange
        self.exchange = getattr(ccxt, self.exchange_id)({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'linear'  # For perpetual futures
            }
        })
        
        # Load markets
        await self.exchange.load_markets()
        
        # Initialize orderbook indicators with manipulation detection
        config = {
            'analysis': {
                'indicators': {
                    'orderbook': {
                        'manipulation_detection': {
                            'enabled': True,
                            'history': {
                                'max_snapshots': 100
                            },
                            'spoofing': {
                                'enabled': True,
                                'volatility_threshold': 2.0,
                                'min_order_size_usd': 50000
                            },
                            'layering': {
                                'enabled': True,
                                'price_gap_threshold': 0.001,
                                'min_layers': 3
                            }
                        }
                    }
                }
            }
        }
        
        self.orderbook_indicators = OrderbookIndicators(config, self.logger)
        console.print(f"[green]Initialized {self.exchange_id} for {self.symbol}[/green]")
    
    async def fetch_market_data(self) -> dict:
        """Fetch current orderbook and recent trades"""
        try:
            # Fetch orderbook
            orderbook = await self.exchange.fetch_order_book(self.symbol, limit=25)
            
            # Fetch recent trades
            trades = await self.exchange.fetch_trades(self.symbol, limit=50)
            
            # Format for indicators
            market_data = {
                'symbol': self.symbol,
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
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market data: {str(e)}")
            return None
    
    def create_display_table(self, result: dict) -> Table:
        """Create a rich table displaying manipulation detection results"""
        table = Table(title=f"Manipulation Detection - {self.symbol}")
        
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", style="white", width=20)
        table.add_column("Status", style="white", width=15)
        
        # Overall metrics
        manipulation_data = result.get('manipulation_analysis', {})
        overall_likelihood = manipulation_data.get('overall_likelihood', 0)
        manipulation_type = manipulation_data.get('manipulation_type', 'none')
        severity = manipulation_data.get('severity', 'NONE')
        
        # Color code severity
        severity_color = {
            'NONE': 'white',
            'LOW': 'yellow',
            'MEDIUM': 'orange1',
            'HIGH': 'red',
            'CRITICAL': 'red bold'
        }.get(severity, 'white')
        
        table.add_row(
            "Overall Likelihood",
            f"{overall_likelihood:.1%}",
            f"[{severity_color}]{severity}[/{severity_color}]"
        )
        
        table.add_row(
            "Manipulation Type",
            manipulation_type.upper() if manipulation_type != 'none' else 'None Detected',
            "🚨" if overall_likelihood > 0.5 else "✅"
        )
        
        # Spoofing details
        spoofing_data = manipulation_data.get('spoofing', {})
        if spoofing_data:
            table.add_section()
            table.add_row("SPOOFING ANALYSIS", "", "")
            table.add_row(
                "  Likelihood",
                f"{spoofing_data.get('likelihood', 0):.1%}",
                "⚠️" if spoofing_data.get('detected', False) else "✓"
            )
            table.add_row(
                "  Volatility Ratio",
                f"{spoofing_data.get('volatility_ratio', 0):.2f}",
                ""
            )
            table.add_row(
                "  Execution Ratio",
                f"{spoofing_data.get('execution_ratio', 0):.1%}",
                ""
            )
            table.add_row(
                "  Reversals",
                str(spoofing_data.get('reversals', 0)),
                ""
            )
        
        # Layering details
        layering_data = manipulation_data.get('layering', {})
        if layering_data:
            table.add_section()
            table.add_row("LAYERING ANALYSIS", "", "")
            table.add_row(
                "  Likelihood",
                f"{layering_data.get('likelihood', 0):.1%}",
                "⚠️" if layering_data.get('detected', False) else "✓"
            )
            
            # Bid side
            bid_side = layering_data.get('bid_side', {})
            if bid_side:
                table.add_row(
                    "  Bid Side Likelihood",
                    f"{bid_side.get('likelihood', 0):.1%}",
                    ""
                )
                table.add_row(
                    "  Bid Layers Analyzed",
                    str(bid_side.get('layers_analyzed', 0)),
                    ""
                )
            
            # Ask side
            ask_side = layering_data.get('ask_side', {})
            if ask_side:
                table.add_row(
                    "  Ask Side Likelihood",
                    f"{ask_side.get('likelihood', 0):.1%}",
                    ""
                )
        
        # Component scores
        table.add_section()
        table.add_row("COMPONENT SCORES", "", "")
        components = result.get('components', {})
        for component, score in components.items():
            if component == 'manipulation':
                table.add_row(
                    f"  {component.title()}",
                    f"{score:.1f}",
                    "🔍"
                )
            else:
                table.add_row(
                    f"  {component.title()}",
                    f"{score:.1f}",
                    ""
                )
        
        # Overall score and confidence
        table.add_section()
        table.add_row(
            "Overall Score",
            f"{result.get('score', 50):.1f}",
            "📊"
        )
        table.add_row(
            "Confidence",
            f"{result.get('confidence', 0):.1f}%",
            "🎯"
        )
        
        return table
    
    def create_history_panel(self) -> Panel:
        """Create a panel showing detection history"""
        if not self.detection_history:
            return Panel("No manipulations detected yet", title="Detection History")
        
        history_text = ""
        for i, detection in enumerate(self.detection_history[-5:]):  # Last 5 detections
            history_text += (
                f"[{detection['timestamp']}] "
                f"{detection['type'].upper()} - "
                f"Likelihood: {detection['likelihood']:.1%} - "
                f"Severity: {detection['severity']}\n"
            )
        
        return Panel(history_text.strip(), title="Recent Detections")
    
    async def monitor_continuous(self, interval: int = 1):
        """Continuously monitor for manipulation patterns"""
        console.print("[yellow]Starting continuous monitoring...[/yellow]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                try:
                    # Fetch market data
                    market_data = await self.fetch_market_data()
                    if not market_data:
                        await asyncio.sleep(interval)
                        continue
                    
                    # Calculate indicators with manipulation detection
                    result = await self.orderbook_indicators.calculate(market_data)
                    
                    # Check for significant manipulation
                    manipulation_data = result.get('manipulation_analysis', {})
                    if manipulation_data.get('overall_likelihood', 0) > 0.5:
                        detection = {
                            'timestamp': datetime.now().strftime('%H:%M:%S'),
                            'type': manipulation_data.get('manipulation_type', 'unknown'),
                            'likelihood': manipulation_data.get('overall_likelihood', 0),
                            'severity': manipulation_data.get('severity', 'UNKNOWN')
                        }
                        self.detection_history.append(detection)
                        
                        # Alert
                        console.bell()
                        console.print(
                            f"\n[red bold]⚠️  MANIPULATION DETECTED: "
                            f"{detection['type'].upper()} "
                            f"({detection['likelihood']:.1%})[/red bold]\n"
                        )
                    
                    # Create display
                    layout = Layout()
                    layout.split_column(
                        Layout(self.create_display_table(result), name="main"),
                        Layout(self.create_history_panel(), name="history", size=8)
                    )
                    
                    live.update(layout)
                    
                    # Wait before next update
                    await asyncio.sleep(interval)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
                    await asyncio.sleep(interval)
    
    async def run_single_analysis(self):
        """Run a single analysis and display results"""
        console.print("[yellow]Fetching market data...[/yellow]")
        
        market_data = await self.fetch_market_data()
        if not market_data:
            console.print("[red]Failed to fetch market data[/red]")
            return
        
        console.print("[yellow]Analyzing for manipulation patterns...[/yellow]")
        result = await self.orderbook_indicators.calculate(market_data)
        
        # Display results
        console.print(self.create_display_table(result))
        
        # Show raw data if manipulation detected
        manipulation_data = result.get('manipulation_analysis', {})
        if manipulation_data.get('overall_likelihood', 0) > 0.5:
            console.print("\n[yellow]Raw Manipulation Data:[/yellow]")
            console.print(json.dumps(manipulation_data, indent=2))
    
    async def close(self):
        """Close exchange connection"""
        if self.exchange:
            await self.exchange.close()


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test manipulation detection with live data')
    parser.add_argument('--symbol', default='BTC/USDT', help='Trading symbol (default: BTC/USDT)')
    parser.add_argument('--exchange', default='bybit', help='Exchange to use (default: bybit)')
    parser.add_argument('--interval', type=int, default=1, help='Update interval in seconds')
    parser.add_argument('--single', action='store_true', help='Run single analysis instead of continuous')
    
    args = parser.parse_args()
    
    monitor = ManipulationMonitor(args.exchange, args.symbol)
    
    try:
        await monitor.initialize()
        
        if args.single:
            await monitor.run_single_analysis()
        else:
            await monitor.monitor_continuous(args.interval)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        await monitor.close()


if __name__ == '__main__':
    asyncio.run(main())
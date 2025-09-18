"""
Refactored Market Monitor

This is the new, simplified MarketMonitor class that uses the extracted components:
- SignalProcessor for analysis and signal generation
- MonitoringWebSocketManager for real-time data
- MetricsTracker for system health and performance monitoring

This refactored version maintains the same interface while delegating functionality
to specialized components.
"""

import asyncio
import logging
import signal
import sys
import time
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.monitoring.signal_processor import SignalProcessor
from src.monitoring.websocket_manager import MonitoringWebSocketManager
from src.monitoring.metrics_tracker import MetricsTracker
from src.monitoring.alert_manager import AlertManager
from src.monitoring.metrics_manager import MetricsManager
from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.market_reporter import MarketReporter
from src.monitoring.data_collector import DataCollector
from src.monitoring.validator import MarketDataValidator
from src.monitoring.utils.logging import LoggingUtility
from src.monitoring.utils.timestamp import TimestampUtility

from src.core.analysis.confluence import ConfluenceAnalyzer
from src.core.market.market_data_manager import MarketDataManager
from src.core.interpretation.interpretation_manager import InterpretationManager
from src.signal_generation.signal_generator import SignalGenerator
from src.core.market.top_symbols import TopSymbolsManager


class MarketMonitor:
    """
    Refactored Market Monitor using extracted components.
    
    This class orchestrates market monitoring by coordinating specialized components
    for signal processing, WebSocket management, metrics tracking, and more.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        exchange_manager=None,
        symbol: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the refactored Market Monitor.
        
        Args:
            config: Configuration dictionary
            exchange_manager: Exchange manager instance
            symbol: Trading symbol to monitor
            **kwargs: Additional configuration options
        """
        self.config = config
        self.exchange_manager = exchange_manager
        self.symbol = symbol
        self.symbol_str = symbol
        self.exchange_id = config.get('exchange', 'bybit')
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize utilities
        self.logging_utility = LoggingUtility(self.logger)
        self.timestamp_utility = TimestampUtility()
        
        # Initialize core components
        self._initialize_core_components()
        
        # Initialize extracted components
        self._initialize_extracted_components()
        
        # Runtime state
        self.running = False
        self.interval = config.get('monitoring_interval', 30)  # seconds
        self._analysis_tasks = set()
        self._task_stats = {
            'total_created': 0,
            'total_completed': 0,
            'currently_running': 0,
            'failed': 0
        }
        
        # Register signal handlers for graceful shutdown
        self._register_signal_handlers()
        
        self.logger.info("Refactored Market Monitor initialized")

    def _initialize_core_components(self):
        """Initialize core system components."""
        # Initialize managers
        self.metrics_manager = MetricsManager(self.config)
        self.alert_manager = AlertManager(self.config)
        self.health_monitor = HealthMonitor(self.config)
        self.market_reporter = MarketReporter(self.config)
        
        # Initialize market components
        self.market_data_manager = MarketDataManager(
            config=self.config,
            exchange_manager=self.exchange_manager
        )
        
        self.confluence_analyzer = ConfluenceAnalyzer(
            config=self.config.get('confluence', {}),
            market_data_manager=self.market_data_manager
        )
        
        self.interpretation_manager = InterpretationManager(self.config)
        self.signal_generator = SignalGenerator(self.config)
        
        # Initialize data handling components
        self.data_collector = DataCollector(
            config=self.config,
            market_data_manager=self.market_data_manager,
            logger=self.logger
        )
        
        self.validator = MarketDataValidator(self.config, self.logger)
        
        self.logger.info("Core components initialized")

    def _initialize_extracted_components(self):
        """Initialize the extracted specialized components."""
        # Initialize Signal Processor
        self.signal_processor = SignalProcessor(
            config=self.config,
            signal_generator=self.signal_generator,
            metrics_manager=self.metrics_manager,
            interpretation_manager=self.interpretation_manager,
            market_data_manager=self.market_data_manager,
            logger=self.logger
        )
        
        # Initialize WebSocket Manager
        self.websocket_manager = MonitoringWebSocketManager(
            config=self.config,
            symbol=self.symbol,
            exchange_id=self.exchange_id,
            timestamp_utility=self.timestamp_utility,
            metrics_manager=self.metrics_manager,
            health_monitor=self.health_monitor,
            logger=self.logger
        )
        
        # Initialize Metrics Tracker
        self.metrics_tracker = MetricsTracker(
            config=self.config,
            metrics_manager=self.metrics_manager,
            market_data_manager=self.market_data_manager,
            exchange_manager=self.exchange_manager,
            logger=self.logger
        )
        
        self.logger.info("Extracted components initialized")

    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
            if self.running:
                asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def start(self):
        """Start the market monitor."""
        try:
            self.logger.info("Starting Market Monitor...")
            self.running = True
            
            # Initialize WebSocket connection
            await self.websocket_manager.initialize()
            
            # Start monitoring loop
            await self._run_monitoring_loop()
            
        except Exception as e:
            self.logger.error(f"Error in Market Monitor start: {str(e)}")
            self.logger.debug(traceback.format_exc())
            await self.stop()

    async def _run_monitoring_loop(self):
        """Main monitoring loop."""
        self.logger.info("Starting monitoring loop...")
        
        while self.running:
            try:
                cycle_start_time = time.time()
                
                # Run monitoring cycle
                await self._monitoring_cycle()
                
                # Update metrics
                await self.metrics_tracker.update_metrics()
                
                # Check system health
                health_status = await self.metrics_tracker.check_system_health()
                if health_status['status'] != 'healthy':
                    self.logger.warning(f"System health check: {health_status['status']}")
                    # Generate alert if critical
                    if health_status['status'] == 'critical':
                        await self._generate_health_alert(health_status)
                
                # Check thresholds and generate alerts
                alerts = await self.metrics_tracker.check_thresholds()
                for alert in alerts:
                    await self._handle_threshold_alert(alert)
                
                # Calculate sleep time to maintain interval
                cycle_duration = time.time() - cycle_start_time
                sleep_time = max(0, self.interval - cycle_duration)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    self.logger.warning(f"Monitoring cycle took {cycle_duration:.2f}s, longer than interval {self.interval}s")
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                self.logger.debug(traceback.format_exc())
                await asyncio.sleep(5)  # Brief pause before retry

    async def _monitoring_cycle(self):
        """Run a single monitoring cycle."""
        try:
            self.logger.debug("Starting monitoring cycle")
            
            if self.symbol:
                # Process single symbol
                await self._process_symbol(self.symbol)
            else:
                # Process multiple symbols from top symbols manager
                top_symbols_manager = TopSymbolsManager()
                symbols = await top_symbols_manager.get_top_symbols()
                
                for symbol in symbols:
                    if not self.running:
                        break
                    await self._process_symbol(symbol)
            
            self.logger.debug("Completed monitoring cycle")
            
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _process_symbol(self, symbol: str) -> None:
        """Process a single symbol with market data and analysis."""
        try:
            self.logger.info(f"=== Processing {symbol} ===")
            
            # Collect market data
            market_data = await self.data_collector.collect_market_data(symbol)
            if not market_data:
                self.logger.warning(f"No market data available for {symbol}")
                return
            
            # Validate market data
            if not await self.validator.validate_market_data(market_data):
                self.logger.warning(f"Market data validation failed for {symbol}")
                self.metrics_tracker.record_message(is_valid=False)
                return
            
            self.metrics_tracker.record_message(is_valid=True)
            
            # Convert symbol format for analysis
            symbol_str = symbol if isinstance(symbol, str) else str(symbol)
            
            # Perform confluence analysis
            self.logger.info(f"Starting confluence analysis for {symbol_str}")
            analysis_result = await self.confluence_analyzer.analyze(market_data, symbol_str)
            
            if analysis_result:
                # Process analysis results and generate signals
                await self.signal_processor.process_analysis_result(symbol_str, analysis_result)
                
                # Monitor for whale activity (if applicable)
                await self._monitor_whale_activity(symbol_str, market_data)
                
                self.logger.info(f"=== Completed analysis process for {symbol_str} ===")
            else:
                self.logger.warning(f"No analysis result for {symbol_str}")
            
        except Exception as e:
            self.logger.error(f"Error processing symbol {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.metrics_tracker.record_error()

    async def _monitor_whale_activity(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """Monitor whale activity using market data."""
        try:
            # This is a placeholder for whale activity monitoring
            # Implementation would analyze large orders and unusual trading patterns
            orderbook = market_data.get('orderbook', {})
            trades = market_data.get('trades', [])
            
            # Analyze for large orders or unusual volume
            if orderbook and trades:
                # Simple whale detection based on order size
                large_orders = []
                for trade in trades[-10:]:  # Check last 10 trades
                    if isinstance(trade, dict) and 'amount' in trade and 'price' in trade:
                        trade_value = float(trade['amount']) * float(trade['price'])
                        if trade_value > 100000:  # $100k threshold
                            large_orders.append(trade)
                
                if large_orders:
                    self.logger.info(f"Detected {len(large_orders)} large orders for {symbol}")
                    # Generate whale activity alert
                    await self._generate_whale_alert(symbol, large_orders)
            
        except Exception as e:
            self.logger.error(f"Error monitoring whale activity for {symbol}: {str(e)}")

    async def _generate_health_alert(self, health_status: Dict[str, Any]) -> None:
        """Generate alert for system health issues."""
        try:
            message = f"System health status: {health_status['status']}"
            if 'summary' in health_status and 'issues' in health_status['summary']:
                issues = health_status['summary']['issues']
                if issues:
                    message += f"\nIssues: {len(issues)}"
                    for issue in issues[:3]:  # Show first 3 issues
                        message += f"\n- {issue['component']}: {issue['message']}"
            
            await self.alert_manager.send_alert(
                title="System Health Alert",
                message=message,
                severity="critical" if health_status['status'] == 'critical' else "warning"
            )
            
        except Exception as e:
            self.logger.error(f"Error generating health alert: {str(e)}")

    async def _handle_threshold_alert(self, alert: Dict[str, Any]) -> None:
        """Handle threshold violation alerts."""
        try:
            message = alert.get('message', 'Threshold violation detected')
            severity = alert.get('severity', 'warning')
            
            await self.alert_manager.send_alert(
                title=f"Threshold Alert: {alert.get('component', 'Unknown')}",
                message=message,
                severity=severity
            )
            
        except Exception as e:
            self.logger.error(f"Error handling threshold alert: {str(e)}")

    async def _generate_whale_alert(self, symbol: str, large_orders: List[Dict[str, Any]]) -> None:
        """Generate alert for whale activity."""
        try:
            total_value = sum(float(order['amount']) * float(order['price']) for order in large_orders)
            message = f"Whale activity detected on {symbol}: {len(large_orders)} large orders, total value: ${total_value:,.2f}"
            
            await self.alert_manager.send_alert(
                title=f"Whale Alert: {symbol}",
                message=message,
                severity="info"
            )
            
        except Exception as e:
            self.logger.error(f"Error generating whale alert: {str(e)}")

    async def stop(self) -> None:
        """Stop the market monitor."""
        self.logger.info("Stopping Market Monitor...")
        self.running = False
        
        try:
            # Close WebSocket connections
            await self.websocket_manager.close()
            
            # Clean up analysis tasks
            await self._cleanup_analysis_tasks()
            
            # Close other components
            if hasattr(self.market_data_manager, 'close'):
                await self.market_data_manager.close()
            
            self.logger.info("Market Monitor stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping Market Monitor: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _cleanup_analysis_tasks(self):
        """Clean up any remaining analysis tasks."""
        if self._analysis_tasks:
            self.logger.info(f"Cleaning up {len(self._analysis_tasks)} analysis tasks...")
            
            for task in list(self._analysis_tasks):
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        self.logger.error(f"Error cancelling task: {str(e)}")
            
            self._analysis_tasks.clear()

    # Public interface methods for backward compatibility
    
    def get_websocket_status(self) -> Dict[str, Any]:
        """Get current WebSocket status."""
        return self.websocket_manager.get_websocket_status()

    def stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        stats = self.metrics_tracker.get_stats()
        stats['analysis_tasks'] = self._task_stats.copy()
        return stats

    async def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate market data."""
        return await self.validator.validate_market_data(market_data)

    async def fetch_market_data(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch market data for a symbol."""
        return await self.data_collector.collect_market_data(symbol, force_refresh)

    async def process_symbol(self, symbol: str) -> None:
        """Process a single symbol."""
        await self._process_symbol(symbol)

    async def generate_market_report(self) -> None:
        """Generate a market report."""
        try:
            if self.market_reporter:
                await self.market_reporter.generate_report()
        except Exception as e:
            self.logger.error(f"Error generating market report: {str(e)}")

    def get_monitored_symbols(self) -> List[str]:
        """Get list of monitored symbols."""
        if self.symbol:
            return [self.symbol]
        else:
            # Return symbols from top symbols manager or configuration
            return self.config.get('symbols', [])


# Main execution function
async def main():
    """Main entry point for standalone execution."""
    import yaml
    
    # Load configuration
    try:
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        # Use default configuration
        config = {
            'exchange': 'bybit',
            'monitoring_interval': 30,
            'symbols': ['BTCUSDT', 'ETHUSDT'],
            'confluence': {
                'thresholds': {
                    'buy': 60.0,
                    'sell': 40.0
                }
            }
        }
    
    # Create and start monitor
    monitor = MarketMonitor(config)
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt")
    finally:
        await monitor.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)
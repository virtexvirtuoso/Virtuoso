"""
Monitoring Orchestration Service

This service encapsulates the core business logic for orchestrating the monitoring workflow.
It coordinates between components and manages the monitoring lifecycle while providing
clean separation of concerns.
"""

import asyncio
import logging
import time
import traceback
from typing import Dict, List, Any, Optional

from src.monitoring.components import (
    WebSocketProcessor,
    MarketDataProcessor,
    SignalProcessor,
    WhaleActivityMonitor,
    ManipulationMonitor,
    HealthMonitor as ComponentHealthMonitor
)
from src.monitoring.utilities import MarketDataValidator


class MonitoringOrchestrationService:
    """
    Service that orchestrates the monitoring workflow.
    
    This service encapsulates the business logic for:
    - Running the main monitoring loop
    - Processing symbols with components
    - Managing monitoring tasks
    - Coordinating health checks
    - Tracking monitoring statistics
    """
    
    def __init__(
        self,
        websocket_processor: WebSocketProcessor,
        market_data_processor: MarketDataProcessor,
        signal_processor: SignalProcessor,
        whale_activity_monitor: WhaleActivityMonitor,
        manipulation_monitor: ManipulationMonitor,
        component_health_monitor: ComponentHealthMonitor,
        market_data_validator: MarketDataValidator,
        alert_manager=None,
        top_symbols_manager=None,
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the monitoring orchestration service.
        
        Args:
            websocket_processor: WebSocket processing component
            market_data_processor: Market data processing component  
            signal_processor: Signal processing component
            whale_activity_monitor: Whale activity monitoring component
            manipulation_monitor: Manipulation monitoring component
            component_health_monitor: Health monitoring component
            market_data_validator: Market data validation utility
            alert_manager: Alert management service
            top_symbols_manager: Top symbols management service
            logger: Logger instance
            config: Configuration dictionary
        """
        # Store component dependencies
        self.websocket_processor = websocket_processor
        self.market_data_processor = market_data_processor
        self.signal_processor = signal_processor
        self.whale_activity_monitor = whale_activity_monitor
        self.manipulation_monitor = manipulation_monitor
        self.component_health_monitor = component_health_monitor
        self.market_data_validator = market_data_validator
        
        # Store service dependencies
        self.alert_manager = alert_manager
        self.top_symbols_manager = top_symbols_manager
        
        # Configuration and logging
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        
        # Monitoring state
        self.is_running = False
        self.monitoring_tasks = []
        
        # Statistics tracking
        self.stats_data = {
            'processed_symbols': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'alerts_generated': 0,
            'start_time': None,
            'last_analysis_time': None,
            'total_cycles': 0,
            'health_check_failures': 0
        }
        
        self.logger.info("MonitoringOrchestrationService initialized")

    async def start_monitoring(self, symbol: Optional[str] = None) -> None:
        """
        Start the monitoring workflow.
        
        Args:
            symbol: Optional specific symbol to monitor
        """
        try:
            self.logger.info("Starting monitoring orchestration service...")
            self.is_running = True
            self.stats_data['start_time'] = time.time()
            
            # Start monitoring tasks
            await self._start_monitoring_tasks()
            
            # Start main monitoring loop
            await self._run_monitoring_loop(symbol)
            
        except Exception as e:
            self.logger.error(f"Error starting monitoring orchestration: {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise

    async def stop_monitoring(self) -> None:
        """Stop the monitoring workflow gracefully."""
        try:
            self.logger.info("Stopping monitoring orchestration service...")
            self.is_running = False
            
            # Cancel monitoring tasks
            for task in self.monitoring_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self.monitoring_tasks.clear()
            self.logger.info("Monitoring orchestration service stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping monitoring orchestration: {str(e)}")
            raise

    async def _start_monitoring_tasks(self) -> None:
        """Start background monitoring tasks."""
        try:
            tasks = []
            
            # Start health monitoring task
            if hasattr(self.component_health_monitor, 'start_monitoring'):
                tasks.append(
                    asyncio.create_task(self.component_health_monitor.start_monitoring())
                )
            
            # Add other background tasks as needed
            self.monitoring_tasks = tasks
            self.logger.info(f"Started {len(tasks)} monitoring tasks")
            
        except Exception as e:
            self.logger.error(f"Error starting monitoring tasks: {str(e)}")
            raise

    async def _run_monitoring_loop(self, target_symbol: Optional[str] = None) -> None:
        """
        Main monitoring loop that orchestrates symbol processing.
        
        Args:
            target_symbol: Optional specific symbol to monitor
        """
        try:
            while self.is_running:
                try:
                    cycle_start_time = time.time()
                    
                    # Get symbols to monitor
                    symbols = self._get_monitored_symbols(target_symbol)
                    
                    if not symbols:
                        self.logger.warning("No symbols to monitor")
                        await asyncio.sleep(10)
                        continue
                    
                    self.logger.debug(f"Processing {len(symbols)} symbols in monitoring cycle")
                    
                    # Process each symbol
                    for symbol in symbols:
                        if not self.is_running:
                            break
                            
                        await self._process_symbol_with_components(symbol)
                        
                        # Small delay between symbols to prevent overwhelming
                        await asyncio.sleep(1)
                    
                    # Update cycle statistics
                    self.stats_data['last_analysis_time'] = time.time()
                    self.stats_data['total_cycles'] += 1
                    
                    # Perform health checks
                    await self._perform_health_checks()
                    
                    # Calculate cycle time and adaptive sleep
                    cycle_time = time.time() - cycle_start_time
                    base_sleep = self.config.get('monitoring', {}).get('cycle_interval', 30)
                    
                    # Ensure minimum cycle time
                    sleep_time = max(base_sleep - cycle_time, 5)
                    
                    self.logger.debug(f"Cycle completed in {cycle_time:.2f}s, sleeping {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    await asyncio.sleep(5)  # Short delay on error
                    
        except Exception as e:
            self.logger.error(f"Fatal error in monitoring loop: {str(e)}")
            raise

    async def _process_symbol_with_components(self, symbol: str) -> None:
        """
        Process a single symbol through all monitoring components.
        
        Args:
            symbol: Trading symbol to process
        """
        symbol_start_time = time.time()
        
        try:
            self.logger.debug(f"Processing symbol {symbol} with component orchestration")
            
            # 1. Fetch market data using MarketDataProcessor
            market_data = await self.market_data_processor.fetch_market_data(symbol)
            
            if not market_data:
                self.logger.warning(f"No market data available for {symbol}")
                return
            
            # 2. Validate market data
            is_valid = await self.market_data_validator.validate_market_data(market_data)
            if not is_valid:
                self.logger.warning(f"Market data validation failed for {symbol}")
                self.stats_data['failed_analyses'] += 1
                return
            
            # 3. Enhance with real-time WebSocket data if available
            if hasattr(self.websocket_processor, 'get_real_time_data'):
                real_time_data = self.websocket_processor.get_real_time_data(symbol)
                if real_time_data:
                    market_data.update(real_time_data)
                    self.logger.debug(f"Enhanced {symbol} with real-time WebSocket data")
            
            # 4. Process through all analysis components in parallel for efficiency
            analysis_tasks = []
            
            # Signal processing
            analysis_tasks.append(
                self.signal_processor.analyze_confluence_and_generate_signals(market_data)
            )
            
            # Whale activity monitoring
            analysis_tasks.append(
                self.whale_activity_monitor.monitor_whale_activity(symbol, market_data)
            )
            
            # Manipulation monitoring
            analysis_tasks.append(
                self.manipulation_monitor.monitor_manipulation_activity(symbol, market_data)
            )
            
            # Execute all analysis tasks concurrently
            analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Check for any analysis failures
            failed_analyses = [result for result in analysis_results if isinstance(result, Exception)]
            if failed_analyses:
                self.logger.warning(f"Some analyses failed for {symbol}: {len(failed_analyses)} failures")
                for failure in failed_analyses:
                    self.logger.debug(f"Analysis failure: {str(failure)}")
            
            # Update statistics
            self.stats_data['processed_symbols'] += 1
            if not failed_analyses:
                self.stats_data['successful_analyses'] += 1
            else:
                self.stats_data['failed_analyses'] += 1
            
            processing_time = time.time() - symbol_start_time
            self.logger.debug(f"Successfully processed {symbol} in {processing_time:.3f}s")
            
        except Exception as e:
            self.logger.error(f"Error processing symbol {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.stats_data['failed_analyses'] += 1

    async def _perform_health_checks(self) -> None:
        """Perform system health checks using the health monitoring component."""
        try:
            # Use the component health monitor
            health_status = await self.component_health_monitor.check_health()
            
            if not health_status.get('healthy', True):
                self.logger.warning(f"Health check failed: {health_status}")
                self.stats_data['health_check_failures'] += 1
                
                # Send alert if configured
                if self.alert_manager:
                    await self.alert_manager.send_alert(
                        level="warning",
                        message="System health check failed",
                        details=health_status
                    )
            
        except Exception as e:
            self.logger.error(f"Error performing health checks: {str(e)}")
            self.stats_data['health_check_failures'] += 1

    def _get_monitored_symbols(self, target_symbol: Optional[str] = None) -> List[str]:
        """
        Get the list of symbols to monitor.
        
        Args:
            target_symbol: Optional specific symbol to monitor
            
        Returns:
            List of symbols to monitor
        """
        try:
            if target_symbol:
                return [target_symbol]
            elif self.top_symbols_manager:
                symbols = self.top_symbols_manager.get_top_symbols()
                self.logger.debug(f"Retrieved {len(symbols)} symbols from top symbols manager")
                return symbols
            else:
                # Default symbols for testing/fallback
                default_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
                self.logger.debug(f"Using default symbols: {default_symbols}")
                return default_symbols
                
        except Exception as e:
            self.logger.error(f"Error getting monitored symbols: {str(e)}")
            return []

    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring statistics.
        
        Returns:
            Dictionary containing monitoring statistics
        """
        current_time = time.time()
        start_time = self.stats_data.get('start_time')
        
        stats = {
            # Basic metrics
            'uptime_seconds': current_time - start_time if start_time else 0,
            'is_running': self.is_running,
            'total_cycles': self.stats_data['total_cycles'],
            
            # Processing metrics
            'processed_symbols': self.stats_data['processed_symbols'],
            'successful_analyses': self.stats_data['successful_analyses'],
            'failed_analyses': self.stats_data['failed_analyses'],
            'success_rate': 0.0,
            
            # Health metrics
            'health_check_failures': self.stats_data['health_check_failures'],
            'last_analysis_time': self.stats_data.get('last_analysis_time'),
            
            # Component status
            'active_tasks': len(self.monitoring_tasks),
            'component_stats': self._get_component_statistics()
        }
        
        # Calculate success rate
        total_analyses = stats['successful_analyses'] + stats['failed_analyses']
        if total_analyses > 0:
            stats['success_rate'] = stats['successful_analyses'] / total_analyses
        
        return stats

    def _get_component_statistics(self) -> Dict[str, Any]:
        """Get statistics from all components."""
        return {
            'whale_activity_stats': self.whale_activity_monitor.get_whale_activity_stats(),
            'manipulation_stats': self.manipulation_monitor.get_manipulation_stats(),
            'validation_stats': self.market_data_validator.get_validation_stats(),
            'websocket_status': self.websocket_processor.get_websocket_status() if hasattr(self.websocket_processor, 'get_websocket_status') else {},
            'market_data_cache_stats': self.market_data_processor.get_cache_stats() if hasattr(self.market_data_processor, 'get_cache_stats') else {}
        }

    def get_service_status(self) -> Dict[str, Any]:
        """Get the current status of the orchestration service."""
        return {
            'service_name': 'MonitoringOrchestrationService',
            'is_running': self.is_running,
            'active_tasks': len(self.monitoring_tasks),
            'statistics': self.get_monitoring_statistics(),
            'component_dependencies': {
                'websocket_processor': self.websocket_processor is not None,
                'market_data_processor': self.market_data_processor is not None,
                'signal_processor': self.signal_processor is not None,
                'whale_activity_monitor': self.whale_activity_monitor is not None,
                'manipulation_monitor': self.manipulation_monitor is not None,
                'component_health_monitor': self.component_health_monitor is not None,
                'market_data_validator': self.market_data_validator is not None
            }
        } 
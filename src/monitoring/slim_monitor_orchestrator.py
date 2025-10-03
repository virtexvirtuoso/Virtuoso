from src.utils.task_tracker import create_tracked_task
"""
Slim Monitor Orchestrator - Optimized Dependencies.

This orchestrator uses clean interfaces and minimal dependencies following
Single Responsibility Principle. It coordinates monitoring components
without creating tight coupling between them.

Reduced from 13+ dependencies to 6 interface dependencies.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from .interfaces import (
    IDataFetcher, IDataValidator, ISignalAnalyzer, 
    ITradeParameterCalculator, IMetricsCollector, IHealthChecker
)


class SlimMonitorOrchestrator:
    """
    Slim monitor orchestrator with optimized dependencies.
    
    This orchestrator follows SOLID principles:
    - Single Responsibility: Only orchestrates monitoring workflow
    - Open/Closed: Extensible through interface implementations
    - Liskov Substitution: Any interface implementation can be substituted
    - Interface Segregation: Depends only on specific interfaces needed
    - Dependency Inversion: Depends on abstractions, not concretions
    
    Constructor Dependencies: 6 interfaces (vs 13+ concrete classes before)
    """
    
    def __init__(
        self,
        data_fetcher: IDataFetcher,
        data_validator: IDataValidator,
        signal_analyzer: ISignalAnalyzer,
        trade_calculator: ITradeParameterCalculator,
        metrics_collector: IMetricsCollector,
        health_checker: IHealthChecker,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize with minimal interface dependencies.
        
        Args:
            data_fetcher: Interface for fetching market data
            data_validator: Interface for validating data quality
            signal_analyzer: Interface for analyzing signals
            trade_calculator: Interface for calculating trade parameters
            metrics_collector: Interface for collecting metrics
            health_checker: Interface for health monitoring
            logger: Optional logger instance
        """
        # Core interfaces - single responsibility each
        self.data_fetcher = data_fetcher
        self.data_validator = data_validator
        self.signal_analyzer = signal_analyzer
        self.trade_calculator = trade_calculator
        self.metrics_collector = metrics_collector
        self.health_checker = health_checker
        
        self.logger = logger or logging.getLogger(__name__)
        
        # Orchestrator state
        self._running = False
        self._monitoring_task = None
        self._start_time = None
        
        # Performance metrics
        self._stats = {
            'symbols_processed': 0,
            'signals_generated': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'avg_processing_time': 0.0,
            'uptime': 0.0
        }
        
        # Register health checks
        self._register_health_checks()
        
        self.logger.info("SlimMonitorOrchestrator initialized with optimized dependencies")
    
    async def start_monitoring(self, symbols: List[str], interval: float = 1.0) -> None:
        """
        Start monitoring the specified symbols.
        
        Args:
            symbols: List of symbols to monitor
            interval: Monitoring interval in seconds
        """
        if self._running:
            self.logger.warning("Monitor already running")
            return
        
        self._running = True
        self._start_time = time.time()
        
        self.logger.info(f"Starting optimized monitoring for {len(symbols)} symbols")
        
        # Record startup metrics
        self.metrics_collector.record_counter('monitor.startup')
        self.metrics_collector.record_metric('monitor.symbols_count', len(symbols))
        
        # Start monitoring loop
        self._monitoring_task = create_tracked_task(
            self._monitoring_loop(symbols, interval, name="auto_tracked_task")
        )
        
        self.logger.info("🚀 Optimized monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring gracefully."""
        if not self._running:
            return
        
        self.logger.info("Stopping optimized monitoring...")
        
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Record shutdown metrics
        self.metrics_collector.record_counter('monitor.shutdown')
        if self._start_time:
            uptime = time.time() - self._start_time
            self.metrics_collector.record_metric('monitor.total_uptime', uptime)
        
        self.logger.info("✅ Optimized monitoring stopped")
    
    async def _monitoring_loop(self, symbols: List[str], interval: float) -> None:
        """
        Main monitoring loop with clean separation of concerns.
        
        Args:
            symbols: Symbols to monitor
            interval: Loop interval
        """
        while self._running:
            loop_start = time.time()
            
            try:
                # Process all symbols concurrently for better performance
                tasks = [self._process_symbol(symbol) for symbol in symbols]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Update statistics
                successful = sum(1 for r in results if not isinstance(r, Exception))
                failed = len(results) - successful
                
                self._stats['symbols_processed'] += len(symbols)
                self._stats['successful_analyses'] += successful
                self._stats['failed_analyses'] += failed
                
                # Record metrics
                self.metrics_collector.record_metric('monitor.symbols_processed_batch', len(symbols))
                self.metrics_collector.record_metric('monitor.successful_analyses', successful)
                self.metrics_collector.record_metric('monitor.failed_analyses', failed)
                
                # Calculate processing time
                loop_time = time.time() - loop_start
                self._stats['avg_processing_time'] = (
                    self._stats['avg_processing_time'] * 0.9 + loop_time * 0.1
                )
                self.metrics_collector.record_timer('monitor.loop_time', loop_time * 1000)
                
                # Update uptime
                if self._start_time:
                    self._stats['uptime'] = time.time() - self._start_time
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                self.metrics_collector.record_counter('monitor.loop_errors')
            
            # Wait for next iteration
            await asyncio.sleep(max(0, interval - (time.time() - loop_start)))
    
    async def _process_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Process a single symbol through the monitoring pipeline.
        
        Single Responsibility: Coordinate the analysis pipeline for one symbol.
        
        Args:
            symbol: Symbol to process
            
        Returns:
            Processing result
        """
        processing_start = time.time()
        
        try:
            # Step 1: Fetch market data (IDataFetcher responsibility)
            market_data = await self.data_fetcher.fetch_market_data(symbol)
            
            if not market_data:
                self.logger.warning(f"No market data for {symbol}")
                return {'symbol': symbol, 'status': 'no_data'}
            
            # Step 2: Validate data quality (IDataValidator responsibility)
            is_valid = await self.data_validator.validate_market_data(market_data)
            
            if not is_valid:
                validation_errors = self.data_validator.get_validation_errors()
                self.logger.warning(f"Invalid data for {symbol}: {validation_errors}")
                self.metrics_collector.record_counter('validation.failed', tags={'symbol': symbol})
                return {'symbol': symbol, 'status': 'invalid_data', 'errors': validation_errors}
            
            # Step 3: Analyze signals (ISignalAnalyzer responsibility)
            analysis_result = await self.signal_analyzer.analyze_market_data(symbol, market_data)
            
            # Step 4: Calculate trade parameters if signal is strong enough (ITradeParameterCalculator responsibility)
            trade_params = None
            if analysis_result.get('confluence_score', 0) >= 60:  # Configurable threshold
                trade_params = self.trade_calculator.calculate_trade_parameters(analysis_result)
                self._stats['signals_generated'] += 1
                self.metrics_collector.record_counter('signals.generated', tags={'symbol': symbol})
            
            # Record processing metrics
            processing_time = (time.time() - processing_start) * 1000
            self.metrics_collector.record_timer('symbol.processing_time', processing_time, {'symbol': symbol})
            self.metrics_collector.record_metric('symbol.confluence_score', 
                                                analysis_result.get('confluence_score', 0), 
                                                {'symbol': symbol})
            
            return {
                'symbol': symbol,
                'status': 'success',
                'analysis': analysis_result,
                'trade_params': trade_params,
                'processing_time_ms': processing_time
            }
            
        except Exception as e:
            self.logger.error(f"Error processing {symbol}: {e}")
            self.metrics_collector.record_counter('symbol.processing_errors', tags={'symbol': symbol})
            return {'symbol': symbol, 'status': 'error', 'error': str(e)}
    
    def _register_health_checks(self) -> None:
        """Register health checks for monitoring components."""
        
        def check_orchestrator_health():
            return {
                'status': 'healthy' if self._running else 'stopped',
                'uptime': self._stats['uptime'],
                'symbols_processed': self._stats['symbols_processed'],
                'avg_processing_time': self._stats['avg_processing_time']
            }
        
        def check_data_fetcher_health():
            # Basic check - could be enhanced based on interface
            return {'status': 'healthy', 'component': 'data_fetcher'}
        
        def check_signal_analyzer_health():
            # Basic check - could be enhanced based on interface
            return {'status': 'healthy', 'component': 'signal_analyzer'}
        
        # Register health checks
        self.health_checker.register_health_check('orchestrator', check_orchestrator_health)
        self.health_checker.register_health_check('data_fetcher', check_data_fetcher_health)
        self.health_checker.register_health_check('signal_analyzer', check_signal_analyzer_health)
    
    # Public API methods for external integration
    
    async def analyze_single_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze a single symbol on-demand.
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            Analysis result
        """
        return await self._process_symbol(symbol)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status.
        
        Returns:
            Health status from IHealthChecker
        """
        return await self.health_checker.check_health()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Performance statistics
        """
        stats = dict(self._stats)
        stats['metrics_summary'] = self.metrics_collector.get_metrics_summary()
        return stats
    
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running
    
    # Interface compliance methods
    
    def get_dependencies(self) -> List[str]:
        """
        Get list of dependencies for inspection.
        
        Returns:
            List of interface names this orchestrator depends on
        """
        return [
            'IDataFetcher',
            'IDataValidator', 
            'ISignalAnalyzer',
            'ITradeParameterCalculator',
            'IMetricsCollector',
            'IHealthChecker'
        ]
    
    def validate_dependencies(self) -> Dict[str, bool]:
        """
        Validate that all dependencies are properly injected.
        
        Returns:
            Dictionary showing which dependencies are valid
        """
        return {
            'IDataFetcher': hasattr(self.data_fetcher, 'fetch_market_data'),
            'IDataValidator': hasattr(self.data_validator, 'validate_market_data'),
            'ISignalAnalyzer': hasattr(self.signal_analyzer, 'analyze_market_data'),
            'ITradeParameterCalculator': hasattr(self.trade_calculator, 'calculate_trade_parameters'),
            'IMetricsCollector': hasattr(self.metrics_collector, 'record_metric'),
            'IHealthChecker': hasattr(self.health_checker, 'check_health')
        }
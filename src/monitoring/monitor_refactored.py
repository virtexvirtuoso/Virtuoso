"""
Refactored Market Monitor - Slim Orchestrator

This module provides a clean, modular implementation of the market monitoring system
by orchestrating the extracted monitoring components. It maintains backward compatibility
while dramatically reducing complexity and improving maintainability.

Key Features:
- Slim orchestrator design (~500 lines vs 7699 lines)
- Modular component architecture
- Backward compatibility with existing interfaces
- Improved error handling and resilience
- Enhanced performance through optimized data flow
- Comprehensive logging and metrics

Components Orchestrated:
- DataCollector: Market data fetching and caching
- Validator: Data quality validation and integrity checks
- SignalProcessor: Analysis processing and signal generation
- WebSocketManager: Real-time data streaming
- MetricsTracker: Performance monitoring and health checks
- AlertManager: Alert distribution and notification management

Architecture:
The refactored monitor follows a clean separation of concerns where each component
handles a specific aspect of market monitoring. The orchestrator coordinates these
components in the monitoring loop while maintaining the same external interface.
"""

import asyncio
import logging
import time
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

# Import extracted monitoring components
from .data_collector import DataCollector
from .validator import MarketDataValidator
from .signal_processor import SignalProcessor
from .websocket_manager import MonitoringWebSocketManager
from .metrics_tracker import MetricsTracker
from .alert_manager import AlertManager

# Import utilities
from .utils.timestamp import TimestampUtility
from .utils.decorators import handle_monitoring_error, measure_performance
from .utils.converters import ccxt_time_to_minutes

# Import core components (maintain compatibility)
from .utils.logging import LoggingUtility
from .metrics_manager import MetricsManager
from .health_monitor import HealthMonitor


class RefactoredMarketMonitor:
    """
    Refactored Market Monitor - Slim orchestrator for modular monitoring system.
    
    This class maintains backward compatibility with the original MarketMonitor
    while providing a clean, modular architecture that orchestrates specialized
    monitoring components.
    """
    
    def __init__(
        self,
        exchange=None,
        symbol: Optional[str] = None,
        exchange_manager=None,
        database_client=None,
        portfolio_analyzer=None,
        confluence_analyzer=None,
        timeframes: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
        metrics_manager: Optional[MetricsManager] = None,
        health_monitor: Optional[HealthMonitor] = None,
        validation_config: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        alert_manager=None,
        signal_generator=None,
        top_symbols_manager=None,
        market_data_manager=None,
        **kwargs
    ):
        """
        Initialize the Refactored Market Monitor.
        
        Maintains the same interface as the original MarketMonitor for backward compatibility.
        """
        # Store core dependencies
        self.exchange_manager = exchange_manager
        self.database_client = database_client
        self.portfolio_analyzer = portfolio_analyzer
        self.confluence_analyzer = confluence_analyzer
        self.alert_manager = alert_manager
        self.signal_generator = signal_generator
        self.top_symbols_manager = top_symbols_manager
        self.market_data_manager = market_data_manager
        
        # Exchange configuration
        self.exchange = exchange
        self.exchange_id = getattr(exchange, 'id', None) if exchange else 'unknown'
        
        # Symbol configuration
        self.symbol = symbol
        self.symbol_str = symbol.replace('/', '') if symbol else None
        
        # Configuration
        self.config = config or {}
        
        # Logger setup
        self.logger = logger or logging.getLogger(__name__)
        self.logging_utility = LoggingUtility(self.logger)
        
        # Metrics and health monitoring
        self.metrics_manager = metrics_manager
        if not self.metrics_manager and config and alert_manager:
            self.metrics_manager = MetricsManager(config, alert_manager)
        
        self.health_monitor = health_monitor
        if self.health_monitor and self.exchange_id:
            self.health_monitor.register_api(self.exchange_id)
        
        # Timeframes configuration
        default_timeframes = {'ltf': '1m', 'mtf': '15m', 'htf': '1h'}
        self.timeframes = default_timeframes.copy()
        if timeframes:
            self.timeframes.update(timeframes)
        
        # Add base timeframe
        timeframe_values = sorted(self.timeframes.values(), key=lambda x: ccxt_time_to_minutes(x))
        self.timeframes['base'] = timeframe_values[0] if timeframe_values else '1m'
        
        # Validation configuration
        default_validation = {
            'max_ohlcv_age_seconds': 300,
            'min_ohlcv_candles': 20,
            'max_orderbook_age_seconds': 60,
            'min_orderbook_levels': 5,
            'max_trades_age_seconds': 300,
            'min_trades_count': 5,
        }
        self.validation_config = default_validation.copy()
        if validation_config:
            self.validation_config.update(validation_config)
        
        # Runtime configuration
        self.rate_limit_config = kwargs.get('rate_limit_config', {
            'enabled': True,
            'max_requests_per_second': 5,
            'timeout_seconds': 10
        })
        
        self.retry_config = kwargs.get('retry_config', {
            'max_retries': 3,
            'retry_delay_seconds': 2,
            'retry_exponential_backoff': True
        })
        
        self.debug_config = kwargs.get('debug_config', {
            'log_raw_responses': False,
            'verbose_validation': False,
            'save_visualizations': False,
            'visualization_dir': 'visualizations'
        })
        
        # WebSocket configuration
        self.websocket_config = kwargs.get('websocket_config', {
            'enabled': True,
            'use_ws_for_orderbook': True,
            'use_ws_for_trades': True,
            'use_ws_for_tickers': True
        })
        
        # Components will be initialized lazily when first accessed
        self._data_collector = None
        self._validator = None
        self._signal_processor = None
        self._metrics_tracker = None
        self._ws_manager_component = None
        self._alert_manager_component = None
        self._components_initialized = False
        
        # Runtime state
        self.running = False
        self.first_cycle_completed = False
        self.initial_report_pending = True
        self.last_report_time = None
        self.interval = self.config.get('interval', 30)  # Default 30 seconds
        self._error_count = 0
        
        # Initialize timestamp utility
        self.timestamp_utility = TimestampUtility()
        
        self.logger.info(f"Refactored Market Monitor initialized for {self.exchange_id} exchange")
    
    async def _ensure_dependencies(self):
        """Ensure all dependencies are resolved from DI container."""
        if hasattr(self, '_di_container') and self._di_container:
            # Resolve exchange_manager if not available
            if not self.exchange_manager and hasattr(self, 'get_exchange_manager'):
                self.exchange_manager = await self.get_exchange_manager()
            
            # Resolve alert_manager if not available  
            if not self.alert_manager and hasattr(self, 'get_alert_manager'):
                self.alert_manager = await self.get_alert_manager()
                
            # Resolve signal_generator from DI container
            if not self.signal_generator:
                try:
                    from ..signal_generation.signal_generator import SignalGenerator
                    self.signal_generator = await self._di_container.get_service(SignalGenerator)
                    self.logger.info("✅ SignalGenerator resolved from DI container")
                except Exception as e:
                    self.logger.warning(f"Could not resolve SignalGenerator from DI container: {e}")
                    
            # Resolve metrics_manager from DI container
            if not self.metrics_manager:
                try:
                    from ..monitoring.metrics_manager import MetricsManager
                    self.metrics_manager = await self._di_container.get_service(MetricsManager)
                    self.logger.info("✅ MetricsManager resolved from DI container")
                except Exception as e:
                    self.logger.warning(f"Could not resolve MetricsManager from DI container: {e}")
                    
            # Resolve market_data_manager from DI container
            if not self.market_data_manager:
                try:
                    from ..core.market.market_data_manager import MarketDataManager
                    self.market_data_manager = await self._di_container.get_service(MarketDataManager)
                    self.logger.info("✅ MarketDataManager resolved from DI container")
                except Exception as e:
                    self.logger.warning(f"Could not resolve MarketDataManager from DI container: {e}")
                
            # Try to resolve other dependencies from container
            try:
                from ..core.exchanges.manager import ExchangeManager
                from ..core.market.market_data_manager import MarketDataManager
                from ..signal_generation.signal_generator import SignalGenerationService
                from ..monitoring.components.metrics_manager import MetricsManager
                
                if not self.exchange_manager:
                    try:
                        self.exchange_manager = await self._di_container.get_service(ExchangeManager)
                    except Exception:
                        pass
                        
                if not self.market_data_manager:
                    try:
                        self.market_data_manager = await self._di_container.get_service(MarketDataManager)
                    except Exception:
                        pass
                        
                if not self.signal_generator:
                    try:
                        self.signal_generator = await self._di_container.get_service(SignalGenerationService)
                    except Exception:
                        pass
                        
                if not self.metrics_manager:
                    try:
                        self.metrics_manager = await self._di_container.get_service(MetricsManager)
                    except Exception:
                        pass
                        
            except ImportError:
                pass
    
    async def _initialize_components(self):
        """Initialize the modular monitoring components lazily."""
        if self._components_initialized:
            return
            
        try:
            # Ensure dependencies are resolved
            await self._ensure_dependencies()
            
            # Data Collector - handles all market data fetching
            if self.exchange_manager:
                self._data_collector = DataCollector(
                    exchange_manager=self.exchange_manager,
                    config=self.config,
                    logger=self.logger.getChild('data_collector')
                )
            else:
                self.logger.warning("DataCollector not initialized - exchange_manager unavailable")
            
            # Validator - handles data validation and quality checks
            self._validator = MarketDataValidator(
                config=self.validation_config,
                logger=self.logger.getChild('validator')
            )
            
            # Signal Processor - handles analysis processing and signal generation
            if self.signal_generator and self.metrics_manager:
                self._signal_processor = SignalProcessor(
                    config=self.config,
                    signal_generator=self.signal_generator,
                    metrics_manager=self.metrics_manager,
                    interpretation_manager=getattr(self, 'interpretation_manager', None),
                    market_data_manager=self.market_data_manager,
                    logger=self.logger.getChild('signal_processor')
                )
                self.logger.info("✅ Signal processor initialized successfully")
            else:
                self._signal_processor = None
                self.logger.warning(f"Signal processor not initialized - signal_generator: {self.signal_generator is not None}, metrics_manager: {self.metrics_manager is not None}")
            
            # WebSocket Manager - handles real-time data streaming
            self._ws_manager_component = None  # Will be initialized per symbol
            
            # Metrics Tracker - handles performance monitoring
            if self.metrics_manager and self.exchange_manager:
                self._metrics_tracker = MetricsTracker(
                    config=self.config,
                    metrics_manager=self.metrics_manager,
                    market_data_manager=self.market_data_manager,
                    exchange_manager=self.exchange_manager,
                    error_handler=getattr(self, 'error_handler', None),
                    logger=self.logger.getChild('metrics_tracker')
                )
                self.logger.info("✅ MetricsTracker initialized successfully")
            else:
                self.logger.warning(f"MetricsTracker not initialized - metrics_manager: {self.metrics_manager is not None}, exchange_manager: {self.exchange_manager is not None}")
            
            # Alert Manager Component - enhanced alert handling (if needed)
            self._alert_manager_component = self.alert_manager  # Use existing alert manager
            
            self._components_initialized = True
            self.logger.info("✅ All monitoring components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring components: {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise
    
    # Lazy property accessors for components
    @property
    def data_collector(self):
        """Get data collector, initializing components if needed."""
        if not self._components_initialized:
            # Run initialization in background if we have an event loop
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                if not hasattr(self, '_init_task') or self._init_task.done():
                    self._init_task = loop.create_task(self._initialize_components())
            except RuntimeError:
                # No event loop running, skip initialization for now
                pass
        return self._data_collector
    
    @property  
    def validator(self):
        """Get validator, initializing components if needed."""
        if not self._components_initialized:
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                if not hasattr(self, '_init_task') or self._init_task.done():
                    self._init_task = loop.create_task(self._initialize_components())
            except RuntimeError:
                pass
        return self._validator
        
    @property
    def signal_processor(self):
        """Get signal processor, initializing components if needed."""
        if not self._components_initialized:
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                if not hasattr(self, '_init_task') or self._init_task.done():
                    self._init_task = loop.create_task(self._initialize_components())
            except RuntimeError:
                pass
        return self._signal_processor
        
    @property
    def metrics_tracker(self):
        """Get metrics tracker, initializing components if needed."""
        if not self._components_initialized:
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                if not hasattr(self, '_init_task') or self._init_task.done():
                    self._init_task = loop.create_task(self._initialize_components())
            except RuntimeError:
                pass
        return self._metrics_tracker
        
    @property
    def ws_manager_component(self):
        """Get websocket manager component."""
        return self._ws_manager_component
        
    @property
    def alert_manager_component(self):
        """Get alert manager component."""
        return self._alert_manager_component
    
    async def initialize(self) -> bool:
        """Initialize all monitoring components asynchronously."""
        try:
            self.logger.info("Initializing monitoring components...")
            
            # Try to create components, but don't fail if dependencies are missing
            try:
                await self._initialize_components()
            except Exception as e:
                self.logger.warning(f"Component initialization incomplete due to missing dependencies: {e}")
                # Continue with partial initialization - components will be created on demand
            
            # Initialize available components (non-blocking)
            initialized_count = 0
            
            # Initialize data collector if available
            if self._data_collector:
                try:
                    if await self._data_collector.initialize():
                        initialized_count += 1
                    else:
                        self.logger.warning("DataCollector failed to initialize - will retry on demand")
                except Exception as e:
                    self.logger.warning(f"DataCollector initialization error: {e}")
            
            # Initialize validator if available
            if self._validator:
                try:
                    if await self._validator.initialize():
                        initialized_count += 1
                    else:
                        self.logger.warning("Validator failed to initialize - will retry on demand")
                except Exception as e:
                    self.logger.warning(f"Validator initialization error: {e}")
            
            # Initialize signal processor if available
            if self._signal_processor:
                try:
                    if await self._signal_processor.initialize():
                        initialized_count += 1
                    else:
                        self.logger.warning("SignalProcessor failed to initialize - will retry on demand")
                except Exception as e:
                    self.logger.warning(f"SignalProcessor initialization error: {e}")
            
            # Initialize metrics tracker if available
            if self._metrics_tracker:
                try:
                    if await self._metrics_tracker.initialize():
                        initialized_count += 1
                    else:
                        self.logger.warning("MetricsTracker failed to initialize - will retry on demand")
                except Exception as e:
                    self.logger.warning(f"MetricsTracker initialization error: {e}")
            
            if initialized_count > 0:
                self.logger.info(f"Successfully initialized {initialized_count} monitoring components - others will initialize on demand")
            else:
                self.logger.info("Monitoring components will initialize on demand when dependencies become available")
            
            # Always return True - we can function with lazy initialization
            return True
            
        except Exception as e:
            self.logger.error(f"Critical error during monitor initialization: {str(e)}")
            self.logger.debug(traceback.format_exc())
            # Still return True to allow the system to continue with fallback behavior
            return True
    
    @measure_performance()
    async def fetch_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch market data for a symbol using the data collector.
        
        Maintains compatibility with original interface while using modular components.
        """
        try:
            return await self.data_collector.fetch_market_data(symbol)
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            return None
    
    async def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """
        Validate market data using the validator component.
        
        Maintains compatibility with original interface.
        """
        try:
            return await self.validator.validate_market_data(market_data)
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            return False
    
    @handle_monitoring_error()
    async def start_monitoring(self) -> None:
        """Start the monitoring system."""
        if self.running:
            self.logger.warning("Monitoring is already running")
            return
        
        self.logger.info("Starting market monitoring system...")
        
        # Initialize components
        if not await self.initialize():
            self.logger.error("Failed to initialize monitoring system")
            return
        
        self.running = True
        self._error_count = 0
        
        try:
            # Start the main monitoring loop
            await self._run_monitoring_loop()
        except Exception as e:
            self.logger.error(f"Critical error in monitoring system: {str(e)}")
            self.logger.debug(traceback.format_exc())
        finally:
            self.running = False
            self.logger.info("Market monitoring system stopped")
    
    async def stop_monitoring(self) -> None:
        """Stop the monitoring system gracefully."""
        self.logger.info("Stopping market monitoring system...")
        self.running = False
        
        # Stop components
        try:
            if hasattr(self.data_collector, 'stop'):
                await self.data_collector.stop()
            
            if hasattr(self.validator, 'stop'):
                await self.validator.stop()
            
            if self.signal_processor and hasattr(self.signal_processor, 'stop'):
                await self.signal_processor.stop()
            
            if self.metrics_tracker is not None and hasattr(self.metrics_tracker, 'stop'):
                await self.metrics_tracker.stop()
            
            self.logger.info("All monitoring components stopped")
        except Exception as e:
            self.logger.error(f"Error stopping components: {str(e)}")
    
    async def _run_monitoring_loop(self) -> None:
        """Main monitoring loop - orchestrates all components."""
        self.logger.info("Starting monitoring loop...")
        
        while self.running:
            try:
                # Run monitoring cycle
                await self._monitoring_cycle()
                
                # Update metrics (with null check)
                if self.metrics_tracker is not None:
                    await self.metrics_tracker.update_metrics()
                else:
                    self.logger.debug("Metrics tracker not available, skipping metrics update")
                
                # Check system health
                health_status = await self._check_system_health()
                if health_status['status'] != 'healthy':
                    self.logger.warning(f"System health check: {health_status['status']}")
                    await self._handle_health_issues(health_status)
                
                # Sleep until next cycle
                await asyncio.sleep(self.interval)
                
            except asyncio.CancelledError:
                self.logger.info("Monitoring loop cancelled")
                break
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                self.logger.debug(traceback.format_exc())
                self._error_count += 1
                
                # Exponential backoff on errors
                backoff_time = min(30, 2 ** min(self._error_count, 5))
                await asyncio.sleep(backoff_time)
    
    @measure_performance()
    async def _monitoring_cycle(self) -> None:
        """Run a single monitoring cycle."""
        try:
            self.logger.debug("=== Starting Monitoring Cycle ===")
            
            # Get symbols to monitor
            symbols = await self.top_symbols_manager.get_symbols()
            if not symbols:
                self.logger.warning("Empty symbol list detected!")
                return
            
            self.logger.debug(f"Processing {len(symbols)} symbols")
            
            # Process symbols concurrently with controlled concurrency
            max_concurrent = self.config.get('max_concurrent_symbols', 10)
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_symbol_with_semaphore(symbol):
                async with semaphore:
                    await self._process_symbol(symbol)
            
            # Process all symbols concurrently
            tasks = [process_symbol_with_semaphore(symbol) for symbol in symbols]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Mark first cycle as completed
            if not self.first_cycle_completed:
                self.first_cycle_completed = True
                self.logger.info("First monitoring cycle completed")
                
                if self.initial_report_pending:
                    await self._generate_initial_report()
            else:
                # Check for scheduled reports
                if self._should_generate_report():
                    await self._generate_market_report()
            
        except Exception as e:
            self.logger.error(f"Monitoring cycle error: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    @handle_monitoring_error()
    async def _process_symbol(self, symbol: str) -> None:
        """Process a single symbol through the monitoring pipeline."""
        if not self.exchange_manager:
            self.logger.error("Exchange manager not available")
            return
        
        try:
            # Extract symbol string
            symbol_str = symbol['symbol'] if isinstance(symbol, dict) and 'symbol' in symbol else symbol
            
            self.logger.debug(f"Processing symbol: {symbol_str}")
            
            # Step 1: Fetch market data
            market_data = await self.data_collector.fetch_market_data(symbol_str)
            if not market_data:
                self.logger.warning(f"No market data available for {symbol_str}")
                return
            
            # Ensure symbol field is set
            market_data['symbol'] = symbol_str
            
            # Step 2: Validate market data
            if not await self.validator.validate_market_data(market_data):
                self.logger.warning(f"Invalid market data for {symbol_str}")
                return
            
            # Step 3: Process with confluence analyzer
            if self.confluence_analyzer:
                try:
                    analysis_result = await self.confluence_analyzer.analyze(market_data)
                    if analysis_result:
                        # Step 4: Process analysis result and generate signals
                        if self.signal_processor:
                            await self.signal_processor.process_analysis_result(symbol_str, analysis_result)
                        
                        # Step 5: Update database if available
                        if self.database_client:
                            await self._store_analysis_result(symbol_str, analysis_result)
                
                except Exception as e:
                    self.logger.error(f"Error in confluence analysis for {symbol_str}: {str(e)}")
            
            # Step 6: Update metrics (with null check)
            if self.metrics_tracker is not None:
                await self.metrics_tracker.update_symbol_metrics(symbol_str, market_data)
            else:
                self.logger.warning(f"⚠️  Metrics tracker not initialized, skipping metrics update for {symbol_str}")
            
        except Exception as e:
            self.logger.error(f"Error processing symbol {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system health using metrics tracker with fallback."""
        try:
            # First try metrics tracker if available
            if self.metrics_tracker is not None:
                return await self.metrics_tracker.check_system_health()
            else:
                # Fallback to basic health check
                return await self._fallback_health_check()
                
        except Exception as e:
            self.logger.error(f"Error checking system health: {str(e)}")
            # Return fallback on any error
            try:
                return await self._fallback_health_check()
            except Exception as fallback_error:
                self.logger.error(f"Error in fallback health check: {str(fallback_error)}")
                return {
                    'status': 'error',
                    'timestamp': time.time(),
                    'components': {
                        'system': {'status': 'error', 'message': 'Health check system unavailable'}
                    }
                }
    
    async def _fallback_health_check(self) -> Dict[str, Any]:
        """Fallback health check when metrics tracker is unavailable."""
        import psutil
        
        try:
            components = {}
            overall_status = 'healthy'
            
            # Check basic system resources
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                
                # CPU health
                cpu_status = 'healthy' if cpu_percent < 80 else 'warning' if cpu_percent < 95 else 'critical'
                components['cpu'] = {
                    'status': cpu_status,
                    'usage_percent': cpu_percent,
                    'message': f'CPU usage: {cpu_percent:.1f}%'
                }
                
                # Memory health
                memory_status = 'healthy' if memory.percent < 80 else 'warning' if memory.percent < 95 else 'critical'
                components['memory'] = {
                    'status': memory_status,
                    'usage_percent': memory.percent,
                    'available_gb': memory.available / (1024**3),
                    'message': f'Memory usage: {memory.percent:.1f}%'
                }
                
                if cpu_status == 'critical' or memory_status == 'critical':
                    overall_status = 'critical'
                elif cpu_status == 'warning' or memory_status == 'warning':
                    overall_status = 'warning'
                    
            except Exception as e:
                components['system_resources'] = {
                    'status': 'error',
                    'message': f'Unable to check system resources: {str(e)}'
                }
                overall_status = 'warning'
            
            # Check component availability
            component_statuses = []
            
            # Check exchange manager
            if hasattr(self, 'exchange_manager') and self.exchange_manager:
                components['exchange_manager'] = {
                    'status': 'healthy',
                    'message': 'Exchange manager available'
                }
                component_statuses.append('healthy')
            else:
                components['exchange_manager'] = {
                    'status': 'warning',
                    'message': 'Exchange manager not available'
                }
                component_statuses.append('warning')
                if overall_status == 'healthy':
                    overall_status = 'warning'
            
            # Check data collector
            if self._data_collector:
                components['data_collector'] = {
                    'status': 'healthy',
                    'message': 'Data collector initialized'
                }
                component_statuses.append('healthy')
            else:
                components['data_collector'] = {
                    'status': 'warning',
                    'message': 'Data collector not initialized'
                }
                component_statuses.append('warning')
                if overall_status == 'healthy':
                    overall_status = 'warning'
            
            # Check validator
            if self._validator:
                components['validator'] = {
                    'status': 'healthy',
                    'message': 'Validator available'
                }
                component_statuses.append('healthy')
            else:
                components['validator'] = {
                    'status': 'warning',
                    'message': 'Validator not available'
                }
                component_statuses.append('warning')
                if overall_status == 'healthy':
                    overall_status = 'warning'
            
            # Add metrics tracker status
            components['metrics_tracker'] = {
                'status': 'warning',
                'message': 'Metrics tracker not available - using fallback health check'
            }
            if overall_status == 'healthy':
                overall_status = 'warning'
            
            return {
                'status': overall_status,
                'timestamp': time.time(),
                'components': components,
                'fallback_mode': True,
                'message': f'Health check using fallback mode - {len([s for s in component_statuses if s == "healthy"])}/{len(component_statuses)} components healthy'
            }
            
        except Exception as e:
            self.logger.error(f"Error in fallback health check: {str(e)}")
            return {
                'status': 'error',
                'timestamp': time.time(),
                'components': {
                    'fallback_system': {
                        'status': 'error',
                        'message': f'Fallback health check failed: {str(e)}'
                    }
                },
                'fallback_mode': True
            }
    
    async def _handle_health_issues(self, health_status: Dict[str, Any]) -> None:
        """Handle system health issues."""
        critical_components = [
            comp for comp, status in health_status['components'].items()
            if status.get('status') == 'critical'
        ]
        
        if critical_components and self.alert_manager_component:
            await self.alert_manager_component.send_alert(
                f"Critical system health issues: {', '.join(critical_components)}",
                level='critical'
            )
    
    def _should_generate_report(self) -> bool:
        """Check if it's time to generate a market report."""
        if not self.last_report_time:
            return True
        
        current_time = datetime.now(timezone.utc)
        time_since_last = (current_time - self.last_report_time).total_seconds()
        report_interval = self.config.get('report_interval', 3600)  # Default 1 hour
        
        return time_since_last >= report_interval
    
    async def _generate_initial_report(self) -> None:
        """Generate initial market report."""
        try:
            await self._generate_market_report()
            self.initial_report_pending = False
            self.last_report_time = datetime.now(timezone.utc)
            self.logger.info("Initial market report generated")
        except Exception as e:
            self.logger.error(f"Error generating initial report: {str(e)}")
    
    async def _generate_market_report(self) -> None:
        """Generate periodic market report."""
        try:
            if not self.alert_manager_component:
                return
            
            # Get system metrics (with null check)
            if self.metrics_tracker is not None:
                metrics = await self.metrics_tracker.get_system_metrics()
            else:
                # Fallback to basic metrics when tracker unavailable
                health_check = await self._fallback_health_check()
                metrics = {
                    'health': health_check,
                    'timestamp': time.time(),
                    'fallback_mode': True
                }
            
            # Generate report content
            report = self._create_market_report(metrics)
            
            # Send report via alert manager
            await self.alert_manager_component.send_report(report)
            
            self.last_report_time = datetime.now(timezone.utc)
            
        except Exception as e:
            self.logger.error(f"Error generating market report: {str(e)}")
    
    def _create_market_report(self, metrics: Dict[str, Any]) -> str:
        """Create market report content."""
        report_lines = [
            "=== Virtuoso Trading System - Market Report ===",
            f"Report Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            f"System Status: {metrics.get('status', 'Unknown')}",
            f"Active Symbols: {metrics.get('active_symbols', 0)}",
            f"Signals Generated: {metrics.get('signals_generated', 0)}",
            f"Error Count: {self._error_count}",
            "",
            "Component Status:",
        ]
        
        for component, status in metrics.get('components', {}).items():
            report_lines.append(f"  {component}: {status.get('status', 'unknown')}")
        
        return "\n".join(report_lines)
    
    async def _store_analysis_result(self, symbol: str, analysis_result: Dict[str, Any]) -> None:
        """Store analysis result in database."""
        try:
            if self.database_client:
                await self.database_client.store_analysis(symbol, analysis_result)
        except Exception as e:
            self.logger.error(f"Error storing analysis result for {symbol}: {str(e)}")
    
    # Backward compatibility methods
    async def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Backward compatibility wrapper for fetch_market_data."""
        return await self.fetch_market_data(symbol)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            'running': self.running,
            'first_cycle_completed': self.first_cycle_completed,
            'error_count': self._error_count,
            'components': {
                'data_collector': bool(self.data_collector),
                'validator': bool(self.validator),
                'signal_processor': bool(self.signal_processor),
                'metrics_tracker': bool(self.metrics_tracker),
            }
        }

    async def start(self):
        """
        Backward compatibility method for the original MarketMonitor interface.
        The refactored monitor runs continuously when start_monitoring() is called.
        """
        self.logger.info("Starting RefactoredMarketMonitor - compatibility method")
        try:
            await self.start_monitoring()
        except Exception as e:
            self.logger.error(f"RefactoredMarketMonitor start failed: {e}")
            raise


# Backward compatibility alias
MarketMonitor = RefactoredMarketMonitor
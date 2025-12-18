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
import math
import time
import traceback
import uuid
from datetime import datetime, timezone, timedelta
import numpy as np
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
import logging

logger = logging.getLogger(__name__)



class MarketMonitor:
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
        self._regime_monitor = None
        self._regime_detector = None
        self._components_initialized = False
        
        # Runtime state
        self.running = False
        self.first_cycle_completed = False
        self.initial_report_pending = True
        self.last_report_time = None
        self.interval = self.config.get('interval', 15)  # Default 15 seconds (optimized for production)
        self._error_count = 0

        # Whale trade detection cooldown tracking (Bug #2 fix - initialize here to avoid race condition)
        self._last_whale_trade_alert = {}

        # Maintain symbols attribute for backward compatibility
        self.symbols = []
        
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
                        logger.error(f"Unhandled exception: {e}", exc_info=True)
                        pass
                        
                if not self.market_data_manager:
                    try:
                        self.market_data_manager = await self._di_container.get_service(MarketDataManager)
                    except Exception:
                        logger.error(f"Unhandled exception: {e}", exc_info=True)
                        pass
                        
                if not self.signal_generator:
                    try:
                        self.signal_generator = await self._di_container.get_service(SignalGenerationService)
                    except Exception:
                        logger.error(f"Unhandled exception: {e}", exc_info=True)
                        pass
                        
                if not self.metrics_manager:
                    try:
                        self.metrics_manager = await self._di_container.get_service(MetricsManager)
                    except Exception:
                        logger.error(f"Unhandled exception: {e}", exc_info=True)
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

            # Initialize cache data aggregator to fix circular dependency
            try:
                from .cache_data_aggregator import CacheDataAggregator
                from src.api.cache_adapter_direct import DirectCacheAdapter
                cache_adapter = DirectCacheAdapter()
                # CRITICAL: Pass exchange for market-wide ticker fetching
                # DEBUG: Check if exchange exists before passing
                self.logger.info(f"🔍 DEBUG: self.exchange = {self.exchange}, type = {type(self.exchange)}, id = {getattr(self.exchange, 'id', 'NO_ID')}")
                # Note: shared_cache can be set later via set_shared_cache() method
                self.cache_data_aggregator = CacheDataAggregator(cache_adapter, self.config, self.exchange, shared_cache=getattr(self, 'shared_cache', None))
                self.logger.info("✅ Cache data aggregator initialized with exchange for market-wide metrics")
            except Exception as e:
                self.logger.warning(f"Cache data aggregator initialization failed: {e}")
                self.cache_data_aggregator = None
            
            # Validator - handles data validation and quality checks
            self._validator = MarketDataValidator(
                config=self.validation_config,
                logger=self.logger.getChild('validator')
            )
            
            # Initialize RiskManager for trade parameter calculations
            risk_manager = None
            try:
                from src.risk.risk_manager import RiskManager
                risk_manager = RiskManager(self.config)
                self.logger.info("✅ RiskManager initialized for trade parameter calculations")
            except Exception as e:
                self.logger.warning(f"RiskManager initialization failed: {str(e)} - will use fallback calculations")

            # Signal Processor - handles analysis processing and signal generation
            if self.signal_generator and self.metrics_manager:
                self._signal_processor = SignalProcessor(
                    config=self.config,
                    signal_generator=self.signal_generator,
                    metrics_manager=self.metrics_manager,
                    interpretation_manager=getattr(self, 'interpretation_manager', None),
                    market_data_manager=self.market_data_manager,
                    risk_manager=risk_manager,
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

            # Regime Detection Components - for market regime monitoring and alerts
            try:
                from src.core.analysis.market_regime_detector import MarketRegimeDetector
                from src.monitoring.regime_monitor import RegimeMonitor

                self._regime_detector = MarketRegimeDetector(self.config)
                self._regime_monitor = RegimeMonitor(
                    alert_manager=self.alert_manager,
                    config=self.config,
                    enable_external_data=True
                )
                self.logger.info("✅ Regime detection components initialized (detector + monitor + external data)")
            except Exception as e:
                self.logger.warning(f"Regime detection initialization failed: {e} - regime alerts will be disabled")
                self._regime_detector = None
                self._regime_monitor = None

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

    @property
    def regime_monitor(self):
        """Get regime monitor, initializing components if needed."""
        if not self._components_initialized:
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                if not hasattr(self, '_init_task') or self._init_task.done():
                    self._init_task = loop.create_task(self._initialize_components())
            except RuntimeError:
                pass
        return self._regime_monitor

    @property
    def regime_detector(self):
        """Get regime detector, initializing components if needed."""
        if not self._components_initialized:
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                if not hasattr(self, '_init_task') or self._init_task.done():
                    self._init_task = loop.create_task(self._initialize_components())
            except RuntimeError:
                pass
        return self._regime_detector

    def set_shared_cache(self, shared_cache_bridge):
        """
        Set the shared cache bridge for cross-process communication.

        This should be called after initialization to enable the monitoring system
        to write data that the web server can read.

        Args:
            shared_cache_bridge: SharedCacheBridge instance
        """
        self.shared_cache = shared_cache_bridge

        # Update cache_data_aggregator if it exists
        if hasattr(self, 'cache_data_aggregator') and self.cache_data_aggregator:
            if hasattr(self.cache_data_aggregator, 'cache_writer'):
                self.cache_data_aggregator.cache_writer.shared_cache = shared_cache_bridge
                self.logger.info("✅ Shared cache bridge set on cache_data_aggregator.cache_writer")
            self.cache_data_aggregator.shared_cache = shared_cache_bridge
            self.logger.info("✅ Shared cache bridge enabled for monitoring system")
        else:
            self.logger.warning("⚠️ cache_data_aggregator not available - shared cache set but not connected")

    async def initialize(self) -> bool:
        """Initialize all monitoring components asynchronously."""
        try:
            self.logger.info("Initializing monitoring components...")

            # CRITICAL: Validate core dependencies before proceeding
            missing_deps = []
            if not self.exchange_manager:
                missing_deps.append("exchange_manager")
            if not self.alert_manager:
                missing_deps.append("alert_manager")
            if not self.top_symbols_manager:
                missing_deps.append("top_symbols_manager")

            if missing_deps:
                error_msg = f"🚨 CRITICAL: MarketMonitor missing required dependencies: {missing_deps} - cannot initialize monitoring"
                self.logger.error(error_msg)
                return False

            self.logger.info("✅ Core dependencies validated successfully")
            
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
            
            # Initialize symbols for backward compatibility
            if self.top_symbols_manager:
                try:
                    max_symbols = self.config.get('market', {}).get('symbols', {}).get('max_symbols', 15)
                    self.symbols = await self.top_symbols_manager.get_top_symbols(limit=max_symbols)
                    if self.symbols:
                        self.logger.info(f"✅ Initialized with {len(self.symbols)} symbols for backward compatibility")
                except Exception as e:
                    self.logger.warning(f"Could not initialize symbols during startup: {e}")
                    # Not critical - will be populated in monitoring cycle

            # Pre-warm cache aggregator for faster dashboard startup
            # This fetches market-wide tickers and populates cache before monitoring begins
            if self.cache_data_aggregator:
                try:
                    await self.cache_data_aggregator.initialize()
                    self.logger.info("✅ Cache aggregator pre-warmed for instant dashboard data")
                except Exception as e:
                    self.logger.warning(f"Cache aggregator pre-warming failed (non-critical): {e}")
                    # Not critical - cache will warm up gradually during normal operation

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
            cycle_start_time = time.time()
            try:
                self.logger.info(f"🔄 Starting monitoring cycle (interval: {self.interval}s)")
                
                # Run monitoring cycle with timeout protection (no timeout for now to prevent cancellation)
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
                
                cycle_duration = time.time() - cycle_start_time
                self._last_successful_cycle = time.time()  # Track successful completion
                self.logger.info(f"🏁 Monitoring cycle completed in {cycle_duration:.2f}s, sleeping for {self.interval}s")
                
                # Sleep until next cycle
                await asyncio.sleep(self.interval)
                
            except asyncio.CancelledError:
                import sys
                import inspect
                # traceback is already imported at module level - no need to re-import

                # Get detailed cancellation information for debugging
                frame_info = []
                frame = sys._getframe()
                while frame:
                    frame_info.append(f"{frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}")
                    frame = frame.f_back
                    if len(frame_info) > 10:  # Limit to prevent spam
                        break
                
                self.logger.error("🚨 MONITORING LOOP CANCELLED - DEBUG INFO:")
                self.logger.error(f"Current task: {asyncio.current_task()}")
                self.logger.error(f"All tasks: {len(asyncio.all_tasks())}")
                self.logger.error("📚 Call stack:")
                for i, frame_str in enumerate(frame_info):
                    self.logger.error(f"  {i}: {frame_str}")
                
                # Log current loop iteration info
                if hasattr(self, '_current_cycle_start'):
                    elapsed = time.time() - self._current_cycle_start
                    self.logger.error(f"⏱️  Cancelled after {elapsed:.2f}s into current cycle")
                
                self.logger.error("💥 MONITORING LOOP CANCELLED - DEBUGGING ENABLED")
                break
                
            except asyncio.TimeoutError:
                self.logger.error("⚠️ Monitoring cycle timed out after 90 seconds!")
                self._error_count += 1

                # More aggressive backoff for timeouts to prevent cascading failures
                backoff_time = min(30, 5 + (2 ** min(self._error_count, 4)))
                self.logger.warning(f"🔄 Timeout #{self._error_count}, backing off for {backoff_time}s...")

                # Reset error count if we've been running for a while without issues
                if hasattr(self, '_last_successful_cycle'):
                    if time.time() - self._last_successful_cycle > 300:  # 5 minutes
                        self.logger.info("🔄 Resetting error count after extended runtime")
                        self._error_count = max(0, self._error_count - 1)

                await asyncio.sleep(backoff_time)
                
            except Exception as e:
                self.logger.error(f"❌ Error in monitoring loop: {str(e)}")
                self.logger.error(traceback.format_exc())  # Changed from debug to error level
                self._error_count += 1
                
                # Exponential backoff on errors
                backoff_time = min(30, 2 ** min(self._error_count, 5))
                self.logger.error(f"Backing off for {backoff_time}s due to error #{self._error_count}")
                await asyncio.sleep(backoff_time)
    
    @measure_performance()
    async def _monitoring_cycle(self) -> None:
        """Run a single monitoring cycle."""
        try:
            self._current_cycle_start = time.time()  # Track cycle start time for debugging
            self.logger.info("=== Starting Monitoring Cycle ===")
            self.logger.info(f"🔬 DEBUG: Current task ID: {id(asyncio.current_task())}")
            
            # Get symbols to monitor - use get_top_symbols with a limit and timeout handling
            # Get max_symbols from config, default to 15 per config.yaml
            max_symbols = self.config.get('market', {}).get('symbols', {}).get('max_symbols', 15)
            self.logger.info(f"🎯 Configured to process {max_symbols} symbols per cycle")
            try:
                symbols = await asyncio.wait_for(
                    self.top_symbols_manager.get_top_symbols(limit=max_symbols),
                    timeout=15.0  # Increased timeout to 15 seconds
                )
            except asyncio.TimeoutError:
                self.logger.error("⚠️ get_top_symbols timed out after 15 seconds - using fallback")
                # Try to get cached symbols as fallback
                symbols = await self.top_symbols_manager.get_symbols(limit=max_symbols)
                if not symbols:
                    self.logger.error("No fallback symbols available - skipping cycle")
                    return
            except Exception as e:
                self.logger.error(f"Error getting top symbols: {str(e)} - using fallback")
                symbols = await self.top_symbols_manager.get_symbols(limit=max_symbols)
                if not symbols:
                    self.logger.error("No fallback symbols available - skipping cycle")
                    return
            
            if not symbols:
                self.logger.warning("Empty symbol list detected!")
                return
            
            # Store symbols for backward compatibility with dashboard integration
            self.symbols = symbols
            self.logger.info(f"Processing {len(symbols)} symbols")
            
            # Process symbols concurrently with controlled concurrency
            # Read from config.monitoring.performance.max_concurrent_symbols
            max_concurrent = self.config.get('monitoring', {}).get('performance', {}).get('max_concurrent_symbols', 10)
            semaphore = asyncio.Semaphore(max_concurrent)
            self.logger.info(f"Processing symbols with concurrency limit: {max_concurrent}")
            
            async def process_symbol_with_semaphore(symbol):
                async with semaphore:
                    return await self._process_symbol(symbol)  # CRITICAL FIX: Return the result!
            
            # Process all symbols concurrently
            tasks = [process_symbol_with_semaphore(symbol) for symbol in symbols]
            self.logger.info(f"📋 Created {len(tasks)} tasks for symbol processing")

            # Performance tracking (time already imported at module level)
            cycle_start_time = time.time()

            results = await asyncio.gather(*tasks, return_exceptions=True)

            cycle_elapsed_time = time.time() - cycle_start_time

            # Enhanced result validation to detect both exceptions AND silent failures
            exceptions = [r for r in results if isinstance(r, Exception)]
            none_results = [i for i, r in enumerate(results) if r is None]
            successful_tasks = len(results) - len(exceptions) - len(none_results)

            if exceptions:
                self.logger.error(f"❌ {len(exceptions)} tasks failed with exceptions:")
                for i, exc in enumerate(exceptions):
                    self.logger.error(f"  Task {i}: {exc}")

            if none_results:
                self.logger.error(f"⚠️ {len(none_results)} tasks completed but did no work (silent failures)")

            # Performance metrics logging
            if successful_tasks > 0:
                avg_time_per_symbol = cycle_elapsed_time / len(symbols)
                self.logger.info(
                    f"✅ {successful_tasks}/{len(symbols)} symbols processed successfully in {cycle_elapsed_time:.2f}s "
                    f"(avg: {avg_time_per_symbol:.2f}s/symbol, concurrency: {max_concurrent})"
                )
            else:
                self.logger.error("🚨 NO TASKS COMPLETED SUCCESSFULLY - SYSTEM MALFUNCTION DETECTED")
            
            # Mark first cycle as completed
            if not self.first_cycle_completed:
                self.first_cycle_completed = True
                self.logger.info("✅ First monitoring cycle completed successfully")
                
                if self.initial_report_pending:
                    await self._generate_initial_report()
            else:
                self.logger.info("✅ Monitoring cycle completed successfully")
                # Check for scheduled reports
                if self._should_generate_report():
                    await self._generate_market_report()
            
        except Exception as e:
            self.logger.error(f"❌ Monitoring cycle error: {str(e)}")
            self.logger.error(traceback.format_exc())  # Changed from debug to error level
            raise  # Re-raise to ensure proper error handling in the main loop
    
    @handle_monitoring_error(reraise=True)
    async def _process_symbol(self, symbol: str) -> None:
        """Process a single symbol through the monitoring pipeline."""
        # Debug log at the very start
        self.logger.debug(f"🚀 _process_symbol called for {symbol}")

        if not self.exchange_manager:
            error_msg = f"🚨 CRITICAL: Exchange manager not available for {symbol} - system misconfigured"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            # Extract symbol string
            symbol_str = symbol['symbol'] if isinstance(symbol, dict) and 'symbol' in symbol else symbol
            self.logger.debug(f"📊 Processing symbol_str: {symbol_str}")
            
            self.logger.debug(f"Processing symbol: {symbol_str}")
            
            # Step 1: Fetch market data
            self.logger.debug(f"🎯 TASK STEP 1: Fetching market data for {symbol_str}")
            market_data = await self.data_collector.fetch_market_data(symbol_str)
            if not market_data:
                self.logger.warning(f"No market data available for {symbol_str}")
                return {"success": False, "reason": "no_market_data", "symbol": symbol_str}
            
            # Ensure symbol field is set
            market_data['symbol'] = symbol_str
            
            # Step 2: Validate market data
            self.logger.debug(f"🎯 TASK STEP 2: Validating market data for {symbol_str}")
            if not await self.validator.validate_market_data(market_data):
                self.logger.warning(f"Invalid market data for {symbol_str}")
                return {"success": False, "reason": "invalid_market_data", "symbol": symbol_str}

            # Step 3: Process with confluence analyzer (MUST happen before regime detection)
            # NOTE: Order changed in v1.1 - confluence analysis provides the primary directional signal
            self.logger.debug(f"🎯 TASK STEP 3: Starting confluence analysis for {symbol_str}")
            confluence_score = None  # Will be populated by analyzer
            analyzer = getattr(self, 'confluence_analyzer', None)
            if analyzer and hasattr(analyzer, 'analyze') and callable(getattr(analyzer, 'analyze')):
                try:
                    # [LSR-MONITOR] Log what we're passing to confluence
                    if 'long_short_ratio' in market_data:
                        self.logger.info(f'[LSR-MONITOR] Passing LSR to confluence: {market_data["long_short_ratio"]}')
                    else:
                        self.logger.warning('[LSR-MONITOR] No LSR in market_data being passed to confluence')
                    analysis_result = await analyzer.analyze(market_data)
                    if analysis_result:
                        # Log confluence score
                        confluence_score = analysis_result.get('confluence_score', 0)
                        self.logger.info(f"✅ Confluence analysis complete for {symbol_str}: Score={confluence_score:.2f}")

                        # Step 3.5: Unified Regime Detection (NOW uses confluence as primary signal)
                        # Moved AFTER confluence analysis to enable unified classification
                        if self.regime_detector and self.regime_monitor:
                            try:
                                await self._detect_and_update_regime(symbol_str, market_data, confluence_score)
                            except Exception as e:
                                self.logger.warning(f"Regime detection error for {symbol_str}: {e}")

                        # Step 4: Process analysis result (handles signal generation internally)
                        await self._process_analysis_result(symbol_str, analysis_result, market_data)
                        
                        # Step 5: Update database if available
                        if self.database_client:
                            await self._store_analysis_result(symbol_str, analysis_result)
                    else:
                        self.logger.warning(f"No analysis result returned for {symbol_str}")
                        return {"success": False, "reason": "no_analysis_result", "symbol": symbol_str}
                
                except Exception as e:
                    self.logger.error(f"Error in confluence analysis for {symbol_str}: {str(e)}")
            
            # Step 6: Update metrics (with null check)
            if self.metrics_tracker is not None:
                await self.metrics_tracker.update_symbol_metrics(symbol_str, market_data)
            else:
                self.logger.warning(f"⚠️  Metrics tracker not initialized, skipping metrics update for {symbol_str}")

            # Step 7: Manipulation detection and alerting
            try:
                from .manipulation_detector import ManipulationDetector
                detector = getattr(self, '_manipulation_detector', None)
                if detector is None:
                    detector = ManipulationDetector(self.config, logger=self.logger.getChild('manipulation'))
                    self._manipulation_detector = detector
                alert = await detector.analyze_market_data(symbol_str, market_data)
                if alert and self.alert_manager:
                    await self.alert_manager.send_alert(
                        level="warning" if alert.severity in ("medium", "high") else "info",
                        message=f"🚨 Manipulation signal on {symbol_str}: {alert.description}",
                        details={
                            "type": "manipulation",
                            "symbol": symbol_str,
                            "manipulation_type": alert.manipulation_type,
                            "confidence": alert.confidence_score,
                            "metrics": alert.metrics,
                            "severity": alert.severity,
                        },
                        throttle=True,
                    )
            except Exception as e:
                self.logger.error(f"Manipulation detection error for {symbol_str}: {str(e)}")

            # Step 8: Whale activity detection and alerting
            try:
                self.logger.debug(f"🔍 About to call whale detection for {symbol_str}")
                await self._analyze_and_alert_whale_activity(symbol_str, market_data)
                self.logger.debug(f"✅ Whale detection completed for {symbol_str}")
            except Exception as e:
                self.logger.error(f"Whale detection error for {symbol_str}: {str(e)}")

            # Step 9: Whale trade execution detection (individual large trades)
            try:
                self.logger.debug(f"🐋 About to call whale trade detection for {symbol_str}")
                await self._detect_whale_trades(symbol_str, market_data)
                self.logger.debug(f"✅ Whale trade detection completed for {symbol_str}")
            except Exception as e:
                self.logger.error(f"Whale trade detection error for {symbol_str}: {str(e)}")

            # Step 10: Update Bitcoin prediction system with BTC price
            if symbol_str in ['BTCUSDT', 'BTC/USDT'] and self.signal_generator:
                try:
                    btc_price = market_data.get('ticker', {}).get('last', 0) or market_data.get('price', 0)
                    if btc_price > 0 and hasattr(self.signal_generator, 'update_btc_price'):
                        self.signal_generator.update_btc_price(btc_price)
                        self.logger.debug(f"✅ Updated BTC price for prediction: ${btc_price:,.2f}")
                except Exception as e:
                    self.logger.debug(f"BTC price update failed: {e}")

            # CRITICAL SUCCESS RETURN - This fixes the "15 tasks completed but did no work" error
            self.logger.debug(f"🎯 TASK SUCCESS: {symbol_str} processing completed successfully")
            return {
                "success": True,
                "symbol": symbol_str,
                "confluence_score": confluence_score if 'confluence_score' in locals() else None,
                "analysis_completed": True,
                "steps_completed": ["market_data", "validation", "confluence", "analysis", "metrics", "manipulation", "whale"],
                "timestamp": time.time()
            }

        except Exception as e:
            self.logger.error(f"❌ DETAILED ERROR in _process_symbol for {symbol_str if 'symbol_str' in locals() else symbol}: {str(e)}")
            self.logger.error(f"❌ ERROR TYPE: {type(e).__name__}")
            self.logger.error(f"❌ ERROR TRACEBACK: {traceback.format_exc()}")
            return {
                "success": False,
                "symbol": symbol_str if 'symbol_str' in locals() else str(symbol),
                "reason": "exception",
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }

    async def _analyze_and_alert_whale_activity(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """Analyze whale accumulation/distribution and emit alerts via AlertManager.

        Minimal, reliable port of legacy logic with thresholds from config.
        """
        # Debug log to confirm whale detection is being called
        self.logger.debug(f"🐋 Whale detection called for {symbol}")

        # Config
        config = self.config.get('monitoring', {}).get('whale_activity', {})
        if not config.get('enabled', True):
            return
        if not self.alert_manager:
            return

        orderbook = market_data.get('orderbook') or {}
        ticker = market_data.get('ticker') or {}
        current_price = float(ticker.get('last') or 0)
        bids = orderbook.get('bids') or []
        asks = orderbook.get('asks') or []
        if current_price <= 0 or not bids or not asks:
            return

        # Compute whale threshold from order sizes
        try:
            bid_sizes = [float(level[1]) for level in bids if len(level) >= 2]
            ask_sizes = [float(level[1]) for level in asks if len(level) >= 2]
            all_sizes = bid_sizes + ask_sizes
            if not all_sizes:
                return
            mean_size = float(np.mean(all_sizes))
            std_size = float(np.std(all_sizes))
            whale_threshold = mean_size + (2.0 * std_size)
        except Exception:
            return

        whale_bids = [lvl for lvl in bids if len(lvl) >= 2 and float(lvl[1]) >= whale_threshold]
        whale_asks = [lvl for lvl in asks if len(lvl) >= 2 and float(lvl[1]) >= whale_threshold]
        whale_bid_volume = sum(float(lvl[1]) for lvl in whale_bids)
        whale_ask_volume = sum(float(lvl[1]) for lvl in whale_asks)
        total_bid_volume = sum(float(lvl[1]) for lvl in bids)
        total_ask_volume = sum(float(lvl[1]) for lvl in asks)

        bid_usd = whale_bid_volume * current_price
        ask_usd = whale_ask_volume * current_price
        net_volume = whale_bid_volume - whale_ask_volume
        net_usd = net_volume * current_price

        bid_pct = (whale_bid_volume / total_bid_volume) if total_bid_volume > 0 else 0.0
        ask_pct = (whale_ask_volume / total_ask_volume) if total_ask_volume > 0 else 0.0
        total_whale_vol = whale_bid_volume + whale_ask_volume
        if total_whale_vol > 0:
            bid_ratio = whale_bid_volume / total_whale_vol
            ask_ratio = whale_ask_volume / total_whale_vol
            imbalance = abs(bid_ratio - ask_ratio)
        else:
            imbalance = 0.0

        accumulation_threshold = float(config.get('accumulation_threshold', 1_000_000))
        distribution_threshold = float(config.get('distribution_threshold', 1_000_000))
        imbalance_threshold = float(config.get('imbalance_threshold', 0.2))
        min_order_count = int(config.get('min_order_count', 4))
        market_percentage = float(config.get('market_percentage', 0.02))

        current_time = time.time()
        if not hasattr(self, '_last_whale_alert'):
            self._last_whale_alert = {}
        cooldown = int(config.get('cooldown', 900))
        last_time = float(self._last_whale_alert.get(symbol, 0))
        if current_time - last_time < cooldown:
            return

        # Trade-based context if present
        trades = market_data.get('trades') or []
        whale_trades_count = 0
        whale_buy_volume = 0.0
        whale_sell_volume = 0.0
        trade_imbalance = 0.0
        if trades:
            recent_cutoff = current_time - 1800
            for t in trades:
                ts = float(t.get('timestamp') or t.get('time') or 0) / (1000.0 if (t.get('timestamp') and t.get('timestamp') > 1e12) else 1.0)
                if ts and ts < recent_cutoff:
                    continue
                size = float(t.get('amount') or t.get('size') or 0)
                price = float(t.get('price') or current_price)
                side = (t.get('side') or '').lower()
                if size <= 0:
                    continue
                # slightly lower threshold for trades
                if size >= (whale_threshold / 2.0):
                    whale_trades_count += 1
                    if side == 'buy':
                        whale_buy_volume += size
                    elif side == 'sell':
                        whale_sell_volume += size
            total_trade_vol = whale_buy_volume + whale_sell_volume
            if total_trade_vol > 0:
                trade_imbalance = (whale_buy_volume - whale_sell_volume) / total_trade_vol

        # Significant conditions
        significant_acc = (
            net_usd > accumulation_threshold and
            len(whale_bids) >= min_order_count and
            bid_pct > market_percentage and
            imbalance > imbalance_threshold
        )
        significant_dist = (
            net_usd < -distribution_threshold and
            len(whale_asks) >= min_order_count and
            ask_pct > market_percentage and
            imbalance > imbalance_threshold
        )

        if not significant_acc and not significant_dist:
            return

        subtype = 'accumulation' if significant_acc else 'distribution'

        # Prepare whale trades list for display (top 10)
        whale_trades_list = []
        if trades:
            recent_cutoff = current_time - 1800
            for t in trades:
                ts = float(t.get('timestamp') or t.get('time') or 0) / (1000.0 if (t.get('timestamp') and t.get('timestamp') > 1e12) else 1.0)
                if ts and ts < recent_cutoff:
                    continue
                size = float(t.get('amount') or t.get('size') or 0)
                price = float(t.get('price') or current_price)
                side = (t.get('side') or '').lower()
                if size > 0 and size >= (whale_threshold / 2.0):
                    whale_trades_list.append({
                        'side': side,
                        'size': size,
                        'price': price,
                        'value': size * price,
                        'time': ts
                    })
            whale_trades_list = whale_trades_list[:10]  # Top 10 for display

        # Format whale bids and asks for alert display (top 10 each)
        # Convert from [price, size] format to (price, size, usd_value) tuples
        top_whale_bids = [(float(order[0]), float(order[1]), float(order[0]) * float(order[1]))
                         for order in whale_bids[:10]]
        top_whale_asks = [(float(order[0]), float(order[1]), float(order[0]) * float(order[1]))
                         for order in whale_asks[:10]]

        # Calculate trade_confirmation for manipulation detection
        net_trade_volume = whale_buy_volume - whale_sell_volume
        trade_confirmation = False
        if whale_trades_count > 0:
            trade_confirmation = (trade_imbalance > 0 and net_volume > 0) or (trade_imbalance < 0 and net_volume < 0)

        details = {
            'type': 'whale_activity',
            'subtype': subtype,
            'symbol': symbol,
            'market_data': market_data,  # QUICK WIN: Pass full market data for OI/Liquidation/LSR context
            'data': {
                'whale_bid_volume': whale_bid_volume,
                'whale_ask_volume': whale_ask_volume,
                'whale_bid_usd': bid_usd,
                'whale_ask_usd': ask_usd,
                'net_volume': net_volume,
                'net_usd_value': net_usd,
                'imbalance': imbalance,
                'threshold': whale_threshold,
                'bid_percentage': bid_pct,
                'ask_percentage': ask_pct,
                'whale_bid_orders': len(whale_bids),
                'whale_ask_orders': len(whale_asks),
                'current_price': current_price,
                'whale_trades_count': whale_trades_count,
                'whale_buy_volume': whale_buy_volume,
                'whale_sell_volume': whale_sell_volume,
                'trade_imbalance': trade_imbalance,
                'trade_confirmation': trade_confirmation,
                'top_whale_trades': whale_trades_list,
                'top_whale_bids': top_whale_bids,
                'top_whale_asks': top_whale_asks,
            }
        }

        emoji = '🐋📈' if subtype == 'accumulation' else '🐋📉'
        msg = (
            f"{emoji} Whale {subtype.title()} detected on {symbol} | "
            f"Whale bids: {len(whale_bids)}, asks: {len(whale_asks)} | "
            f"Net USD: ${abs(net_usd):,.0f} | Imbalance: {imbalance:.0%}"
        )

        await self.alert_manager.send_alert(
            level='warning',
            message=msg,
            details=details,
            throttle=True,
        )
        self._last_whale_alert[symbol] = current_time

    async def _detect_and_update_regime(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        confluence_score: Optional[float] = None
    ) -> None:
        """
        Detect market regime and push update to RegimeMonitor.

        UNIFIED REGIME SYSTEM (v1.1):
        This method now uses confluence_score as the PRIMARY directional signal,
        with ADX/EMA as validators. This provides more accurate regime detection
        by leveraging the indicator consensus from confluence analysis.

        This method performs multi-timeframe regime detection using available OHLCV data,
        enhances it with external signals (perps-tracker, CoinGecko, Fear/Greed), and
        sends updates to the RegimeMonitor which handles change detection and alerting.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            market_data: Market data dict containing OHLCV, orderbook, etc.
            confluence_score: Optional confluence score (0-100) for unified regime detection
                - 0-40: Bearish indicator consensus
                - 40-60: Neutral/mixed signals
                - 60-100: Bullish indicator consensus
        """
        import pandas as pd

        if not self.regime_detector or not self.regime_monitor:
            return

        try:
            # Extract OHLCV data by timeframe
            ohlcv_data = market_data.get('ohlcv', {})
            if not ohlcv_data:
                self.logger.debug(f"No OHLCV data for regime detection: {symbol}")
                return

            # Build timeframe dict for MTF detection
            ohlcv_by_timeframe = {}

            # Map internal timeframe names to expected format
            tf_mappings = {
                'base': '5m',    # or whatever base timeframe is
                'ltf': '1m',
                'mtf': '15m',
                'htf': '1h'
            }

            for internal_name, tf_key in tf_mappings.items():
                df = ohlcv_data.get(internal_name)
                if df is not None and isinstance(df, pd.DataFrame) and len(df) >= 50:
                    ohlcv_by_timeframe[tf_key] = df

            if len(ohlcv_by_timeframe) < 2:
                # Fall back to single timeframe if not enough MTF data
                for key, df in ohlcv_data.items():
                    if isinstance(df, pd.DataFrame) and len(df) >= 50:
                        ohlcv_by_timeframe['5m'] = df
                        break

            if not ohlcv_by_timeframe:
                self.logger.debug(f"Insufficient OHLCV data for regime detection: {symbol}")
                return

            # Extract orderbook for liquidity assessment
            orderbook = market_data.get('orderbook', {})

            # Perform MTF regime detection with unified confluence signal
            # v1.1: confluence_score is now the PRIMARY directional signal
            detection = self.regime_detector.detect_regime_mtf(
                ohlcv_by_timeframe=ohlcv_by_timeframe,
                orderbook=orderbook,
                confluence_score=confluence_score  # Unified regime: confluence as primary signal
            )

            # Log unified mode status
            if confluence_score is not None:
                self.logger.debug(
                    f"Unified regime detection for {symbol}: "
                    f"confluence={confluence_score:.1f}, regime={detection.regime.value}"
                )

            # Enhance with external signals (perps-tracker, CoinGecko, Fear/Greed)
            external_signals = await self.regime_monitor.fetch_external_signals()
            if external_signals:
                detection = self.regime_detector.enhance_regime_with_external_data(
                    detection, external_signals
                )

            # Push to RegimeMonitor (handles change detection and alerting)
            # Trigger name indicates detection mode: unified (with confluence) vs mtf (legacy)
            trigger_mode = 'unified' if confluence_score is not None else 'mtf'
            if external_signals:
                trigger_mode += '_external'

            change = await self.regime_monitor.update_regime(
                symbol=symbol,
                detection=detection,
                trigger=trigger_mode
            )

            if change:
                self.logger.info(
                    f"📊 Regime change detected: {symbol} "
                    f"{change.previous_regime} → {change.new_regime} "
                    f"(confidence: {change.new_confidence:.1%})"
                )

        except Exception as e:
            self.logger.warning(f"Regime detection failed for {symbol}: {e}")

    async def _detect_whale_trades(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """Detect individual large trades (executed whales), not just orderbook positioning.

        This complements _analyze_and_alert_whale_activity by detecting immediate
        large trade executions rather than sustained orderbook positioning.

        A $20M market buy will trigger this, even if no large orders remain in the orderbook.
        """
        config = self.config.get('monitoring', {}).get('whale_activity', {})
        if not config.get('trade_alerts_enabled', True):
            return
        if not self.alert_manager:
            return

        # Get config thresholds
        try:
            alert_threshold_usd = float(config.get('alert_threshold_usd', 300000))
            trade_cooldown = int(config.get('trade_cooldown', 600))  # 10 min
        except (ValueError, TypeError) as e:
            self.logger.error(f"Invalid whale trade config values: {e}")
            return

        # Bug #2 fix: Cooldown tracking now initialized in __init__(), no need to check hasattr
        current_time = time.time()
        last_alert = self._last_whale_trade_alert.get(symbol, 0)
        if current_time - last_alert < trade_cooldown:
            return

        # Get current price with error handling (Bug #1 fix)
        ticker = market_data.get('ticker', {})
        try:
            current_price = float(ticker.get('last', 0))
            # Bug #3 fix: Validate for NaN/Infinity
            if not (current_price > 0 and math.isfinite(current_price)):
                self.logger.warning(f"Invalid current price for {symbol}: {current_price}")
                return
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Could not parse current price for {symbol}: {e}")
            return

        # Analyze recent trades (last 5 minutes)
        trades = market_data.get('trades', [])
        if not trades or not isinstance(trades, list):
            return

        recent_cutoff = current_time - 300  # 5 min lookback
        whale_trades = []

        # Bug #1 fix: Comprehensive error handling in trade parsing loop
        for trade in trades:
            try:
                # Parse timestamp with multiple fallbacks
                ts_raw = trade.get('timestamp') or trade.get('time') or 0

                # Handle string timestamps
                if isinstance(ts_raw, str):
                    try:
                        ts = float(ts_raw)
                    except ValueError:
                        self.logger.debug(f"Skipping trade with invalid timestamp string: {ts_raw}")
                        continue
                else:
                    ts = float(ts_raw)

                # Bug #3 fix: Validate timestamp is finite
                if not math.isfinite(ts):
                    self.logger.debug(f"Skipping trade with non-finite timestamp: {ts}")
                    continue

                # Convert milliseconds to seconds if needed
                if ts > 1e12:
                    ts = ts / 1000

                # Skip old trades
                if ts < recent_cutoff or ts <= 0:
                    continue

                # Parse size/amount with fallback
                size_raw = trade.get('amount') or trade.get('size') or 0
                size = float(size_raw)

                # Bug #3 fix: Validate size
                if not (size > 0 and math.isfinite(size)):
                    continue

                # Parse price with fallback to current price
                price_raw = trade.get('price', current_price)
                price = float(price_raw) if price_raw else current_price

                # Bug #3 fix: Validate price
                if not (price > 0 and math.isfinite(price)):
                    price = current_price

                # Calculate trade value
                value_usd = size * price

                # Bug #3 fix: Validate calculated value
                if not math.isfinite(value_usd):
                    self.logger.debug(f"Skipping trade with non-finite value: size={size}, price={price}")
                    continue

                # Check if whale trade
                if value_usd >= alert_threshold_usd:
                    side = trade.get('side', 'unknown')
                    if isinstance(side, str):
                        side = side.lower()
                    else:
                        side = 'unknown'

                    whale_trades.append({
                        'size': size,
                        'price': price,
                        'value_usd': value_usd,
                        'side': side,
                        'timestamp': ts,
                        'time_ago': int(current_time - ts)
                    })

            except (ValueError, TypeError, KeyError) as e:
                # Log but continue processing other trades
                self.logger.debug(f"Skipping malformed trade in {symbol}: {e}")
                continue
            except Exception as e:
                # Catch any other unexpected errors
                self.logger.warning(f"Unexpected error processing trade in {symbol}: {e}")
                continue

        # Sort by value (largest first)
        whale_trades.sort(key=lambda x: x['value_usd'], reverse=True)

        if not whale_trades:
            return

        # Aggregate statistics
        total_buy_volume = sum(t['size'] for t in whale_trades if t['side'] == 'buy')
        total_sell_volume = sum(t['size'] for t in whale_trades if t['side'] == 'sell')
        total_buy_usd = sum(t['value_usd'] for t in whale_trades if t['side'] == 'buy')
        total_sell_usd = sum(t['value_usd'] for t in whale_trades if t['side'] == 'sell')

        net_volume = total_buy_volume - total_sell_volume
        net_usd = total_buy_usd - total_sell_usd

        # Determine priority based on largest trade
        largest_trade = whale_trades[0]
        if largest_trade['value_usd'] >= 10_000_000:
            priority = 'MEGA_WHALE'
            emoji = '🐋🚨'
            level = 'critical'
        elif largest_trade['value_usd'] >= 1_000_000:
            priority = 'LARGE_WHALE'
            emoji = '🐋⚠️'
            level = 'warning'
        else:
            priority = 'WHALE'
            emoji = '🐋'
            level = 'warning'

        # Determine direction
        direction = 'BUY' if net_usd > 0 else 'SELL' if net_usd < 0 else 'MIXED'

        # Prepare alert details (no market_data to avoid DataFrame serialization issues)
        details = {
            'type': 'whale_trade',
            'subtype': 'trade_execution',
            'priority': priority,
            'symbol': symbol,
            'data': {
                'largest_trade_usd': largest_trade['value_usd'],
                'largest_trade_side': largest_trade['side'],
                'largest_trade_size': largest_trade['size'],
                'largest_trade_price': largest_trade['price'],
                'total_whale_trades': len(whale_trades),
                'total_buy_usd': total_buy_usd,
                'total_sell_usd': total_sell_usd,
                'net_usd': net_usd,
                'direction': direction,
                'whale_trades': whale_trades[:10],  # Top 10
                'current_price': current_price,
                'lookback_seconds': 300,
                'alert_threshold_usd': alert_threshold_usd
            }
        }

        # Format alert message
        msg = (
            f"{emoji} WHALE TRADE EXECUTION on {symbol} | "
            f"Largest: ${largest_trade['value_usd']:,.0f} {largest_trade['side'].upper()} | "
            f"Total: {len(whale_trades)} whale trades, Net: ${abs(net_usd):,.0f} {direction}"
        )

        # Send alert
        await self.alert_manager.send_alert(
            level=level,
            message=msg,
            details=details,
            throttle=True
        )

        self._last_whale_trade_alert[symbol] = current_time
        self.logger.info(f"🐋 Whale trade alert sent for {symbol}: ${largest_trade['value_usd']:,.0f} {largest_trade['side']}")

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
                logger.error(f"Unhandled exception: {e}", exc_info=True)
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
        """Handle system health issues and recovery notifications."""
        if not self.alert_manager_component:
            return

        # Check for critical components
        critical_components = []
        recovered_components = []

        for comp, status in health_status['components'].items():
            current_status = status.get('status')
            previous_status = status.get('previous_status')

            # Detect critical issues
            if current_status == 'critical':
                critical_components.append({
                    'name': comp,
                    'message': status.get('message', 'No details'),
                    'response_time_ms': status.get('response_time_ms'),
                    'thresholds': status.get('thresholds')
                })

            # Detect recoveries (was critical/error, now healthy/warning)
            if previous_status in ['critical', 'error'] and current_status in ['healthy', 'warning']:
                recovered_components.append({
                    'name': comp,
                    'previous': previous_status,
                    'current': current_status,
                    'message': status.get('message', 'No details')
                })

        # Send critical alerts with enhanced context
        if critical_components:
            # Build detailed message with diagnostic info
            details_lines = []
            for comp_info in critical_components:
                comp_name = comp_info['name']
                msg = comp_info['message']
                details_lines.append(f"• {comp_name}: {msg}")

                # Add response time if available
                if comp_info.get('response_time_ms'):
                    details_lines.append(f"  Response time: {comp_info['response_time_ms']:.1f}ms")

                # Add thresholds if available
                if comp_info.get('thresholds'):
                    thresh = comp_info['thresholds']
                    details_lines.append(f"  Thresholds: warning={thresh.get('warning_ms')}ms, critical={thresh.get('critical_ms')}ms")

            await self.alert_manager_component.send_alert(
                level='critical',
                message=f"Critical system health issues: {', '.join([c['name'] for c in critical_components])}",
                details={
                    'type': 'health',
                    'components': [c['name'] for c in critical_components],
                    'diagnostic_details': '\n'.join(details_lines),
                    'health_status': health_status
                }
            )

        # Send recovery notifications
        if recovered_components:
            recovery_lines = []
            for comp_info in recovered_components:
                recovery_lines.append(
                    f"• {comp_info['name']}: {comp_info['previous']} → {comp_info['current']}"
                )
                if comp_info.get('message'):
                    recovery_lines.append(f"  {comp_info['message']}")

            await self.alert_manager_component.send_alert(
                level='info',
                message=f"✅ System health recovered: {', '.join([c['name'] for c in recovered_components])}",
                details={
                    'type': 'health_recovery',
                    'components': [c['name'] for c in recovered_components],
                    'recovery_details': '\n'.join(recovery_lines),
                    'health_status': health_status
                }
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

            # Validate that report has meaningful data before sending
            status = metrics.get('status', 'Unknown')
            active_symbols = metrics.get('active_symbols', 0)
            signals_generated = metrics.get('signals_generated', 0)

            # Skip sending empty/useless reports (typically at startup)
            if status == 'Unknown' and active_symbols == 0 and signals_generated == 0:
                self.logger.info("Skipping market report - no meaningful data yet (likely at startup)")
                return

            # Generate report content
            report = self._create_market_report(metrics)

            # Send report via alert manager (now implemented)
            try:
                sent = await self.alert_manager_component.send_report(report)
                if not sent:
                    self.logger.warning(f"Market report generated but delivery failed: {len(report)} chars")
                else:
                    self.logger.info(f"Market report delivered: {len(report)} chars")
            except Exception as e:
                self.logger.error(f"send_report raised: {e}")

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

    # ===== New monitor-level wrappers for API parity =====
    def get_monitored_symbols(self) -> List[str]:
        """Return symbols tracked in the current cycle for dashboard parity."""
        return list(self.symbols or [])

    def get_websocket_status(self) -> Dict[str, Any]:
        """Return websocket status from MarketDataManager if available; else basic status."""
        try:
            if self.market_data_manager and hasattr(self.market_data_manager, 'websocket_manager'):
                ws = getattr(self.market_data_manager, 'websocket_manager', None)
                if ws and hasattr(ws, 'get_status'):
                    return ws.get_status()
        except Exception as e:
            self.logger.warning(f"get_websocket_status fallback due to error: {e}")
        # Fallback minimal status
        return {
            'connected': False,
            'last_message_time': 0,
            'seconds_since_last_message': None,
            'messages_received': 0,
            'errors': 0,
            'active_connections': 0
        }

    async def get_ohlcv_for_report(self, symbol: str, timeframe: str = 'base') -> Optional['pd.DataFrame']:
        """Retrieve OHLCV data for reporting via MarketDataManager cache if available."""
        try:
            import pandas as pd  # Local import to avoid hard dependency if unused
            if self.market_data_manager and hasattr(self.market_data_manager, 'data_cache'):
                cache = getattr(self.market_data_manager, 'data_cache', {})
                md = cache.get(symbol) or {}
                kline = md.get('kline') or {}
                df = kline.get(timeframe)
                # Normalize list-of-candles to DataFrame if necessary
                if isinstance(df, list) and df:
                    try:
                        cols = ['timestamp','open','high','low','close','volume']
                        n = len(df[0])
                        if n >= 6:
                            frame = pd.DataFrame(df, columns=cols + [f'c{i}' for i in range(n-6)])
                        else:
                            frame = pd.DataFrame(df)
                        if 'timestamp' in frame.columns:
                            frame['timestamp'] = pd.to_datetime(frame['timestamp'], unit='ms', errors='coerce')
                            frame.set_index('timestamp', inplace=True)
                        return frame
                    except Exception:
                        pass
                # If already a DataFrame, return as-is
                try:
                    import pandas as pd  # re-import safe
                    if isinstance(df, pd.DataFrame):
                        return df
                except Exception:
                    pass
        except Exception as e:
            self.logger.warning(f"get_ohlcv_for_report error for {symbol} {timeframe}: {e}")
        return None
    
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

    async def _process_analysis_result(self, symbol: str, result: Dict[str, Any], market_data: Optional[Dict[str, Any]] = None) -> None:
        """Process analysis result and generate signals if appropriate."""
        try:
            # Generate a transaction ID for tracking this analysis throughout the system
            transaction_id = str(uuid.uuid4())
            signal_id = str(uuid.uuid4())[:8]
            result['transaction_id'] = transaction_id
            result['signal_id'] = signal_id

            # Attach market_data if provided (needed for cache aggregator to extract price/volume)
            if market_data:
                result['market_data'] = market_data
            
            # Extract key information
            confluence_score = result.get('confluence_score', 0)
            reliability = result.get('reliability', 0)
            components = result.get('components', {})
            
            # Get thresholds from config
            confluence_config = self.config.get('confluence', {})
            threshold_config = confluence_config.get('thresholds', {})
            long_threshold = float(threshold_config.get('long', threshold_config.get('buy', 71.0)))
            short_threshold = float(threshold_config.get('short', threshold_config.get('sell', 35.0)))
            
            # Log component scores
            self.logger.debug("\n=== Component Scores ===")
            for component, score in components.items():
                self.logger.debug(f"{component}: {score}")
            
            # Note: Confluence breakdown is already logged by confluence.py:611 with full quality metrics
            # Removing duplicate logging here to avoid log spam and confusion
            # The breakdown in confluence.py includes: Base Score, Quality Impact, Consensus, Confidence, Disagreement
            # If you need to re-enable this, ensure all quality parameters are passed to avoid incomplete breakdowns
            
            # Generate signal if score meets thresholds
            self.logger.info(f"=== Signal Generation Check for {symbol} ===")
            self.logger.info(f"Score: {confluence_score:.2f}, Long threshold: {long_threshold}, Short threshold: {short_threshold}")

            # Store threshold information in result for downstream processing
            result['long_threshold'] = long_threshold
            result['short_threshold'] = short_threshold

            # Determine signal type based on thresholds
            signal_type = "NEUTRAL"
            if confluence_score >= long_threshold:
                signal_type = "LONG"
            elif confluence_score <= short_threshold:
                signal_type = "SHORT"
                
            result['signal_type'] = signal_type
            
            # Process through signal processor for all signal types
            if self.signal_processor:
                self.logger.info(f"Passing {signal_type} signal for {symbol} to signal processor (score: {confluence_score:.2f})")
                await self.signal_processor.process_analysis_result(symbol, result)
            else:
                self.logger.warning(f"Signal processor not available for {symbol}")
            
            # Update metrics
            if self.metrics_tracker and hasattr(self.metrics_tracker, 'update_analysis_metrics'):
                await self.metrics_tracker.update_analysis_metrics(symbol, result)
            elif self.metrics_manager:
                # Fallback for environments where MetricsTracker lacks the bridge method
                try:
                    await self.metrics_manager.update_analysis_metrics(symbol, result)
                except Exception:
                    # Ensure metrics failures never break the analysis pipeline
                    self.logger.debug(traceback.format_exc())

            # CRITICAL FIX: Push data directly to cache to eliminate circular dependency
            if self.cache_data_aggregator:
                try:
                    await self.cache_data_aggregator.add_analysis_result(symbol, result)
                    self.logger.debug(f"✅ Pushed analysis result to cache for {symbol}")
                except Exception as cache_error:
                    self.logger.warning(f"Cache aggregator update failed for {symbol}: {cache_error}")

        except Exception as e:
            self.logger.error(f"Error processing analysis result: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def start(self):
        """
        Backward compatibility method for the original MarketMonitor interface.
        The refactored monitor runs continuously when start_monitoring() is called.
        """
        self.logger.info("Starting MarketMonitor - refactored implementation")
        try:
            await self.start_monitoring()
        except Exception as e:
            self.logger.error(f"MarketMonitor start failed: {e}")
            raise


# MarketMonitor class is defined above - no alias needed
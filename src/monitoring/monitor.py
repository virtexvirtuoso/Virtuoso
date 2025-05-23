"""Production Market Monitoring System.

This module provides the production-ready market monitoring system using 
a service-oriented architecture. The original monolithic implementation
has been refactored into modular components and services for better
maintainability, testability, and scalability.

Architecture:
- Utilities Layer: Core utility functions and validation
- Components Layer: Modular business logic components  
- Services Layer: Orchestration and workflow management
- Monitor Layer: Thin coordination and public API

Signal Generation Flow:
- The MarketMonitor coordinates all monitoring activities through the MonitoringOrchestrationService
- Market data is fetched and processed by specialized components
- Confluence analysis generates signals when thresholds are exceeded
- Signals are passed to the SignalGenerator for processing and alert dispatch
- All thresholds are defined in the config.yaml file under analysis.confluence_thresholds
"""

import asyncio
import logging
import signal
import sys
import traceback
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Import our service-based architecture
from src.monitoring.services import MonitoringOrchestrationService
from src.monitoring.components import (
    WebSocketProcessor,
    MarketDataProcessor,
    SignalProcessor,
    WhaleActivityMonitor,
    ManipulationMonitor,
    HealthMonitor as ComponentHealthMonitor
)
from src.monitoring.utilities import (
    TimestampUtility,
    MarketDataValidator,
    LoggingUtility
)

# Import external dependencies
from src.monitoring.alert_manager import AlertManager
from src.monitoring.metrics_manager import MetricsManager
from src.monitoring.health_monitor import HealthMonitor
from src.core.market.top_symbols import TopSymbolsManager
from src.core.market.market_data_manager import MarketDataManager
from src.signal_generation.signal_generator import SignalGenerator

logger = logging.getLogger(__name__)


class MarketMonitor:
    """Production Market Monitor using service-oriented architecture.
    
    This class provides the public API for market monitoring while delegating
    all business logic to the underlying service layer. It maintains backward
    compatibility with the original monolithic implementation.
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
        manipulation_detector=None,
        **kwargs
    ):
        """Initialize the MarketMonitor with service-based architecture.
        
        Args:
            exchange: Exchange instance for market data
            symbol: Optional default symbol to monitor
            exchange_manager: Exchange manager instance
            database_client: Database client for data storage
            portfolio_analyzer: Portfolio analysis instance
            confluence_analyzer: Confluence analysis instance
            timeframes: Timeframe configuration
            logger: Logger instance
            metrics_manager: Metrics manager for performance tracking
            health_monitor: Health monitor for system monitoring
            validation_config: Validation configuration
            config: Main configuration dictionary
            alert_manager: Alert manager instance
            signal_generator: Signal generator instance
            top_symbols_manager: Top symbols manager instance
            market_data_manager: Market data manager instance
            manipulation_detector: Manipulation detector instance
            **kwargs: Additional arguments for backward compatibility
        """
        # Initialize logger
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("Initializing production MarketMonitor with service-based architecture")
        
        # Store configuration and dependencies
        self.config = config or {}
        self.symbol = symbol
        self.exchange = exchange
        self.exchange_manager = exchange_manager
        self.database_client = database_client
        self.portfolio_analyzer = portfolio_analyzer
        self.confluence_analyzer = confluence_analyzer
        self.timeframes = timeframes or {
            'base': '1m',
            'ltf': '5m', 
            'mtf': '30m',
            'htf': '4h'
        }
        
        # Initialize external dependencies
        self.metrics_manager = metrics_manager
        self.health_monitor = health_monitor
        self.alert_manager = alert_manager or AlertManager(config=self.config.get('alerts', {}))
        self.signal_generator = signal_generator
        # Initialize TopSymbolsManager with proper error handling
        if top_symbols_manager:
            self.top_symbols_manager = top_symbols_manager
        else:
            try:
                from src.core.validation.service import AsyncValidationService
                validation_service = AsyncValidationService()
                self.top_symbols_manager = TopSymbolsManager(
                    exchange_manager=self.exchange_manager,
                    config=self.config,
                    validation_service=validation_service
                )
            except Exception as e:
                self.logger.warning(f"Failed to initialize TopSymbolsManager: {str(e)}")
                # Create a simple mock for testing
                class MockTopSymbolsManager:
                    def get_top_symbols(self):
                        return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
                self.top_symbols_manager = MockTopSymbolsManager()
        self.market_data_manager = market_data_manager or MarketDataManager(
            config=self.config.get('market_data', {}),
            exchange_manager=self.exchange_manager
        )
        self.manipulation_detector = manipulation_detector
        
        # Initialize utilities
        self.market_data_validator = MarketDataValidator(logger=self.logger)
        self.logging_utility = LoggingUtility(logger=self.logger)
        self.timestamp_utility = TimestampUtility()
        
        # Initialize components
        self._initialize_components()
        
        # Initialize orchestration service
        self._initialize_orchestration_service()
        
        # Monitoring state
        self.is_running = False
        self.monitoring_tasks = []
        
        # Backward compatibility attributes
        self._stats = {
            'processed_symbols': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'start_time': None,
            'uptime_seconds': 0
        }
        
        # Setup shutdown handlers
        self._setup_shutdown_handlers()
        
        self.logger.info("MarketMonitor initialized successfully with service-based architecture")
    
    def _initialize_components(self):
        """Initialize all monitoring components."""
        try:
            # WebSocket processor for real-time data
            self.websocket_processor = WebSocketProcessor(
                config=self.config,
                logger=self.logger
            )
            
            # Market data processor for data fetching and caching
            self.market_data_processor = MarketDataProcessor(
                config=self.config.get('market_data', {}),
                logger=self.logger,
                market_data_manager=self.market_data_manager,
                validator=self.market_data_validator
            )
            
            # Signal processor for confluence analysis
            self.signal_processor = SignalProcessor(
                config=self.config.get('signal_processing', {}),
                logger=self.logger,
                signal_generator=self.signal_generator,
                alert_manager=self.alert_manager,
                market_data_manager=self.market_data_manager,
                database_client=self.database_client
            )
            
            # Whale activity monitor
            self.whale_activity_monitor = WhaleActivityMonitor(
                config=self.config,
                logger=self.logger,
                alert_manager=self.alert_manager
            )
            
            # Manipulation monitor
            self.manipulation_monitor = ManipulationMonitor(
                config=self.config,
                logger=self.logger,
                alert_manager=self.alert_manager,
                manipulation_detector=self.manipulation_detector,
                database_client=self.database_client
            )
            
            # Component health monitor
            if self.metrics_manager:
                self.component_health_monitor = ComponentHealthMonitor(
                    metrics_manager=self.metrics_manager,
                    config=self.config.get('health', {})
                )
            else:
                self.component_health_monitor = None
                self.logger.warning("MetricsManager not provided, health monitoring disabled")
            
            self.logger.info("All monitoring components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {str(e)}")
            raise
    
    def _initialize_orchestration_service(self):
        """Initialize the monitoring orchestration service."""
        try:
            self.orchestration_service = MonitoringOrchestrationService(
                websocket_processor=self.websocket_processor,
                market_data_processor=self.market_data_processor,
                signal_processor=self.signal_processor,
                whale_activity_monitor=self.whale_activity_monitor,
                manipulation_monitor=self.manipulation_monitor,
                component_health_monitor=self.component_health_monitor,
                market_data_validator=self.market_data_validator,
                alert_manager=self.alert_manager,
                top_symbols_manager=self.top_symbols_manager,
                logger=self.logger,
                config=self.config
            )
            
            self.logger.info("Monitoring orchestration service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestration service: {str(e)}")
            raise
    
    def _setup_shutdown_handlers(self):
        """Setup graceful shutdown handlers."""
        def shutdown_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
    
    async def start(self, symbol: Optional[str] = None):
        """Start the market monitoring system.
        
        Args:
            symbol: Optional symbol to monitor. If not provided, monitors top symbols.
        """
        try:
            self.logger.info("Starting production MarketMonitor...")
            
            # Use provided symbol or default
            target_symbol = symbol or self.symbol
            
            # Update stats
            self._stats['start_time'] = self.timestamp_utility.get_utc_timestamp(as_ms=False)
            self.is_running = True
            
            # Start monitoring through orchestration service
            if target_symbol:
                self.logger.info(f"Starting monitoring for symbol: {target_symbol}")
                await self.orchestration_service.start_monitoring(target_symbol)
            else:
                self.logger.info("Starting monitoring for top symbols")
                await self.orchestration_service.start_monitoring()
            
            self.logger.info("MarketMonitor started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start MarketMonitor: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.is_running = False
            raise
    
    async def stop(self):
        """Stop the market monitoring system gracefully."""
        try:
            self.logger.info("Stopping MarketMonitor...")
            self.is_running = False
            
            # Stop orchestration service
            await self.orchestration_service.stop_monitoring()
            
            # Close WebSocket connections
            if self.websocket_processor:
                await self.websocket_processor.close()
            
            # Update stats
            if self._stats['start_time']:
                current_time = self.timestamp_utility.get_utc_timestamp(as_ms=False)
                self._stats['uptime_seconds'] = current_time - self._stats['start_time']
            
            self.logger.info("MarketMonitor stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error during MarketMonitor shutdown: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    async def process_symbol(self, symbol: str):
        """Process a single symbol through the monitoring workflow.
        
        Args:
            symbol: Symbol to process
        """
        try:
            await self.orchestration_service._process_symbol_with_components(symbol)
            
            # Update stats for backward compatibility
            self._stats['processed_symbols'] += 1
            self._stats['successful_analyses'] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to process symbol {symbol}: {str(e)}")
            self._stats['failed_analyses'] += 1
            raise
    
    async def fetch_market_data(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch market data for a symbol.
        
        Args:
            symbol: Symbol to fetch data for
            force_refresh: Whether to force refresh cached data
            
        Returns:
            Market data dictionary
        """
        return await self.market_data_processor.fetch_market_data(symbol, force_refresh)
    
    async def analyze_confluence_and_generate_signals(self, market_data: Dict[str, Any]):
        """Analyze confluence and generate trading signals.
        
        Args:
            market_data: Market data to analyze
        """
        await self.signal_processor.analyze_confluence_and_generate_signals(market_data)
    
    async def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate market data.
        
        Args:
            market_data: Market data to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        return await self.market_data_validator.validate_market_data(market_data)
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get monitoring statistics.
        
        Returns:
            Statistics dictionary for backward compatibility
        """
        # Get stats from orchestration service
        service_stats = self.orchestration_service.get_monitoring_statistics()
        
        # Merge with local stats for backward compatibility
        combined_stats = {**self._stats, **service_stats}
        
        # Calculate uptime if running
        if self.is_running and self._stats['start_time']:
            current_time = self.timestamp_utility.get_utc_timestamp(as_ms=False)
            combined_stats['uptime_seconds'] = current_time - self._stats['start_time']
        
        return combined_stats
    
    def get_websocket_status(self) -> Dict[str, Any]:
        """Get WebSocket connection status.
        
        Returns:
            WebSocket status information
        """
        return self.websocket_processor.get_websocket_status()
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get comprehensive monitoring statistics.
        
        Returns:
            Comprehensive statistics from the orchestration service
        """
        return self.orchestration_service.get_monitoring_statistics()
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status information.
        
        Returns:
            Service status and health information
        """
        return self.orchestration_service.get_service_status()
    
    def get_monitored_symbols(self) -> List[str]:
        """Get list of currently monitored symbols.
        
        Returns:
            List of monitored symbols
        """
        try:
            return self.top_symbols_manager.get_top_symbols()
        except Exception as e:
            self.logger.error(f"Failed to get monitored symbols: {str(e)}")
            return []
    
    def get_manipulation_stats(self) -> Dict[str, Any]:
        """Get manipulation detection statistics.
        
        Returns:
            Manipulation detection statistics
        """
        return self.manipulation_monitor.get_manipulation_stats()
    
    def get_whale_activity_stats(self) -> Dict[str, Any]:
        """Get whale activity statistics.
        
        Returns:
            Whale activity statistics
        """
        return self.whale_activity_monitor.get_whale_activity_stats()
    
    # Legacy method compatibility
    async def _monitoring_cycle(self):
        """Legacy method for backward compatibility."""
        self.logger.warning("_monitoring_cycle is deprecated, use start() instead")
        await self.start()
    
    async def _process_symbol(self, symbol: str):
        """Legacy method for backward compatibility."""
        self.logger.warning("_process_symbol is deprecated, use process_symbol() instead")
        await self.process_symbol(symbol)
    
    def _handle_shutdown(self, signum, frame):
        """Legacy shutdown handler for backward compatibility."""
        self.logger.warning("_handle_shutdown is deprecated, shutdown handling is automatic")
        asyncio.create_task(self.stop())


# Maintain backward compatibility with utility classes
# Import them from utilities module but expose them at module level
from src.monitoring.utilities import (
    TimestampUtility as TimestampUtility,
    MarketDataValidator as MarketDataValidator,
    LoggingUtility as LoggingUtility
)

# Version information
__version__ = "2.0.0"
__architecture__ = "service-oriented"

logger.info(f"Production MarketMonitor module loaded - Version {__version__} ({__architecture__})") 
"""Market data monitoring system - Refactored Version.

This module provides monitoring functionality for market data:
- Performance monitoring
- Data quality monitoring
- System health monitoring
- Alert generation

Signal Generation Flow:
- The MarketMonitor analyzes market data and calculates confluence scores
- When a score exceeds the buy threshold (60) or falls below the sell threshold (40),
  the MarketMonitor initiates signal generation
- Signals are passed to the SignalGenerator for further processing and alert dispatch
- All thresholds are defined in the config.yaml file under analysis.confluence_thresholds

This is the refactored version using extracted components for better modularity and maintainability.
"""

import logging
import time
import asyncio
import traceback
import json
import os
import signal
import sys
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

# Import and apply matplotlib silencing before matplotlib imports
from src.utils.matplotlib_utils import silence_matplotlib_logs
silence_matplotlib_logs()

import matplotlib
import psutil
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from decimal import Decimal

# Import local modules
from src.monitoring.alert_manager import AlertManager
from src.monitoring.metrics_manager import MetricsManager
from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.market_reporter import MarketReporter

# Import extracted components
from src.monitoring.components import (
    WebSocketProcessor,
    MarketDataProcessor,
    SignalProcessor,
    WhaleActivityMonitor,
    ManipulationMonitor,
    HealthMonitor as ComponentHealthMonitor
)

# Import extracted utilities
from src.monitoring.utilities import (
    TimestampUtility,
    MarketDataValidator,
    LoggingUtility,
    TimeRangeValidationRule,
    ccxt_time_to_minutes,
    handle_monitoring_error
)

from src.core.formatting import AnalysisFormatter, format_analysis_result, LogFormatter
from src.indicators.orderflow_indicators import DataUnavailableError
from src.signal_generation.signal_generator import SignalGenerator
import tracemalloc
from collections import defaultdict
import datetime as dt
import copy

# Import matplotlib for visualization
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import io
import base64
from pathlib import Path

from src.core.validation import (
    ValidationService,
    AsyncValidationService,
    ValidationContext,
    ValidationResult,
    TimeRangeRule,
    SymbolRule
)
from src.core.error.models import ErrorContext, ErrorSeverity
from src.monitoring.metrics_manager import MetricsManager
from src.monitoring.alert_manager import AlertManager
from src.core.market.top_symbols import TopSymbolsManager
from src.core.analysis.confluence import ConfluenceAnalyzer
from src.core.market.market_data_manager import MarketDataManager
from src.monitoring.health_monitor import HealthMonitor
from src.core.exchanges.websocket_manager import WebSocketManager

# Add import for liquidation cache
from src.utils.liquidation_cache import liquidation_cache

import gc

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

tracemalloc.start()


class MarketMonitor:
    """
    Market monitoring service using extracted components.
    
    This refactored version demonstrates the integration of the extracted components:
    - WebSocketProcessor: Handles real-time data processing
    - MarketDataProcessor: Manages market data fetching and processing
    - SignalProcessor: Handles signal generation and trade parameters
    - WhaleActivityMonitor: Monitors whale activity patterns
    - ManipulationMonitor: Detects market manipulation
    - HealthMonitor: System health monitoring
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
        """
        Initialize the MarketMonitor with extracted components.
        
        Args:
            exchange: Exchange instance
            symbol: Trading symbol to monitor
            exchange_manager: Exchange manager instance
            database_client: Database client for data storage
            portfolio_analyzer: Portfolio analysis component
            confluence_analyzer: Confluence analysis component
            timeframes: Timeframe configuration
            logger: Logger instance
            metrics_manager: Metrics management component
            health_monitor: Health monitoring component
            validation_config: Validation configuration
            config: General configuration
            alert_manager: Alert management component
            signal_generator: Signal generation component
            top_symbols_manager: Top symbols management component
            market_data_manager: Market data management component
            manipulation_detector: Manipulation detection component
            **kwargs: Additional arguments
        """
        # Initialize basic attributes
        self.exchange = exchange
        self.symbol = symbol
        self.exchange_manager = exchange_manager
        self.database_client = database_client
        self.portfolio_analyzer = portfolio_analyzer
        self.confluence_analyzer = confluence_analyzer
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        self.alert_manager = alert_manager
        self.signal_generator = signal_generator
        self.top_symbols_manager = top_symbols_manager
        self.market_data_manager = market_data_manager
        self.manipulation_detector = manipulation_detector
        
        # Initialize extracted utilities
        self.market_data_validator = MarketDataValidator(self.logger)
        self.logging_utility = LoggingUtility(self.logger)
        self.timestamp_utility = TimestampUtility()
        
        # Initialize extracted components with dependency injection
        self.websocket_processor = WebSocketProcessor(
            logger=self.logger,
            config=self.config.get('websocket', {}),
            exchange_manager=self.exchange_manager
        )
        
        self.market_data_processor = MarketDataProcessor(
            logger=self.logger,
            config=self.config.get('market_data', {}),
            exchange=self.exchange,
            market_data_manager=self.market_data_manager,
            validator=self.market_data_validator
        )
        
        self.signal_processor = SignalProcessor(
            logger=self.logger,
            config=self.config.get('signal_processing', {}),
            signal_generator=self.signal_generator,
            alert_manager=self.alert_manager,
            market_data_manager=self.market_data_manager,
            database_client=self.database_client
        )
        
        self.whale_activity_monitor = WhaleActivityMonitor(
            logger=self.logger,
            config=self.config,
            alert_manager=self.alert_manager
        )
        
        self.manipulation_monitor = ManipulationMonitor(
            logger=self.logger,
            config=self.config,
            alert_manager=self.alert_manager,
            manipulation_detector=self.manipulation_detector,
            database_client=self.database_client
        )
        
        self.component_health_monitor = ComponentHealthMonitor(
            logger=self.logger,
            config=self.config.get('health', {}),
            database_client=self.database_client
        )
        
        # Set up timeframes
        self.timeframes = timeframes or {
            'base': '1m',
            'ltf': '5m',
            'mtf': '15m',
            'htf': '1h'
        }
        
        # Initialize other attributes
        self.is_running = False
        self.metrics_manager = metrics_manager
        self.health_monitor = health_monitor
        self.validation_config = validation_config or {}
        
        # Initialize statistics and tracking
        self.stats_data = {
            'processed_symbols': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'alerts_generated': 0,
            'start_time': None,
            'last_analysis_time': None
        }
        
        # Set up signal handling
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        self.logger.info("MarketMonitor initialized with extracted components")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.is_running = False

    async def start(self):
        """Start the monitoring system."""
        try:
            self.logger.info("Starting MarketMonitor with component-based architecture...")
            self.is_running = True
            self.stats_data['start_time'] = time.time()
            
            # Initialize WebSocket processor
            await self.websocket_processor.initialize()
            
            # Start monitoring tasks
            await self._start_monitoring_tasks()
            
            # Start main monitoring loop
            await self._run_monitoring_loop()
            
        except Exception as e:
            self.logger.error(f"Error starting MarketMonitor: {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise

    async def _start_monitoring_tasks(self) -> None:
        """Start monitoring tasks using components."""
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

    async def _run_monitoring_loop(self) -> None:
        """Main monitoring loop using extracted components."""
        try:
            while self.is_running:
                try:
                    # Get symbols to monitor
                    symbols = self.get_monitored_symbols()
                    
                    if not symbols:
                        self.logger.warning("No symbols to monitor")
                        await asyncio.sleep(10)
                        continue
                    
                    # Process each symbol
                    for symbol in symbols:
                        if not self.is_running:
                            break
                            
                        await self._process_symbol_with_components(symbol)
                        
                        # Small delay between symbols
                        await asyncio.sleep(1)
                    
                    # Update statistics
                    self.stats_data['last_analysis_time'] = time.time()
                    
                    # Health check
                    await self._perform_health_checks()
                    
                    # Wait before next cycle
                    await asyncio.sleep(30)  # 30 second cycle
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    await asyncio.sleep(5)  # Short delay on error
                    
        except Exception as e:
            self.logger.error(f"Fatal error in monitoring loop: {str(e)}")
            raise

    async def _process_symbol_with_components(self, symbol: str) -> None:
        """Process a symbol using the extracted components."""
        try:
            self.logger.debug(f"Processing symbol {symbol} with components")
            
            # 1. Fetch market data using MarketDataProcessor
            market_data = await self.market_data_processor.fetch_market_data(symbol)
            
            if not market_data:
                self.logger.warning(f"No market data available for {symbol}")
                return
            
            # 2. Validate market data
            is_valid = await self.market_data_validator.validate_market_data(market_data)
            if not is_valid:
                self.logger.warning(f"Market data validation failed for {symbol}")
                return
            
            # 3. Process with WebSocket data if available
            real_time_data = self.websocket_processor.get_real_time_data(symbol)
            if real_time_data:
                market_data.update(real_time_data)
            
            # 4. Analyze confluence and generate signals using SignalProcessor
            await self.signal_processor.analyze_confluence_and_generate_signals(market_data)
            
            # 5. Monitor whale activity
            await self.whale_activity_monitor.monitor_whale_activity(symbol, market_data)
            
            # 6. Monitor for manipulation
            await self.manipulation_monitor.monitor_manipulation_activity(symbol, market_data)
            
            # Update statistics
            self.stats_data['processed_symbols'] += 1
            self.stats_data['successful_analyses'] += 1
            
            self.logger.debug(f"Successfully processed {symbol} with components")
            
        except Exception as e:
            self.logger.error(f"Error processing symbol {symbol} with components: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.stats_data['failed_analyses'] += 1

    async def _perform_health_checks(self) -> None:
        """Perform system health checks using the component."""
        try:
            # Use the component health monitor
            health_status = await self.component_health_monitor.check_health()
            
            if not health_status.get('healthy', True):
                self.logger.warning(f"Health check failed: {health_status}")
                
                # Send alert if configured
                if self.alert_manager:
                    await self.alert_manager.send_alert(
                        level="warning",
                        message="System health check failed",
                        details=health_status
                    )
            
        except Exception as e:
            self.logger.error(f"Error performing health checks: {str(e)}")

    def get_monitored_symbols(self) -> List[str]:
        """Get the list of symbols to monitor."""
        try:
            if self.top_symbols_manager:
                return self.top_symbols_manager.get_top_symbols()
            elif self.symbol:
                return [self.symbol]
            else:
                # Default symbols for testing
                return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
                
        except Exception as e:
            self.logger.error(f"Error getting monitored symbols: {str(e)}")
            return []

    async def stop(self) -> None:
        """Stop the monitoring system gracefully."""
        try:
            self.logger.info("Stopping MarketMonitor...")
            self.is_running = False
            
            # Stop WebSocket processor
            await self.websocket_processor.close()
            
            # Cancel monitoring tasks
            if hasattr(self, 'monitoring_tasks'):
                for task in self.monitoring_tasks:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
            
            # Cleanup components
            await self._cleanup_components()
            
            self.logger.info("MarketMonitor stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping MarketMonitor: {str(e)}")
            raise

    async def _cleanup_components(self):
        """Cleanup all components."""
        try:
            # Cleanup each component if needed
            cleanup_tasks = []
            
            if hasattr(self.market_data_processor, 'cleanup'):
                cleanup_tasks.append(self.market_data_processor.cleanup())
                
            if hasattr(self.signal_processor, 'cleanup'):
                cleanup_tasks.append(self.signal_processor.cleanup())
            
            # Wait for all cleanup tasks
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            self.logger.info("Component cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during component cleanup: {str(e)}")

    @property
    def stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        current_time = time.time()
        start_time = self.stats_data.get('start_time')
        
        stats = {
            'uptime_seconds': current_time - start_time if start_time else 0,
            'processed_symbols': self.stats_data['processed_symbols'],
            'successful_analyses': self.stats_data['successful_analyses'],
            'failed_analyses': self.stats_data['failed_analyses'],
            'success_rate': 0.0,
            'last_analysis_time': self.stats_data.get('last_analysis_time'),
            'is_running': self.is_running
        }
        
        # Calculate success rate
        total_analyses = stats['successful_analyses'] + stats['failed_analyses']
        if total_analyses > 0:
            stats['success_rate'] = stats['successful_analyses'] / total_analyses
        
        # Add component statistics
        stats.update({
            'websocket_status': self.websocket_processor.get_status() if hasattr(self.websocket_processor, 'get_status') else {},
            'market_data_cache_stats': self.market_data_processor.get_cache_stats() if hasattr(self.market_data_processor, 'get_cache_stats') else {},
            'whale_activity_stats': self.whale_activity_monitor.get_whale_activity_stats(),
            'manipulation_stats': self.manipulation_monitor.get_manipulation_stats(),
            'validation_stats': self.market_data_validator.get_validation_stats()
        })
        
        return stats

    def get_component_status(self) -> Dict[str, Any]:
        """Get status of all components."""
        return {
            'websocket_processor': {
                'initialized': self.websocket_processor is not None,
                'status': self.websocket_processor.get_status() if hasattr(self.websocket_processor, 'get_status') else {}
            },
            'market_data_processor': {
                'initialized': self.market_data_processor is not None,
                'cache_stats': self.market_data_processor.get_cache_stats() if hasattr(self.market_data_processor, 'get_cache_stats') else {}
            },
            'signal_processor': {
                'initialized': self.signal_processor is not None
            },
            'whale_activity_monitor': {
                'initialized': self.whale_activity_monitor is not None,
                'stats': self.whale_activity_monitor.get_whale_activity_stats()
            },
            'manipulation_monitor': {
                'initialized': self.manipulation_monitor is not None,
                'component_status': self.manipulation_monitor.get_component_status()
            },
            'health_monitor': {
                'initialized': self.component_health_monitor is not None
            }
        }

    # Legacy method compatibility - delegate to components
    async def fetch_market_data(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Legacy compatibility - delegate to MarketDataProcessor."""
        return await self.market_data_processor.fetch_market_data(symbol, force_refresh)

    async def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Legacy compatibility - delegate to MarketDataValidator."""
        return await self.market_data_validator.validate_market_data(market_data)

    def get_websocket_status(self) -> Dict[str, Any]:
        """Legacy compatibility - delegate to WebSocketProcessor."""
        return self.websocket_processor.get_status() if hasattr(self.websocket_processor, 'get_status') else {}

    # Add any additional methods that need to maintain backward compatibility...


# Example usage and demonstration
async def main():
    """Example usage of the refactored MarketMonitor."""
    
    # Configuration
    config = {
        'websocket': {
            'enabled': True,
            'reconnect_attempts': 5
        },
        'market_data': {
            'cache_ttl': 300,
            'enable_validation': True
        },
        'signal_processing': {
            'confluence_thresholds': {
                'buy': 60,
                'sell': 40
            }
        },
        'whale_activity': {
            'enabled': True,
            'cooldown': 900,
            'accumulation_threshold': 1000000
        },
        'health': {
            'check_interval': 60
        }
    }
    
    # Initialize and start the monitor
    monitor = MarketMonitor(
        symbol='BTCUSDT',
        config=config,
        logger=logging.getLogger(__name__)
    )
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt, stopping...")
    finally:
        await monitor.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 
"""Market data monitoring system - Service-Based Version (Phase 3).

This module demonstrates Phase 3 of the refactoring: Service Layer Creation.
The MarketMonitor now delegates its core business logic to services, showing
the evolution from:
  Monolithic (6,731 lines) → Components (601 lines) → Services (~200 lines)

This version uses the MonitoringOrchestrationService to handle all monitoring
business logic while the MarketMonitor becomes a thin coordination layer.
"""

import logging
import time
import signal
import asyncio
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

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
    LoggingUtility
)

# Import service layer
from src.monitoring.services import MonitoringOrchestrationService

logger = logging.getLogger(__name__)


class MarketMonitor:
    """
    Service-based Market monitoring system (Phase 3).
    
    This version demonstrates the service layer pattern where the MarketMonitor
    becomes a thin coordination layer that delegates all business logic to
    specialized services.
    
    Key improvements in Phase 3:
    - Business logic extracted to MonitoringOrchestrationService
    - Clean separation between infrastructure and business concerns
    - Enhanced testability through service isolation
    - Better reusability of monitoring workflows
    - Simplified main class focused on initialization and coordination
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
        metrics_manager=None,
        health_monitor=None,
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
        Initialize the service-based MarketMonitor.
        
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
        
        # Initialize utilities
        self.market_data_validator = MarketDataValidator(self.logger)
        self.logging_utility = LoggingUtility(self.logger)
        self.timestamp_utility = TimestampUtility()
        
        # Initialize components
        self._initialize_components()
        
        # Initialize the orchestration service (Phase 3)
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
        
        # Set up timeframes
        self.timeframes = timeframes or {
            'base': '1m',
            'ltf': '5m',
            'mtf': '15m',
            'htf': '1h'
        }
        
        # Set up signal handling
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        self.logger.info("Service-based MarketMonitor initialized (Phase 3)")

    def _initialize_components(self):
        """Initialize all monitoring components."""
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

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        # The orchestration service will handle the actual shutdown

    async def start(self):
        """
        Start the monitoring system using the orchestration service.
        
        This is now a thin wrapper that delegates to the service layer.
        """
        try:
            self.logger.info("Starting service-based MarketMonitor...")
            
            # Initialize WebSocket processor
            await self.websocket_processor.initialize()
            
            # Delegate to orchestration service
            await self.orchestration_service.start_monitoring(self.symbol)
            
        except Exception as e:
            self.logger.error(f"Error starting service-based MarketMonitor: {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise

    async def stop(self) -> None:
        """
        Stop the monitoring system gracefully.
        
        This delegates to the orchestration service for proper cleanup.
        """
        try:
            self.logger.info("Stopping service-based MarketMonitor...")
            
            # Delegate to orchestration service
            await self.orchestration_service.stop_monitoring()
            
            # Stop WebSocket processor
            await self.websocket_processor.close()
            
            self.logger.info("Service-based MarketMonitor stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping service-based MarketMonitor: {str(e)}")
            raise

    @property
    def stats(self) -> Dict[str, Any]:
        """
        Get monitoring statistics.
        
        Delegates to the orchestration service for comprehensive statistics.
        """
        return self.orchestration_service.get_monitoring_statistics()

    def get_component_status(self) -> Dict[str, Any]:
        """
        Get status of all components.
        
        Combines service status with component status for full visibility.
        """
        service_status = self.orchestration_service.get_service_status()
        
        return {
            'service_layer': service_status,
            'components': {
                'websocket_processor': {
                    'initialized': self.websocket_processor is not None,
                    'status': self.websocket_processor.get_websocket_status() if hasattr(self.websocket_processor, 'get_websocket_status') else {}
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
        }

    # Legacy method compatibility - delegate to components/services
    async def fetch_market_data(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Legacy compatibility - delegate to MarketDataProcessor."""
        return await self.market_data_processor.fetch_market_data(symbol, force_refresh)

    async def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Legacy compatibility - delegate to MarketDataValidator."""
        return await self.market_data_validator.validate_market_data(market_data)

    def get_websocket_status(self) -> Dict[str, Any]:
        """Legacy compatibility - delegate to WebSocketProcessor."""
        return self.websocket_processor.get_websocket_status() if hasattr(self.websocket_processor, 'get_websocket_status') else {}

    def get_monitored_symbols(self) -> List[str]:
        """Legacy compatibility - delegate to orchestration service."""
        return self.orchestration_service._get_monitored_symbols(self.symbol)

    # Service layer specific methods
    def get_orchestration_service(self) -> MonitoringOrchestrationService:
        """Get direct access to the orchestration service for advanced usage."""
        return self.orchestration_service

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get detailed service layer statistics."""
        return {
            'architecture_version': 'Phase 3 - Service Layer',
            'total_services': 1,
            'total_components': 6,
            'total_utilities': 4,
            'orchestration_service': self.orchestration_service.get_monitoring_statistics()
        }


# Example usage demonstrating the service-based architecture
async def main():
    """Example usage of the service-based MarketMonitor."""
    
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
        },
        'monitoring': {
            'cycle_interval': 30
        }
    }
    
    # Initialize and start the service-based monitor
    monitor = MarketMonitor(
        symbol='BTCUSDT',
        config=config,
        logger=logging.getLogger(__name__)
    )
    
    # Display architecture information
    print("\n🚀 Phase 3: Service-Based Architecture")
    print("=" * 50)
    
    service_stats = monitor.get_service_statistics()
    print(f"Architecture Version: {service_stats['architecture_version']}")
    print(f"Total Services: {service_stats['total_services']}")
    print(f"Total Components: {service_stats['total_components']}")
    print(f"Total Utilities: {service_stats['total_utilities']}")
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt, stopping...")
    finally:
        await monitor.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 
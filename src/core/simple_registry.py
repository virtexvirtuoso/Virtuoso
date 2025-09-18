"""
Simple Service Registry for Virtuoso CCXT

A lightweight replacement for the over-engineered DI container.
This provides basic service registration and retrieval in ~50 lines
instead of 535 lines of complex abstraction.

Philosophy: Keep it simple. We don't need enterprise-grade DI for a trading system.
"""

import logging
from typing import Dict, Any, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SimpleRegistry:
    """
    Simple service registry for managing application components.
    
    No complex lifetime management, no memory leak detection, no factories.
    Just a simple dictionary of services that works.
    """
    
    def __init__(self):
        """Initialize the simple registry."""
        self._services: Dict[str, Any] = {}
        self._types: Dict[Type, Any] = {}
        logger.info("SimpleRegistry initialized")
    
    def register(self, name: str, service: Any) -> None:
        """
        Register a service by name.
        
        Args:
            name: Service name
            service: Service instance
        """
        self._services[name] = service
        self._types[type(service)] = service
        logger.debug(f"Registered service: {name}")
    
    def register_type(self, service_type: Type[T], instance: T) -> None:
        """
        Register a service by type.
        
        Args:
            service_type: Service type/class
            instance: Service instance
        """
        self._types[service_type] = instance
        logger.debug(f"Registered type: {service_type.__name__}")
    
    def get(self, name: str) -> Optional[Any]:
        """
        Get a service by name.
        
        Args:
            name: Service name
            
        Returns:
            Service instance or None
        """
        return self._services.get(name)
    
    def get_type(self, service_type: Type[T]) -> Optional[T]:
        """
        Get a service by type.
        
        Args:
            service_type: Service type/class
            
        Returns:
            Service instance or None
        """
        return self._types.get(service_type)
    
    def get_required(self, name: str) -> Any:
        """
        Get a required service by name (raises if not found).
        
        Args:
            name: Service name
            
        Returns:
            Service instance
            
        Raises:
            ValueError: If service not found
        """
        service = self.get(name)
        if service is None:
            raise ValueError(f"Required service '{name}' not found")
        return service
    
    def get_all(self) -> Dict[str, Any]:
        """Get all registered services."""
        return self._services.copy()
    
    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._types.clear()
        logger.info("Registry cleared")


# Global registry instance
registry = SimpleRegistry()


def register_core_services(config: Dict[str, Any]) -> SimpleRegistry:
    """
    Register core services for the application.
    
    This replaces the complex DI registration with simple, direct instantiation.
    
    Args:
        config: Application configuration
        
    Returns:
        Registry with services registered
    """
    logger.info("Registering core services...")
    
    # Import only what we need
    from ..exchanges.manager import ExchangeManager
    from ..market.market_data_manager import MarketDataManager
    from ..analysis.confluence import ConfluenceAnalyzer
    from ..analysis.interpretation_generator import InterpretationGenerator
    from ..cache_warmer import CacheWarmer
    from ..streaming.realtime_pipeline import RealTimePipeline
    from ..formatting.formatter import OutputFormatter
    from monitoring.smart_money_detector import SmartMoneyDetector
    from ..exchanges.liquidation_collector import LiquidationDataCollector
    from monitoring.monitor import MarketMonitor
    from monitoring.alert_manager import AlertManager
    from monitoring.metrics_manager import MetricsManager
    
    # Create instances directly - no factory pattern needed
    exchange_manager = ExchangeManager(config)
    registry.register('exchange_manager', exchange_manager)
    registry.register_type(ExchangeManager, exchange_manager)
    
    # Alert manager (needed by market data manager)
    alert_manager = AlertManager(config)
    registry.register('alert_manager', alert_manager)
    registry.register_type(AlertManager, alert_manager)
    
    # Market data manager
    market_data_manager = MarketDataManager(config, exchange_manager, alert_manager)
    registry.register('market_data_manager', market_data_manager)
    registry.register_type(MarketDataManager, market_data_manager)
    
    # Confluence analyzer
    confluence_analyzer = ConfluenceAnalyzer(config)
    registry.register('confluence_analyzer', confluence_analyzer)
    registry.register_type(ConfluenceAnalyzer, confluence_analyzer)
    
    # Interpretation generator
    interpretation_generator = InterpretationGenerator()
    registry.register('interpretation_generator', interpretation_generator)
    registry.register_type(InterpretationGenerator, interpretation_generator)
    
    # Cache warmer
    cache_warmer = CacheWarmer(config)
    registry.register('cache_warmer', cache_warmer)
    registry.register_type(CacheWarmer, cache_warmer)
    
    # Real-time pipeline
    realtime_pipeline = RealTimePipeline(config)
    registry.register('realtime_pipeline', realtime_pipeline)
    registry.register_type(RealTimePipeline, realtime_pipeline)
    
    # Output formatter
    formatter = OutputFormatter()
    registry.register('formatter', formatter)
    registry.register_type(OutputFormatter, formatter)
    
    # Smart money detector - CONNECT THE ORPHANED COMPONENT
    smart_money_detector = SmartMoneyDetector(
        exchange_manager=exchange_manager,
        alert_manager=alert_manager
    )
    registry.register('smart_money_detector', smart_money_detector)
    registry.register_type(SmartMoneyDetector, smart_money_detector)
    
    # Liquidation collector - CONNECT THE ORPHANED COMPONENT
    liquidation_collector = LiquidationDataCollector(config)
    registry.register('liquidation_collector', liquidation_collector)
    registry.register_type(LiquidationDataCollector, liquidation_collector)
    
    # Metrics manager
    metrics_manager = MetricsManager()
    registry.register('metrics_manager', metrics_manager)
    registry.register_type(MetricsManager, metrics_manager)
    
    # Market monitor with all components connected
    market_monitor = MarketMonitor(
        exchange_manager=exchange_manager,
        confluence_analyzer=confluence_analyzer,
        alert_manager=alert_manager,
        metrics_manager=metrics_manager,
        market_data_manager=market_data_manager,
        smart_money_detector=smart_money_detector,  # NOW CONNECTED!
        liquidation_collector=liquidation_collector,  # NOW CONNECTED!
        config=config
    )
    registry.register('market_monitor', market_monitor)
    registry.register_type(MarketMonitor, market_monitor)
    
    logger.info(f"Registered {len(registry.get_all())} core services")
    return registry
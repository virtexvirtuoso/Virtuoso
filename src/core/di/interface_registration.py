"""
Interface-Based Service Registration for Virtuoso DI System.

This module provides clean, interface-based service registration following SOLID
principles and proper dependency injection patterns. This is the recommended
approach for new registrations and the migration target for existing concrete
registrations.

Key Principles:
- Interface-based registration: Services registered via interfaces
- Loose coupling: Dependencies injected through abstractions
- Single responsibility: Each service has a focused purpose
- Proper lifetime management: Singletons for state, transients for stateless
- Backward compatibility: Dual registration during migration
"""

from typing import Optional, Dict, Any
import logging
from ..interfaces.services import (
    # Core Infrastructure Interfaces
    IAlertService, IMetricsService, IInterpretationService, 
    IFormattingService, IValidationService, IConfigService,
    
    # Extended Core Interfaces (Priority 1)
    IExchangeManagerService, IMarketDataService, IMonitoringService,
    ISignalService, IWebSocketService, IHealthService, IReportingService,
    
    # Existing Interfaces
    IExchangeService, IIndicatorService, IAnalysisService, IPortfolioService
)
from .container import ServiceContainer, ServiceLifetime

logger = logging.getLogger(__name__)


def register_interface_based_services(container: ServiceContainer, config: Optional[Dict[str, Any]] = None) -> ServiceContainer:
    """
    Register all services using interface-based dependency injection patterns.
    
    This is the new, clean registration approach that follows SOLID principles:
    - Services registered via interfaces for loose coupling
    - Proper lifetime management 
    - Clean factory functions with minimal dependencies
    - Backward compatibility through dual registration
    
    Args:
        container: The DI container to register services with
        config: Optional configuration dictionary
        
    Returns:
        The container with interface-based services registered
    """
    logger.info("🔄 Registering interface-based services...")
    
    config = config or {}
    
    # Register services in dependency order (least dependent first)
    _register_infrastructure_services(container, config)
    _register_exchange_services(container, config)
    _register_data_services(container, config)
    _register_analysis_services(container, config)
    _register_monitoring_services(container, config)
    _register_api_services(container, config)
    
    logger.info("✅ Interface-based services registered successfully")
    return container


def _register_infrastructure_services(container: ServiceContainer, config: Dict[str, Any]) -> None:
    """Register core infrastructure services via interfaces."""
    logger.info("📦 Registering infrastructure services...")
    
    # IConfigService - Singleton (shared configuration state)
    async def create_config_service():
        from src.utils.config import ConfigManager
        if config:
            return ConfigManager(config)
        return ConfigManager()
    
    container.register_factory(IConfigService, create_config_service, ServiceLifetime.SINGLETON)
    
    # IValidationService - Singleton (shared validation rules and state)
    async def create_validation_service():
        try:
            from src.validation.core.validator import CoreValidator
            return CoreValidator()
        except ImportError as e:
            logger.warning(f"Using fallback validator: {e}")
            class FallbackValidator:
                async def validate(self, data, rules=None):
                    return {'valid': True, 'errors': [], 'warnings': [], 'metadata': {}}
                def add_rule(self, rule_name: str, rule: Any) -> None: pass
                def remove_rule(self, rule_name: str) -> None: pass
                def get_validation_stats(self) -> Dict[str, Any]: return {}
                async def validate_config(self, config: Dict[str, Any]): return self.validate(config)
                async def validate_market_data(self, market_data: Dict[str, Any]): return self.validate(market_data)
            return FallbackValidator()
    
    container.register_factory(IValidationService, create_validation_service, ServiceLifetime.SINGLETON)
    
    # IFormattingService - Transient (stateless formatting)
    async def create_formatting_service():
        from src.utils.formatters import DataFormatter
        return DataFormatter()
    
    container.register_factory(IFormattingService, create_formatting_service, ServiceLifetime.TRANSIENT)
    
    # IInterpretationService - Scoped (per-analysis context)
    async def create_interpretation_service():
        from src.core.analysis.interpretation_generator import InterpretationGenerator
        return InterpretationGenerator()
    
    container.register_factory(IInterpretationService, create_interpretation_service, ServiceLifetime.SCOPED)


def _register_exchange_services(container: ServiceContainer, config: Dict[str, Any]) -> None:
    """Register exchange-related services via interfaces."""
    logger.info("🔗 Registering exchange services...")
    
    # IExchangeManagerService - Singleton (connection pooling, state management)
    async def create_exchange_manager():
        # Fast mode: use lightweight mock instead of real exchange manager
        if config.get('_fast_mode', False):
            class FastExchangeManager:
                def __init__(self, *args, **kwargs): pass
                async def initialize(self): pass
                def get_exchange_status(self): return {'status': 'connected', 'exchange': 'mock'}
                def get_supported_symbols(self): return ['BTCUSDT', 'ETHUSDT']
                async def get_market_data(self, symbol, timeframe): return {}
                async def fetch_ohlcv(self, symbol, timeframe, limit=100): return []
                def is_healthy(self): return True
            return FastExchangeManager()
        
        from src.core.exchanges.manager import ExchangeManager
        from src.config.manager import ConfigManager
        
        config_service = await container.get_service(IConfigService)
        if isinstance(config_service, ConfigManager):
            manager = ExchangeManager(config_service)
        else:
            manager = ExchangeManager(ConfigManager())
        
        await manager.initialize()
        return manager
    
    container.register_factory(IExchangeManagerService, create_exchange_manager, ServiceLifetime.SINGLETON)
    
    # IExchangeService - Singleton (primary exchange connection)
    async def create_exchange_service():
        from src.core.exchanges.bybit import BybitExchange
        
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
        
        if 'exchanges' not in config_dict:
            config_dict['exchanges'] = {
                'bybit': {
                    'rest_endpoint': 'https://api.bybit.com',
                    'websocket_endpoint': 'wss://stream.bybit.com',
                    'testnet': False,
                    'primary': True
                }
            }
        
        return BybitExchange(config_dict)
    
    container.register_factory(IExchangeService, create_exchange_service, ServiceLifetime.SINGLETON)
    
    # IWebSocketService - Singleton (stateful connection management)
    async def create_websocket_service():
        from src.core.exchanges.websocket_manager import WebSocketManager
        
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
        return WebSocketManager(config_dict)
    
    container.register_factory(IWebSocketService, create_websocket_service, ServiceLifetime.SINGLETON)


def _register_data_services(container: ServiceContainer, config: Dict[str, Any]) -> None:
    """Register data management services via interfaces."""
    logger.info("📊 Registering data services...")
    
    # IMarketDataService - Singleton (data caching, expensive initialization)
    async def create_market_data_service():
        # Fast mode: use lightweight mock instead of real market data manager
        if config.get('_fast_mode', False):
            class FastMarketDataManager:
                def __init__(self, *args, **kwargs): pass
                def get_supported_symbols(self): return ['BTCUSDT', 'ETHUSDT']
                async def get_market_data(self, symbol): return {'symbol': symbol, 'price': 50000}
                async def fetch_ohlcv_data(self, symbol, timeframe, limit=100): return []
                def is_healthy(self): return True
            return FastMarketDataManager()
        
        from src.core.market.market_data_manager import MarketDataManager
        
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
        
        exchange_manager = await container.get_service(IExchangeManagerService)
        return MarketDataManager(config_dict, exchange_manager, None)
    
    container.register_factory(IMarketDataService, create_market_data_service, ServiceLifetime.SINGLETON)


def _register_analysis_services(container: ServiceContainer, config: Dict[str, Any]) -> None:
    """Register analysis services via interfaces."""
    logger.info("🔍 Registering analysis services...")
    
    # IAnalysisService - Singleton (confluence analysis state)
    async def create_analysis_service():
        # Fast mode: use lightweight mock instead of real confluence analyzer
        if config.get('_fast_mode', False):
            class FastConfluenceAnalyzer:
                def __init__(self, *args, **kwargs): pass
                async def analyze(self, symbol, data=None): return {'confluence_score': 75.0, 'signals': ['BULLISH']}
                async def calculate_confluence(self, symbol, timeframe_data): return 75.0
                def get_analysis_status(self): return {'status': 'active', 'symbols_analyzed': 5}
                def is_healthy(self): return True
            return FastConfluenceAnalyzer()
        
        from src.core.analysis.confluence import ConfluenceAnalyzer
        
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
        
        # Get interpretation service for enhanced analysis
        interpretation_service = None
        try:
            interpretation_service = await container.get_service(IInterpretationService)
        except Exception as e:
            logger.debug(f"InterpretationService not available: {e}")
        
        # Ensure timeframes config exists with validation requirements
        if 'timeframes' not in config_dict:
            config_dict['timeframes'] = {
                'base': {
                    'interval': 1, 
                    'required': 1000, 
                    'weight': 0.4,
                    'validation': {'min_candles': 100}
                },
                'ltf': {
                    'interval': 5, 
                    'required': 200, 
                    'weight': 0.3,
                    'validation': {'min_candles': 50}
                },
                'mtf': {
                    'interval': 30, 
                    'required': 200, 
                    'weight': 0.2,
                    'validation': {'min_candles': 30}
                },
                'htf': {
                    'interval': 240, 
                    'required': 200, 
                    'weight': 0.1,
                    'validation': {'min_candles': 20}
                }
            }
        
        return ConfluenceAnalyzer(config_dict, interpretation_service=interpretation_service)
    
    container.register_factory(IAnalysisService, create_analysis_service, ServiceLifetime.SINGLETON)
    
    # IIndicatorService - Transient (stateless calculations)
    async def create_indicator_service():
        from src.indicators.technical_indicators import TechnicalIndicators
        
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
        
        if 'timeframes' not in config_dict:
            config_dict['timeframes'] = {
                'base': {
                    'interval': 1,
                    'validation': {'min_candles': 100}
                }
            }
        
        return TechnicalIndicators(config_dict)
    
    container.register_factory(IIndicatorService, create_indicator_service, ServiceLifetime.TRANSIENT)


def _register_monitoring_services(container: ServiceContainer, config: Dict[str, Any]) -> None:
    """Register monitoring services via interfaces."""
    logger.info("📡 Registering monitoring services...")
    
    # IAlertService - Singleton (rate limiting, alert history)
    async def create_alert_service():
        from src.monitoring.alert_manager import AlertManager
        
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {
            'monitoring': {
                'alerts': {
                    'discord_webhook_url': 'test_webhook',
                    'rate_limit_window': 300,
                    'max_alerts_per_window': 5
                }
            }
        }
        return AlertManager(config_dict)
    
    container.register_factory(IAlertService, create_alert_service, ServiceLifetime.SINGLETON)
    
    # IMetricsService - Singleton (metric aggregation state)
    async def create_metrics_service():
        from src.monitoring.metrics_manager import MetricsManager
        
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {
            'monitoring': {'metrics': {'collection_interval': 30}}
        }
        
        alert_service = await container.get_service(IAlertService)
        return MetricsManager(config_dict, alert_service)
    
    container.register_factory(IMetricsService, create_metrics_service, ServiceLifetime.SINGLETON)
    
    # ISignalService - Singleton (signal state and history)
    async def create_signal_service():
        from src.signal_generation.signal_generator import SignalGenerator
        
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
        
        alert_service = await container.get_service(IAlertService)
        
        # Ensure required config structure
        if 'analysis' not in config_dict:
            config_dict['analysis'] = {
                'confluence_thresholds': {'buy': 60, 'sell': 40, 'neutral_buffer': 5}
            }
        if 'timeframes' not in config_dict:
            config_dict['timeframes'] = {
                'base': {
                    'interval': 1, 
                    'weight': 0.4,
                    'validation': {'min_candles': 100}
                },
                'ltf': {
                    'interval': 5, 
                    'weight': 0.3,
                    'validation': {'min_candles': 50}
                },
                'mtf': {
                    'interval': 30, 
                    'weight': 0.2,
                    'validation': {'min_candles': 30}
                },
                'htf': {
                    'interval': 240, 
                    'weight': 0.1,
                    'validation': {'min_candles': 20}
                }
            }
        
        return SignalGenerator(config_dict, alert_service)
    
    container.register_factory(ISignalService, create_signal_service, ServiceLifetime.SINGLETON)
    
    # IMonitoringService - Singleton (monitoring state and coordination)
    async def create_monitoring_service():
        # Fast mode: use lightweight mock instead of real market monitor
        if config.get('_fast_mode', False):
            class FastMarketMonitor:
                def __init__(self, *args, **kwargs): pass
                async def start_monitoring(self): pass
                async def stop_monitoring(self): pass
                def get_monitoring_status(self): return {'status': 'running', 'symbols': 5, 'uptime': '1m'}
                def is_healthy(self): return True
                async def analyze_symbols(self, symbols): return {'analyzed': len(symbols)}
            return FastMarketMonitor()
        
        from src.monitoring.monitor import MarketMonitor
        
        # Get configuration
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
        
        # Resolve dependencies through interfaces
        exchange_manager = await container.get_service(IExchangeManagerService)
        alert_service = await container.get_service(IAlertService)
        metrics_service = await container.get_service(IMetricsService)
        signal_service = await container.get_service(ISignalService)
        market_data_service = await container.get_service(IMarketDataService)
        analysis_service = await container.get_service(IAnalysisService)
        
        # Optional dependencies
        database_client = None
        portfolio_analyzer = None
        top_symbols_manager = None
        
        return MarketMonitor(
            config=config_dict,
            logger=logging.getLogger('monitoring'),
            exchange_manager=exchange_manager,
            database_client=database_client,
            portfolio_analyzer=portfolio_analyzer,
            confluence_analyzer=analysis_service,
            alert_manager=alert_service,
            signal_generator=signal_service,
            top_symbols_manager=top_symbols_manager,
            market_data_manager=market_data_service,
            metrics_manager=metrics_service
        )
    
    container.register_factory(IMonitoringService, create_monitoring_service, ServiceLifetime.SINGLETON)
    
    # IHealthService - Singleton (health tracking over time)
    async def create_health_service():
        from src.monitoring.components.health_monitor import HealthMonitor
        
        metrics_service = await container.get_service(IMetricsService)
        return HealthMonitor(metrics_service)
    
    container.register_factory(IHealthService, create_health_service, ServiceLifetime.SINGLETON)


def _register_api_services(container: ServiceContainer, config: Dict[str, Any]) -> None:
    """Register API and web services via interfaces."""
    logger.info("🌐 Registering API services...")
    
    # IReportingService - Scoped (per-request report generation)
    async def create_reporting_service():
        from src.core.reporting.report_manager import ReportManager
        return ReportManager()
    
    container.register_factory(IReportingService, create_reporting_service, ServiceLifetime.SCOPED)


def register_backward_compatibility_services(container: ServiceContainer) -> ServiceContainer:
    """
    Register concrete services for backward compatibility during migration.
    
    This function provides dual registration - services are available both via
    interfaces (new code) and concrete types (existing code). This enables
    gradual migration without breaking existing functionality.
    
    Args:
        container: The DI container to register compatibility services with
        
    Returns:
        The container with backward compatibility services registered
    """
    logger.info("🔄 Registering backward compatibility services...")
    
    # Core Services - Register concrete types that resolve to interface implementations
    _register_concrete_aliases(container)
    
    logger.info("✅ Backward compatibility services registered")
    return container


def _register_concrete_aliases(container: ServiceContainer) -> None:
    """Register concrete type aliases that resolve to interface implementations."""
    
    # ExchangeManager -> IExchangeManagerService
    async def get_exchange_manager():
        return await container.get_service(IExchangeManagerService)
    container.register_factory('ExchangeManager', get_exchange_manager, ServiceLifetime.SINGLETON)
    
    # MarketDataManager -> IMarketDataService
    async def get_market_data_manager():
        return await container.get_service(IMarketDataService)
    container.register_factory('MarketDataManager', get_market_data_manager, ServiceLifetime.SINGLETON)
    
    # MarketMonitor -> IMonitoringService
    async def get_market_monitor():
        return await container.get_service(IMonitoringService)
    container.register_factory('MarketMonitor', get_market_monitor, ServiceLifetime.SINGLETON)
    
    # SignalGenerator -> ISignalService
    async def get_signal_generator():
        return await container.get_service(ISignalService)
    container.register_factory('SignalGenerator', get_signal_generator, ServiceLifetime.SINGLETON)
    
    # AlertManager -> IAlertService
    async def get_alert_manager():
        return await container.get_service(IAlertService)
    container.register_factory('AlertManager', get_alert_manager, ServiceLifetime.SINGLETON)
    
    # MetricsManager -> IMetricsService
    async def get_metrics_manager():
        return await container.get_service(IMetricsService)
    container.register_factory('MetricsManager', get_metrics_manager, ServiceLifetime.SINGLETON)
    
    # ConfluenceAnalyzer -> IAnalysisService
    async def get_confluence_analyzer():
        return await container.get_service(IAnalysisService)
    container.register_factory('ConfluenceAnalyzer', get_confluence_analyzer, ServiceLifetime.SINGLETON)
    
    # WebSocketManager -> IWebSocketService
    async def get_websocket_manager():
        return await container.get_service(IWebSocketService)
    container.register_factory('WebSocketManager', get_websocket_manager, ServiceLifetime.SINGLETON)
    
    # HealthMonitor -> IHealthService
    async def get_health_monitor():
        return await container.get_service(IHealthService)
    container.register_factory('HealthMonitor', get_health_monitor, ServiceLifetime.SINGLETON)
    
    # ReportManager -> IReportingService
    async def get_report_manager():
        return await container.get_service(IReportingService)
    container.register_factory('ReportManager', get_report_manager, ServiceLifetime.SCOPED)



def bootstrap_interface_container(config: Optional[Dict[str, Any]] = None, fast_mode: bool = False) -> ServiceContainer:
    """
    Bootstrap a fully configured DI container with interface-based services.
    
    This is the recommended way to create a DI container with clean, SOLID
    principles-based service registration.
    
    Args:
        config: Optional configuration dictionary
        fast_mode: If True, uses lightweight implementations for validation/testing
        
    Returns:
        Fully configured ServiceContainer with interface-based services
    """
    logger.info("🚀 Bootstrapping interface-based DI container...")
    
    container = ServiceContainer()
    
    # Pass fast_mode to registration functions
    if config is None:
        config = {}
    config['_fast_mode'] = fast_mode
    
    # Register interface-based services (new architecture)
    register_interface_based_services(container, config)
    
    # Register backward compatibility services (migration support)
    register_backward_compatibility_services(container)
    
    # Add health checks for critical interfaces
    _register_health_checks(container)
    
    logger.info("✅ Interface-based DI container bootstrapped successfully")
    logger.info(f"📊 Container stats: {container.get_stats()}")
    
    return container


def _register_health_checks(container: ServiceContainer) -> None:
    """Register health checks for critical services."""
    
    container.register_health_check(
        IExchangeManagerService,
        lambda service: service.get_exchange_status() is not None
    )
    
    container.register_health_check(
        IMarketDataService,
        lambda service: len(service.get_supported_symbols()) > 0
    )
    
    container.register_health_check(
        IMonitoringService,
        lambda service: service.get_monitoring_status().get('status') == 'running'
    )


# Validation Functions

def validate_interface_registration(container: ServiceContainer) -> Dict[str, Any]:
    """
    Validate that all required interfaces are properly registered.
    
    Args:
        container: DI container to validate
        
    Returns:
        Validation results with status and details
    """
    validation_results = {
        'status': 'success',
        'interface_coverage': 0.0,
        'registered_interfaces': [],
        'missing_interfaces': [],
        'registration_errors': []
    }
    
    # Required interfaces for a complete system
    required_interfaces = [
        IConfigService,
        IValidationService,
        IFormattingService,
        IInterpretationService,
        IExchangeManagerService,
        IExchangeService,
        IMarketDataService,
        IWebSocketService,
        IAnalysisService,
        IIndicatorService,
        IAlertService,
        IMetricsService,
        ISignalService,
        IMonitoringService,
        IHealthService,
        IReportingService
    ]
    
    registered_count = 0
    
    for interface in required_interfaces:
        try:
            service_info = container.get_service_info(interface)
            if service_info:
                validation_results['registered_interfaces'].append({
                    'interface': interface.__name__,
                    'implementation': service_info.get('implementation_type', 'Unknown'),
                    'lifetime': service_info.get('lifetime', 'Unknown')
                })
                registered_count += 1
            else:
                validation_results['missing_interfaces'].append(interface.__name__)
        except Exception as e:
            validation_results['registration_errors'].append({
                'interface': interface.__name__,
                'error': str(e)
            })
    
    # Calculate interface coverage
    validation_results['interface_coverage'] = (registered_count / len(required_interfaces)) * 100
    
    # Determine overall status
    if validation_results['missing_interfaces'] or validation_results['registration_errors']:
        validation_results['status'] = 'error'
    elif validation_results['interface_coverage'] < 100:
        validation_results['status'] = 'warning'
    
    return validation_results


# Example Usage and Testing

async def test_interface_registration():
    """Test the interface-based registration system."""
    
    # Create test container
    container = ServiceContainer()
    
    # Test configuration
    test_config = {
        'exchanges': {
            'bybit': {
                'rest_endpoint': 'https://api.bybit.com',
                'testnet': False,
                'primary': True
            }
        },
        'monitoring': {
            'alerts': {'discord_webhook_url': 'test'},
            'metrics': {'collection_interval': 30}
        },
        'timeframes': {
            'base': {'interval': 1, 'weight': 0.4}
        }
    }
    
    # Bootstrap container
    container = bootstrap_interface_container(test_config)
    
    # Validate registration
    validation_results = validate_interface_registration(container)
    
    logger.info("Interface registration test results:")
    logger.info(f"Status: {validation_results['status']}")
    logger.info(f"Interface coverage: {validation_results['interface_coverage']:.1f}%")
    logger.info(f"Registered interfaces: {len(validation_results['registered_interfaces'])}")
    
    if validation_results['missing_interfaces']:
        logger.warning(f"Missing interfaces: {validation_results['missing_interfaces']}")
    
    if validation_results['registration_errors']:
        logger.error(f"Registration errors: {validation_results['registration_errors']}")
    
    # Test key service resolution
    try:
        config_service = await container.get_service(IConfigService)
        exchange_service = await container.get_service(IExchangeService)
        alert_service = await container.get_service(IAlertService)
        
        logger.info("✅ Core services resolved successfully")
        return validation_results['status'] == 'success'
        
    except Exception as e:
        logger.error(f"❌ Service resolution failed: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_interface_registration())
"""
Service registration functions for Virtuoso Dependency Injection.

This module provides pre-configured service registration functions for
different layers of the application, making it easy to bootstrap the
DI container with all required services.
"""

from typing import Optional, Dict, Any
import logging
from ..interfaces.services import (
    IAlertService, IMetricsService, IInterpretationService, 
    IFormattingService, IValidationService, IConfigService, IExchangeService,
    IMarketMonitorService, IDashboardService, ITopSymbolsManagerService, 
    IConfluenceAnalyzerService, ICacheService, IAnalysisEngineService
)
from .container import ServiceContainer, ServiceLifetime

logger = logging.getLogger(__name__)


def register_core_services(container: ServiceContainer, config: Optional[Dict[str, Any]] = None) -> ServiceContainer:
    """
    Register core infrastructure services.
    
    Args:
        container: The DI container to register services with
        config: Optional configuration dictionary
        
    Returns:
        The container with core services registered
    """
    logger.info("Registering core services...")
    
    # Configuration Service (singleton)
    from ...utils.config import ConfigManager
    if config:
        config_instance = ConfigManager(config)
        container.register_instance(IConfigService, config_instance)
    else:
        container.register_singleton(IConfigService, ConfigManager)
    
    # Error Handler (singleton)
    from ..error.handlers import SimpleErrorHandler
    container.register_singleton(SimpleErrorHandler, SimpleErrorHandler)
    
    # Validation Service (singleton) - use a simpler implementation to avoid circular imports
    try:
        from ...validation.core.validator import CoreValidator
        container.register_singleton(IValidationService, CoreValidator)
    except ImportError as e:
        logger.warning(f"Could not import CoreValidator: {e}, using fallback")
        # Create a simple fallback validator
        class FallbackValidator:
            def validate(self, data, rules=None):
                return {'valid': True, 'errors': []}
        container.register_instance(IValidationService, FallbackValidator())
    
    # Formatting Service (transient)
    from ...utils.formatters import DataFormatter
    container.register_transient(IFormattingService, DataFormatter)
    
    logger.info("Core services registered successfully")
    return container


def register_analysis_services(container: ServiceContainer) -> ServiceContainer:
    """
    Register analysis and data processing services.
    
    Args:
        container: The DI container to register services with
        
    Returns:
        The container with analysis services registered
    """
    logger.info("Registering analysis services...")
    
    # Interpretation Service (scoped)
    from ...core.analysis.interpretation_generator import InterpretationGenerator
    container.register_scoped(IInterpretationService, InterpretationGenerator)
    
    # Market Data Manager (singleton) - needs config and exchange manager
    from ...core.market.market_data_manager import MarketDataManager
    from ...core.exchanges.manager import ExchangeManager
    
    async def create_market_data_manager():
        try:
            config_service = await container.get_service(IConfigService)
            config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
            
            # Try to get exchange manager
            try:
                exchange_manager = await container.get_service(ExchangeManager)
            except:
                exchange_manager = None
                
            return MarketDataManager(config_dict, exchange_manager, None)
        except Exception as e:
            logger.warning(f"Could not create market data manager: {e}")
            raise
    
    container.register_factory(MarketDataManager, create_market_data_manager, ServiceLifetime.SINGLETON)
    
    # Alpha Scanner (scoped) - needs exchange manager and config
    from ...core.analysis.alpha_scanner import AlphaScannerEngine
    
    async def create_alpha_scanner():
        try:
            exchange_manager = await container.get_service(ExchangeManager)
            config_service = await container.get_service(IConfigService)
            config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else None
            return AlphaScannerEngine(exchange_manager, config_dict)
        except Exception as e:
            logger.warning(f"Could not create alpha scanner: {e}")
            raise
    
    container.register_factory(AlphaScannerEngine, create_alpha_scanner, ServiceLifetime.SCOPED)
    
    # Confluence Analyzer (scoped) - needs config
    from ...core.analysis.confluence import ConfluenceAnalyzer
    
    async def create_confluence_analyzer():
        try:
            config_service = await container.get_service(IConfigService)
            config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
            
            # Get interpretation service
            interpretation_service = None
            try:
                interpretation_service = await container.get_service(IInterpretationService)
            except Exception as e:
                logger.debug(f"InterpretationService not available for ConfluenceAnalyzer: {e}")
            
            # Ensure required config structure exists
            if 'timeframes' not in config_dict:
                config_dict['timeframes'] = {
                    'base': {
                        'interval': 1,
                        'required': 1000,
                        'validation': {
                            'max_gap': 60,
                            'min_candles': 100
                        },
                        'weight': 0.4
                    },
                    'htf': {
                        'interval': 240,
                        'required': 200,
                        'validation': {
                            'max_gap': 14400,
                            'min_candles': 50
                        },
                        'weight': 0.1
                    },
                    'ltf': {
                        'interval': 5,
                        'required': 200,
                        'validation': {
                            'max_gap': 300,
                            'min_candles': 50
                        },
                        'weight': 0.3
                    },
                    'mtf': {
                        'interval': 30,
                        'required': 200,
                        'validation': {
                            'max_gap': 1800,
                            'min_candles': 50
                        },
                        'weight': 0.2
                    }
                }
            
            return ConfluenceAnalyzer(config_dict, interpretation_service=interpretation_service)
        except Exception as e:
            logger.warning(f"Could not create confluence analyzer: {e}")
            # Return with minimal config as fallback
            return ConfluenceAnalyzer({
                'timeframes': {
                    'base': {'interval': 1},
                    'ltf': {'interval': 5},
                    'mtf': {'interval': 30},
                    'htf': {'interval': 240}
                }
            })
    
    container.register_factory(ConfluenceAnalyzer, create_confluence_analyzer, ServiceLifetime.SCOPED)
    
    # Register with interface for proper DI resolution
    container.register_factory(IConfluenceAnalyzerService, create_confluence_analyzer, ServiceLifetime.SCOPED)
    
    # Liquidation Detector (scoped) - needs exchange manager
    from ...core.analysis.liquidation_detector import LiquidationDetectionEngine
    
    async def create_liquidation_detector():
        try:
            exchange_manager = await container.get_service(ExchangeManager)
            # Database URL is optional
            database_url = None
            return LiquidationDetectionEngine(exchange_manager, database_url)
        except Exception as e:
            logger.warning(f"Could not create liquidation detector: {e}")
            raise
    
    container.register_factory(LiquidationDetectionEngine, create_liquidation_detector, ServiceLifetime.SCOPED)
    
    # Data Validator (singleton)
    from ...validation.validators.data_validator import DataValidator
    container.register_singleton(DataValidator, DataValidator)
    
    logger.info("Analysis services registered successfully")
    return container


def register_monitoring_services(container: ServiceContainer) -> ServiceContainer:
    """
    Register monitoring and alerting services.
    
    Args:
        container: The DI container to register services with
        
    Returns:
        The container with monitoring services registered
    """
    logger.info("Registering monitoring services...")
    
    # Alert Service (singleton) - use factory to inject config
    from ...monitoring.alert_manager import AlertManager
    logger.info("Using AlertManager for DI registration")
    from .container import ServiceLifetime
    
    async def create_alert_manager():
        # Get config from the container
        try:
            config_service = await container.get_service(IConfigService)
            if hasattr(config_service, 'to_dict'):
                config_dict = config_service.to_dict()
            else:
                config_dict = {
                    'monitoring': {
                        'alerts': {
                            'discord_webhook_url': 'test_webhook',
                            'rate_limit_window': 300,
                            'max_alerts_per_window': 5
                        }
                    }
                }
        except Exception as e:
            logger.warning(f"Could not get config service: {e}")
            config_dict = {
                'monitoring': {
                    'alerts': {
                        'discord_webhook_url': 'test_webhook'
                    }
                }
            }
        return AlertManager(config_dict)
    
    container.register_factory(IAlertService, create_alert_manager, ServiceLifetime.SINGLETON)
    
    # Also register AlertManager with concrete types for backward compatibility
    container.register_factory(AlertManager, create_alert_manager, ServiceLifetime.SINGLETON)
    
    # Metrics Service (singleton) - use factory to inject config and alert manager
    from ...monitoring.metrics_manager import MetricsManager
    
    async def create_metrics_manager():
        # Get alert service that was just registered
        alert_service = await container.get_service(IAlertService)
        
        # Get config from the container
        try:
            config_service = await container.get_service(IConfigService)
            if hasattr(config_service, 'to_dict'):
                config_dict = config_service.to_dict()
            else:
                config_dict = {
                    'monitoring': {
                        'metrics': {
                            'collection_interval': 30
                        }
                    }
                }
        except Exception as e:
            logger.warning(f"Could not get config service: {e}")
            config_dict = {
                'monitoring': {
                    'metrics': {
                        'collection_interval': 30
                    }
                }
            }
        
        return MetricsManager(config_dict, alert_service)
    
    container.register_factory(IMetricsService, create_metrics_manager, ServiceLifetime.SINGLETON)
    
    # Also register MetricsManager as concrete type for backward compatibility
    container.register_factory(MetricsManager, create_metrics_manager, ServiceLifetime.SINGLETON)
    
    # Signal Generator (singleton) - needs config and alert manager
    from ...signal_generation.signal_generator import SignalGenerator
    
    async def create_signal_generator():
        try:
            # Get alert service that was just registered
            alert_service = await container.get_service(IAlertService)
            
            # Get config from the container
            config_service = await container.get_service(IConfigService)
            if hasattr(config_service, 'to_dict'):
                config_dict = config_service.to_dict()
            else:
                config_dict = {}
            
            # Ensure required config structure exists for SignalGenerator
            if 'analysis' not in config_dict:
                config_dict['analysis'] = {}
            if 'confluence_thresholds' not in config_dict['analysis']:
                config_dict['analysis']['confluence_thresholds'] = {
                    'buy': 60,
                    'sell': 40,
                    'neutral_buffer': 5
                }
            
            # Ensure timeframes config exists (required by SignalGenerator)
            if 'timeframes' not in config_dict:
                config_dict['timeframes'] = {
                    'base': {
                        'interval': 1,
                        'required': 1000,
                        'validation': {
                            'max_gap': 60,
                            'min_candles': 100
                        },
                        'weight': 0.4
                    },
                    'ltf': {
                        'interval': 5,
                        'required': 200,
                        'validation': {
                            'max_gap': 300,
                            'min_candles': 50
                        },
                        'weight': 0.3
                    },
                    'mtf': {
                        'interval': 30,
                        'required': 200,
                        'validation': {
                            'max_gap': 1800,
                            'min_candles': 50
                        },
                        'weight': 0.2
                    },
                    'htf': {
                        'interval': 240,
                        'required': 200,
                        'validation': {
                            'max_gap': 14400,
                            'min_candles': 50
                        },
                        'weight': 0.1
                    }
                }
                
            return SignalGenerator(config_dict, alert_service)
        except Exception as e:
            logger.warning(f"Could not create SignalGenerator: {e}")
            # Return with minimal config including required timeframes and validation
            return SignalGenerator({
                'analysis': {
                    'confluence_thresholds': {
                        'buy': 60,
                        'sell': 40,
                        'neutral_buffer': 5
                    }
                },
                'timeframes': {
                    'base': {
                        'interval': 1,
                        'required': 1000,
                        'validation': {
                            'max_gap': 60,
                            'min_candles': 100
                        },
                        'weight': 0.4
                    },
                    'ltf': {
                        'interval': 5,
                        'required': 200,
                        'validation': {
                            'max_gap': 300,
                            'min_candles': 50
                        },
                        'weight': 0.3
                    },
                    'mtf': {
                        'interval': 30,
                        'required': 200,
                        'validation': {
                            'max_gap': 1800,
                            'min_candles': 50
                        },
                        'weight': 0.2
                    },
                    'htf': {
                        'interval': 240,
                        'required': 200,
                        'validation': {
                            'max_gap': 14400,
                            'min_candles': 50
                        },
                        'weight': 0.1
                    }
                }
            }, None)
    
    container.register_factory(SignalGenerator, create_signal_generator, ServiceLifetime.SINGLETON)
    
    # Market Reporter (scoped) - needs exchange and other dependencies
    from ...monitoring.market_reporter import MarketReporter
    from ...core.exchanges.manager import ExchangeManager
    from ...core.market.top_symbols import TopSymbolsManager
    
    async def create_market_reporter():
        # Try to get optional dependencies
        exchange = None
        top_symbols_manager = None
        alert_manager = None
        
        try:
            exchange_manager = await container.get_service(ExchangeManager)
            if exchange_manager:
                exchange = await exchange_manager.get_primary_exchange()
                if exchange:
                    logger.info(f"MarketReporter using exchange: {type(exchange).__name__}")
                    # Verify the exchange has required methods
                    required_methods = ['fetch_ticker', 'fetch_order_book', 'fetch_trades']
                    missing_methods = [m for m in required_methods if not hasattr(exchange, m)]
                    if missing_methods:
                        logger.warning(f"Exchange missing methods: {missing_methods}")
                else:
                    logger.warning("ExchangeManager returned None for primary exchange")
        except Exception as e:
            logger.warning(f"Exchange not available for MarketReporter: {e}")
            
        try:
            top_symbols_manager = await container.get_service(TopSymbolsManager)
        except Exception as e:
            logger.warning(f"TopSymbolsManager not available for MarketReporter: {e}")
            
        try:
            alert_manager = await container.get_service(IAlertService)
        except Exception as e:
            logger.warning(f"AlertManager not available for MarketReporter: {e}")
        
        return MarketReporter(
            exchange=exchange,
            logger=logging.getLogger('src.monitoring.market_reporter'),
            top_symbols_manager=top_symbols_manager,
            alert_manager=alert_manager
        )
    
    container.register_factory(MarketReporter, create_market_reporter, ServiceLifetime.SCOPED)
    
    # MarketMonitor (singleton) - needs many optional dependencies
    try:
        # Try to import refactored MarketMonitor first for better performance
        from ...monitoring.monitor import MarketMonitor
        logger.info("Using MarketMonitor for DI registration")
        
        from ...core.exchanges.manager import ExchangeManager
        from ...core.market.market_data_manager import MarketDataManager
        from ...core.market.top_symbols import TopSymbolsManager
        
        async def create_market_monitor():
            """
            Create MarketMonitor using proper constructor dependency injection.
            All dependencies are resolved through the DI container.
            """
            # Get configuration
            config_dict = {}
            try:
                config_service = await container.get_service(IConfigService)
                config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
            except Exception as e:
                logger.warning(f"Config service not available: {e}")
            
            # Resolve all dependencies through DI container for proper injection
            exchange_manager = None
            database_client = None
            portfolio_analyzer = None
            confluence_analyzer = None
            alert_manager = None
            signal_generator = None
            top_symbols_manager = None
            market_data_manager = None
            metrics_manager = None
            liquidation_detector = None
            
            # Try to resolve each dependency - these should be registered as instances
            try:
                exchange_manager = await container.get_service(ExchangeManager)
            except Exception as e:
                logger.debug(f"ExchangeManager not available: {e}")
                
            try:
                from ...core.database.database_client import DatabaseClient
                database_client = await container.get_service(DatabaseClient)
            except Exception as e:
                logger.debug(f"DatabaseClient not available: {e}")
                
            try:
                from ...core.analysis.portfolio_analyzer import PortfolioAnalyzer
                portfolio_analyzer = await container.get_service(PortfolioAnalyzer)
            except Exception as e:
                logger.debug(f"PortfolioAnalyzer not available: {e}")
                
            try:
                confluence_analyzer = await container.get_service(ConfluenceAnalyzer)
            except Exception as e:
                logger.debug(f"ConfluenceAnalyzer not available: {e}")
                
            try:
                alert_manager = await container.get_service(IAlertService)
            except Exception as e:
                logger.debug(f"AlertManager not available: {e}")
                
            try:
                signal_generator = await container.get_service(SignalGenerator)
            except Exception as e:
                logger.debug(f"SignalGenerator not available: {e}")
                
            try:
                top_symbols_manager = await container.get_service(TopSymbolsManager)
            except Exception as e:
                logger.debug(f"TopSymbolsManager not available: {e}")
                
            try:
                market_data_manager = await container.get_service(MarketDataManager)
            except Exception as e:
                logger.debug(f"MarketDataManager not available: {e}")
                
            try:
                metrics_manager = await container.get_service(IMetricsService)
            except Exception as e:
                logger.debug(f"MetricsManager not available: {e}")
                
            try:
                from ...core.analysis.liquidation_detector import LiquidationDetectionEngine
                liquidation_detector = await container.get_service(LiquidationDetectionEngine)
            except Exception as e:
                logger.debug(f"LiquidationDetectionEngine not available: {e}")
            
            # Create monitor with proper constructor injection
            monitor = MarketMonitor(
                config=config_dict,
                logger=logging.getLogger('src.monitoring.monitor'),
                exchange_manager=exchange_manager,
                database_client=database_client,
                portfolio_analyzer=portfolio_analyzer,
                confluence_analyzer=confluence_analyzer,
                alert_manager=alert_manager,
                signal_generator=signal_generator,
                top_symbols_manager=top_symbols_manager,
                market_data_manager=market_data_manager,
                metrics_manager=metrics_manager
            )
            
            # Set liquidation detector if available (not in constructor params)
            if liquidation_detector:
                monitor.liquidation_detector = liquidation_detector
            
            logger.info("MarketMonitor created with proper dependency injection")
            return monitor
            
        container.register_factory(MarketMonitor, create_market_monitor, ServiceLifetime.SINGLETON)
        
        # Register with interface for proper DI resolution
        container.register_factory(IMarketMonitorService, create_market_monitor, ServiceLifetime.SINGLETON)
        
        
        # Register the original MarketMonitor import path for compatibility
        try:
            from ...monitoring.monitor import MarketMonitor as OriginalMarketMonitor
            container.register_factory(OriginalMarketMonitor, create_market_monitor, ServiceLifetime.SINGLETON)
        except ImportError:
            pass
    except ImportError:
        logger.warning("MarketMonitor class not found, skipping registration")
    
    # Health Monitor (singleton) - needs MetricsManager
    from ...monitoring.components.health_monitor import HealthMonitor
    
    async def create_health_monitor():
        try:
            metrics_manager = await container.get_service(IMetricsService)
            # alert_callback and config are optional
            return HealthMonitor(metrics_manager)
        except Exception as e:
            logger.warning(f"Could not create HealthMonitor: {e}")
            # Create without metrics manager (will have limited functionality)
            return HealthMonitor(None)
    
    container.register_factory(HealthMonitor, create_health_monitor, ServiceLifetime.SINGLETON)
    
    # Signal Frequency Tracker (singleton) - Class doesn't exist, skipped
    # SignalFrequencyTracker is referenced in tests but not implemented
    # TODO: Implement SignalFrequencyTracker if needed for production
    logger.info("SignalFrequencyTracker registration skipped - class not implemented")
    
    logger.info("Monitoring services registered successfully")
    return container


def register_exchange_services(container: ServiceContainer) -> ServiceContainer:
    """
    Register exchange and trading services.
    
    Args:
        container: The DI container to register services with
        
    Returns:
        The container with exchange services registered
    """
    logger.info("Registering exchange services...")
    
    # Exchange Manager (singleton) - needs ConfigManager
    from ...core.exchanges.manager import ExchangeManager
    from ...config.manager import ConfigManager
    
    async def create_exchange_manager():
        try:
            # Get config service and extract ConfigManager
            config_service = await container.get_service(IConfigService)
            if isinstance(config_service, ConfigManager):
                manager = ExchangeManager(config_service)
            else:
                # If it's not a ConfigManager, create a new one
                manager = ExchangeManager(ConfigManager())
            
            # Initialize the exchange manager to load exchanges
            await manager.initialize()
            return manager
        except Exception as e:
            logger.warning(f"Could not get config service or initialize exchange manager: {e}")
            # Fallback to creating a new ConfigManager
            manager = ExchangeManager(ConfigManager())
            await manager.initialize()
            return manager
    
    container.register_factory(ExchangeManager, create_exchange_manager, ServiceLifetime.SINGLETON)
    
    # Bybit Exchange (singleton) - needs config and error handler
    from ...core.exchanges.bybit import BybitExchange
    
    async def create_bybit_exchange():
        try:
            config_service = await container.get_service(IConfigService)
            config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
            
            # Ensure exchanges config exists
            if 'exchanges' not in config_dict:
                config_dict['exchanges'] = {
                    'bybit': {
                        'rest_endpoint': 'https://api.bybit.com',
                        'websocket_endpoint': 'wss://stream.bybit.com',
                        'testnet': False,
                        'primary': True
                    }
                }
            elif 'bybit' not in config_dict['exchanges']:
                config_dict['exchanges']['bybit'] = {
                    'rest_endpoint': 'https://api.bybit.com',
                    'websocket_endpoint': 'wss://stream.bybit.com',
                    'testnet': False,
                    'primary': True
                }
            
            return BybitExchange(config_dict)
        except Exception as e:
            logger.warning(f"Could not create BybitExchange: {e}")
            # Return with minimal config
            return BybitExchange({
                'exchanges': {
                    'bybit': {
                        'rest_endpoint': 'https://api.bybit.com',
                        'testnet': False,
                        'primary': True
                    }
                }
            })
    
    container.register_factory(IExchangeService, create_bybit_exchange, ServiceLifetime.SINGLETON)
    
    # WebSocket Manager (singleton) - needs config
    from ...core.exchanges.websocket_manager import WebSocketManager
    
    async def create_websocket_manager():
        try:
            config_service = await container.get_service(IConfigService)
            config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
            return WebSocketManager(config_dict)
        except Exception as e:
            logger.warning(f"Could not create WebSocketManager: {e}")
            return WebSocketManager({})
    
    container.register_factory(WebSocketManager, create_websocket_manager, ServiceLifetime.SINGLETON)
    
    # Liquidation Collector (singleton) - needs ExchangeManager
    from ...core.exchanges.liquidation_collector import LiquidationDataCollector
    
    async def create_liquidation_collector():
        try:
            exchange_manager = await container.get_service(ExchangeManager)
            # storage_callback is optional
            return LiquidationDataCollector(exchange_manager)
        except Exception as e:
            logger.warning(f"Could not create LiquidationDataCollector: {e}")
            # Create a placeholder - will have limited functionality without exchange manager
            return LiquidationDataCollector(None)
    
    container.register_factory(LiquidationDataCollector, create_liquidation_collector, ServiceLifetime.SINGLETON)
    
    # TopSymbolsManager (singleton) - needs dependencies
    from ...core.market.top_symbols import TopSymbolsManager
    from ...validation import AsyncValidationService
    
    async def create_top_symbols_manager():
        try:
            # Get required dependencies
            exchange_manager = await container.get_service(ExchangeManager)
            config_service = await container.get_service(IConfigService)
            config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
            
            # Ensure required config fields exist
            if 'timeframes' not in config_dict:
                # Provide default timeframes configuration matching config.yaml
                config_dict['timeframes'] = {
                    'base': {
                        'interval': 1,
                        'required': 1000,
                        'validation': {
                            'max_gap': 60,
                            'min_candles': 100
                        },
                        'weight': 0.4
                    },
                    'htf': {
                        'interval': 240,
                        'required': 200,
                        'validation': {
                            'max_gap': 14400,
                            'min_candles': 50
                        },
                        'weight': 0.1
                    },
                    'ltf': {
                        'interval': 5,
                        'required': 200,
                        'validation': {
                            'max_gap': 300,
                            'min_candles': 50
                        },
                        'weight': 0.3
                    },
                    'mtf': {
                        'interval': 30,
                        'required': 200,
                        'validation': {
                            'max_gap': 1800,
                            'min_candles': 50
                        },
                        'weight': 0.2
                    }
                }
            
            # Ensure data_processing config exists
            if 'data_processing' not in config_dict:
                config_dict['data_processing'] = {
                    'pipeline': [
                        {'name': 'validation', 'enabled': True, 'timeout': 5},
                        {'name': 'normalization', 'enabled': True, 'timeout': 5},
                        {'name': 'feature_engineering', 'enabled': True, 'timeout': 10},
                        {'name': 'aggregation', 'enabled': True, 'timeout': 10}
                    ]
                }
            
            # Create validation service
            validation_service = AsyncValidationService()
            
            return TopSymbolsManager(
                exchange_manager=exchange_manager,
                config=config_dict,
                validation_service=validation_service
            )
        except Exception as e:
            logger.error(f"Failed to create TopSymbolsManager: {e}")
            raise
    
    container.register_factory(TopSymbolsManager, create_top_symbols_manager, ServiceLifetime.SINGLETON)
    
    # Register with interface for proper DI resolution
    container.register_factory(ITopSymbolsManagerService, create_top_symbols_manager, ServiceLifetime.SINGLETON)
    
    logger.info("Exchange services registered successfully")
    return container


def register_indicator_services(container: ServiceContainer) -> ServiceContainer:
    """
    Register indicator and calculation services.
    
    Args:
        container: The DI container to register services with
        
    Returns:
        The container with indicator services registered
    """
    logger.info("Registering indicator services...")
    
    # Create indicator factory function
    async def create_indicator(indicator_class):
        """Factory function for creating indicators with config."""
        try:
            config_service = await container.get_service(IConfigService)
            config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
            
            # Ensure timeframes config exists for indicators
            if 'timeframes' not in config_dict:
                config_dict['timeframes'] = {
                    'base': {'interval': 1, 'weight': 0.4},
                    'ltf': {'interval': 5, 'weight': 0.3},
                    'mtf': {'interval': 30, 'weight': 0.2},
                    'htf': {'interval': 240, 'weight': 0.1}
                }
            
            return indicator_class(config_dict)
        except Exception as e:
            logger.warning(f"Could not create {indicator_class.__name__}: {e}")
            # Return with minimal config
            return indicator_class({'timeframes': {'base': {'interval': 1}}})
    
    # Technical Indicators (transient)
    from ...indicators.technical_indicators import TechnicalIndicators
    container.register_factory(
        TechnicalIndicators, 
        lambda: create_indicator(TechnicalIndicators), 
        ServiceLifetime.TRANSIENT
    )
    
    # Volume Indicators (transient)
    from ...indicators.volume_indicators import VolumeIndicators
    container.register_factory(
        VolumeIndicators, 
        lambda: create_indicator(VolumeIndicators), 
        ServiceLifetime.TRANSIENT
    )
    
    # Price Structure Indicators (transient)
    from ...indicators.price_structure_indicators import PriceStructureIndicators
    container.register_factory(
        PriceStructureIndicators, 
        lambda: create_indicator(PriceStructureIndicators), 
        ServiceLifetime.TRANSIENT
    )
    
    # Orderbook Indicators (transient)
    from ...indicators.orderbook_indicators import OrderbookIndicators
    container.register_factory(
        OrderbookIndicators, 
        lambda: create_indicator(OrderbookIndicators), 
        ServiceLifetime.TRANSIENT
    )
    
    # Orderflow Indicators (transient)
    from ...indicators.orderflow_indicators import OrderflowIndicators
    container.register_factory(
        OrderflowIndicators, 
        lambda: create_indicator(OrderflowIndicators), 
        ServiceLifetime.TRANSIENT
    )
    
    # Sentiment Indicators (transient)
    from ...indicators.sentiment_indicators import SentimentIndicators
    container.register_factory(
        SentimentIndicators, 
        lambda: create_indicator(SentimentIndicators), 
        ServiceLifetime.TRANSIENT
    )
    
    logger.info("Indicator services registered successfully")
    return container


def register_api_services(container: ServiceContainer) -> ServiceContainer:
    """
    Register API and web services.
    
    Args:
        container: The DI container to register services with
        
    Returns:
        The container with API services registered
    """
    logger.info("Registering API services...")
    
    # Dashboard Integration Service (singleton) - use factory to avoid dependency analysis issues
    try:
        from ...dashboard.dashboard_integration import DashboardIntegrationService
        
        async def create_dashboard_integration_service():
            try:
                # Try to get MarketMonitor via interface first, then fallback to concrete type
                market_monitor = None
                try:
                    market_monitor = await container.get_service(IMarketMonitorService)
                except Exception:
                    try:
                        market_monitor = await container.get_service(MarketMonitor)
                    except Exception as e:
                        logger.warning(f"MarketMonitor not available for DashboardIntegrationService: {e}")
                
                return DashboardIntegrationService(monitor=market_monitor)
            except Exception as e:
                logger.warning(f"Could not create DashboardIntegrationService: {e}")
                # Return service with no monitor (fallback mode)
                return DashboardIntegrationService(monitor=None)
        
        container.register_factory(DashboardIntegrationService, create_dashboard_integration_service, ServiceLifetime.SINGLETON)
        
        # Register with interface for proper DI resolution
        container.register_factory(IDashboardService, create_dashboard_integration_service, ServiceLifetime.SINGLETON)
    except ImportError:
        logger.warning("DashboardIntegrationService class not found, skipping registration")
    
    # Report Manager (scoped)
    from ...core.reporting.report_manager import ReportManager
    container.register_scoped(ReportManager, ReportManager)
    
    # PDF Generator (transient)
    from ...core.reporting.pdf_generator import ReportGenerator as PDFGenerator
    container.register_transient(PDFGenerator, PDFGenerator)
    
    logger.info("API services registered successfully")
    return container


def bootstrap_container(config: Optional[Dict[str, Any]] = None, enable_events: bool = True) -> ServiceContainer:
    """
    Bootstrap a fully configured dependency injection container.
    
    This function registers all services in the correct order and
    returns a ready-to-use container.
    
    Args:
        config: Optional configuration dictionary
        enable_events: Whether to enable event-driven architecture (default: True)
        
    Returns:
        Fully configured ServiceContainer
    """
    logger.info("Bootstrapping DI container...")
    
    container = ServiceContainer()
    
    # Register services in dependency order
    register_core_services(container, config)
    register_exchange_services(container)
    register_indicator_services(container)
    register_analysis_services(container)
    register_monitoring_services(container)
    register_api_services(container)
    
    # Register event-driven services if enabled
    if enable_events:
        try:
            from .event_services_registration import register_event_services
            register_event_services(container)
            logger.info("Event-driven architecture services registered")
        except ImportError as e:
            logger.warning(f"Event-driven services not available: {e}")
        except Exception as e:
            logger.error(f"Failed to register event-driven services: {e}")
    
    # Add health checks for critical services  
    try:
        from ...core.exchanges.manager import ExchangeManager
        container.register_health_check(
            ExchangeManager, 
            lambda: True  # Basic health check - can be enhanced
        )
    except ImportError:
        logger.warning("ExchangeManager not available for health check")
    
    try:
        from ...core.market.market_data_manager import MarketDataManager
        container.register_health_check(
            MarketDataManager,
            lambda: True  # Basic health check - can be enhanced
        )
    except ImportError:
        logger.warning("MarketDataManager not available for health check")
    
    logger.info("DI container bootstrapped successfully")
    logger.info(f"Container stats: {container.get_stats()}")
    
    return container


# Convenience function for common registration patterns
def register_with_factory(container: ServiceContainer, service_type, factory_func, lifetime=None):
    """
    Register a service with a custom factory function.
    
    Args:
        container: The DI container
        service_type: The service interface/type
        factory_func: Factory function to create the service
        lifetime: Service lifetime (defaults to transient)
    """
    from .container import ServiceLifetime
    lifetime = lifetime or ServiceLifetime.TRANSIENT
    return container.register_factory(service_type, factory_func, lifetime)


def register_conditional(container: ServiceContainer, service_type, implementation_type, condition_func, lifetime=None):
    """
    Register a service conditionally based on a predicate.
    
    Args:
        container: The DI container
        service_type: The service interface/type
        implementation_type: The implementation type
        condition_func: Function that returns True if service should be registered
        lifetime: Service lifetime (defaults to transient)
    """
    if condition_func():
        from .container import ServiceLifetime
        lifetime = lifetime or ServiceLifetime.TRANSIENT
        
        if lifetime == ServiceLifetime.SINGLETON:
            container.register_singleton(service_type, implementation_type)
        elif lifetime == ServiceLifetime.SCOPED:
            container.register_scoped(service_type, implementation_type)
        else:
            container.register_transient(service_type, implementation_type)
    
    return container
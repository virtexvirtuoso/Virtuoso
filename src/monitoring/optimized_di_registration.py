"""
Optimized DI Registration for Refactored Monitor Components.

This module provides clean, minimal dependency registration following SOLID principles
and proper lifetime management for the monitoring system components.

Key Optimizations:
- Interface-based registration instead of concrete classes
- Minimal dependencies per component (2-4 vs 6-13 before)
- Proper lifetime management (singleton, transient, scoped)
- Clean separation of concerns
"""

import logging
from typing import Dict, Any, Optional

from ..core.di.container import ServiceContainer, ServiceLifetime
from .interfaces import (
    IDataFetcher, IDataValidator, ISignalAnalyzer,
    ITradeParameterCalculator, IMetricsCollector, IHealthChecker
)
from .slim_monitor_orchestrator import SlimMonitorOrchestrator

logger = logging.getLogger(__name__)


def register_optimized_monitoring_services(
    container: ServiceContainer, 
    config: Optional[Dict[str, Any]] = None
) -> ServiceContainer:
    """
    Register optimized monitoring services with minimal dependencies.
    
    This registration follows the optimized architecture:
    - Each component has single responsibility
    - Interface-based registration for loose coupling
    - Proper lifetime management
    - Minimal dependency chains
    
    Args:
        container: DI container to register services with
        config: Optional configuration
        
    Returns:
        Container with optimized services registered
    """
    logger.info("Registering optimized monitoring services...")
    
    config = config or {}
    
    # 1. Register Data Layer Services (2-3 dependencies each)
    _register_data_services(container, config)
    
    # 2. Register Signal Processing Services (2-3 dependencies each) 
    _register_signal_services(container, config)
    
    # 3. Register System Services (1-2 dependencies each)
    _register_system_services(container, config)
    
    # 4. Register Orchestrator (6 interface dependencies)
    _register_orchestrator(container, config)
    
    logger.info("✅ Optimized monitoring services registered")
    return container


def _register_data_services(container: ServiceContainer, config: Dict[str, Any]) -> None:
    """Register data fetching and validation services."""
    
    # IDataFetcher - Singleton (stateful, expensive to create)
    async def create_data_fetcher():
        from ..core.exchanges.manager import ExchangeManager
        from .components.optimized_data_fetcher import OptimizedDataFetcher
        
        try:
            exchange_manager = await container.get_service(ExchangeManager)
            return OptimizedDataFetcher(
                exchange_manager=exchange_manager,
                config=config.get('data_fetching', {}),
                logger=logging.getLogger('data_fetcher')
            )
        except Exception as e:
            logger.warning(f"Could not create OptimizedDataFetcher: {e}")
            # Fallback implementation
            from .components.fallback_data_fetcher import FallbackDataFetcher
            return FallbackDataFetcher(config.get('data_fetching', {}))
    
    container.register_factory(IDataFetcher, create_data_fetcher, ServiceLifetime.SINGLETON)
    
    # IDataValidator - Transient (stateless, lightweight)
    async def create_data_validator():
        from .components.optimized_data_validator import OptimizedDataValidator
        
        return OptimizedDataValidator(
            validation_rules=config.get('validation', {}),
            logger=logging.getLogger('data_validator')
        )
    
    container.register_factory(IDataValidator, create_data_validator, ServiceLifetime.TRANSIENT)


def _register_signal_services(container: ServiceContainer, config: Dict[str, Any]) -> None:
    """Register signal analysis and trade parameter services."""
    
    # ISignalAnalyzer - Singleton (stateful, complex initialization)
    async def create_signal_analyzer():
        from .components.optimized_signal_analyzer import OptimizedSignalAnalyzer
        from ..analysis.core.confluence import ConfluenceAnalyzer
        
        try:
            # Minimal dependency: only ConfluenceAnalyzer
            confluence_analyzer = await container.get_service(ConfluenceAnalyzer)
            
            return OptimizedSignalAnalyzer(
                confluence_analyzer=confluence_analyzer,
                config=config.get('signal_analysis', {}),
                logger=logging.getLogger('signal_analyzer')
            )
        except Exception as e:
            logger.warning(f"Could not create OptimizedSignalAnalyzer: {e}")
            # Fallback with basic analysis
            from .components.basic_signal_analyzer import BasicSignalAnalyzer
            return BasicSignalAnalyzer(config.get('signal_analysis', {}))
    
    container.register_factory(ISignalAnalyzer, create_signal_analyzer, ServiceLifetime.SINGLETON)
    
    # ITradeParameterCalculator - Transient (stateless, pure calculations)
    async def create_trade_calculator():
        from .components.optimized_trade_calculator import OptimizedTradeCalculator
        
        return OptimizedTradeCalculator(
            risk_config=config.get('risk_management', {}),
            logger=logging.getLogger('trade_calculator')
        )
    
    container.register_factory(ITradeParameterCalculator, create_trade_calculator, ServiceLifetime.TRANSIENT)


def _register_system_services(container: ServiceContainer, config: Dict[str, Any]) -> None:
    """Register system monitoring services."""
    
    # IMetricsCollector - Singleton (stateful, aggregates metrics)
    async def create_metrics_collector():
        from .components.optimized_metrics_collector import OptimizedMetricsCollector
        
        # Minimal dependency: just configuration
        return OptimizedMetricsCollector(
            config=config.get('metrics', {}),
            logger=logging.getLogger('metrics_collector')
        )
    
    container.register_factory(IMetricsCollector, create_metrics_collector, ServiceLifetime.SINGLETON)
    
    # IHealthChecker - Singleton (stateful, tracks health over time)
    async def create_health_checker():
        from .components.optimized_health_checker import OptimizedHealthChecker
        
        return OptimizedHealthChecker(
            config=config.get('health_monitoring', {}),
            logger=logging.getLogger('health_checker')
        )
    
    container.register_factory(IHealthChecker, create_health_checker, ServiceLifetime.SINGLETON)


def _register_orchestrator(container: ServiceContainer, config: Dict[str, Any]) -> None:
    """Register the slim monitor orchestrator."""
    
    async def create_slim_orchestrator():
        """
        Create orchestrator with all interface dependencies injected.
        
        This is the key optimization: 6 interface dependencies instead of 13+ concrete classes.
        """
        # Resolve all interface dependencies
        data_fetcher = await container.get_service(IDataFetcher)
        data_validator = await container.get_service(IDataValidator)
        signal_analyzer = await container.get_service(ISignalAnalyzer)
        trade_calculator = await container.get_service(ITradeParameterCalculator)
        metrics_collector = await container.get_service(IMetricsCollector)
        health_checker = await container.get_service(IHealthChecker)
        
        return SlimMonitorOrchestrator(
            data_fetcher=data_fetcher,
            data_validator=data_validator,
            signal_analyzer=signal_analyzer,
            trade_calculator=trade_calculator,
            metrics_collector=metrics_collector,
            health_checker=health_checker,
            logger=logging.getLogger('slim_orchestrator')
        )
    
    container.register_factory(SlimMonitorOrchestrator, create_slim_orchestrator, ServiceLifetime.SINGLETON)
    
    # Also register with generic interface for backward compatibility
    container.register_factory('IMonitorOrchestrator', create_slim_orchestrator, ServiceLifetime.SINGLETON)


# Utility function for validating optimized registration

def validate_optimized_registration(container: ServiceContainer) -> Dict[str, Any]:
    """
    Validate that optimized monitoring services are properly registered.
    
    Args:
        container: DI container to validate
        
    Returns:
        Validation results
    """
    validation_results = {
        'status': 'success',
        'registered_interfaces': [],
        'missing_interfaces': [],
        'registration_errors': []
    }
    
    # Check required interfaces
    required_interfaces = [
        IDataFetcher,
        IDataValidator,
        ISignalAnalyzer,
        ITradeParameterCalculator,
        IMetricsCollector,
        IHealthChecker,
        SlimMonitorOrchestrator
    ]
    
    for interface in required_interfaces:
        try:
            service_info = container.get_service_info(interface)
            if service_info:
                validation_results['registered_interfaces'].append({
                    'interface': interface.__name__,
                    'implementation': service_info['implementation_type'],
                    'lifetime': service_info['lifetime']
                })
            else:
                validation_results['missing_interfaces'].append(interface.__name__)
        except Exception as e:
            validation_results['registration_errors'].append({
                'interface': interface.__name__,
                'error': str(e)
            })
    
    # Determine overall status
    if validation_results['missing_interfaces'] or validation_results['registration_errors']:
        validation_results['status'] = 'error'
    
    return validation_results


# Example usage and testing

async def test_optimized_registration():
    """
    Test the optimized registration to ensure it works correctly.
    
    This function can be called during development or testing to validate
    that the optimized DI registration is working properly.
    """
    from ..core.di.container import ServiceContainer
    
    # Create test container
    container = ServiceContainer()
    
    # Register optimized services
    test_config = {
        'data_fetching': {'timeout': 30},
        'validation': {'strict_mode': True},
        'signal_analysis': {'confluence_threshold': 60},
        'risk_management': {'default_risk_percent': 0.02},
        'metrics': {'enabled': True},
        'health_monitoring': {'check_interval': 60}
    }
    
    register_optimized_monitoring_services(container, test_config)
    
    # Validate registration
    validation_results = validate_optimized_registration(container)
    
    logger.info("Optimized registration test results:")
    logger.info(f"Status: {validation_results['status']}")
    logger.info(f"Registered interfaces: {len(validation_results['registered_interfaces'])}")
    
    if validation_results['missing_interfaces']:
        logger.warning(f"Missing interfaces: {validation_results['missing_interfaces']}")
    
    if validation_results['registration_errors']:
        logger.error(f"Registration errors: {validation_results['registration_errors']}")
    
    # Test orchestrator creation
    try:
        orchestrator = await container.get_service(SlimMonitorOrchestrator)
        dependency_validation = orchestrator.validate_dependencies()
        
        logger.info("Orchestrator dependency validation:")
        for dep, valid in dependency_validation.items():
            status = "✅" if valid else "❌"
            logger.info(f"  {status} {dep}")
        
        all_valid = all(dependency_validation.values())
        logger.info(f"All dependencies valid: {'✅' if all_valid else '❌'}")
        
        return all_valid
        
    except Exception as e:
        logger.error(f"Error creating orchestrator: {e}")
        return False
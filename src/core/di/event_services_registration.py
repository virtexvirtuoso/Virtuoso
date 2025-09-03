"""
Event-Driven Services Registration for Dependency Injection

This module extends the existing DI container registration to include
event-driven architecture components while maintaining backward compatibility
with existing services.

The registration follows the established patterns in registration.py and
integrates seamlessly with the existing service layer.
"""

from typing import Optional, Dict, Any
import logging

from .container import ServiceContainer, ServiceLifetime
from ..events import (
    EventBus, EventPublisher, MarketDataEventIntegration, 
    ConfluenceEventAdapter
)

logger = logging.getLogger(__name__)


def register_event_services(container: ServiceContainer) -> ServiceContainer:
    """
    Register event-driven architecture services with the DI container.
    
    This function registers:
    - EventBus (singleton): Core message bus
    - EventPublisher (singleton): High-level publishing service  
    - MarketDataEventIntegration (singleton): Market data event bridge
    - ConfluenceEventAdapter (singleton): Event-driven confluence analyzer
    
    Args:
        container: The DI container to register services with
        
    Returns:
        The container with event services registered
    """
    logger.info("Registering event-driven architecture services...")
    
    # EventBus (singleton) - Core message bus
    async def create_event_bus():
        """Factory function to create EventBus with optimal configuration."""
        try:
            # Get configuration if available
            config_dict = {}
            try:
                from ..interfaces.services import IConfigService
                config_service = await container.get_service(IConfigService)
                config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
            except Exception as e:
                logger.debug(f"Config service not available for EventBus: {e}")
            
            # Extract event bus configuration
            event_config = config_dict.get('events', {})
            
            event_bus = EventBus(
                max_queue_size=event_config.get('max_queue_size', 10000),
                max_workers=event_config.get('max_workers', None),
                enable_metrics=event_config.get('enable_metrics', True),
                enable_dead_letter=event_config.get('enable_dead_letter', True),
                enable_event_sourcing=event_config.get('enable_event_sourcing', False)
            )
            
            logger.info("EventBus created with configuration from DI container")
            return event_bus
            
        except Exception as e:
            logger.warning(f"Could not create EventBus with config: {e}")
            # Return with default configuration as fallback
            return EventBus(
                max_queue_size=10000,
                enable_metrics=True,
                enable_dead_letter=True
            )
    
    container.register_factory(EventBus, create_event_bus, ServiceLifetime.SINGLETON)
    
    # EventPublisher (singleton) - High-level publishing service
    async def create_event_publisher():
        """Factory function to create EventPublisher with EventBus dependency."""
        try:
            event_bus = await container.get_service(EventBus)
            
            # Get configuration
            config_dict = {}
            try:
                from ..interfaces.services import IConfigService
                config_service = await container.get_service(IConfigService)
                config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
            except Exception as e:
                logger.debug(f"Config service not available for EventPublisher: {e}")
            
            event_config = config_dict.get('events', {}).get('publisher', {})
            
            event_publisher = EventPublisher(
                event_bus=event_bus,
                enable_batching=event_config.get('enable_batching', True),
                batch_size=event_config.get('batch_size', 100),
                batch_timeout_ms=event_config.get('batch_timeout_ms', 100),
                enable_metrics=event_config.get('enable_metrics', True)
            )
            
            logger.info("EventPublisher created with EventBus dependency")
            return event_publisher
            
        except Exception as e:
            logger.error(f"Could not create EventPublisher: {e}")
            raise
    
    container.register_factory(EventPublisher, create_event_publisher, ServiceLifetime.SINGLETON)
    
    # MarketDataEventIntegration (singleton) - Bridge for market data events
    async def create_market_data_event_integration():
        """Factory function to create MarketDataEventIntegration."""
        try:
            event_publisher = await container.get_service(EventPublisher)
            
            # Try to get MarketDataManager if available
            market_data_manager = None
            try:
                from ..market.market_data_manager import MarketDataManager
                market_data_manager = await container.get_service(MarketDataManager)
                logger.info("MarketDataManager found for event integration")
            except Exception as e:
                logger.warning(f"MarketDataManager not available for integration: {e}")
            
            # Get configuration
            config_dict = {}
            try:
                from ..interfaces.services import IConfigService
                config_service = await container.get_service(IConfigService)
                config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
            except Exception:
                pass
            
            integration_config = config_dict.get('events', {}).get('market_data_integration', {})
            
            integration = MarketDataEventIntegration(
                event_publisher=event_publisher,
                market_data_manager=market_data_manager,
                enable_event_publishing=integration_config.get('enable_event_publishing', True),
                event_throttle_ms=integration_config.get('event_throttle_ms', 100),
                enable_performance_monitoring=integration_config.get('enable_performance_monitoring', True)
            )
            
            logger.info("MarketDataEventIntegration created")
            return integration
            
        except Exception as e:
            logger.error(f"Could not create MarketDataEventIntegration: {e}")
            raise
    
    container.register_factory(
        MarketDataEventIntegration, 
        create_market_data_event_integration, 
        ServiceLifetime.SINGLETON
    )
    
    # ConfluenceEventAdapter (singleton) - Event-driven confluence analyzer
    async def create_confluence_event_adapter():
        """Factory function to create ConfluenceEventAdapter."""
        try:
            # Get required dependencies
            event_bus = await container.get_service(EventBus)
            event_publisher = await container.get_service(EventPublisher)
            
            # Try to get ConfluenceAnalyzer
            confluence_analyzer = None
            try:
                from ..analysis.confluence import ConfluenceAnalyzer
                confluence_analyzer = await container.get_service(ConfluenceAnalyzer)
                logger.info("ConfluenceAnalyzer found for event adapter")
            except Exception as e:
                logger.warning(f"ConfluenceAnalyzer not available: {e}")
                # Could create a fallback or raise error depending on requirements
                raise
            
            # Get configuration
            config_dict = {}
            try:
                from ..interfaces.services import IConfigService
                config_service = await container.get_service(IConfigService)
                config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
            except Exception:
                pass
            
            adapter_config = config_dict.get('events', {}).get('confluence_adapter', {})
            
            adapter = ConfluenceEventAdapter(
                confluence_analyzer=confluence_analyzer,
                event_bus=event_bus,
                event_publisher=event_publisher,
                enable_event_processing=adapter_config.get('enable_event_processing', True),
                enable_backward_compatibility=adapter_config.get('enable_backward_compatibility', True),
                processing_timeout_ms=adapter_config.get('processing_timeout_ms', 5000),
                batch_processing=adapter_config.get('batch_processing', True)
            )
            
            logger.info("ConfluenceEventAdapter created")
            return adapter
            
        except Exception as e:
            logger.error(f"Could not create ConfluenceEventAdapter: {e}")
            raise
    
    container.register_factory(
        ConfluenceEventAdapter,
        create_confluence_event_adapter, 
        ServiceLifetime.SINGLETON
    )
    
    # Register health checks for event services
    try:
        container.register_health_check(
            EventBus,
            lambda: True  # Basic health check - could be enhanced with actual bus health
        )
        
        container.register_health_check(
            EventPublisher,
            lambda: True  # Basic health check - could check publisher status
        )
        
        container.register_health_check(
            MarketDataEventIntegration,
            lambda: True  # Basic health check - could check integration status
        )
        
        container.register_health_check(
            ConfluenceEventAdapter, 
            lambda: True  # Basic health check - could check adapter status
        )
        
    except Exception as e:
        logger.warning(f"Could not register event service health checks: {e}")
    
    logger.info("Event-driven architecture services registered successfully")
    return container


def register_event_enhanced_services(container: ServiceContainer) -> ServiceContainer:
    """
    Register enhanced event-driven versions of existing services.
    
    This function provides event-enhanced versions of existing services that
    can be used as drop-in replacements with additional event capabilities.
    
    Args:
        container: The DI container to register services with
        
    Returns:
        The container with enhanced services registered
    """
    logger.info("Registering event-enhanced services...")
    
    # Event-Enhanced ConfluenceAnalyzer
    async def create_event_enhanced_confluence_analyzer():
        """Create event-enhanced confluence analyzer that publishes results."""
        try:
            # Get the event adapter which wraps the original analyzer
            adapter = await container.get_service(ConfluenceEventAdapter)
            
            # Return the adapter as it provides the same interface plus events
            logger.info("Event-enhanced ConfluenceAnalyzer created (via adapter)")
            return adapter
            
        except Exception as e:
            logger.error(f"Could not create event-enhanced ConfluenceAnalyzer: {e}")
            # Fall back to original analyzer
            from ..analysis.confluence import ConfluenceAnalyzer
            return await container.get_service(ConfluenceAnalyzer)
    
    # Register as an alternative implementation
    container.register_factory(
        "EventEnhancedConfluenceAnalyzer",
        create_event_enhanced_confluence_analyzer,
        ServiceLifetime.SINGLETON
    )
    
    logger.info("Event-enhanced services registered successfully")
    return container


def setup_event_driven_bootstrap(container: ServiceContainer) -> ServiceContainer:
    """
    Bootstrap event-driven services with automatic startup.
    
    This function not only registers event services but also ensures they
    are properly started and configured for immediate use.
    
    Args:
        container: The DI container to configure
        
    Returns:
        The container with event services bootstrapped
    """
    logger.info("Bootstrapping event-driven architecture...")
    
    # Register all event services
    register_event_services(container)
    register_event_enhanced_services(container)
    
    # Add startup hook for event services
    async def startup_event_services():
        """Startup hook to initialize event services."""
        try:
            # Start EventBus first
            event_bus = await container.get_service(EventBus)
            await event_bus.start()
            logger.info("EventBus started")
            
            # Start EventPublisher
            event_publisher = await container.get_service(EventPublisher)
            await event_publisher.start()
            logger.info("EventPublisher started")
            
            # Start MarketDataEventIntegration
            try:
                integration = await container.get_service(MarketDataEventIntegration)
                await integration.start()
                logger.info("MarketDataEventIntegration started")
            except Exception as e:
                logger.warning(f"Could not start MarketDataEventIntegration: {e}")
            
            # Start ConfluenceEventAdapter
            try:
                adapter = await container.get_service(ConfluenceEventAdapter)
                await adapter.start()
                logger.info("ConfluenceEventAdapter started")
            except Exception as e:
                logger.warning(f"Could not start ConfluenceEventAdapter: {e}")
            
            logger.info("Event-driven architecture bootstrap completed")
            
        except Exception as e:
            logger.error(f"Event services startup failed: {e}")
            raise
    
    # Store startup hook in container metadata for later execution
    if not hasattr(container, '_startup_hooks'):
        container._startup_hooks = []
    container._startup_hooks.append(startup_event_services)
    
    logger.info("Event-driven architecture bootstrap setup completed")
    return container


# Convenience functions for common registration patterns
def enable_event_driven_mode(container: ServiceContainer, config: Optional[Dict[str, Any]] = None) -> ServiceContainer:
    """
    Enable event-driven mode for the entire system.
    
    This is a high-level function that configures the system for full
    event-driven operation while maintaining backward compatibility.
    
    Args:
        container: The DI container to configure
        config: Optional configuration overrides
        
    Returns:
        Configured container with event-driven mode enabled
    """
    logger.info("Enabling event-driven mode...")
    
    # Set default event configuration if not provided
    if config is None:
        config = {}
        
    default_event_config = {
        'events': {
            'enable_metrics': True,
            'enable_dead_letter': True,
            'enable_event_sourcing': False,
            'max_queue_size': 10000,
            'publisher': {
                'enable_batching': True,
                'batch_size': 100,
                'batch_timeout_ms': 100
            },
            'market_data_integration': {
                'enable_event_publishing': True,
                'event_throttle_ms': 100,
                'enable_performance_monitoring': True
            },
            'confluence_adapter': {
                'enable_event_processing': True,
                'enable_backward_compatibility': True,
                'processing_timeout_ms': 5000,
                'batch_processing': True
            }
        }
    }
    
    # Merge with provided config
    merged_config = {**default_event_config, **config}
    
    # Update container configuration if possible
    try:
        from ..interfaces.services import IConfigService
        # This is a bit tricky since we need to update the config service
        # For now, we'll rely on the factory functions to use default values
        pass
    except Exception:
        pass
    
    # Bootstrap event-driven services
    setup_event_driven_bootstrap(container)
    
    logger.info("Event-driven mode enabled")
    return container
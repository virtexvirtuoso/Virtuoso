"""Adapter for integrating trading components with the existing Container system."""

import logging
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TradingComponentAdapter:
    """Adapter to integrate trading components with existing Container system."""
    
    def __init__(self, container, config_manager):
        """Initialize the adapter with container and config manager."""
        self.container = container
        self.config_manager = config_manager
        self.logger = logger
        self._components = {}
        self._initialized = {}
        
    async def register_and_initialize_trading_components(self) -> None:
        """Register and initialize all trading components in dependency order."""
        try:
            self.logger.info("Starting trading components registration and initialization")
            
            # Import trading components with error handling
            try:
                from src.core.exchanges.manager import ExchangeManager
                from src.data_storage.database import DatabaseClient
                from src.analysis.core.portfolio import PortfolioAnalyzer
                from src.analysis.core.confluence import ConfluenceAnalyzer
                from src.validation import AsyncValidationService
                from src.core.market.top_symbols import TopSymbolsManager
                from src.core.market.market_data_manager import MarketDataManager
                from src.monitoring.metrics_manager import MetricsManager
                from src.monitoring.alert_manager import AlertManager
                from src.monitoring.market_reporter import MarketReporter
                from src.monitoring.monitor import MarketMonitor
            except ImportError as import_error:
                self.logger.error(f"Failed to import trading components: {import_error}")
                raise RuntimeError(f"Trading components not available: {import_error}")
            
            # Phase 1: Core infrastructure components
            await self._initialize_component('config_manager', self.config_manager)
            
            # Phase 2: Exchange and database
            exchange_manager = ExchangeManager(self.config_manager)
            await self._initialize_component('exchange_manager', exchange_manager)
            
            database_client = DatabaseClient(self.config_manager.config)
            await self._initialize_component('database_client', database_client)
            
            # Phase 3: Analysis services
            portfolio_analyzer = PortfolioAnalyzer(self.config_manager.config)
            await self._initialize_component('portfolio_analyzer', portfolio_analyzer)
            
            confluence_analyzer = ConfluenceAnalyzer(self.config_manager.config)
            await self._initialize_component('confluence_analyzer', confluence_analyzer)
            
            validation_service = AsyncValidationService()
            await self._initialize_component('validation_service', validation_service)
            
            # Phase 4: Market services
            top_symbols_manager = TopSymbolsManager(
                exchange_manager=exchange_manager,
                config=self.config_manager.config,
                validation_service=validation_service
            )
            await self._initialize_component('top_symbols_manager', top_symbols_manager)
            
            # Initialize alert manager first for market_data_manager dependency
            alert_manager = AlertManager(self.config_manager.config)
            alert_manager.register_discord_handler()
            await self._initialize_component('alert_manager', alert_manager)
            
            market_data_manager = MarketDataManager(
                self.config_manager.config,
                exchange_manager,
                alert_manager
            )
            await self._initialize_component('market_data_manager', market_data_manager)
            
            # Phase 5: Monitoring services
            metrics_manager = MetricsManager(self.config_manager.config, alert_manager)
            await self._initialize_component('metrics_manager', metrics_manager)
            
            # Get primary exchange for dependent components
            primary_exchange = await exchange_manager.get_primary_exchange()
            if not primary_exchange:
                raise RuntimeError("No primary exchange available for trading components")
            
            market_reporter = MarketReporter(
                top_symbols_manager=top_symbols_manager,
                alert_manager=alert_manager,
                exchange=primary_exchange,
                logger=self.logger
            )
            await self._initialize_component('market_reporter', market_reporter)
            
            market_monitor = MarketMonitor(
                logger=self.logger,
                metrics_manager=metrics_manager,
                exchange=primary_exchange,
                top_symbols_manager=top_symbols_manager,
                alert_manager=alert_manager,
                config=self.config_manager.config,
                market_reporter=market_reporter
            )
            
            # Inject additional dependencies into monitor (from original pattern)
            market_monitor.exchange_manager = exchange_manager
            market_monitor.database_client = database_client
            market_monitor.portfolio_analyzer = portfolio_analyzer
            market_monitor.confluence_analyzer = confluence_analyzer
            
            await self._initialize_component('market_monitor', market_monitor)
            
            component_count = len(self._components)
            self.logger.info(f"✅ Successfully initialized {component_count} trading components")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize trading components: {str(e)}")
            # Cleanup any partially initialized components
            await self.cleanup_trading_components()
            raise
    
    async def _initialize_component(self, name: str, component: Any) -> None:
        """Initialize a single component with proper error handling."""
        try:
            self.logger.debug(f"Initializing component: {name}")
            
            # Check if component has async initialization
            if hasattr(component, 'initialize') and asyncio.iscoroutinefunction(component.initialize):
                await component.initialize()
            elif hasattr(component, 'initialize'):
                component.initialize()
            
            # Store the component
            self._components[name] = component
            self._initialized[name] = True
            
            self.logger.debug(f"✅ Component initialized: {name}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize component {name}: {str(e)}")
            self._initialized[name] = False
            raise
    
    async def cleanup_trading_components(self) -> None:
        """Cleanup all trading components in reverse dependency order."""
        try:
            self.logger.info("Starting trading components cleanup")
            
            # Cleanup in reverse order
            cleanup_order = [
                'market_monitor',
                'market_reporter', 
                'metrics_manager',
                'market_data_manager',
                'alert_manager',
                'top_symbols_manager',
                'validation_service',
                'confluence_analyzer',
                'portfolio_analyzer',
                'database_client',
                'exchange_manager',
                'config_manager'
            ]
            
            for component_name in cleanup_order:
                if component_name in self._components:
                    component = self._components[component_name]
                    try:
                        self.logger.debug(f"Cleaning up component: {component_name}")
                        
                        # Check if component has cleanup method
                        if hasattr(component, 'cleanup'):
                            if asyncio.iscoroutinefunction(component.cleanup):
                                await asyncio.wait_for(component.cleanup(), timeout=10.0)
                            else:
                                component.cleanup()
                        
                        # Remove from tracking
                        del self._components[component_name]
                        self._initialized[component_name] = False
                        
                        self.logger.debug(f"✅ Component cleaned up: {component_name}")
                        
                    except asyncio.TimeoutError:
                        self.logger.warning(f"⚠️ Component {component_name} cleanup timed out")
                    except Exception as e:
                        self.logger.error(f"❌ Error cleaning up component {component_name}: {str(e)}")
            
            remaining_count = len(self._components)
            if remaining_count == 0:
                self.logger.info("✅ All trading components cleaned up successfully")
            else:
                self.logger.warning(f"⚠️ {remaining_count} components not cleaned up properly")
                
        except Exception as e:
            self.logger.error(f"❌ Error during trading components cleanup: {str(e)}")
            raise
    
    def get_component(self, name: str) -> Optional[Any]:
        """Get a trading component by name."""
        return self._components.get(name)
    
    def get_all_components(self) -> Dict[str, Any]:
        """Get all trading components."""
        return self._components.copy()
    
    def is_component_initialized(self, name: str) -> bool:
        """Check if a component is initialized."""
        return self._initialized.get(name, False)
    
    def get_initialization_status(self) -> Dict[str, bool]:
        """Get initialization status of all components."""
        return self._initialized.copy()
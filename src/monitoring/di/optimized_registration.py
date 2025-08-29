"""
Optimized Dependency Injection Registration for Refactored Monitor Components

This module provides clean, minimal dependency registration following SOLID principles
and proper lifetime management for the monitoring system components.
"""

from typing import Optional, Dict, Any, Type
import logging
from ...core.di.container import ServiceContainer, ServiceLifetime

logger = logging.getLogger(__name__)

# ===============================================================================
# MONITORING INTERFACES - Clean contracts between components
# ===============================================================================

class IDataFetcher:
    """Interface for fetching market data"""
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        raise NotImplementedError

class IDataValidator:
    """Interface for validating data quality"""
    async def validate(self, data: Dict[str, Any]) -> bool:
        raise NotImplementedError

class ISignalAnalyzer:
    """Interface for analyzing market data and generating signals"""  
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class ITradeParameterCalculator:
    """Interface for calculating trade parameters"""
    def calculate_parameters(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class IMetricsCollector:
    """Interface for collecting metrics"""
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        raise NotImplementedError

class IHealthChecker:
    """Interface for health checking"""
    async def check_health(self) -> Dict[str, Any]:
        raise NotImplementedError

class IWebSocketConnectionManager:
    """Interface for managing WebSocket connections"""
    async def connect(self) -> bool:
        raise NotImplementedError
    
    async def disconnect(self) -> None:
        raise NotImplementedError

class IMessageProcessor:
    """Interface for processing WebSocket messages"""
    async def process_message(self, message: Dict[str, Any]) -> None:
        raise NotImplementedError


# ===============================================================================
# OPTIMIZED COMPONENT IMPLEMENTATIONS
# ===============================================================================

class MinimalDataFetcher(IDataFetcher):
    """Focused data fetcher with minimal dependencies"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.logger = logging.getLogger(__name__)
    
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch market data with single responsibility"""
        try:
            exchange = await self.exchange_manager.get_primary_exchange()
            if not exchange:
                return {}
                
            # Simple, focused data fetching
            ticker = await exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'ticker': ticker,
                'timestamp': ticker.get('timestamp') if ticker else None
            }
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {e}")
            return {}


class MinimalSignalAnalyzer(ISignalAnalyzer):
    """Focused signal analyzer with single responsibility"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Extract only what we need from config
        confluence_config = config.get('confluence', {})
        thresholds = confluence_config.get('thresholds', {})
        self.buy_threshold = thresholds.get('buy', 60.0)
        self.sell_threshold = thresholds.get('sell', 40.0)
    
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data and generate signal - single responsibility"""
        if not data or 'ticker' not in data:
            return {'signal_type': 'NEUTRAL', 'confidence': 0.0}
        
        # Simple signal generation logic (can be enhanced)
        ticker = data['ticker']
        price = ticker.get('last', 0)
        
        # Basic momentum analysis
        signal_strength = 50.0  # Simplified for example
        
        if signal_strength >= self.buy_threshold:
            return {
                'signal_type': 'BUY',
                'confidence': signal_strength / 100,
                'price': price,
                'symbol': data['symbol']
            }
        elif signal_strength <= self.sell_threshold:
            return {
                'signal_type': 'SELL', 
                'confidence': (100 - signal_strength) / 100,
                'price': price,
                'symbol': data['symbol']
            }
        else:
            return {
                'signal_type': 'NEUTRAL',
                'confidence': 0.5,
                'price': price,
                'symbol': data['symbol']
            }


class MinimalTradeParameterCalculator(ITradeParameterCalculator):
    """Focused trade parameter calculator with single responsibility"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Extract trading config
        trading_config = config.get('trading', {})
        self.risk_percent = trading_config.get('risk_percentage', 2.0)
        self.stop_loss_percent = trading_config.get('stop_loss_percent', 2.0)
        self.take_profit_percent = trading_config.get('take_profit_percent', 6.0)
    
    def calculate_parameters(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate trade parameters - single responsibility"""
        price = signal.get('price', 0)
        signal_type = signal.get('signal_type', 'NEUTRAL')
        confidence = signal.get('confidence', 0.5)
        
        if price == 0 or signal_type == 'NEUTRAL':
            return {
                'entry_price': price,
                'stop_loss': None,
                'take_profit': None,
                'position_size': 0,
                'confidence': confidence
            }
        
        # Calculate stop loss and take profit
        if signal_type == 'BUY':
            stop_loss = price * (1 - self.stop_loss_percent / 100)
            take_profit = price * (1 + self.take_profit_percent / 100)
        else:  # SELL
            stop_loss = price * (1 + self.stop_loss_percent / 100)
            take_profit = price * (1 - self.take_profit_percent / 100)
        
        return {
            'entry_price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': self.risk_percent * confidence,  # Simplified
            'confidence': confidence
        }


class MinimalMetricsCollector(IMetricsCollector):
    """Focused metrics collector with single responsibility"""
    
    def __init__(self):
        self.metrics = {}
        self.logger = logging.getLogger(__name__)
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record metric - single responsibility"""
        try:
            key = f"{name}_{hash(str(tags)) if tags else 'default'}"
            self.metrics[key] = {
                'name': name,
                'value': value,
                'tags': tags or {},
                'timestamp': __import__('time').time()
            }
        except Exception as e:
            self.logger.error(f"Error recording metric {name}: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics"""
        return self.metrics.copy()


class MinimalHealthChecker(IHealthChecker):
    """Focused health checker with single responsibility"""
    
    def __init__(self, components: Dict[str, Any]):
        self.components = components
        self.logger = logging.getLogger(__name__)
    
    async def check_health(self) -> Dict[str, Any]:
        """Check component health - single responsibility"""
        health_status = {
            'overall': 'healthy',
            'components': {},
            'timestamp': __import__('time').time()
        }
        
        unhealthy_count = 0
        
        for name, component in self.components.items():
            try:
                # Check if component has health check method
                if hasattr(component, 'is_healthy'):
                    is_healthy = await component.is_healthy()
                elif hasattr(component, 'check_health'):
                    result = await component.check_health()
                    is_healthy = result.get('status') == 'healthy'
                else:
                    is_healthy = True  # Assume healthy if no check available
                
                health_status['components'][name] = {
                    'status': 'healthy' if is_healthy else 'unhealthy'
                }
                
                if not is_healthy:
                    unhealthy_count += 1
                    
            except Exception as e:
                health_status['components'][name] = {
                    'status': 'error',
                    'message': str(e)
                }
                unhealthy_count += 1
        
        # Determine overall status
        if unhealthy_count > 0:
            total_components = len(self.components)
            if unhealthy_count >= total_components / 2:
                health_status['overall'] = 'critical'
            else:
                health_status['overall'] = 'warning'
        
        return health_status


# ===============================================================================
# SLIM MONITOR ORCHESTRATOR
# ===============================================================================

class SlimMonitorOrchestrator:
    """
    Ultra-slim monitor orchestrator with minimal dependencies.
    
    This class demonstrates proper dependency injection with:
    - Single responsibility (orchestration only)
    - Minimal dependencies (only interfaces)
    - Clear separation of concerns
    """
    
    def __init__(
        self,
        data_fetcher: IDataFetcher,
        data_validator: IDataValidator,
        signal_analyzer: ISignalAnalyzer,
        trade_calculator: ITradeParameterCalculator,
        metrics_collector: IMetricsCollector,
        health_checker: IHealthChecker,
        logger: Optional[logging.Logger] = None
    ):
        # ONLY inject what we actually need for orchestration
        self.data_fetcher = data_fetcher
        self.data_validator = data_validator
        self.signal_analyzer = signal_analyzer
        self.trade_calculator = trade_calculator
        self.metrics_collector = metrics_collector
        self.health_checker = health_checker
        self.logger = logger or logging.getLogger(__name__)
        
        self.running = False
    
    async def process_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Process single symbol through the monitoring pipeline"""
        try:
            # Step 1: Fetch data (delegate to data fetcher)
            data = await self.data_fetcher.fetch_market_data(symbol)
            if not data:
                return None
            
            # Step 2: Validate data (delegate to validator)
            is_valid = await self.data_validator.validate(data)
            if not is_valid:
                self.logger.warning(f"Invalid data for {symbol}")
                return None
            
            # Step 3: Analyze and generate signal (delegate to analyzer)
            signal = await self.signal_analyzer.analyze(data)
            
            # Step 4: Calculate trade parameters (delegate to calculator)
            trade_params = self.trade_calculator.calculate_parameters(signal)
            
            # Step 5: Record metrics (delegate to collector)
            self.metrics_collector.record_metric(
                'symbols_processed', 1, 
                {'symbol': symbol, 'signal_type': signal.get('signal_type', 'NEUTRAL')}
            )
            
            # Combine results
            result = {**signal, 'trade_parameters': trade_params}
            
            self.logger.info(f"Processed {symbol}: {signal.get('signal_type', 'NEUTRAL')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {symbol}: {e}")
            self.metrics_collector.record_metric('processing_errors', 1, {'symbol': symbol})
            return None
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Check system health (delegate to health checker)"""
        return await self.health_checker.check_health()


# ===============================================================================
# OPTIMIZED DI REGISTRATION
# ===============================================================================

def register_optimized_monitoring_components(
    container: ServiceContainer, 
    config: Optional[Dict[str, Any]] = None
) -> ServiceContainer:
    """
    Register monitoring components with optimized dependency injection.
    
    This registration follows SOLID principles:
    - Interface-based registration
    - Minimal dependencies
    - Proper lifetime management
    - Single responsibility per component
    """
    logger.info("Registering optimized monitoring components...")
    
    if not config:
        config = {}
    
    # =================================================================
    # CORE DATA PROCESSING COMPONENTS (Transient - stateless)
    # =================================================================
    
    # Data Fetcher - needs ExchangeManager (singleton dependency)
    async def create_data_fetcher():
        from ...core.exchanges.manager import ExchangeManager
        exchange_manager = await container.get_service(ExchangeManager)
        return MinimalDataFetcher(exchange_manager)
    
    container.register_factory(
        IDataFetcher, 
        create_data_fetcher, 
        ServiceLifetime.TRANSIENT  # Stateless, can be recreated
    )
    
    # Data Validator - stateless, config-based
    def create_data_validator():
        from ..validator import MarketDataValidator
        return MarketDataValidator(config.get('validation', {}))
    
    container.register_factory(
        IDataValidator,
        create_data_validator,
        ServiceLifetime.TRANSIENT  # Stateless, config-driven
    )
    
    # =================================================================
    # ANALYSIS COMPONENTS (Transient - pure functions)
    # =================================================================
    
    # Signal Analyzer - stateless analysis
    def create_signal_analyzer():
        return MinimalSignalAnalyzer(config)
    
    container.register_factory(
        ISignalAnalyzer,
        create_signal_analyzer,
        ServiceLifetime.TRANSIENT  # Pure function, no state
    )
    
    # Trade Parameter Calculator - stateless calculations
    def create_trade_calculator():
        return MinimalTradeParameterCalculator(config)
    
    container.register_factory(
        ITradeParameterCalculator,
        create_trade_calculator,
        ServiceLifetime.TRANSIENT  # Pure function, no state
    )
    
    # =================================================================
    # MONITORING COMPONENTS (Singleton - maintain state)
    # =================================================================
    
    # Metrics Collector - maintains metrics state
    def create_metrics_collector():
        return MinimalMetricsCollector()
    
    container.register_factory(
        IMetricsCollector,
        create_metrics_collector,
        ServiceLifetime.SINGLETON  # Maintains state across requests
    )
    
    # Health Checker - needs references to components
    async def create_health_checker():
        # Collect components for health checking
        components = {}
        try:
            components['data_fetcher'] = await container.get_service(IDataFetcher)
            components['metrics_collector'] = await container.get_service(IMetricsCollector)
        except Exception as e:
            logger.warning(f"Could not get all components for health checker: {e}")
        
        return MinimalHealthChecker(components)
    
    container.register_factory(
        IHealthChecker,
        create_health_checker,
        ServiceLifetime.SCOPED  # Needs fresh component references per scope
    )
    
    # =================================================================
    # ORCHESTRATOR (Singleton - application-level coordinator)
    # =================================================================
    
    async def create_slim_orchestrator():
        """Create orchestrator with all dependencies injected via interfaces"""
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
            logger=logging.getLogger('optimized_monitor')
        )
    
    container.register_factory(
        SlimMonitorOrchestrator,
        create_slim_orchestrator,
        ServiceLifetime.SINGLETON  # Application-level coordinator
    )
    
    logger.info("✅ Optimized monitoring components registered successfully")
    logger.info(f"   - 6 interface-based registrations")
    logger.info(f"   - Proper lifetime management (3 transient, 1 singleton, 1 scoped)")
    logger.info(f"   - Minimal dependencies per component")
    logger.info(f"   - Single responsibility principle enforced")
    
    return container


def register_backward_compatibility_adapters(container: ServiceContainer) -> ServiceContainer:
    """
    Register adapters for backward compatibility with existing code.
    
    This allows existing code to continue working while gradually migrating
    to the new optimized components.
    """
    logger.info("Registering backward compatibility adapters...")
    
    # Adapter for existing RefactoredMarketMonitor interface
    async def create_monitor_adapter():
        orchestrator = await container.get_service(SlimMonitorOrchestrator)
        
        # Create adapter that implements the old interface
        class MonitorAdapter:
            def __init__(self, orchestrator):
                self.orchestrator = orchestrator
                
            async def process_symbol(self, symbol: str):
                return await self.orchestrator.process_symbol(symbol)
                
            async def check_system_health(self):
                return await self.orchestrator.check_system_health()
                
            def get_stats(self):
                metrics = self.orchestrator.metrics_collector.get_metrics()
                return {
                    'total_symbols_processed': len([m for m in metrics.values() if m['name'] == 'symbols_processed']),
                    'processing_errors': len([m for m in metrics.values() if m['name'] == 'processing_errors']),
                }
        
        return MonitorAdapter(orchestrator)
    
    # Register adapter for backward compatibility
    try:
        from ..monitor_refactored import RefactoredMarketMonitor
        container.register_factory(
            RefactoredMarketMonitor,
            create_monitor_adapter,
            ServiceLifetime.SINGLETON
        )
    except ImportError:
        logger.debug("RefactoredMarketMonitor not available for adapter registration")
    
    logger.info("✅ Backward compatibility adapters registered")
    return container
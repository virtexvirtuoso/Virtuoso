"""
Service interfaces for dependency injection.

This module defines the contracts for all major services in the Virtuoso system.
These interfaces enable loose coupling, improved testability, and flexible
service implementations.
"""

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from abc import ABC, abstractmethod
import asyncio


@runtime_checkable
class IDisposable(Protocol):
    """Interface for services that require cleanup/disposal of resources."""
    
    async def dispose(self) -> None:
        """Dispose of resources and cleanup."""
        ...


@runtime_checkable  
class IAsyncDisposable(Protocol):
    """Interface for services that require async cleanup/disposal of resources."""
    
    async def dispose_async(self) -> None:
        """Dispose of resources and cleanup asynchronously."""
        ...


@runtime_checkable
class IAlertService(Protocol):
    """Interface for alert management services."""
    
    async def send_alert(
        self, 
        message: str, 
        level: str, 
        context: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send an alert with specified level and context."""
        ...
    
    async def batch_send(self, alerts: List[Dict[str, Any]]) -> List[bool]:
        """Send multiple alerts in batch, return success status for each."""
        ...
    
    def register_handler(self, handler_name: str, handler: Any) -> None:
        """Register an alert handler (Discord, email, etc.)."""
        ...
    
    def set_alert_threshold(self, level: str, threshold: int) -> None:
        """Set alert threshold for rate limiting."""
        ...
    
    def get_alerts(self, level: Optional[str] = None, limit: int = 100, start_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get alerts with optional filtering."""
        ...
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics and metrics."""
        ...


@runtime_checkable
class IMetricsService(Protocol):
    """Interface for metrics collection and reporting services."""
    
    def update_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Update a metric value with optional tags."""
        ...
    
    def increment_counter(self, name: str, amount: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        ...
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value."""
        ...
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric value."""
        ...
    
    def get_metric(self, name: str) -> Optional[float]:
        """Get current value of a metric."""
        ...
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics summary."""
        ...
    
    async def start_collection(self) -> None:
        """Start metrics collection background task."""
        ...
    
    async def stop_collection(self) -> None:
        """Stop metrics collection background task."""
        ...
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect current metrics data."""
        ...
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        ...


@runtime_checkable
class IInterpretationService(Protocol):
    """Interface for analysis interpretation services."""
    
    def get_component_interpretation(self, component: str, data: Dict[str, Any]) -> str:
        """Generate interpretation for a specific component's analysis."""
        ...
    
    def get_market_interpretation(self, analysis_result: Dict[str, Any]) -> str:
        """Generate interpretation for overall market analysis."""
        ...
    
    def get_signal_interpretation(self, signal_data: Dict[str, Any]) -> str:
        """Generate interpretation for trading signals."""
        ...
    
    def get_indicator_interpretation(self, indicator_name: str, values: Dict[str, float]) -> str:
        """Generate interpretation for specific indicator values."""
        ...
    
    def set_interpretation_config(self, config: Dict[str, Any]) -> None:
        """Update interpretation configuration."""
        ...


@runtime_checkable
class IFormattingService(Protocol):
    """Interface for data formatting and display services."""
    
    def format_analysis_result(self, result: Dict[str, Any]) -> str:
        """Format analysis results for display."""
        ...
    
    def format_signal(self, signal: Dict[str, Any]) -> str:
        """Format trading signals for display."""
        ...
    
    def format_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format metrics data for display."""
        ...
    
    def format_for_display(self, data: Dict[str, Any], format_type: str) -> str:
        """Format data for specific display type (console, web, mobile)."""
        ...
    
    def format_table(self, data: List[Dict[str, Any]], columns: List[str]) -> str:
        """Format data as a table."""
        ...
    
    def format_chart_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format data for chart display."""
        ...


@runtime_checkable
class IValidationService(Protocol):
    """Interface for data validation services."""
    
    async def validate(self, data: Dict[str, Any], rules: Optional[List[str]] = None) -> 'ValidationResult':
        """Validate data against specified rules."""
        ...
    
    def add_rule(self, rule_name: str, rule: Any) -> None:
        """Add a validation rule."""
        ...
    
    def remove_rule(self, rule_name: str) -> None:
        """Remove a validation rule."""
        ...
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        ...
    
    async def validate_config(self, config: Dict[str, Any]) -> 'ValidationResult':
        """Validate configuration data."""
        ...
    
    async def validate_market_data(self, market_data: Dict[str, Any]) -> 'ValidationResult':
        """Validate market data structure and completeness."""
        ...


@runtime_checkable
class IConfigService(Protocol):
    """Interface for configuration management services."""
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        ...
    
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        ...
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        ...
    
    def reload_config(self) -> None:
        """Reload configuration from source."""
        ...
    
    def validate_config(self) -> bool:
        """Validate current configuration."""
        ...
    
    def get_environment(self) -> str:
        """Get current environment (dev, staging, prod)."""
        ...


@runtime_checkable
class IExchangeService(Protocol):
    """Interface for exchange communication services."""
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker data for symbol."""
        ...
    
    async def get_orderbook(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Get orderbook data for symbol."""
        ...
    
    async def get_trades(self, symbol: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent trades for symbol."""
        ...
    
    async def get_ohlcv(self, symbol: str, timeframe: str, limit: Optional[int] = None) -> List[List]:
        """Get OHLCV data for symbol and timeframe."""
        ...
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols."""
        ...
    
    def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information and limits."""
        ...
    
    async def check_connection(self) -> bool:
        """Check if exchange connection is healthy."""
        ...


# Additional specialized interfaces

@runtime_checkable
class IIndicatorService(Protocol):
    """Interface for indicator calculation services."""
    
    async def calculate(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate indicator values from market data."""
        ...
    
    def get_required_data(self) -> List[str]:
        """Get list of required data fields for calculation."""
        ...
    
    def get_config(self) -> Dict[str, Any]:
        """Get indicator configuration."""
        ...
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Update indicator configuration."""
        ...


@runtime_checkable
class IAnalysisService(Protocol):
    """Interface for market analysis services."""
    
    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform market analysis on provided data."""
        ...
    
    def get_supported_symbols(self) -> List[str]:
        """Get list of supported symbols for analysis."""
        ...
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """Get analysis configuration."""
        ...
    
    async def get_historical_analysis(self, symbol: str, days: int) -> List[Dict[str, Any]]:
        """Get historical analysis results."""
        ...


@runtime_checkable
class IPortfolioService(Protocol):
    """Interface for portfolio management services."""
    
    async def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status."""
        ...
    
    async def calculate_position_size(self, symbol: str, risk_percent: float) -> float:
        """Calculate appropriate position size."""
        ...
    
    async def get_risk_metrics(self) -> Dict[str, Any]:
        """Get portfolio risk metrics."""
        ...
    
    async def update_positions(self, positions: List[Dict[str, Any]]) -> None:
        """Update portfolio positions."""
        ...


# Data classes for service responses

from dataclasses import dataclass
from typing import Union

@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


@dataclass
class ServiceHealth:
    """Health status of a service."""
    service_name: str
    is_healthy: bool
    status_message: str
    last_check: datetime
    response_time_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


# Additional Core Service Interfaces (Priority 1)

@runtime_checkable
class IMarketDataService(Protocol):
    """Interface for market data management services."""
    
    async def get_market_data(self, symbol: str, timeframe: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Get market data for symbol and timeframe."""
        ...
    
    async def get_real_time_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Get real-time data for multiple symbols."""
        ...
    
    async def get_historical_data(self, symbol: str, timeframe: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get historical market data."""
        ...
    
    def get_supported_symbols(self) -> List[str]:
        """Get list of supported trading symbols."""
        ...
    
    def get_supported_timeframes(self) -> List[str]:
        """Get list of supported timeframes."""
        ...
    
    async def validate_market_data(self, data: Dict[str, Any]) -> bool:
        """Validate market data structure and completeness."""
        ...


@runtime_checkable
class IExchangeManagerService(Protocol):
    """Interface for exchange management services."""
    
    async def get_primary_exchange(self) -> Any:
        """Get the primary exchange instance."""
        ...
    
    async def get_exchange(self, name: str) -> Any:
        """Get exchange instance by name."""
        ...
    
    def get_available_exchanges(self) -> List[str]:
        """Get list of available exchange names."""
        ...
    
    async def initialize(self) -> None:
        """Initialize exchange connections."""
        ...
    
    async def shutdown(self) -> None:
        """Shutdown all exchange connections."""
        ...
    
    def get_exchange_status(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get status of exchanges."""
        ...


@runtime_checkable
class IMonitoringService(Protocol):
    """Interface for market monitoring services."""
    
    async def start_monitoring(self, symbols: List[str]) -> None:
        """Start monitoring specified symbols."""
        ...
    
    async def stop_monitoring(self) -> None:
        """Stop all monitoring activities."""
        ...
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        ...
    
    async def add_symbol(self, symbol: str) -> None:
        """Add symbol to monitoring list."""
        ...
    
    async def remove_symbol(self, symbol: str) -> None:
        """Remove symbol from monitoring list."""
        ...
    
    def get_monitored_symbols(self) -> List[str]:
        """Get list of currently monitored symbols."""
        ...
    
    async def get_monitoring_data(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get monitoring data for symbols."""
        ...


@runtime_checkable
class ISignalService(Protocol):
    """Interface for signal generation and processing services."""
    
    async def generate_signals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signals from market data."""
        ...
    
    async def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Validate signal structure and data."""
        ...
    
    def get_signal_config(self) -> Dict[str, Any]:
        """Get signal generation configuration."""
        ...
    
    def update_signal_config(self, config: Dict[str, Any]) -> None:
        """Update signal generation configuration."""
        ...
    
    async def get_signal_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get signal generation history."""
        ...
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """Get signal generation statistics."""
        ...


@runtime_checkable
class IWebSocketService(Protocol):
    """Interface for WebSocket management services."""
    
    async def connect(self, streams: List[str]) -> None:
        """Connect to WebSocket streams."""
        ...
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        ...
    
    async def subscribe(self, stream: str) -> None:
        """Subscribe to a WebSocket stream."""
        ...
    
    async def unsubscribe(self, stream: str) -> None:
        """Unsubscribe from a WebSocket stream."""
        ...
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        ...
    
    def get_active_streams(self) -> List[str]:
        """Get list of active streams."""
        ...
    
    async def send_message(self, message: Dict[str, Any]) -> None:
        """Send message through WebSocket."""
        ...


@runtime_checkable
class IHealthService(Protocol):
    """Interface for health monitoring services."""
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health."""
        ...
    
    async def check_component_health(self, component: str) -> Dict[str, Any]:
        """Check health of specific component."""
        ...
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        ...
    
    def register_health_check(self, name: str, check_func: Any) -> None:
        """Register a health check function."""
        ...
    
    async def run_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive system diagnostics."""
        ...


@runtime_checkable
class IReportingService(Protocol):
    """Interface for reporting and document generation services."""
    
    async def generate_report(self, report_type: str, data: Dict[str, Any], format: str = 'pdf') -> bytes:
        """Generate report in specified format."""
        ...
    
    def get_available_reports(self) -> List[str]:
        """Get list of available report types."""
        ...
    
    def get_report_config(self, report_type: str) -> Dict[str, Any]:
        """Get configuration for report type."""
        ...
    
    async def schedule_report(self, report_type: str, schedule: str, recipients: List[str]) -> str:
        """Schedule recurring report generation."""
        ...
    
    async def cancel_scheduled_report(self, schedule_id: str) -> None:
        """Cancel scheduled report."""
        ...


# Missing Core Service Interfaces (Priority 2)

@runtime_checkable
class IMarketMonitorService(Protocol):
    """Interface for market monitoring services."""
    
    async def start_monitoring(self, symbols: Optional[List[str]] = None) -> None:
        """Start monitoring market data for specified symbols."""
        ...
    
    async def stop_monitoring(self) -> None:
        """Stop all monitoring activities."""
        ...
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        ...
    
    def get_monitored_symbols(self) -> List[str]:
        """Get list of currently monitored symbols."""
        ...
    
    async def get_market_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive market analysis for a symbol."""
        ...
    
    def get_confluence_analyzer(self) -> Any:
        """Get the confluence analyzer instance."""
        ...
    
    def get_signal_generator(self) -> Any:
        """Get the signal generator instance."""
        ...
    
    def get_alert_manager(self) -> Any:
        """Get the alert manager instance."""
        ...


@runtime_checkable
class IDashboardService(Protocol):
    """Interface for dashboard integration services."""
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        ...
    
    async def get_signals_data(self) -> List[Dict[str, Any]]:
        """Get current trading signals."""
        ...
    
    async def get_alerts_data(self) -> List[Dict[str, Any]]:
        """Get current alerts."""
        ...
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview data."""
        ...
    
    async def get_top_symbols(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top symbols with market data."""
        ...
    
    async def get_confluence_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get confluence analysis for a specific symbol."""
        ...
    
    async def initialize(self) -> bool:
        """Initialize the dashboard service."""
        ...


@runtime_checkable
class ITopSymbolsManagerService(Protocol):
    """Interface for top symbols management services."""
    
    async def get_top_symbols(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get top trading symbols by volume/activity."""
        ...
    
    async def get_symbols(self, limit: int = 30) -> List[str]:
        """Get symbol names only."""
        ...
    
    async def update_symbols(self) -> None:
        """Update the symbol rankings."""
        ...
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific symbol."""
        ...


@runtime_checkable
class IConfluenceAnalyzerService(Protocol):
    """Interface for confluence analysis services."""
    
    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform confluence analysis on market data."""
        ...
    
    async def get_confluence_score(self, symbol: str) -> float:
        """Get confluence score for a symbol."""
        ...
    
    def get_analysis_components(self) -> List[str]:
        """Get list of analysis components used."""
        ...
    
    def set_weights(self, weights: Dict[str, float]) -> None:
        """Set component weights for analysis."""
        ...


@runtime_checkable
class ICacheService(Protocol):
    """Interface for caching services."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        ...
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        ...
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        ...
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        ...


@runtime_checkable
class IAnalysisEngineService(Protocol):
    """Interface for analysis engine services (Alpha Scanner, Liquidation Detector, etc.)."""
    
    async def analyze_symbol(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single symbol."""
        ...
    
    async def analyze_batch(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Analyze multiple symbols in batch."""
        ...
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """Get current analysis configuration."""
        ...
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """Update analysis configuration."""
        ...
    
    def get_supported_symbols(self) -> List[str]:
        """Get list of supported symbols."""
        ...


# Export all interfaces for easy importing
__all__ = [
    'IAlertService',
    'IMetricsService',
    'IInterpretationService',
    'IFormattingService', 
    'IValidationService',
    'IConfigService',
    'IExchangeService',
    'IIndicatorService',
    'IAnalysisService',
    'IPortfolioService',
    'IMarketDataService',
    'IExchangeManagerService',
    'IMonitoringService',
    'ISignalService',
    'IWebSocketService',
    'IHealthService',
    'IReportingService',
    'IMarketMonitorService',
    'IDashboardService',
    'ITopSymbolsManagerService',
    'IConfluenceAnalyzerService',
    'ICacheService',
    'IAnalysisEngineService',
    'ValidationResult',
    'ServiceHealth'
]
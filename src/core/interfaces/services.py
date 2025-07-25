"""
Service interfaces for dependency injection.

This module defines the contracts for all major services in the Virtuoso system.
These interfaces enable loose coupling, improved testability, and flexible
service implementations.
"""

from typing import Protocol, Dict, Any, List, Optional, Union, runtime_checkable
from datetime import datetime
from abc import ABC, abstractmethod
import asyncio


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
    'ValidationResult',
    'ServiceHealth'
]
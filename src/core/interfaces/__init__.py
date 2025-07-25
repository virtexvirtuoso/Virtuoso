"""
Core interfaces for dependency injection and type safety.

This package provides protocol interfaces and adapters for major system components,
enabling better dependency injection, type safety, and testability.
"""

# Service interfaces (existing)
from .services import (
    IAlertService,
    IMetricsService, 
    IInterpretationService,
    IFormattingService,
    IValidationService,
    IConfigService,
    IExchangeService
)

# Component interfaces (new)
from .monitoring import (
    MonitorInterface,
    AlertInterface,
    MetricsInterface,
    HealthCheckInterface,
    MonitoringAdapter
)

from .analysis import (
    AnalysisInterface,
    IndicatorInterface,
    ConfluenceAnalyzerInterface,
    BacktestInterface,
    AnalysisAdapter
)

from .validation import (
    ValidationResult,
    ValidatorInterface,
    DataValidatorInterface,
    ConfigValidatorInterface,
    SchemaValidatorInterface,
    ValidatorAdapter
)

from .exchange import (
    ExchangeInterface,
    TradingInterface,
    WebSocketInterface,
    MarketDataInterface,
    ExchangeAdapter
)

from .reporting import (
    ReportGeneratorInterface,
    PDFGeneratorInterface,
    ChartGeneratorInterface,
    NotificationInterface,
    DashboardInterface,
    ReportingAdapter
)

from .data_processing import (
    DataProcessorInterface,
    DataTransformerInterface,
    DataAggregatorInterface,
    DataFilterInterface,
    DataCacheInterface,
    DataPipelineInterface,
    DataProcessorAdapter
)

__all__ = [
    # Existing service interfaces
    'IAlertService',
    'IMetricsService',
    'IInterpretationService', 
    'IFormattingService',
    'IValidationService',
    'IConfigService',
    'IExchangeService',
    
    # Monitoring
    'MonitorInterface',
    'AlertInterface',
    'MetricsInterface',
    'HealthCheckInterface',
    'MonitoringAdapter',
    
    # Analysis
    'AnalysisInterface',
    'IndicatorInterface',
    'ConfluenceAnalyzerInterface',
    'BacktestInterface',
    'AnalysisAdapter',
    
    # Validation
    'ValidationResult',
    'ValidatorInterface',
    'DataValidatorInterface',
    'ConfigValidatorInterface',
    'SchemaValidatorInterface',
    'ValidatorAdapter',
    
    # Exchange
    'ExchangeInterface',
    'TradingInterface',
    'WebSocketInterface',
    'MarketDataInterface',
    'ExchangeAdapter',
    
    # Reporting
    'ReportGeneratorInterface',
    'PDFGeneratorInterface',
    'ChartGeneratorInterface',
    'NotificationInterface',
    'DashboardInterface',
    'ReportingAdapter',
    
    # Data Processing
    'DataProcessorInterface',
    'DataTransformerInterface',
    'DataAggregatorInterface',
    'DataFilterInterface',
    'DataCacheInterface',
    'DataPipelineInterface',
    'DataProcessorAdapter',
]
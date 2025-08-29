"""
Monitoring Component Interfaces.

Clean interfaces following Single Responsibility Principle for the
refactored monitoring system components.
"""

from .data_interfaces import IDataFetcher, IDataValidator
from .signal_interfaces import ISignalAnalyzer, ITradeParameterCalculator
from .system_interfaces import IMetricsCollector, IHealthChecker, IWebSocketConnectionManager

__all__ = [
    'IDataFetcher',
    'IDataValidator', 
    'ISignalAnalyzer',
    'ITradeParameterCalculator',
    'IMetricsCollector',
    'IHealthChecker',
    'IWebSocketConnectionManager'
]
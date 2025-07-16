# src/monitoring/__init__.py

"""
Monitoring package for the trading system.

This package provides market monitoring and reporting capabilities.
"""

# Import only what's safe and doesn't cause circular dependencies
try:
    from .market_reporter import MarketReporter
    __all__ = ['MarketReporter']
except ImportError as e:
    # Graceful fallback if dependencies aren't available
    import logging
    logging.getLogger(__name__).warning(f"MarketReporter import failed: {e}")
    __all__ = []

# Note: monitor.py is commented out due to circular import issues
# If you need MarketMonitor, import it directly:
# from src.monitoring.monitor import MarketMonitor

__version__ = "1.0.0"

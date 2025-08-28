"""
Virtuoso CCXT Core Package

This package contains the core components of the Virtuoso CCXT trading system,
providing foundational functionality for market analysis, exchange integration,
caching, error handling, and system coordination.

Core Components:
    exchanges: Multi-exchange integration layer (Bybit, Binance)
    analysis: Market analysis and confluence scoring engine
    cache: High-performance caching layer (Memcached/Redis)
    config: Configuration management and validation
    error: Centralized error handling and exception management
    validation: Data validation and schema enforcement
    monitoring: System monitoring and health checks
    reporting: Report generation and data export
    resilience: Circuit breakers and fallback mechanisms

Architecture:
    The core package follows a layered architecture with clear separation
    of concerns:
    - Infrastructure layer: Caching, database, networking
    - Service layer: Exchange clients, data processors
    - Domain layer: Trading logic, analysis engines
    - Application layer: API endpoints, web interfaces

Design Principles:
    - Dependency injection for loose coupling
    - Async/await for high-performance I/O
    - Circuit breaker pattern for resilience
    - Observer pattern for event handling
    - Factory pattern for component creation

Usage:
    from src.core.exchanges import ExchangeManager
    from src.core.analysis import ConfluenceAnalyzer
    from src.core.cache import CacheManager

Author: Virtuoso CCXT Development Team
Version: 2.5.0
"""

__version__ = "2.5.0"
__author__ = "Virtuoso CCXT Development Team"

# Core component imports for convenience
from . import exchanges
from . import analysis
from . import cache
from . import config
from . import error
from . import validation

__all__ = [
    "exchanges",
    "analysis", 
    "cache",
    "config",
    "error",
    "validation"
]
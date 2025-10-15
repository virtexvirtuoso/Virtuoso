"""
Core Data Package

Provides access to real market data services and data management utilities.
"""

from .real_market_data_service import (
    RealMarketDataService,
    get_real_market_data_service
)

__all__ = [
    'RealMarketDataService',
    'get_real_market_data_service'
]
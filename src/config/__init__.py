"""
Configuration package for Virtuoso CCXT Trading System

Provides configuration validation and management functionality.
"""

from .validator import (
    ConfigValidator,
    validate_config_file,
    get_config_health
)

__all__ = [
    "ConfigValidator",
    "validate_config_file", 
    "get_config_health"
]

"""Resilience module for handling failures gracefully."""

from .circuit_breaker import CircuitBreaker, get_circuit_breaker, CircuitOpenError
from .fallback_provider import FallbackDataProvider, get_fallback_provider
from .exchange_wrapper import ResilientExchangeWrapper, wrap_exchange_manager

__all__ = [
    'CircuitBreaker',
    'get_circuit_breaker',
    'CircuitOpenError',
    'FallbackDataProvider',
    'get_fallback_provider',
    'ResilientExchangeWrapper',
    'wrap_exchange_manager'
]

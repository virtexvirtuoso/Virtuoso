"""Resilient wrapper for exchange operations with circuit breaker and fallback."""

import asyncio
from typing import Dict, Any, Optional
import logging
from src.core.resilience.circuit_breaker import get_circuit_breaker, CircuitBreakerError
from src.core.resilience.fallback_provider import get_fallback_provider

logger = logging.getLogger(__name__)


class ResilientExchangeWrapper:
    """Wraps exchange operations with resilience patterns."""
    
    def __init__(self, exchange_manager):
        """Initialize resilient wrapper.
        
        Args:
            exchange_manager: Original exchange manager
        """
        self.exchange_manager = exchange_manager
        self.fallback_provider = get_fallback_provider()
        
        # Create circuit breakers for different operations
        self.ticker_breaker = get_circuit_breaker(
            "ticker",
            failure_threshold=3,
            recovery_timeout=30.0
        )
        
        self.market_breaker = get_circuit_breaker(
            "market",
            failure_threshold=5,
            recovery_timeout=60.0
        )
    
    async def get_ticker_resilient(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get ticker with circuit breaker and fallback.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            Ticker data or fallback data
        """
        try:
            # Try to get real data with circuit breaker
            async def fetch_ticker():
                return await self.exchange_manager.get_market_data(symbol, exchange)
            
            data = await self.ticker_breaker.async_call(fetch_ticker)
            
            # Cache successful response
            if data and exchange in data:
                ticker_data = data[exchange].get('ticker', {})
                if ticker_data:
                    self.fallback_provider.save_to_cache(
                        "ticker",
                        ticker_data,
                        key=f"{exchange}_{symbol}"
                    )
            
            return data
            
        except CircuitBreakerError:
            logger.warning(f"Circuit open for ticker {symbol}, using fallback")
            return await self.fallback_provider.get_ticker_fallback(symbol, exchange)
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {e}, using fallback")
            return await self.fallback_provider.get_ticker_fallback(symbol, exchange)
    
    async def get_market_overview_resilient(self) -> Dict[str, Any]:
        """Get market overview with circuit breaker and fallback.
        
        Returns:
            Market overview or fallback data
        """
        try:
            # Try to get real data with circuit breaker
            async def fetch_overview():
                # This would call the actual market overview method
                return await self._fetch_market_overview_internal()
            
            data = await self.market_breaker.async_call(fetch_overview)
            
            # Cache successful response
            if data:
                self.fallback_provider.save_to_cache("market_overview", data)
            
            return data
            
        except CircuitBreakerError:
            logger.warning("Circuit open for market overview, using fallback")
            return await self.fallback_provider.get_market_overview_fallback()
        except Exception as e:
            logger.error(f"Error getting market overview: {e}, using fallback")
            return await self.fallback_provider.get_market_overview_fallback()
    
    async def _fetch_market_overview_internal(self) -> Dict[str, Any]:
        """Internal method to fetch market overview."""
        # This would contain the actual logic to fetch market overview
        # For now, return a placeholder
        return {
            "total_volume_24h": 0,
            "active_symbols": 0,
            "top_gainers": [],
            "top_losers": [],
            "status": "live"
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of resilient system.
        
        Returns:
            Combined health status
        """
        from src.core.resilience.circuit_breaker import get_all_circuit_states
        
        return {
            "circuit_breakers": get_all_circuit_states(),
            "fallback_system": self.fallback_provider.get_health_status()
        }


def wrap_exchange_manager(exchange_manager) -> ResilientExchangeWrapper:
    """Wrap an exchange manager with resilience patterns.
    
    Args:
        exchange_manager: Original exchange manager
        
    Returns:
        Resilient wrapper
    """
    return ResilientExchangeWrapper(exchange_manager)

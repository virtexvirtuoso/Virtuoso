#!/usr/bin/env python3
"""
Implement resilient decoupling between monitoring and web services.

This script adds circuit breakers, fallback mechanisms, and graceful degradation
to ensure the dashboard and web services remain operational even when external
dependencies (like Bybit API) are unavailable.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_circuit_breaker():
    """Create a circuit breaker implementation for external API calls."""
    
    circuit_breaker_code = '''"""Circuit Breaker pattern implementation for external API calls."""

import asyncio
import time
from typing import Optional, Callable, Any, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"     # Normal operation
    OPEN = "open"         # Failures exceeded threshold, blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker implementation for protecting against cascading failures."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name for logging
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.success_count = 0
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Function result or None if circuit is open
            
        Raises:
            CircuitOpenError: If circuit is open and not ready to test
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker {self.name}: Attempting recovery (HALF_OPEN)")
            else:
                logger.warning(f"Circuit breaker {self.name}: Circuit OPEN, call blocked")
                raise CircuitOpenError(f"Circuit {self.name} is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Function result or None if circuit is open
            
        Raises:
            CircuitOpenError: If circuit is open and not ready to test
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker {self.name}: Attempting recovery (HALF_OPEN)")
            else:
                logger.warning(f"Circuit breaker {self.name}: Circuit OPEN, call blocked")
                raise CircuitOpenError(f"Circuit {self.name} is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:  # Require 2 successful calls to fully close
                self.state = CircuitState.CLOSED
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name}: Circuit CLOSED (recovered)")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name}: Recovery failed, circuit OPEN again")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker {self.name}: Threshold exceeded, circuit OPEN")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }
    
    def reset(self):
        """Manually reset the circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info(f"Circuit breaker {self.name}: Manually reset to CLOSED")


class CircuitOpenError(Exception):
    """Raised when circuit is open and calls are blocked."""
    pass


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: type = Exception
) -> CircuitBreaker:
    """Get or create a circuit breaker.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before attempting recovery
        expected_exception: Exception type to catch
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception
        )
    return _circuit_breakers[name]


def get_all_circuit_states() -> Dict[str, Dict[str, Any]]:
    """Get state of all circuit breakers."""
    return {
        name: cb.get_state()
        for name, cb in _circuit_breakers.items()
    }
'''
    
    circuit_breaker_path = project_root / "src" / "core" / "resilience" / "circuit_breaker.py"
    circuit_breaker_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(circuit_breaker_path, 'w') as f:
        f.write(circuit_breaker_code)
    
    print(f"✅ Created circuit breaker at {circuit_breaker_path}")
    return circuit_breaker_path


def create_fallback_data_provider():
    """Create fallback data provider for when external APIs are unavailable."""
    
    fallback_code = '''"""Fallback data provider for graceful degradation."""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FallbackDataProvider:
    """Provides fallback data when external services are unavailable."""
    
    def __init__(self):
        """Initialize fallback data provider."""
        self.cache_dir = Path("cache/fallback")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Default fallback data
        self.default_ticker = {
            "symbol": "BTCUSDT",
            "last": 0,
            "bid": 0,
            "ask": 0,
            "volume": 0,
            "timestamp": int(time.time() * 1000),
            "status": "fallback"
        }
        
        self.default_market_overview = {
            "total_volume_24h": 0,
            "active_symbols": 0,
            "top_gainers": [],
            "top_losers": [],
            "status": "degraded",
            "message": "Using cached data - external services unavailable"
        }
        
        self.default_signals = {
            "signals": [],
            "total": 0,
            "strong": 0,
            "medium": 0,
            "weak": 0,
            "status": "cached"
        }
    
    async def get_ticker_fallback(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get fallback ticker data.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            Fallback ticker data
        """
        # Try to load from cache first
        cache_file = self.cache_dir / f"ticker_{exchange}_{symbol}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is not too old (1 hour)
                    if time.time() - data.get("cached_at", 0) < 3600:
                        data["status"] = "cached"
                        logger.info(f"Using cached ticker data for {symbol}")
                        return data
            except Exception as e:
                logger.error(f"Error loading cached ticker: {e}")
        
        # Return default with symbol
        fallback = self.default_ticker.copy()
        fallback["symbol"] = symbol
        fallback["exchange"] = exchange
        fallback["message"] = "External API unavailable - showing default values"
        logger.warning(f"Using default fallback for {symbol}")
        return fallback
    
    async def get_market_overview_fallback(self) -> Dict[str, Any]:
        """Get fallback market overview data.
        
        Returns:
            Fallback market overview
        """
        # Try to load from cache
        cache_file = self.cache_dir / "market_overview.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is not too old (15 minutes)
                    if time.time() - data.get("cached_at", 0) < 900:
                        data["status"] = "cached"
                        data["age_minutes"] = int((time.time() - data["cached_at"]) / 60)
                        logger.info("Using cached market overview")
                        return data
            except Exception as e:
                logger.error(f"Error loading cached market overview: {e}")
        
        # Return default
        logger.warning("Using default fallback for market overview")
        return self.default_market_overview.copy()
    
    async def get_signals_fallback(self) -> Dict[str, Any]:
        """Get fallback signals data.
        
        Returns:
            Fallback signals
        """
        # Try to load from cache
        cache_file = self.cache_dir / "signals.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is not too old (30 minutes)
                    if time.time() - data.get("cached_at", 0) < 1800:
                        data["status"] = "cached"
                        data["age_minutes"] = int((time.time() - data["cached_at"]) / 60)
                        logger.info("Using cached signals")
                        return data
            except Exception as e:
                logger.error(f"Error loading cached signals: {e}")
        
        # Return default
        logger.warning("Using default fallback for signals")
        return self.default_signals.copy()
    
    def save_to_cache(self, data_type: str, data: Dict[str, Any], key: Optional[str] = None):
        """Save data to cache for future fallback use.
        
        Args:
            data_type: Type of data (ticker, market_overview, signals)
            data: Data to cache
            key: Optional key for specific data (e.g., symbol for ticker)
        """
        try:
            data["cached_at"] = time.time()
            
            if data_type == "ticker" and key:
                cache_file = self.cache_dir / f"ticker_{key}.json"
            else:
                cache_file = self.cache_dir / f"{data_type}.json"
            
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            
            logger.debug(f"Saved {data_type} to cache")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of fallback system.
        
        Returns:
            Health status information
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        
        cache_stats = {}
        for file in cache_files:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    age = time.time() - data.get("cached_at", 0)
                    cache_stats[file.stem] = {
                        "age_seconds": int(age),
                        "age_readable": f"{int(age/60)}m {int(age%60)}s"
                    }
            except:
                pass
        
        return {
            "status": "operational",
            "cache_dir": str(self.cache_dir),
            "cached_files": len(cache_files),
            "cache_stats": cache_stats
        }


# Global instance
_fallback_provider: Optional[FallbackDataProvider] = None


def get_fallback_provider() -> FallbackDataProvider:
    """Get global fallback provider instance."""
    global _fallback_provider
    if _fallback_provider is None:
        _fallback_provider = FallbackDataProvider()
    return _fallback_provider
'''
    
    fallback_path = project_root / "src" / "core" / "resilience" / "fallback_provider.py"
    fallback_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(fallback_path, 'w') as f:
        f.write(fallback_code)
    
    print(f"✅ Created fallback provider at {fallback_path}")
    return fallback_path


def create_resilient_exchange_wrapper():
    """Create a resilient wrapper for exchange operations."""
    
    wrapper_code = '''"""Resilient wrapper for exchange operations with circuit breaker and fallback."""

import asyncio
from typing import Dict, Any, Optional
import logging
from src.core.resilience.circuit_breaker import get_circuit_breaker, CircuitOpenError
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
            
        except CircuitOpenError:
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
            
        except CircuitOpenError:
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
'''
    
    wrapper_path = project_root / "src" / "core" / "resilience" / "exchange_wrapper.py"
    
    with open(wrapper_path, 'w') as f:
        f.write(wrapper_code)
    
    print(f"✅ Created resilient exchange wrapper at {wrapper_path}")
    return wrapper_path


def patch_dashboard_integration():
    """Patch dashboard integration to handle failures gracefully."""
    
    patch_code = '''"""Patch dashboard integration for resilient operation."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def patch_dashboard_integration_resilience():
    """Apply resilience patches to dashboard integration."""
    
    try:
        from src.dashboard.dashboard_integration import DashboardIntegrationService
        from src.core.resilience.fallback_provider import get_fallback_provider
        
        # Store original method
        original_update = DashboardIntegrationService._update_dashboard_data
        
        async def resilient_update_dashboard_data(self):
            """Resilient version of dashboard data update."""
            try:
                # Try normal update
                await original_update(self)
            except Exception as e:
                logger.error(f"Dashboard update failed: {e}, using fallback data")
                
                # Use fallback data
                fallback = get_fallback_provider()
                
                self._dashboard_data = {
                    'signals': (await fallback.get_signals_fallback())['signals'],
                    'alerts': [],
                    'alpha_opportunities': [],
                    'system_status': {
                        'status': 'degraded',
                        'message': 'External services unavailable - showing cached data',
                        'timestamp': time.time()
                    },
                    'market_overview': await fallback.get_market_overview_fallback()
                }
                
                logger.info("Dashboard using fallback data")
        
        # Replace method
        DashboardIntegrationService._update_dashboard_data = resilient_update_dashboard_data
        
        logger.info("✅ Dashboard integration patched for resilience")
        
    except ImportError as e:
        logger.error(f"Could not patch dashboard integration: {e}")


def patch_api_routes_resilience():
    """Apply resilience patches to API routes."""
    
    try:
        from src.api.routes import market, dashboard
        from src.core.resilience.circuit_breaker import get_circuit_breaker, CircuitOpenError
        from src.core.resilience.fallback_provider import get_fallback_provider
        
        # Patch market ticker endpoint
        original_get_ticker = market.get_ticker
        
        async def resilient_get_ticker(
            symbol: str,
            exchange_id: str,
            exchange_manager = None
        ):
            """Resilient version of get_ticker."""
            breaker = get_circuit_breaker(f"ticker_{exchange_id}")
            
            try:
                # Try with circuit breaker
                async def fetch():
                    return await original_get_ticker(symbol, exchange_id, exchange_manager)
                
                return await breaker.async_call(fetch)
                
            except CircuitOpenError:
                # Circuit is open, use fallback
                fallback = get_fallback_provider()
                return await fallback.get_ticker_fallback(symbol, exchange_id)
            except Exception as e:
                logger.error(f"Ticker endpoint failed: {e}, using fallback")
                fallback = get_fallback_provider()
                return await fallback.get_ticker_fallback(symbol, exchange_id)
        
        # Replace endpoint
        market.get_ticker = resilient_get_ticker
        
        logger.info("✅ API routes patched for resilience")
        
    except ImportError as e:
        logger.error(f"Could not patch API routes: {e}")
'''
    
    patch_path = project_root / "src" / "core" / "resilience" / "patches.py"
    
    with open(patch_path, 'w') as f:
        f.write(patch_code)
    
    print(f"✅ Created resilience patches at {patch_path}")
    return patch_path


def create_health_endpoint():
    """Create a health check endpoint that doesn't depend on external services."""
    
    health_code = '''"""Independent health check endpoint."""

from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime
import psutil
import time

router = APIRouter()


@router.get("/health/system")
async def system_health() -> Dict[str, Any]:
    """Get system health independent of external services.
    
    Returns:
        System health status
    """
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get process info
    process = psutil.Process()
    process_info = {
        "pid": process.pid,
        "cpu_percent": process.cpu_percent(),
        "memory_mb": process.memory_info().rss / 1024 / 1024,
        "threads": process.num_threads(),
        "connections": len(process.connections())
    }
    
    # Check internal services
    services_status = {}
    
    # Check cache
    try:
        from pymemcache.client.base import Client
        mc = Client(('127.0.0.1', 11211))
        mc.get(b'test')
        mc.close()
        services_status["memcached"] = "healthy"
    except:
        services_status["memcached"] = "unavailable"
    
    # Check circuit breakers
    try:
        from src.core.resilience.circuit_breaker import get_all_circuit_states
        breakers = get_all_circuit_states()
        services_status["circuit_breakers"] = {
            "total": len(breakers),
            "open": sum(1 for b in breakers.values() if b["state"] == "open")
        }
    except:
        services_status["circuit_breakers"] = "not_initialized"
    
    # Overall health determination
    is_healthy = (
        cpu_percent < 90 and
        memory.percent < 90 and
        disk.percent < 90
    )
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - process.create_time(),
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent
        },
        "process": process_info,
        "services": services_status
    }


@router.get("/health/resilience")
async def resilience_health() -> Dict[str, Any]:
    """Get resilience system health.
    
    Returns:
        Resilience system status
    """
    try:
        from src.core.resilience.circuit_breaker import get_all_circuit_states
        from src.core.resilience.fallback_provider import get_fallback_provider
        
        breakers = get_all_circuit_states()
        fallback = get_fallback_provider()
        
        return {
            "status": "operational",
            "circuit_breakers": breakers,
            "fallback_system": fallback.get_health_status(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
'''
    
    health_path = project_root / "src" / "api" / "routes" / "health.py"
    
    with open(health_path, 'w') as f:
        f.write(health_code)
    
    print(f"✅ Created health endpoint at {health_path}")
    return health_path


def create_init_file():
    """Create __init__.py for resilience module."""
    
    init_code = '''"""Resilience module for handling failures gracefully."""

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
'''
    
    init_path = project_root / "src" / "core" / "resilience" / "__init__.py"
    
    with open(init_path, 'w') as f:
        f.write(init_code)
    
    print(f"✅ Created resilience module __init__.py")
    return init_path


def main():
    """Main execution."""
    print("=" * 60)
    print("🔧 Implementing Resilient Decoupling Solution")
    print("=" * 60)
    
    # Create resilience components
    circuit_breaker_path = create_circuit_breaker()
    fallback_path = create_fallback_data_provider()
    wrapper_path = create_resilient_exchange_wrapper()
    patch_path = patch_dashboard_integration()
    health_path = create_health_endpoint()
    init_path = create_init_file()
    
    print("\n✅ Resilience components created successfully!")
    print("\n📝 Next steps:")
    print("1. Update main.py to use resilient wrappers")
    print("2. Add health endpoints to API routes")
    print("3. Apply patches during startup")
    print("4. Test with simulated failures")
    
    print("\n🎯 Key features implemented:")
    print("- Circuit breakers for external API calls")
    print("- Fallback data providers for graceful degradation")
    print("- Resilient exchange wrapper")
    print("- Independent health check endpoints")
    print("- Automatic recovery mechanisms")


if __name__ == "__main__":
    main()
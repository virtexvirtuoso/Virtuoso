#!/usr/bin/env python3
"""
Distributed Rate Limiter using Memcached
Provides system-wide rate limiting across multiple processes and servers
"""

import time
import asyncio
from typing import Optional, Dict, Any, Tuple
from pymemcache.client.base import Client
from pymemcache import serde
import logging
import json
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RateLimitScope(Enum):
    """Scope of rate limiting"""
    GLOBAL = "global"           # System-wide
    EXCHANGE = "exchange"       # Per exchange
    USER = "user"              # Per user
    API_ENDPOINT = "endpoint"   # Per API endpoint
    SYMBOL = "symbol"          # Per trading symbol
    ALERT = "alert"            # Alert throttling

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    max_requests: int
    window_seconds: int
    scope: RateLimitScope
    burst_allowance: float = 1.0  # Allow burst up to this multiplier
    
class DistributedRateLimiter:
    """
    Distributed rate limiter using Memcached for coordination
    Supports multiple scopes and sliding window rate limiting
    """
    
    # Default configurations for different scopes
    DEFAULT_CONFIGS = {
        RateLimitScope.GLOBAL: RateLimitConfig(1000, 60, RateLimitScope.GLOBAL),
        RateLimitScope.EXCHANGE: RateLimitConfig(100, 60, RateLimitScope.EXCHANGE),
        RateLimitScope.USER: RateLimitConfig(60, 60, RateLimitScope.USER),
        RateLimitScope.API_ENDPOINT: RateLimitConfig(30, 60, RateLimitScope.API_ENDPOINT),
        RateLimitScope.SYMBOL: RateLimitConfig(20, 60, RateLimitScope.SYMBOL),
        RateLimitScope.ALERT: RateLimitConfig(5, 300, RateLimitScope.ALERT, burst_allowance=2.0),
    }
    
    # Exchange-specific rate limits
    EXCHANGE_LIMITS = {
        'binance': {'requests': 1200, 'window': 60},
        'bybit': {'requests': 100, 'window': 60},
        'okx': {'requests': 60, 'window': 2},
        'kucoin': {'requests': 100, 'window': 10},
        'gate': {'requests': 900, 'window': 60},
    }
    
    def __init__(self, host: str = '127.0.0.1', port: int = 11211):
        """Initialize distributed rate limiter"""
        try:
            self.mc = Client(
                (host, port),
                serializer=serde.python_memcache_serializer,
                deserializer=serde.python_memcache_deserializer,
                connect_timeout=1,
                timeout=0.5
            )
            # Test connection
            self.mc.set(b'ratelimit:test', b'1', expire=1)
            self.available = True
            logger.info(f"Distributed rate limiter connected to Memcached at {host}:{port}")
        except Exception as e:
            logger.warning(f"Memcached not available for rate limiting: {e}")
            self.available = False
            self.mc = None
            # Fallback to local tracking
            self.local_counters = {}
            
        # Metrics tracking
        self.metrics = {
            'allowed': 0,
            'blocked': 0,
            'errors': 0,
            'by_scope': {}
        }
        
    async def check_rate_limit(self, 
                              key: str, 
                              scope: RateLimitScope = RateLimitScope.GLOBAL,
                              config: Optional[RateLimitConfig] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limit
        
        Args:
            key: Unique identifier (e.g., user_id, exchange_name, endpoint)
            scope: Scope of rate limiting
            config: Optional custom configuration
            
        Returns:
            Tuple of (allowed: bool, info: dict with details)
        """
        if config is None:
            config = self.DEFAULT_CONFIGS.get(scope, self.DEFAULT_CONFIGS[RateLimitScope.GLOBAL])
            
        # Generate cache key with sliding window
        window_id = int(time.time() / config.window_seconds)
        cache_key = f"ratelimit:{scope.value}:{key}:{window_id}"
        
        try:
            if self.available and self.mc:
                return await self._check_distributed(cache_key, config)
            else:
                return await self._check_local(cache_key, config)
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            self.metrics['errors'] += 1
            # On error, be permissive
            return True, {'error': str(e), 'fallback': True}
    
    async def _check_distributed(self, cache_key: str, config: RateLimitConfig) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using distributed Memcached"""
        try:
            # Try atomic increment
            try:
                count = self.mc.incr(cache_key.encode(), 1)
            except:
                # Key doesn't exist, set it
                self.mc.set(cache_key.encode(), 1, expire=config.window_seconds)
                count = 1
            
            # Check against limit (with burst allowance)
            max_allowed = int(config.max_requests * config.burst_allowance)
            allowed = count <= max_allowed
            
            # Update metrics
            if allowed:
                self.metrics['allowed'] += 1
            else:
                self.metrics['blocked'] += 1
                
            # Track by scope
            scope_key = config.scope.value if hasattr(config, 'scope') else 'global'
            if scope_key not in self.metrics['by_scope']:
                self.metrics['by_scope'][scope_key] = {'allowed': 0, 'blocked': 0}
            
            if allowed:
                self.metrics['by_scope'][scope_key]['allowed'] += 1
            else:
                self.metrics['by_scope'][scope_key]['blocked'] += 1
            
            # Calculate remaining requests and reset time
            remaining = max(0, max_allowed - count)
            reset_time = (int(time.time() / config.window_seconds) + 1) * config.window_seconds
            
            return allowed, {
                'allowed': allowed,
                'count': count,
                'limit': max_allowed,
                'remaining': remaining,
                'reset_time': reset_time,
                'window': config.window_seconds,
                'scope': scope_key
            }
            
        except Exception as e:
            logger.error(f"Distributed rate limit error: {e}")
            self.metrics['errors'] += 1
            return True, {'error': str(e), 'fallback': True}
    
    async def _check_local(self, cache_key: str, config: RateLimitConfig) -> Tuple[bool, Dict[str, Any]]:
        """Fallback to local rate limiting when Memcached unavailable"""
        current_time = time.time()
        window_start = int(current_time / config.window_seconds) * config.window_seconds
        
        # Clean old entries
        self._cleanup_local_counters(window_start)
        
        # Get or create counter
        if cache_key not in self.local_counters:
            self.local_counters[cache_key] = {
                'count': 0,
                'window_start': window_start
            }
        
        counter = self.local_counters[cache_key]
        
        # Reset if new window
        if counter['window_start'] < window_start:
            counter['count'] = 0
            counter['window_start'] = window_start
        
        # Increment and check
        counter['count'] += 1
        max_allowed = int(config.max_requests * config.burst_allowance)
        allowed = counter['count'] <= max_allowed
        
        # Update metrics
        if allowed:
            self.metrics['allowed'] += 1
        else:
            self.metrics['blocked'] += 1
        
        remaining = max(0, max_allowed - counter['count'])
        reset_time = window_start + config.window_seconds
        
        scope_key = config.scope.value if hasattr(config, 'scope') else 'global'
        return allowed, {
            'allowed': allowed,
            'count': counter['count'],
            'limit': max_allowed,
            'remaining': remaining,
            'reset_time': reset_time,
            'window': config.window_seconds,
            'scope': scope_key,
            'local': True
        }
    
    def _cleanup_local_counters(self, current_window_start: float):
        """Clean up old local counter entries"""
        if len(self.local_counters) > 1000:  # Prevent memory leak
            # Remove entries older than current window
            keys_to_remove = [
                key for key, counter in self.local_counters.items()
                if counter['window_start'] < current_window_start - 300  # Keep 5 minutes
            ]
            for key in keys_to_remove:
                del self.local_counters[key]
    
    async def check_exchange_limit(self, exchange: str, endpoint: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check rate limit for specific exchange
        
        Args:
            exchange: Exchange name
            endpoint: Optional specific endpoint
            
        Returns:
            Tuple of (allowed, info)
        """
        # Get exchange-specific limits
        limits = self.EXCHANGE_LIMITS.get(exchange.lower())
        if not limits:
            # Use default if exchange not configured
            return await self.check_rate_limit(
                exchange,
                RateLimitScope.EXCHANGE
            )
        
        # Create custom config for this exchange
        config = RateLimitConfig(
            max_requests=limits['requests'],
            window_seconds=limits['window'],
            scope=RateLimitScope.EXCHANGE
        )
        
        # Use endpoint if provided, otherwise just exchange
        key = f"{exchange}:{endpoint}" if endpoint else exchange
        
        return await self.check_rate_limit(key, RateLimitScope.EXCHANGE, config)
    
    async def check_user_limit(self, user_id: str, action: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check rate limit for specific user
        
        Args:
            user_id: User identifier
            action: Optional action type
            
        Returns:
            Tuple of (allowed, info)
        """
        key = f"{user_id}:{action}" if action else user_id
        return await self.check_rate_limit(key, RateLimitScope.USER)
    
    async def check_alert_limit(self, alert_type: str, symbol: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check rate limit for alerts to prevent spam
        
        Args:
            alert_type: Type of alert
            symbol: Optional symbol for the alert
            
        Returns:
            Tuple of (allowed, info)
        """
        key = f"{alert_type}:{symbol}" if symbol else alert_type
        return await self.check_rate_limit(key, RateLimitScope.ALERT)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics"""
        total = self.metrics['allowed'] + self.metrics['blocked']
        
        return {
            'total_requests': total,
            'allowed': self.metrics['allowed'],
            'blocked': self.metrics['blocked'],
            'block_rate': (self.metrics['blocked'] / total * 100) if total > 0 else 0,
            'errors': self.metrics['errors'],
            'by_scope': self.metrics['by_scope'],
            'backend': 'memcached' if self.available else 'local'
        }
    
    async def reset_limit(self, key: str, scope: RateLimitScope = RateLimitScope.GLOBAL):
        """Reset rate limit for a specific key"""
        window_id = int(time.time() / 60)  # Assume 60 second window
        cache_key = f"ratelimit:{scope.value}:{key}:{window_id}"
        
        if self.available and self.mc:
            try:
                self.mc.delete(cache_key.encode())
                logger.info(f"Reset rate limit for {cache_key}")
            except Exception as e:
                logger.error(f"Failed to reset rate limit: {e}")
        elif cache_key in self.local_counters:
            del self.local_counters[cache_key]
            logger.info(f"Reset local rate limit for {cache_key}")
    
    def close(self):
        """Close connection to Memcached"""
        if self.mc:
            try:
                self.mc.close()
            except:
                pass

# Global instance for easy access
_rate_limiter = None

def get_rate_limiter() -> DistributedRateLimiter:
    """Get or create global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = DistributedRateLimiter()
    return _rate_limiter
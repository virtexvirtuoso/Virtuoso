"""
Liquidation Cache Manager - Redis/Memcached Integration
Replaces file-based caching with high-performance in-memory caching
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import memcache
    MEMCACHE_AVAILABLE = True
except ImportError:
    MEMCACHE_AVAILABLE = False

from src.core.models.liquidation import LiquidationEvent, MarketStressIndicator, CascadeAlert

class LiquidationCacheManager:
    """Manages caching for liquidation data using Redis or Memcached."""
    
    def __init__(self, cache_type: str = "redis", **kwargs):
        """
        Initialize cache manager.
        
        Args:
            cache_type: "redis" or "memcached"
            **kwargs: Connection parameters for cache backend
        """
        self.logger = logging.getLogger(__name__)
        self.cache_type = cache_type
        self.cache_client = None
        
        # Default TTLs for different data types
        self.ttl_config = {
            'liquidation_events': 300,  # 5 minutes
            'market_stress': 60,  # 1 minute
            'cascade_alerts': 120,  # 2 minutes
            'leverage_metrics': 180,  # 3 minutes
            'historical_data': 3600,  # 1 hour
        }
        
        self._initialize_cache(kwargs)
    
    def _initialize_cache(self, config: Dict):
        """Initialize cache connection."""
        try:
            if self.cache_type == "redis" and REDIS_AVAILABLE:
                host = config.get('host', 'localhost')
                port = config.get('port', 6379)
                db = config.get('db', 0)
                password = config.get('password', None)
                
                self.cache_client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True
                    # Removed socket_keepalive_options - not supported by redis-py in this format
                    # The C-style socket options (1, 2, 3) cause "Error 22: Invalid argument"
                )
                
                # Test connection
                self.cache_client.ping()
                self.logger.info(f"Connected to Redis cache at {host}:{port}")
                
            elif self.cache_type == "memcached" and MEMCACHE_AVAILABLE:
                servers = config.get('servers', ['localhost:11211'])
                self.cache_client = memcache.Client(servers, debug=0)
                
                # Test connection
                self.cache_client.set('test_key', 'test_value')
                self.cache_client.delete('test_key')
                self.logger.info(f"Connected to Memcached at {servers}")
                
            else:
                self.logger.warning(f"Cache type {self.cache_type} not available, using in-memory cache")
                self.cache_client = InMemoryCache()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.cache_type} cache: {e}")
            self.cache_client = InMemoryCache()
    
    def _generate_key(self, prefix: str, params: Dict) -> str:
        """Generate cache key from prefix and parameters."""
        # Sort params for consistent key generation
        sorted_params = sorted(params.items())
        param_str = json.dumps(sorted_params)
        hash_str = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"liquidation:{prefix}:{hash_str}"
    
    def get_liquidation_events(self, symbols: List[str], exchanges: List[str], 
                              lookback_minutes: int) -> Optional[List[LiquidationEvent]]:
        """Get cached liquidation events."""
        try:
            key = self._generate_key('events', {
                'symbols': symbols,
                'exchanges': exchanges,
                'lookback': lookback_minutes
            })
            
            if self.cache_type == "redis":
                data = self.cache_client.get(key)
                if data:
                    events_data = json.loads(data)
                    return [LiquidationEvent(**event) for event in events_data]
                    
            elif self.cache_type == "memcached":
                data = self.cache_client.get(key)
                if data:
                    return [LiquidationEvent(**event) for event in json.loads(data)]
            
            else:  # In-memory cache
                return self.cache_client.get(key)
                
        except Exception as e:
            self.logger.error(f"Error getting cached liquidation events: {e}")
        
        return None
    
    def set_liquidation_events(self, symbols: List[str], exchanges: List[str],
                              lookback_minutes: int, events: List[LiquidationEvent]):
        """Cache liquidation events."""
        try:
            key = self._generate_key('events', {
                'symbols': symbols,
                'exchanges': exchanges,
                'lookback': lookback_minutes
            })
            
            # Convert events to dict format
            events_data = [event.dict() for event in events]
            
            if self.cache_type == "redis":
                self.cache_client.setex(
                    key,
                    self.ttl_config['liquidation_events'],
                    json.dumps(events_data)
                )
                
            elif self.cache_type == "memcached":
                self.cache_client.set(
                    key,
                    json.dumps(events_data),
                    time=self.ttl_config['liquidation_events']
                )
            
            else:  # In-memory cache
                self.cache_client.set(key, events, self.ttl_config['liquidation_events'])
                
        except Exception as e:
            self.logger.error(f"Error caching liquidation events: {e}")
    
    def get_market_stress(self, symbols: List[str], exchanges: List[str]) -> Optional[MarketStressIndicator]:
        """Get cached market stress indicator."""
        try:
            key = self._generate_key('stress', {
                'symbols': symbols,
                'exchanges': exchanges
            })
            
            if self.cache_type == "redis":
                data = self.cache_client.get(key)
                if data:
                    return MarketStressIndicator(**json.loads(data))
                    
            elif self.cache_type == "memcached":
                data = self.cache_client.get(key)
                if data:
                    return MarketStressIndicator(**json.loads(data))
            
            else:
                return self.cache_client.get(key)
                
        except Exception as e:
            self.logger.error(f"Error getting cached market stress: {e}")
        
        return None
    
    def set_market_stress(self, symbols: List[str], exchanges: List[str], 
                         stress: MarketStressIndicator):
        """Cache market stress indicator."""
        try:
            key = self._generate_key('stress', {
                'symbols': symbols,
                'exchanges': exchanges
            })
            
            if self.cache_type == "redis":
                self.cache_client.setex(
                    key,
                    self.ttl_config['market_stress'],
                    json.dumps(stress.dict())
                )
                
            elif self.cache_type == "memcached":
                self.cache_client.set(
                    key,
                    json.dumps(stress.dict()),
                    time=self.ttl_config['market_stress']
                )
            
            else:
                self.cache_client.set(key, stress, self.ttl_config['market_stress'])
                
        except Exception as e:
            self.logger.error(f"Error caching market stress: {e}")
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all cache entries matching pattern."""
        try:
            if self.cache_type == "redis":
                keys = self.cache_client.keys(f"liquidation:{pattern}:*")
                if keys:
                    self.cache_client.delete(*keys)
                    
            elif self.cache_type == "memcached":
                # Memcached doesn't support pattern deletion
                self.logger.warning("Pattern invalidation not supported in Memcached")
                
            else:
                self.cache_client.invalidate_pattern(pattern)
                
        except Exception as e:
            self.logger.error(f"Error invalidating cache pattern {pattern}: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        try:
            if self.cache_type == "redis":
                info = self.cache_client.info('stats')
                return {
                    'hits': info.get('keyspace_hits', 0),
                    'misses': info.get('keyspace_misses', 0),
                    'memory_used': info.get('used_memory_human', 'N/A'),
                    'connected_clients': info.get('connected_clients', 0)
                }
                
            elif self.cache_type == "memcached":
                stats = self.cache_client.get_stats()
                if stats:
                    server_stats = list(stats[0][1].values())[0]
                    return {
                        'hits': int(server_stats.get(b'get_hits', 0)),
                        'misses': int(server_stats.get(b'get_misses', 0)),
                        'memory_used': server_stats.get(b'bytes', 0),
                        'current_items': int(server_stats.get(b'curr_items', 0))
                    }
                    
            else:
                return self.cache_client.get_stats()
                
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            
        return {}


class InMemoryCache:
    """Fallback in-memory cache implementation."""
    
    def __init__(self):
        self.cache = {}
        self.expiry = {}
        self.stats = {'hits': 0, 'misses': 0}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self.cache:
            if self.expiry[key] > time.time():
                self.stats['hits'] += 1
                return self.cache[key]
            else:
                del self.cache[key]
                del self.expiry[key]
        
        self.stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: int):
        """Set value in cache with TTL."""
        self.cache[key] = value
        self.expiry[key] = time.time() + ttl
    
    def delete(self, key: str):
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
            del self.expiry[key]
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate keys matching pattern."""
        keys_to_delete = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_delete:
            self.delete(key)
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'items': len(self.cache),
            'hit_rate': self.stats['hits'] / max(self.stats['hits'] + self.stats['misses'], 1)
        }

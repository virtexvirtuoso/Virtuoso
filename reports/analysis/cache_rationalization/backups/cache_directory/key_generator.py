"""
Standardized Cache Key Generator
Provides consistent, structured cache key naming for optimal performance and debugging.
"""

import hashlib
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

class CacheKeyGenerator:
    """Standardized cache key generation with consistent naming patterns"""
    
    # Cache key prefixes for different data types
    PREFIXES = {
        'dashboard': 'dashboard',
        'mobile': 'mobile',
        'confluence': 'confluence', 
        'market': 'market',
        'alerts': 'alerts',
        'symbols': 'symbols',
        'performance': 'performance',
        'websocket': 'ws',
        'beta': 'beta',
        'correlation': 'correlation'
    }
    
    # Version markers for cache invalidation
    VERSIONS = {
        'dashboard': 'v2',
        'mobile': 'v1', 
        'confluence': 'v1',
        'market': 'v1',
        'alerts': 'v1',
        'symbols': 'v1',
        'performance': 'v1',
        'beta': 'v1'
    }
    
    @staticmethod
    def dashboard_data(timestamp: Optional[int] = None) -> str:
        """Generate key for main dashboard data with time buckets"""
        ts = timestamp or int(time.time() // 30)  # 30s buckets
        return f"{CacheKeyGenerator.PREFIXES['dashboard']}:data:{CacheKeyGenerator.VERSIONS['dashboard']}:{ts}"
    
    @staticmethod
    def mobile_data(symbols: List[str]) -> str:
        """Generate key for mobile dashboard data based on symbol list"""
        symbol_hash = hashlib.md5(":".join(sorted(symbols)).encode()).hexdigest()[:8]
        return f"{CacheKeyGenerator.PREFIXES['mobile']}:data:{CacheKeyGenerator.VERSIONS['mobile']}:{symbol_hash}"
    
    @staticmethod
    def mobile_overview() -> str:
        """Generate key for mobile market overview data"""
        ts = int(time.time() // 45)  # 45s buckets for mobile (longer TTL)
        return f"{CacheKeyGenerator.PREFIXES['mobile']}:overview:{CacheKeyGenerator.VERSIONS['mobile']}:{ts}"
    
    @staticmethod
    def confluence_scores(symbol: str, timeframe: str = "1m") -> str:
        """Generate key for confluence scores"""
        return f"{CacheKeyGenerator.PREFIXES['confluence']}:{symbol.upper()}:{timeframe}:{CacheKeyGenerator.VERSIONS['confluence']}"
    
    @staticmethod
    def confluence_analysis(symbol: str) -> str:
        """Generate key for detailed confluence analysis"""
        return f"{CacheKeyGenerator.PREFIXES['confluence']}:analysis:{symbol.upper()}:{CacheKeyGenerator.VERSIONS['confluence']}"
    
    @staticmethod
    def market_data(symbol: str = "all") -> str:
        """Generate key for market data"""
        ts = int(time.time() // 60)  # 60s buckets for market data
        return f"{CacheKeyGenerator.PREFIXES['market']}:data:{symbol.upper()}:{CacheKeyGenerator.VERSIONS['market']}:{ts}"
    
    @staticmethod
    def market_overview() -> str:
        """Generate key for market overview with regime and volatility"""
        ts = int(time.time() // 60)  # 60s buckets
        return f"{CacheKeyGenerator.PREFIXES['market']}:overview:{CacheKeyGenerator.VERSIONS['market']}:{ts}"
    
    @staticmethod
    def market_breadth() -> str:
        """Generate key for market breadth indicators"""
        ts = int(time.time() // 30)  # 30s buckets
        return f"{CacheKeyGenerator.PREFIXES['market']}:breadth:{CacheKeyGenerator.VERSIONS['market']}:{ts}"
    
    @staticmethod
    def alerts_active() -> str:
        """Generate key for active alerts"""
        ts = int(time.time() // 120)  # 2 minute buckets (alerts change less frequently)
        return f"{CacheKeyGenerator.PREFIXES['alerts']}:active:{CacheKeyGenerator.VERSIONS['alerts']}:{ts}"
    
    @staticmethod
    def alerts_recent(limit: int = 50) -> str:
        """Generate key for recent alerts"""
        ts = int(time.time() // 60)  # 1 minute buckets
        return f"{CacheKeyGenerator.PREFIXES['alerts']}:recent:{limit}:{CacheKeyGenerator.VERSIONS['alerts']}:{ts}"
    
    @staticmethod
    def symbols_data() -> str:
        """Generate key for symbols data"""
        return f"{CacheKeyGenerator.PREFIXES['symbols']}:data:{CacheKeyGenerator.VERSIONS['symbols']}"
    
    @staticmethod
    def symbols_top(limit: int = 20) -> str:
        """Generate key for top symbols"""
        ts = int(time.time() // 300)  # 5 minute buckets (top symbols change slowly)
        return f"{CacheKeyGenerator.PREFIXES['symbols']}:top:{limit}:{CacheKeyGenerator.VERSIONS['symbols']}:{ts}"
    
    @staticmethod
    def bitcoin_beta() -> str:
        """Generate key for Bitcoin beta data"""
        ts = int(time.time() // 300)  # 5 minute buckets
        return f"{CacheKeyGenerator.PREFIXES['beta']}:btc:{CacheKeyGenerator.VERSIONS['beta']}:{ts}"
    
    @staticmethod
    def beta_analysis(symbol: str) -> str:
        """Generate key for beta analysis data"""
        ts = int(time.time() // 300)  # 5 minute buckets
        return f"{CacheKeyGenerator.PREFIXES['beta']}:analysis:{symbol.upper()}:{CacheKeyGenerator.VERSIONS['beta']}:{ts}"
    
    @staticmethod
    def correlation_matrix(symbols: List[str]) -> str:
        """Generate key for correlation matrix"""
        symbol_hash = hashlib.md5(":".join(sorted(symbols)).encode()).hexdigest()[:8]
        ts = int(time.time() // 600)  # 10 minute buckets (correlations change slowly)
        return f"{CacheKeyGenerator.PREFIXES['correlation']}:matrix:{symbol_hash}:{ts}"
    
    @staticmethod
    def performance_metrics() -> str:
        """Generate key for performance metrics"""
        ts = int(time.time() // 30)  # 30s buckets
        return f"{CacheKeyGenerator.PREFIXES['performance']}:metrics:{CacheKeyGenerator.VERSIONS['performance']}:{ts}"
    
    @staticmethod
    def websocket_broadcast(channel: str) -> str:
        """Generate key for WebSocket broadcast data"""
        return f"{CacheKeyGenerator.PREFIXES['websocket']}:broadcast:{channel}"
    
    @staticmethod
    def websocket_subscriptions() -> str:
        """Generate key for WebSocket subscription data"""
        return f"{CacheKeyGenerator.PREFIXES['websocket']}:subscriptions"
    
    @staticmethod
    def batch_key(keys: List[str]) -> str:
        """Generate a batch operation identifier"""
        batch_hash = hashlib.md5(":".join(sorted(keys)).encode()).hexdigest()[:12]
        return f"batch:{batch_hash}:{int(time.time())}"
    
    @staticmethod
    def get_dependencies(key: str) -> List[str]:
        """Get cache keys that depend on this key for invalidation cascades"""
        dependencies = {
            'market:overview': ['dashboard:data', 'mobile:overview'],
            'market:data': ['confluence:scores', 'dashboard:data'],
            'confluence:scores': ['dashboard:data', 'mobile:data'],
            'alerts:active': ['dashboard:data', 'mobile:data'],
            'symbols:data': ['dashboard:data', 'mobile:data', 'confluence:scores']
        }
        
        # Extract base key pattern
        base_key = ":".join(key.split(":")[:2])
        return dependencies.get(base_key, [])
    
    @staticmethod
    def validate_key(key: str) -> bool:
        """Validate cache key format"""
        try:
            parts = key.split(":")
            if len(parts) < 3:
                return False
            
            prefix = parts[0]
            return prefix in CacheKeyGenerator.PREFIXES.values()
        except:
            return False
    
    @classmethod
    def get_ttl_for_key(cls, key: str) -> int:
        """Get appropriate TTL based on cache key pattern"""
        ttl_map = {
            'dashboard:data': 30,
            'mobile:data': 45,
            'mobile:overview': 45,
            'market:overview': 60,
            'market:breadth': 30,
            'confluence:': 30,
            'alerts:active': 120,
            'alerts:recent': 60,
            'symbols:data': 300,
            'symbols:top': 300,
            'beta:': 300,
            'correlation:': 600,
            'performance:': 30,
            'ws:': 10
        }
        
        for pattern, ttl in ttl_map.items():
            if key.startswith(pattern):
                return ttl
        
        return 30  # Default TTL
    
    @staticmethod
    def create_debug_info(key: str) -> Dict[str, Any]:
        """Create debug information for a cache key"""
        parts = key.split(":")
        
        return {
            "key": key,
            "prefix": parts[0] if parts else "unknown",
            "type": parts[1] if len(parts) > 1 else "unknown", 
            "version": parts[2] if len(parts) > 2 else "unknown",
            "timestamp_bucket": parts[-1] if parts and parts[-1].isdigit() else None,
            "dependencies": CacheKeyGenerator.get_dependencies(key),
            "recommended_ttl": CacheKeyGenerator.get_ttl_for_key(key),
            "is_valid": CacheKeyGenerator.validate_key(key)
        }
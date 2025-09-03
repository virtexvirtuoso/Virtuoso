"""
Hierarchical TTL Strategy
Optimized TTL management based on data dependencies and update frequencies.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DataType(Enum):
    """Data type classifications for TTL optimization"""
    MARKET_DATA = "market_data"           # Foundation data from exchanges
    DERIVED_METRICS = "derived_metrics"   # Calculated from market data
    CONFLUENCE_SCORES = "confluence"      # Highest frequency analysis
    UI_COMPONENTS = "ui_components"       # Most volatile display data
    ALERTS = "alerts"                     # Event-driven notifications
    PERFORMANCE = "performance"           # System metrics
    CONFIGURATION = "configuration"       # Rarely changing settings

class UpdateFrequency(Enum):
    """Update frequency classifications"""
    REAL_TIME = "real_time"      # < 10 seconds
    HIGH = "high"                # 10-60 seconds  
    MEDIUM = "medium"            # 1-5 minutes
    LOW = "low"                  # 5-30 minutes
    STATIC = "static"            # Hours/days

@dataclass
class TTLConfig:
    """TTL configuration for a specific data type"""
    base_ttl: int
    min_ttl: int
    max_ttl: int
    dependency_bonus: int
    frequency_multiplier: float
    invalidation_cascade: bool

class TTLStrategy:
    """Hierarchical TTL management based on data dependencies"""
    
    # Base TTL configurations
    BASE_CONFIGS = {
        DataType.MARKET_DATA: TTLConfig(
            base_ttl=60,
            min_ttl=30,
            max_ttl=300,
            dependency_bonus=15,
            frequency_multiplier=1.0,
            invalidation_cascade=True
        ),
        DataType.DERIVED_METRICS: TTLConfig(
            base_ttl=45,
            min_ttl=20,
            max_ttl=180,
            dependency_bonus=10,
            frequency_multiplier=0.8,
            invalidation_cascade=True
        ),
        DataType.CONFLUENCE_SCORES: TTLConfig(
            base_ttl=30,
            min_ttl=10,
            max_ttl=120,
            dependency_bonus=5,
            frequency_multiplier=0.6,
            invalidation_cascade=False
        ),
        DataType.UI_COMPONENTS: TTLConfig(
            base_ttl=20,
            min_ttl=5,
            max_ttl=60,
            dependency_bonus=0,
            frequency_multiplier=0.5,
            invalidation_cascade=False
        ),
        DataType.ALERTS: TTLConfig(
            base_ttl=120,
            min_ttl=60,
            max_ttl=600,
            dependency_bonus=30,
            frequency_multiplier=2.0,
            invalidation_cascade=True
        ),
        DataType.PERFORMANCE: TTLConfig(
            base_ttl=30,
            min_ttl=10,
            max_ttl=120,
            dependency_bonus=0,
            frequency_multiplier=1.0,
            invalidation_cascade=False
        ),
        DataType.CONFIGURATION: TTLConfig(
            base_ttl=3600,
            min_ttl=300,
            max_ttl=86400,
            dependency_bonus=300,
            frequency_multiplier=10.0,
            invalidation_cascade=True
        )
    }
    
    # Data dependency hierarchy
    DEPENDENCY_GRAPH = {
        DataType.MARKET_DATA: [DataType.DERIVED_METRICS, DataType.CONFLUENCE_SCORES],
        DataType.DERIVED_METRICS: [DataType.CONFLUENCE_SCORES, DataType.UI_COMPONENTS],
        DataType.CONFLUENCE_SCORES: [DataType.UI_COMPONENTS],
        DataType.ALERTS: [DataType.UI_COMPONENTS],
        DataType.PERFORMANCE: [],
        DataType.CONFIGURATION: [DataType.MARKET_DATA, DataType.DERIVED_METRICS]
    }
    
    # Key pattern mappings
    KEY_PATTERNS = {
        'market:': DataType.MARKET_DATA,
        'dashboard:data': DataType.DERIVED_METRICS,
        'mobile:overview': DataType.DERIVED_METRICS,
        'confluence:': DataType.CONFLUENCE_SCORES,
        'mobile:data': DataType.UI_COMPONENTS,
        'dashboard:mobile': DataType.UI_COMPONENTS,
        'alerts:': DataType.ALERTS,
        'performance:': DataType.PERFORMANCE,
        'config:': DataType.CONFIGURATION,
        'symbols:': DataType.DERIVED_METRICS,
        'beta:': DataType.DERIVED_METRICS,
        'correlation:': DataType.DERIVED_METRICS
    }
    
    def __init__(self):
        self.access_patterns = {}  # Track access frequency (public attribute for compatibility)
        self._access_patterns = self.access_patterns  # Backward compatibility
        self._invalidation_history = {}  # Track invalidation patterns
        self._performance_metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'ttl_adjustments': 0,
            'dependency_invalidations': 0
        }
    
    def get_ttl(self, key: str, dependency_level: int = 0, access_frequency: Optional[UpdateFrequency] = None) -> int:
        """Calculate optimal TTL for a cache key"""
        try:
            # Determine data type from key pattern
            data_type = self._classify_key(key)
            
            # Get base configuration
            config = self.BASE_CONFIGS.get(data_type, self.BASE_CONFIGS[DataType.DERIVED_METRICS])
            
            # Start with base TTL
            ttl = config.base_ttl
            
            # Apply dependency bonus (deeper dependencies live longer)
            ttl += dependency_level * config.dependency_bonus
            
            # Apply frequency adjustment
            if access_frequency:
                ttl = int(ttl * self._get_frequency_multiplier(access_frequency, config))
            
            # Apply access pattern optimization
            ttl = self._apply_access_pattern_optimization(key, ttl)
            
            # Apply bounds
            ttl = max(config.min_ttl, min(config.max_ttl, ttl))
            
            logger.debug(f"TTL for {key}: {ttl}s (base: {config.base_ttl}, deps: {dependency_level})")
            
            return ttl
            
        except Exception as e:
            logger.error(f"Error calculating TTL for {key}: {e}")
            return 30  # Safe default
    
    def _classify_key(self, key: str) -> DataType:
        """Classify cache key by data type"""
        for pattern, data_type in self.KEY_PATTERNS.items():
            if key.startswith(pattern):
                return data_type
        
        # Default classification
        return DataType.DERIVED_METRICS
    
    def _get_frequency_multiplier(self, frequency: UpdateFrequency, config: TTLConfig) -> float:
        """Get frequency multiplier for TTL adjustment"""
        multipliers = {
            UpdateFrequency.REAL_TIME: 0.5,
            UpdateFrequency.HIGH: 0.8,
            UpdateFrequency.MEDIUM: 1.0,
            UpdateFrequency.LOW: 1.5,
            UpdateFrequency.STATIC: 3.0
        }
        
        base_multiplier = multipliers.get(frequency, 1.0)
        return base_multiplier * config.frequency_multiplier
    
    def _apply_access_pattern_optimization(self, key: str, base_ttl: int) -> int:
        """Optimize TTL based on observed access patterns"""
        pattern = self._access_patterns.get(key, {})
        
        # If we have access history, optimize TTL
        if pattern:
            avg_access_interval = pattern.get('avg_interval', base_ttl)
            hit_rate = pattern.get('hit_rate', 0.5)
            
            # Adjust TTL based on access patterns
            if hit_rate > 0.8 and avg_access_interval < base_ttl:
                # High hit rate with frequent access - reduce TTL slightly
                return int(base_ttl * 0.8)
            elif hit_rate < 0.3:
                # Low hit rate - increase TTL to reduce cache churn
                return int(base_ttl * 1.5)
        
        return base_ttl
    
    def record_access(self, key: str, hit: bool):
        """Record access pattern for TTL optimization"""
        current_time = time.time()
        
        if key not in self._access_patterns:
            self._access_patterns[key] = {
                'last_access': current_time,
                'access_count': 0,
                'hit_count': 0,
                'total_interval': 0,
                'avg_interval': 30,
                'hit_rate': 0.5
            }
        
        pattern = self._access_patterns[key]
        
        # Update access statistics
        interval = current_time - pattern['last_access']
        pattern['total_interval'] += interval
        pattern['access_count'] += 1
        
        if hit:
            pattern['hit_count'] += 1
        
        # Update averages
        pattern['avg_interval'] = pattern['total_interval'] / pattern['access_count']
        pattern['hit_rate'] = pattern['hit_count'] / pattern['access_count']
        pattern['last_access'] = current_time
        
        # Update global metrics
        if hit:
            self._performance_metrics['cache_hits'] += 1
        else:
            self._performance_metrics['cache_misses'] += 1
    
    def get_dependent_keys(self, key: str) -> List[str]:
        """Get all keys that depend on this key for cascade invalidation"""
        data_type = self._classify_key(key)
        config = self.BASE_CONFIGS.get(data_type)
        
        if not config or not config.invalidation_cascade:
            return []
        
        # Get dependent data types
        dependent_types = self.DEPENDENCY_GRAPH.get(data_type, [])
        
        # Map back to key patterns (simplified implementation)
        dependent_patterns = []
        for dep_type in dependent_types:
            for pattern, pattern_type in self.KEY_PATTERNS.items():
                if pattern_type == dep_type:
                    dependent_patterns.append(pattern)
        
        return dependent_patterns
    
    def should_invalidate_cascade(self, key: str) -> bool:
        """Determine if key invalidation should cascade to dependents"""
        data_type = self._classify_key(key)
        config = self.BASE_CONFIGS.get(data_type)
        return config.invalidation_cascade if config else False
    
    def get_warming_priority(self, key: str) -> int:
        """Get cache warming priority (1-10, 10 being highest)"""
        data_type = self._classify_key(key)
        
        priorities = {
            DataType.MARKET_DATA: 10,      # Highest priority
            DataType.DERIVED_METRICS: 8,
            DataType.CONFLUENCE_SCORES: 6,
            DataType.UI_COMPONENTS: 4,
            DataType.ALERTS: 7,
            DataType.PERFORMANCE: 3,
            DataType.CONFIGURATION: 2      # Lowest priority
        }
        
        return priorities.get(data_type, 5)
    
    def optimize_ttl_based_on_performance(self, key: str, current_ttl: int, hit_rate: float) -> int:
        """Dynamically optimize TTL based on performance metrics"""
        data_type = self._classify_key(key)
        config = self.BASE_CONFIGS.get(data_type)
        
        if not config:
            return current_ttl
        
        # Adjust TTL based on hit rate
        if hit_rate > 0.9:
            # Very high hit rate - can afford shorter TTL
            new_ttl = int(current_ttl * 0.8)
        elif hit_rate > 0.7:
            # Good hit rate - slight reduction
            new_ttl = int(current_ttl * 0.9)
        elif hit_rate < 0.3:
            # Poor hit rate - increase TTL
            new_ttl = int(current_ttl * 1.5)
        elif hit_rate < 0.5:
            # Below average - moderate increase
            new_ttl = int(current_ttl * 1.2)
        else:
            new_ttl = current_ttl
        
        # Apply bounds
        new_ttl = max(config.min_ttl, min(config.max_ttl, new_ttl))
        
        if new_ttl != current_ttl:
            self._performance_metrics['ttl_adjustments'] += 1
            logger.debug(f"TTL optimization for {key}: {current_ttl} -> {new_ttl} (hit_rate: {hit_rate:.2f})")
        
        return new_ttl
    
    def get_cache_strategy_summary(self) -> Dict[str, Any]:
        """Get summary of current cache strategy and performance"""
        total_requests = self._performance_metrics['cache_hits'] + self._performance_metrics['cache_misses']
        hit_rate = (self._performance_metrics['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "strategy": "hierarchical_ttl",
            "data_types": len(self.KEY_PATTERNS),
            "dependency_levels": len(self.DEPENDENCY_GRAPH),
            "performance": {
                "overall_hit_rate": round(hit_rate, 2),
                "total_requests": total_requests,
                "ttl_adjustments": self._performance_metrics['ttl_adjustments'],
                "dependency_invalidations": self._performance_metrics['dependency_invalidations']
            },
            "access_patterns_tracked": len(self._access_patterns),
            "configurations": {
                data_type.value: {
                    "base_ttl": config.base_ttl,
                    "min_ttl": config.min_ttl,
                    "max_ttl": config.max_ttl,
                    "cascade_invalidation": config.invalidation_cascade
                }
                for data_type, config in self.BASE_CONFIGS.items()
            }
        }
    
    def reset_metrics(self):
        """Reset performance metrics for fresh tracking"""
        self._performance_metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'ttl_adjustments': 0,
            'dependency_invalidations': 0
        }
        self._access_patterns.clear()
        logger.info("TTL strategy metrics reset")
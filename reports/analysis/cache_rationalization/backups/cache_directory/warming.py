"""
Predictive Cache Warming Service
Proactive cache population based on access patterns and predictable usage cycles.
"""

import asyncio
import logging
import time
import schedule
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

from .key_generator import CacheKeyGenerator
from .batch_operations import BatchCacheManager
from .ttl_strategy import TTLStrategy, DataType

logger = logging.getLogger(__name__)

@dataclass
class AccessPattern:
    """Represents an observed access pattern for cache warming"""
    key: str
    access_times: deque = field(default_factory=lambda: deque(maxlen=100))
    access_frequency: float = 0.0
    peak_hours: Set[int] = field(default_factory=set)
    last_access: float = 0.0
    hit_rate: float = 0.0
    importance_score: float = 0.0

@dataclass
class WarmingTask:
    """Represents a cache warming task"""
    key: str
    data_fetcher: Callable
    priority: int
    schedule_time: float
    ttl: int
    estimated_cost: float = 0.0
    dependencies: List[str] = field(default_factory=list)

class CacheWarmingService:
    """Proactive cache warming for predictable access patterns"""
    
    def __init__(self, cache_adapter, batch_manager: BatchCacheManager, ttl_strategy: TTLStrategy):
        self.cache_adapter = cache_adapter
        self.batch_manager = batch_manager
        self.ttl_strategy = ttl_strategy
        
        # Pattern tracking
        self.access_patterns: Dict[str, AccessPattern] = {}
        self.warming_tasks: List[WarmingTask] = []
        self.warming_history: Dict[str, List[float]] = defaultdict(list)
        
        # Configuration
        self.config = {
            'warming_window': 300,  # Start warming 5 minutes before predicted access
            'min_frequency_threshold': 0.1,  # Minimum access frequency to consider warming
            'max_concurrent_warming': 5,
            'warming_enabled': True,
            'adaptive_scheduling': True,
            'peak_hour_bonus': 2.0,
            'dependency_warming': True
        }
        
        # State
        self._running = False
        self._warming_task: Optional[asyncio.Task] = None
        self._stats = {
            'total_warmed': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'cache_hits_from_warming': 0,
            'warming_efficiency': 0.0,
            'avg_warming_time': 0.0
        }
        
        # Data fetchers registry
        self.data_fetchers: Dict[str, Callable] = {}
        self._register_default_fetchers()
    
    def _register_default_fetchers(self):
        """Register default data fetchers for common cache keys"""
        self.data_fetchers.update({
            'dashboard:data': self._fetch_dashboard_data,
            'mobile:overview': self._fetch_mobile_overview,
            'market:overview': self._fetch_market_overview,
            'confluence:scores': self._fetch_confluence_scores,
            'alerts:active': self._fetch_active_alerts,
            'symbols:top': self._fetch_top_symbols,
            'performance:metrics': self._fetch_performance_metrics
        })
    
    async def start(self):
        """Start the cache warming service"""
        if not self.config['warming_enabled'] or self._running:
            return
        
        self._running = True
        self._warming_task = asyncio.create_task(self._warming_loop())
        
        # Schedule periodic pattern analysis
        schedule.every(10).minutes.do(self._analyze_patterns)
        schedule.every(1).hours.do(self._optimize_warming_schedule)
        
        logger.info("Cache warming service started")
    
    async def stop(self):
        """Stop the cache warming service"""
        self._running = False
        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass
        
        schedule.clear()
        logger.info("Cache warming service stopped")
    
    def record_access(self, key: str, hit: bool, access_time: Optional[float] = None):
        """Record cache access for pattern learning"""
        access_time = access_time or time.time()
        
        if key not in self.access_patterns:
            self.access_patterns[key] = AccessPattern(key=key)
        
        pattern = self.access_patterns[key]
        
        # Record access time
        pattern.access_times.append(access_time)
        pattern.last_access = access_time
        
        # Update hit rate
        if hit:
            pattern.hit_rate = min(1.0, pattern.hit_rate + 0.1)
        else:
            pattern.hit_rate = max(0.0, pattern.hit_rate - 0.05)
        
        # Analyze access frequency
        if len(pattern.access_times) >= 2:
            intervals = [
                pattern.access_times[i] - pattern.access_times[i-1]
                for i in range(1, len(pattern.access_times))
            ]
            pattern.access_frequency = 1.0 / (sum(intervals) / len(intervals)) if intervals else 0.0
        
        # Track peak hours
        hour = datetime.fromtimestamp(access_time).hour
        pattern.peak_hours.add(hour)
        
        # Calculate importance score
        pattern.importance_score = self._calculate_importance_score(pattern)
    
    def _calculate_importance_score(self, pattern: AccessPattern) -> float:
        """Calculate importance score for warming prioritization"""
        score = 0.0
        
        # Frequency component (0-40 points)
        score += min(40, pattern.access_frequency * 100)
        
        # Hit rate component (0-30 points)
        score += pattern.hit_rate * 30
        
        # Peak hour bonus (0-20 points)
        current_hour = datetime.now().hour
        if current_hour in pattern.peak_hours:
            score += 20
        
        # Recency bonus (0-10 points)
        time_since_access = time.time() - pattern.last_access
        recency_score = max(0, 10 - (time_since_access / 3600))  # Decay over 1 hour
        score += recency_score
        
        return score
    
    async def _warming_loop(self):
        """Main warming loop"""
        while self._running:
            try:
                current_time = time.time()
                
                # Find keys that need warming
                warming_candidates = await self._identify_warming_candidates(current_time)
                
                if warming_candidates:
                    await self._execute_warming_batch(warming_candidates)
                
                # Run scheduled tasks
                schedule.run_pending()
                
                # Sleep before next iteration
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in warming loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _identify_warming_candidates(self, current_time: float) -> List[str]:
        """Identify cache keys that should be warmed"""
        candidates = []
        
        for key, pattern in self.access_patterns.items():
            # Skip if recently accessed (already warm)
            if current_time - pattern.last_access < 60:
                continue
            
            # Skip if not important enough
            if pattern.importance_score < 20:
                continue
            
            # Skip if no data fetcher available
            if not self._has_data_fetcher(key):
                continue
            
            # Predict next access time
            predicted_access = self._predict_next_access(pattern, current_time)
            
            if predicted_access and predicted_access - current_time <= self.config['warming_window']:
                candidates.append(key)
        
        # Sort by importance score
        candidates.sort(key=lambda k: self.access_patterns[k].importance_score, reverse=True)
        
        # Limit concurrent warming
        return candidates[:self.config['max_concurrent_warming']]
    
    def _predict_next_access(self, pattern: AccessPattern, current_time: float) -> Optional[float]:
        """Predict next access time based on historical patterns"""
        if len(pattern.access_times) < 3:
            return None
        
        # Simple prediction based on average interval
        intervals = [
            pattern.access_times[i] - pattern.access_times[i-1]
            for i in range(1, len(pattern.access_times))
        ]
        
        avg_interval = sum(intervals) / len(intervals)
        predicted_time = pattern.last_access + avg_interval
        
        # Adjust for peak hours
        if self.config['adaptive_scheduling']:
            predicted_hour = datetime.fromtimestamp(predicted_time).hour
            if predicted_hour in pattern.peak_hours:
                predicted_time -= 300  # Warm 5 minutes earlier during peak hours
        
        return predicted_time
    
    async def _execute_warming_batch(self, keys: List[str]):
        """Execute warming for a batch of cache keys"""
        start_time = time.time()
        warming_tasks = []
        
        for key in keys:
            if self._has_data_fetcher(key):
                task = self._warm_single_key(key)
                warming_tasks.append((key, task))
        
        if not warming_tasks:
            return
        
        # Execute warming tasks in parallel
        results = await asyncio.gather(
            *[task for _, task in warming_tasks],
            return_exceptions=True
        )
        
        # Process results
        successful_warms = 0
        for i, (key, _) in enumerate(warming_tasks):
            result = results[i]
            
            if isinstance(result, Exception):
                logger.warning(f"Failed to warm {key}: {result}")
                self._stats['failed_predictions'] += 1
            else:
                successful_warms += 1
                self._stats['successful_predictions'] += 1
                self.warming_history[key].append(time.time())
        
        # Update statistics
        execution_time = (time.time() - start_time) * 1000
        self._stats['total_warmed'] += len(keys)
        
        current_avg = self._stats['avg_warming_time']
        total_batches = len(self.warming_history.get('_batch_times', []))
        self._stats['avg_warming_time'] = ((current_avg * total_batches) + execution_time) / (total_batches + 1)
        
        if successful_warms > 0:
            logger.info(f"Cache warming completed: {successful_warms}/{len(keys)} keys in {execution_time:.2f}ms")
    
    async def _warm_single_key(self, key: str) -> bool:
        """Warm a single cache key"""
        try:
            # Get data fetcher
            fetcher = self._get_data_fetcher(key)
            if not fetcher:
                return False
            
            # Fetch data
            data = await fetcher()
            if data is None:
                return False
            
            # Calculate TTL
            ttl = self.ttl_strategy.get_ttl(key)
            
            # Cache the data
            success = await self.cache_adapter.set(key, data, ttl)
            
            if success:
                logger.debug(f"Successfully warmed cache key: {key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error warming key {key}: {e}")
            return False
    
    def _has_data_fetcher(self, key: str) -> bool:
        """Check if we have a data fetcher for this key"""
        for pattern in self.data_fetchers.keys():
            if key.startswith(pattern):
                return True
        return False
    
    def _get_data_fetcher(self, key: str) -> Optional[Callable]:
        """Get data fetcher for a cache key"""
        for pattern, fetcher in self.data_fetchers.items():
            if key.startswith(pattern):
                return fetcher
        return None
    
    # Default data fetchers
    async def _fetch_dashboard_data(self) -> Dict[str, Any]:
        """Fetch dashboard data"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8004/api/dashboard-cached/signals', timeout=3) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.debug(f"Failed to fetch dashboard data: {e}")
        return None
    
    async def _fetch_mobile_overview(self) -> Dict[str, Any]:
        """Fetch mobile overview data"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8004/api/dashboard-cached/market-overview', timeout=2) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.debug(f"Failed to fetch mobile overview: {e}")
        return None
    
    async def _fetch_market_overview(self) -> Dict[str, Any]:
        """Fetch market overview data"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8004/api/dashboard-cached/market-overview', timeout=2) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.debug(f"Failed to fetch market overview: {e}")
        return None
    
    async def _fetch_confluence_scores(self) -> Dict[str, Any]:
        """Fetch confluence scores"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8004/api/dashboard-cached/confluence-scores', timeout=3) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.debug(f"Failed to fetch confluence scores: {e}")
        return None
    
    async def _fetch_active_alerts(self) -> Dict[str, Any]:
        """Fetch active alerts"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8001/api/monitoring/alerts', timeout=1.5) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.debug(f"Failed to fetch alerts: {e}")
        return None
    
    async def _fetch_top_symbols(self) -> Dict[str, Any]:
        """Fetch top symbols"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8004/api/symbols/top', timeout=2) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.debug(f"Failed to fetch top symbols: {e}")
        return None
    
    async def _fetch_performance_metrics(self) -> Dict[str, Any]:
        """Fetch performance metrics"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8001/api/monitoring/performance', timeout=1) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.debug(f"Failed to fetch performance metrics: {e}")
        return None
    
    def register_data_fetcher(self, key_pattern: str, fetcher: Callable):
        """Register a custom data fetcher for a key pattern"""
        self.data_fetchers[key_pattern] = fetcher
        logger.info(f"Registered data fetcher for pattern: {key_pattern}")
    
    def _analyze_patterns(self):
        """Analyze access patterns for optimization"""
        logger.info("Analyzing cache access patterns")
        
        patterns_analyzed = 0
        for key, pattern in self.access_patterns.items():
            # Update importance scores
            pattern.importance_score = self._calculate_importance_score(pattern)
            
            # Clean old access times
            cutoff_time = time.time() - 86400  # 24 hours
            pattern.access_times = deque([
                t for t in pattern.access_times if t > cutoff_time
            ], maxlen=100)
            
            patterns_analyzed += 1
        
        logger.info(f"Analyzed {patterns_analyzed} access patterns")
    
    def _optimize_warming_schedule(self):
        """Optimize warming schedule based on performance"""
        logger.info("Optimizing warming schedule")
        
        # Calculate warming efficiency
        total_predictions = self._stats['successful_predictions'] + self._stats['failed_predictions']
        if total_predictions > 0:
            efficiency = (self._stats['successful_predictions'] / total_predictions) * 100
            self._stats['warming_efficiency'] = efficiency
            
            # Adjust warming window based on efficiency
            if efficiency > 80:
                self.config['warming_window'] = max(180, self.config['warming_window'] - 30)
            elif efficiency < 50:
                self.config['warming_window'] = min(600, self.config['warming_window'] + 60)
        
        logger.info(f"Warming efficiency: {self._stats['warming_efficiency']:.1f}%")
    
    async def manual_warm(self, keys: List[str]) -> Dict[str, bool]:
        """Manually warm specific cache keys"""
        results = {}
        
        for key in keys:
            try:
                success = await self._warm_single_key(key)
                results[key] = success
                
                if success:
                    self._stats['total_warmed'] += 1
                    
            except Exception as e:
                logger.error(f"Manual warming failed for {key}: {e}")
                results[key] = False
        
        return results
    
    async def warm_critical_paths(self) -> Dict[str, bool]:
        """Warm cache for critical application paths"""
        critical_keys = [
            CacheKeyGenerator.dashboard_data(),
            CacheKeyGenerator.mobile_overview(),
            CacheKeyGenerator.market_overview(),
            CacheKeyGenerator.confluence_scores('all'),
            CacheKeyGenerator.alerts_active()
        ]
        
        logger.info("Warming critical cache paths")
        return await self.manual_warm(critical_keys)
    
    def get_warming_stats(self) -> Dict[str, Any]:
        """Get cache warming statistics"""
        return {
            'service': 'cache_warming',
            'status': 'running' if self._running else 'stopped',
            'statistics': self._stats,
            'configuration': self.config,
            'patterns_tracked': len(self.access_patterns),
            'data_fetchers_registered': len(self.data_fetchers),
            'top_patterns': [
                {
                    'key': pattern.key,
                    'importance_score': pattern.importance_score,
                    'access_frequency': pattern.access_frequency,
                    'hit_rate': pattern.hit_rate,
                    'peak_hours': list(pattern.peak_hours)
                }
                for pattern in sorted(self.access_patterns.values(), 
                                   key=lambda p: p.importance_score, reverse=True)[:10]
            ]
        }
    
    def update_config(self, config_updates: Dict[str, Any]) -> bool:
        """Update warming configuration"""
        try:
            for key, value in config_updates.items():
                if key in self.config:
                    self.config[key] = value
                    logger.info(f"Updated warming config: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Failed to update warming config: {e}")
            return False
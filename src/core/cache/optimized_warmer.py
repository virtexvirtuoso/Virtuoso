from src.utils.task_tracker import create_tracked_task
"""
Optimized Cache Warming Strategy
Phase 1 Performance Excellence - Intelligent Cache Warming

Implements market-aware, priority-based cache warming with
predictive preloading and adaptive scheduling.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import json
import logging
from enum import Enum
from collections import defaultdict
import heapq

logger = logging.getLogger(__name__)


class MarketSession(Enum):
    """Market session classifications"""
    MARKET_HOURS = "market_hours"          # 9:30 AM - 4:00 PM ET
    PRE_MARKET = "pre_market"              # 4:00 AM - 9:30 AM ET
    AFTER_HOURS = "after_hours"            # 4:00 PM - 8:00 PM ET
    OVERNIGHT = "overnight"                # 8:00 PM - 4:00 AM ET
    WEEKEND = "weekend"                    # Saturday - Sunday


class DataPriority(Enum):
    """Cache warming priority levels"""
    CRITICAL = 1    # Real-time trading data
    HIGH = 2        # Active symbol data
    MEDIUM = 3      # Secondary indicators
    LOW = 4         # Historical data
    BACKGROUND = 5  # Precomputed analytics


@dataclass
class WarmingTask:
    """Individual cache warming task"""
    key: str
    priority: DataPriority
    fetch_function: callable
    params: Dict[str, Any]
    ttl_seconds: int
    last_warmed: Optional[datetime] = None
    warm_count: int = 0
    avg_fetch_time_ms: float = 0.0
    error_count: int = 0

    def __lt__(self, other):
        """For priority queue comparison"""
        return self.priority.value < other.priority.value


@dataclass
class WarmingStrategy:
    """Market-specific warming strategy"""
    session: MarketSession
    refresh_interval_seconds: int
    priority_threshold: DataPriority
    concurrent_warmers: int
    batch_size: int


class OptimizedCacheWarmer:
    """Advanced cache warming with predictive and adaptive strategies"""

    def __init__(self, cache_adapter):
        self.cache_adapter = cache_adapter
        self.warming_tasks: List[WarmingTask] = []
        self.task_registry: Dict[str, WarmingTask] = {}
        self.warming_queue = []
        self.is_warming = False
        self._warming_task = None

        # Performance tracking
        self.warming_metrics = {
            "total_warmed": 0,
            "total_errors": 0,
            "avg_warming_time_ms": 0.0,
            "cache_fill_rate": 0.0,
            "last_warming_cycle": None,
        }

        # Access pattern tracking for predictive warming
        self.access_patterns = defaultdict(lambda: {"count": 0, "times": []})
        self.predicted_keys: Set[str] = set()

        # Market-aware strategies
        self.strategies = {
            MarketSession.MARKET_HOURS: WarmingStrategy(
                session=MarketSession.MARKET_HOURS,
                refresh_interval_seconds=15,
                priority_threshold=DataPriority.HIGH,
                concurrent_warmers=10,
                batch_size=50
            ),
            MarketSession.PRE_MARKET: WarmingStrategy(
                session=MarketSession.PRE_MARKET,
                refresh_interval_seconds=30,
                priority_threshold=DataPriority.HIGH,
                concurrent_warmers=5,
                batch_size=25
            ),
            MarketSession.AFTER_HOURS: WarmingStrategy(
                session=MarketSession.AFTER_HOURS,
                refresh_interval_seconds=60,
                priority_threshold=DataPriority.MEDIUM,
                concurrent_warmers=3,
                batch_size=15
            ),
            MarketSession.OVERNIGHT: WarmingStrategy(
                session=MarketSession.OVERNIGHT,
                refresh_interval_seconds=300,
                priority_threshold=DataPriority.LOW,
                concurrent_warmers=2,
                batch_size=10
            ),
            MarketSession.WEEKEND: WarmingStrategy(
                session=MarketSession.WEEKEND,
                refresh_interval_seconds=600,
                priority_threshold=DataPriority.BACKGROUND,
                concurrent_warmers=1,
                batch_size=5
            ),
        }

    def register_warming_task(
        self,
        key: str,
        fetch_function: callable,
        params: Dict[str, Any] = None,
        priority: DataPriority = DataPriority.MEDIUM,
        ttl_seconds: int = 60
    ):
        """Register a new cache warming task"""
        task = WarmingTask(
            key=key,
            priority=priority,
            fetch_function=fetch_function,
            params=params or {},
            ttl_seconds=ttl_seconds
        )

        self.task_registry[key] = task
        heapq.heappush(self.warming_queue, task)

        logger.info(f"Registered warming task: {key} with priority {priority.name}")

    def track_access(self, key: str):
        """Track cache access patterns for predictive warming"""
        current_time = datetime.utcnow()
        pattern = self.access_patterns[key]
        pattern["count"] += 1
        pattern["times"].append(current_time)

        # Keep only last 100 access times
        if len(pattern["times"]) > 100:
            pattern["times"] = pattern["times"][-100:]

        # Predict if this key will be accessed soon
        if pattern["count"] > 10:  # Accessed frequently
            self.predicted_keys.add(key)

    async def start_warming(self):
        """Start the cache warming process"""
        if self.is_warming:
            return

        self.is_warming = True
        self._warming_task = create_tracked_task(self._warming_loop(), name="auto_tracked_task")
        logger.info("Optimized cache warming started")

    async def stop_warming(self):
        """Stop the cache warming process"""
        self.is_warming = False
        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass
            self._warming_task = None
        logger.info("Cache warming stopped")

    async def _warming_loop(self):
        """Main warming loop with adaptive scheduling"""
        while self.is_warming:
            try:
                session = self._get_current_session()
                strategy = self.strategies[session]

                logger.info(f"Starting warming cycle for {session.name} session")

                # Warm caches based on current strategy
                await self._execute_warming_cycle(strategy)

                # Update metrics
                self.warming_metrics["last_warming_cycle"] = datetime.utcnow()

                # Adaptive sleep based on market session
                await asyncio.sleep(strategy.refresh_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in warming loop: {e}")
                await asyncio.sleep(30)  # Error recovery delay

    async def _execute_warming_cycle(self, strategy: WarmingStrategy):
        """Execute a single warming cycle with given strategy"""
        start_time = time.perf_counter()
        warmed_count = 0
        error_count = 0

        # Get tasks that need warming based on priority and TTL
        tasks_to_warm = self._get_tasks_to_warm(strategy)

        if not tasks_to_warm:
            logger.debug("No tasks to warm in this cycle")
            return

        # Warm in batches with concurrency control
        for batch_start in range(0, len(tasks_to_warm), strategy.batch_size):
            batch = tasks_to_warm[batch_start:batch_start + strategy.batch_size]

            # Create concurrent warming tasks
            warming_coroutines = [
                self._warm_single_cache(task)
                for task in batch
            ]

            # Execute with concurrency limit
            semaphore = asyncio.Semaphore(strategy.concurrent_warmers)
            async def limited_warm(coro):
                async with semaphore:
                    return await coro

            results = await asyncio.gather(
                *[limited_warm(coro) for coro in warming_coroutines],
                return_exceptions=True
            )

            # Process results
            for task, result in zip(batch, results):
                if isinstance(result, Exception):
                    error_count += 1
                    task.error_count += 1
                    logger.error(f"Failed to warm {task.key}: {result}")
                else:
                    warmed_count += 1
                    task.warm_count += 1
                    task.last_warmed = datetime.utcnow()

        # Update metrics
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.warming_metrics["total_warmed"] += warmed_count
        self.warming_metrics["total_errors"] += error_count

        # Update rolling average
        prev_avg = self.warming_metrics["avg_warming_time_ms"]
        self.warming_metrics["avg_warming_time_ms"] = (
            (prev_avg * 0.9) + (elapsed_ms * 0.1)  # Exponential moving average
        )

        fill_rate = (warmed_count / (warmed_count + error_count)) * 100 if (warmed_count + error_count) > 0 else 0
        self.warming_metrics["cache_fill_rate"] = fill_rate

        logger.info(
            f"Warming cycle complete: {warmed_count} warmed, {error_count} errors, "
            f"{elapsed_ms:.2f}ms, fill rate: {fill_rate:.1f}%"
        )

    async def _warm_single_cache(self, task: WarmingTask):
        """Warm a single cache entry"""
        start_time = time.perf_counter()

        try:
            # Fetch the data
            if asyncio.iscoroutinefunction(task.fetch_function):
                data = await task.fetch_function(**task.params)
            else:
                data = task.fetch_function(**task.params)

            # Store in cache with TTL
            await self.cache_adapter.set_async(task.key, data, ttl=task.ttl_seconds)

            # Update task metrics
            fetch_time_ms = (time.perf_counter() - start_time) * 1000
            task.avg_fetch_time_ms = (
                (task.avg_fetch_time_ms * 0.9) + (fetch_time_ms * 0.1)
            )

            logger.debug(f"Warmed {task.key} in {fetch_time_ms:.2f}ms")
            return True

        except Exception as e:
            logger.error(f"Error warming {task.key}: {e}")
            raise

    def _get_tasks_to_warm(self, strategy: WarmingStrategy) -> List[WarmingTask]:
        """Get tasks that need warming based on strategy"""
        current_time = datetime.utcnow()
        tasks_to_warm = []

        for task in self.task_registry.values():
            # Check priority threshold
            if task.priority.value > strategy.priority_threshold.value:
                continue

            # Check if needs warming based on TTL
            needs_warming = False

            if task.last_warmed is None:
                needs_warming = True  # Never warmed
            else:
                age_seconds = (current_time - task.last_warmed).total_seconds()
                if age_seconds >= task.ttl_seconds * 0.8:  # Warm at 80% of TTL
                    needs_warming = True

            # Check if key is predicted to be accessed soon
            if task.key in self.predicted_keys:
                needs_warming = True
                self.predicted_keys.discard(task.key)  # Remove after warming

            if needs_warming:
                tasks_to_warm.append(task)

        # Sort by priority and error count (prioritize successful tasks)
        tasks_to_warm.sort(key=lambda t: (t.priority.value, t.error_count))

        return tasks_to_warm

    def _get_current_session(self) -> MarketSession:
        """Determine current market session"""
        now = datetime.now(timezone.utc)

        # Convert to ET (US Eastern Time)
        et_offset = -5 if now.month not in [3, 4, 5, 6, 7, 8, 9, 10] else -4  # Rough DST calculation
        et_hour = (now.hour + et_offset) % 24
        weekday = now.weekday()

        # Weekend check
        if weekday >= 5:  # Saturday = 5, Sunday = 6
            return MarketSession.WEEKEND

        # Weekday sessions
        if 4 <= et_hour < 9.5:
            return MarketSession.PRE_MARKET
        elif 9.5 <= et_hour < 16:
            return MarketSession.MARKET_HOURS
        elif 16 <= et_hour < 20:
            return MarketSession.AFTER_HOURS
        else:
            return MarketSession.OVERNIGHT

    async def warm_critical_data(self):
        """Immediately warm critical data (manual trigger)"""
        logger.info("Manual critical data warming triggered")

        critical_tasks = [
            task for task in self.task_registry.values()
            if task.priority == DataPriority.CRITICAL
        ]

        if not critical_tasks:
            logger.warning("No critical tasks registered for warming")
            return

        # Warm all critical tasks immediately
        results = await asyncio.gather(
            *[self._warm_single_cache(task) for task in critical_tasks],
            return_exceptions=True
        )

        success_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Critical warming complete: {success_count}/{len(critical_tasks)} successful")

    def get_warming_stats(self) -> Dict[str, Any]:
        """Get comprehensive warming statistics"""
        session = self._get_current_session()
        strategy = self.strategies[session]

        task_stats = []
        for task in self.task_registry.values():
            age = "never"
            if task.last_warmed:
                age_seconds = (datetime.utcnow() - task.last_warmed).total_seconds()
                age = f"{age_seconds:.0f}s"

            task_stats.append({
                "key": task.key,
                "priority": task.priority.name,
                "warm_count": task.warm_count,
                "error_count": task.error_count,
                "avg_fetch_ms": task.avg_fetch_time_ms,
                "age": age,
                "ttl": task.ttl_seconds,
            })

        return {
            "current_session": session.name,
            "refresh_interval": strategy.refresh_interval_seconds,
            "metrics": self.warming_metrics,
            "total_tasks": len(self.task_registry),
            "task_stats": sorted(task_stats, key=lambda x: x["priority"]),
            "predicted_keys_count": len(self.predicted_keys),
        }

    async def optimize_warming_pattern(self):
        """Analyze access patterns and optimize warming schedule"""
        logger.info("Analyzing access patterns for optimization")

        # Analyze each key's access pattern
        optimizations = []

        for key, pattern in self.access_patterns.items():
            if pattern["count"] < 10:
                continue  # Not enough data

            times = pattern["times"]
            if len(times) < 2:
                continue

            # Calculate average interval between accesses
            intervals = []
            for i in range(1, len(times)):
                interval = (times[i] - times[i-1]).total_seconds()
                intervals.append(interval)

            avg_interval = sum(intervals) / len(intervals) if intervals else 0

            # Suggest optimal TTL and priority
            if key in self.task_registry:
                task = self.task_registry[key]

                # Adjust TTL based on access pattern
                optimal_ttl = min(max(int(avg_interval * 0.8), 15), 600)  # Between 15s and 10min

                # Adjust priority based on frequency
                if pattern["count"] > 100:
                    optimal_priority = DataPriority.CRITICAL
                elif pattern["count"] > 50:
                    optimal_priority = DataPriority.HIGH
                elif pattern["count"] > 20:
                    optimal_priority = DataPriority.MEDIUM
                else:
                    optimal_priority = DataPriority.LOW

                if task.ttl_seconds != optimal_ttl or task.priority != optimal_priority:
                    optimizations.append({
                        "key": key,
                        "current_ttl": task.ttl_seconds,
                        "optimal_ttl": optimal_ttl,
                        "current_priority": task.priority.name,
                        "optimal_priority": optimal_priority.name,
                    })

                    # Apply optimization
                    task.ttl_seconds = optimal_ttl
                    task.priority = optimal_priority

        if optimizations:
            logger.info(f"Applied {len(optimizations)} warming optimizations")
            for opt in optimizations[:5]:  # Log first 5
                logger.info(f"Optimized {opt['key']}: TTL {opt['current_ttl']}→{opt['optimal_ttl']}s")

        return optimizations
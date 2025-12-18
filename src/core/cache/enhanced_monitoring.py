from src.utils.task_tracker import create_tracked_task
"""
Enhanced Multi-Tier Cache Monitoring System
Phase 1 Performance Excellence Implementation
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import json
import statistics
from collections import deque, defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Comprehensive cache metrics tracking"""
    # Hit/Miss Statistics
    total_requests: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    misses: int = 0

    # Latency Tracking (in milliseconds)
    l1_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    l2_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    l3_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    miss_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))

    # Size Metrics
    l1_size_bytes: int = 0
    l2_size_bytes: int = 0
    l3_size_bytes: int = 0
    l1_item_count: int = 0
    l2_item_count: int = 0
    l3_item_count: int = 0

    # Eviction Tracking
    l1_evictions: int = 0
    l2_evictions: int = 0
    l3_evictions: int = 0

    # Error Tracking
    l1_errors: int = 0
    l2_errors: int = 0
    l3_errors: int = 0

    # Time Windows for Analysis
    hourly_stats: deque = field(default_factory=lambda: deque(maxlen=24))
    minute_stats: deque = field(default_factory=lambda: deque(maxlen=60))

    def get_hit_rates(self) -> Dict[str, float]:
        """Calculate hit rates for each cache tier"""
        if self.total_requests == 0:
            return {"l1": 0.0, "l2": 0.0, "l3": 0.0, "overall": 0.0}

        return {
            "l1": (self.l1_hits / self.total_requests) * 100,
            "l2": (self.l2_hits / self.total_requests) * 100,
            "l3": (self.l3_hits / self.total_requests) * 100,
            "overall": ((self.l1_hits + self.l2_hits + self.l3_hits) / self.total_requests) * 100
        }

    def get_avg_latencies(self) -> Dict[str, float]:
        """Calculate average latencies for each tier"""
        return {
            "l1": statistics.mean(self.l1_latencies) if self.l1_latencies else 0.0,
            "l2": statistics.mean(self.l2_latencies) if self.l2_latencies else 0.0,
            "l3": statistics.mean(self.l3_latencies) if self.l3_latencies else 0.0,
            "miss": statistics.mean(self.miss_latencies) if self.miss_latencies else 0.0
        }

    def get_p99_latencies(self) -> Dict[str, float]:
        """Calculate P99 latencies for each tier"""
        def p99(data):
            if not data:
                return 0.0
            sorted_data = sorted(data)
            index = int(len(sorted_data) * 0.99)
            return sorted_data[min(index, len(sorted_data)-1)]

        return {
            "l1": p99(self.l1_latencies),
            "l2": p99(self.l2_latencies),
            "l3": p99(self.l3_latencies),
            "miss": p99(self.miss_latencies)
        }


class EnhancedCacheMonitor:
    """Advanced monitoring for Phase 1 multi-tier cache system"""

    def __init__(self):
        self.metrics = CacheMetrics()
        self.key_access_patterns = defaultdict(int)
        self.hot_keys = deque(maxlen=100)
        self.cold_keys = deque(maxlen=100)
        self.performance_alerts = []
        self.monitoring_interval = 60  # seconds
        self._monitoring_task = None

    async def start_monitoring(self):
        """Start continuous monitoring loop"""
        if self._monitoring_task:
            return
        self._monitoring_task = create_tracked_task(self._monitoring_loop(), name="auto_tracked_task")
        logger.info("Enhanced cache monitoring started")

    async def stop_monitoring(self):
        """Stop monitoring loop"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        logger.info("Enhanced cache monitoring stopped")

    async def _monitoring_loop(self):
        """Continuous monitoring and alerting loop"""
        while True:
            try:
                await asyncio.sleep(self.monitoring_interval)
                await self._collect_metrics()
                await self._analyze_performance()
                await self._check_alerts()
                await self._report_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")

    async def _collect_metrics(self):
        """Collect current metrics snapshot"""
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hit_rates": self.metrics.get_hit_rates(),
            "avg_latencies": self.metrics.get_avg_latencies(),
            "p99_latencies": self.metrics.get_p99_latencies(),
            "sizes": {
                "l1": self.metrics.l1_size_bytes,
                "l2": self.metrics.l2_size_bytes,
                "l3": self.metrics.l3_size_bytes
            },
            "counts": {
                "l1": self.metrics.l1_item_count,
                "l2": self.metrics.l2_item_count,
                "l3": self.metrics.l3_item_count
            },
            "evictions": {
                "l1": self.metrics.l1_evictions,
                "l2": self.metrics.l2_evictions,
                "l3": self.metrics.l3_evictions
            }
        }

        self.metrics.minute_stats.append(snapshot)

        # Aggregate hourly stats
        if len(self.metrics.minute_stats) >= 60:
            hourly_snapshot = self._aggregate_stats(list(self.metrics.minute_stats))
            self.metrics.hourly_stats.append(hourly_snapshot)

    async def _analyze_performance(self):
        """Analyze cache performance and identify issues"""
        hit_rates = self.metrics.get_hit_rates()
        avg_latencies = self.metrics.get_avg_latencies()

        # Check L1 performance (should be >85% hit rate, <0.1ms latency)
        if hit_rates["l1"] < 85:
            await self._create_alert(
                "LOW_L1_HIT_RATE",
                f"L1 cache hit rate is {hit_rates['l1']:.2f}% (target: >85%)",
                "warning"
            )

        if avg_latencies["l1"] > 0.1:
            await self._create_alert(
                "HIGH_L1_LATENCY",
                f"L1 cache latency is {avg_latencies['l1']:.3f}ms (target: <0.1ms)",
                "warning"
            )

        # Check overall cache effectiveness
        if hit_rates["overall"] < 95:
            await self._create_alert(
                "LOW_OVERALL_HIT_RATE",
                f"Overall cache hit rate is {hit_rates['overall']:.2f}% (target: >95%)",
                "warning"
            )

        # Check for high eviction rates
        eviction_rate = self._calculate_eviction_rate()
        if eviction_rate > 10:  # More than 10% eviction rate
            await self._create_alert(
                "HIGH_EVICTION_RATE",
                f"Cache eviction rate is {eviction_rate:.2f}% - consider increasing cache size",
                "warning"
            )

    async def _check_alerts(self):
        """Check and process performance alerts"""
        # Remove old alerts
        current_time = datetime.now(timezone.utc)
        self.performance_alerts = [
            alert for alert in self.performance_alerts
            if current_time - alert["timestamp"] < timedelta(hours=1)
        ]

        # Log critical alerts
        critical_alerts = [a for a in self.performance_alerts if a["level"] == "critical"]
        if critical_alerts:
            logger.critical(f"Critical cache alerts: {critical_alerts}")

    async def _report_metrics(self):
        """Generate and log performance report"""
        report = self.generate_performance_report()
        logger.info(f"Cache Performance Report:\n{json.dumps(report, indent=2)}")

    def record_cache_access(self, key: str, tier: str, latency_ms: float, hit: bool):
        """Record a cache access event"""
        self.metrics.total_requests += 1
        self.key_access_patterns[key] += 1

        if tier == "L1":
            if hit:
                self.metrics.l1_hits += 1
                self.metrics.l1_latencies.append(latency_ms)
        elif tier == "L2":
            if hit:
                self.metrics.l2_hits += 1
                self.metrics.l2_latencies.append(latency_ms)
        elif tier == "L3":
            if hit:
                self.metrics.l3_hits += 1
                self.metrics.l3_latencies.append(latency_ms)
        else:  # miss
            self.metrics.misses += 1
            self.metrics.miss_latencies.append(latency_ms)

        # Track hot/cold keys
        self._update_key_temperature(key)

    def record_eviction(self, tier: str, count: int = 1):
        """Record cache eviction event"""
        if tier == "L1":
            self.metrics.l1_evictions += count
        elif tier == "L2":
            self.metrics.l2_evictions += count
        elif tier == "L3":
            self.metrics.l3_evictions += count

    def update_cache_size(self, tier: str, size_bytes: int, item_count: int):
        """Update cache size metrics"""
        if tier == "L1":
            self.metrics.l1_size_bytes = size_bytes
            self.metrics.l1_item_count = item_count
        elif tier == "L2":
            self.metrics.l2_size_bytes = size_bytes
            self.metrics.l2_item_count = item_count
        elif tier == "L3":
            self.metrics.l3_size_bytes = size_bytes
            self.metrics.l3_item_count = item_count

    def _update_key_temperature(self, key: str):
        """Track hot and cold keys"""
        access_count = self.key_access_patterns[key]

        # Hot key threshold: accessed more than 10 times per minute
        if access_count > 10:
            if key not in self.hot_keys:
                self.hot_keys.append(key)
            if key in self.cold_keys:
                self.cold_keys.remove(key)
        # Cold key: accessed less than once per minute
        elif access_count < 1:
            if key not in self.cold_keys:
                self.cold_keys.append(key)
            if key in self.hot_keys:
                self.hot_keys.remove(key)

    def _calculate_eviction_rate(self) -> float:
        """Calculate eviction rate as percentage"""
        total_evictions = (self.metrics.l1_evictions +
                          self.metrics.l2_evictions +
                          self.metrics.l3_evictions)
        if self.metrics.total_requests == 0:
            return 0.0
        return (total_evictions / self.metrics.total_requests) * 100

    def _aggregate_stats(self, stats: List[Dict]) -> Dict:
        """Aggregate multiple stat snapshots"""
        if not stats:
            return {}

        aggregated = {
            "timestamp": stats[-1]["timestamp"],
            "period": "hourly",
            "hit_rates": {
                "l1": statistics.mean([s["hit_rates"]["l1"] for s in stats]),
                "l2": statistics.mean([s["hit_rates"]["l2"] for s in stats]),
                "l3": statistics.mean([s["hit_rates"]["l3"] for s in stats]),
                "overall": statistics.mean([s["hit_rates"]["overall"] for s in stats])
            },
            "avg_latencies": {
                "l1": statistics.mean([s["avg_latencies"]["l1"] for s in stats]),
                "l2": statistics.mean([s["avg_latencies"]["l2"] for s in stats]),
                "l3": statistics.mean([s["avg_latencies"]["l3"] for s in stats]),
                "miss": statistics.mean([s["avg_latencies"]["miss"] for s in stats])
            }
        }

        return aggregated

    async def _create_alert(self, alert_type: str, message: str, level: str = "warning"):
        """Create a performance alert"""
        alert = {
            "timestamp": datetime.now(timezone.utc),
            "type": alert_type,
            "message": message,
            "level": level
        }
        self.performance_alerts.append(alert)

        if level == "critical":
            logger.critical(f"CACHE ALERT: {message}")
        elif level == "warning":
            logger.warning(f"CACHE ALERT: {message}")

    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        hit_rates = self.metrics.get_hit_rates()
        avg_latencies = self.metrics.get_avg_latencies()
        p99_latencies = self.metrics.get_p99_latencies()

        return {
            "summary": {
                "total_requests": self.metrics.total_requests,
                "cache_effectiveness": hit_rates["overall"],
                "avg_response_time": statistics.mean([
                    avg_latencies["l1"] * (hit_rates["l1"]/100),
                    avg_latencies["l2"] * (hit_rates["l2"]/100),
                    avg_latencies["l3"] * (hit_rates["l3"]/100),
                    avg_latencies["miss"] * ((100 - hit_rates["overall"])/100)
                ])
            },
            "hit_rates": hit_rates,
            "latencies": {
                "average": avg_latencies,
                "p99": p99_latencies
            },
            "cache_sizes": {
                "l1": {
                    "bytes": self.metrics.l1_size_bytes,
                    "items": self.metrics.l1_item_count,
                    "avg_item_size": self.metrics.l1_size_bytes / max(1, self.metrics.l1_item_count)
                },
                "l2": {
                    "bytes": self.metrics.l2_size_bytes,
                    "items": self.metrics.l2_item_count,
                    "avg_item_size": self.metrics.l2_size_bytes / max(1, self.metrics.l2_item_count)
                },
                "l3": {
                    "bytes": self.metrics.l3_size_bytes,
                    "items": self.metrics.l3_item_count,
                    "avg_item_size": self.metrics.l3_size_bytes / max(1, self.metrics.l3_item_count)
                }
            },
            "evictions": {
                "l1": self.metrics.l1_evictions,
                "l2": self.metrics.l2_evictions,
                "l3": self.metrics.l3_evictions,
                "rate": self._calculate_eviction_rate()
            },
            "key_patterns": {
                "hot_keys": list(self.hot_keys)[:10],
                "cold_keys": list(self.cold_keys)[:10],
                "total_unique_keys": len(self.key_access_patterns)
            },
            "alerts": [
                {
                    "type": alert["type"],
                    "message": alert["message"],
                    "level": alert["level"],
                    "age_minutes": (datetime.now(timezone.utc) - alert["timestamp"]).seconds / 60
                }
                for alert in self.performance_alerts[-5:]  # Last 5 alerts
            ]
        }

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get metrics formatted for dashboard display"""
        hit_rates = self.metrics.get_hit_rates()
        avg_latencies = self.metrics.get_avg_latencies()

        return {
            "performance": {
                "response_time_ms": statistics.mean([
                    avg_latencies["l1"] * (hit_rates["l1"]/100),
                    avg_latencies["l2"] * (hit_rates["l2"]/100),
                    avg_latencies["l3"] * (hit_rates["l3"]/100),
                    avg_latencies["miss"] * ((100 - hit_rates["overall"])/100)
                ]),
                "throughput_rps": self.metrics.total_requests / max(1, self.monitoring_interval),
                "cache_hit_rate": hit_rates["overall"]
            },
            "tier_breakdown": {
                "L1": {
                    "hit_rate": hit_rates["l1"],
                    "avg_latency": avg_latencies["l1"],
                    "size_mb": self.metrics.l1_size_bytes / (1024 * 1024),
                    "items": self.metrics.l1_item_count
                },
                "L2": {
                    "hit_rate": hit_rates["l2"],
                    "avg_latency": avg_latencies["l2"],
                    "size_mb": self.metrics.l2_size_bytes / (1024 * 1024),
                    "items": self.metrics.l2_item_count
                },
                "L3": {
                    "hit_rate": hit_rates["l3"],
                    "avg_latency": avg_latencies["l3"],
                    "size_mb": self.metrics.l3_size_bytes / (1024 * 1024),
                    "items": self.metrics.l3_item_count
                }
            },
            "health_score": self._calculate_health_score()
        }

    def _calculate_health_score(self) -> float:
        """Calculate overall cache health score (0-100)"""
        hit_rates = self.metrics.get_hit_rates()
        avg_latencies = self.metrics.get_avg_latencies()

        # Scoring factors (weighted)
        hit_rate_score = min(100, hit_rates["overall"])  # 40% weight

        # Latency score (inverse, lower is better)
        target_latency = 1.0  # Target 1ms average
        actual_latency = statistics.mean(avg_latencies.values())
        latency_score = max(0, 100 - (actual_latency / target_latency) * 50)  # 30% weight

        # Eviction score (inverse, lower is better)
        eviction_rate = self._calculate_eviction_rate()
        eviction_score = max(0, 100 - eviction_rate * 5)  # 20% weight

        # Error score (inverse, lower is better)
        total_errors = self.metrics.l1_errors + self.metrics.l2_errors + self.metrics.l3_errors
        error_rate = (total_errors / max(1, self.metrics.total_requests)) * 100
        error_score = max(0, 100 - error_rate * 10)  # 10% weight

        # Weighted health score
        health_score = (
            hit_rate_score * 0.4 +
            latency_score * 0.3 +
            eviction_score * 0.2 +
            error_score * 0.1
        )

        return round(health_score, 2)


# Global monitor instance
cache_monitor = EnhancedCacheMonitor()
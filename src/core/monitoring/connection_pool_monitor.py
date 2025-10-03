from src.utils.task_tracker import create_tracked_task
"""
Connection Pool Monitor for tracking and logging connection pool usage
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import aiohttp
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Statistics for a connection pool"""
    timestamp: float = field(default_factory=time.time)
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    pending_connections: int = 0
    failed_connections: int = 0
    connection_timeouts: int = 0
    average_response_time: float = 0.0
    requests_per_second: float = 0.0
    pool_utilization: float = 0.0
    errors: List[str] = field(default_factory=list)


class ConnectionPoolMonitor:
    """Monitor and track connection pool usage for HTTP clients"""
    
    def __init__(self, 
                 check_interval: int = 60,
                 alert_threshold: float = 0.8,
                 history_size: int = 1440):  # 24 hours at 1-minute intervals
        """
        Initialize connection pool monitor
        
        Args:
            check_interval: Seconds between checks
            alert_threshold: Pool utilization threshold for alerts (0.0-1.0)
            history_size: Number of historical stats to keep
        """
        self.check_interval = check_interval
        self.alert_threshold = alert_threshold
        self.history_size = history_size
        
        self._stats_history: Dict[str, List[ConnectionStats]] = {}
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self._request_counts: Dict[str, int] = {}
        self._last_check: Dict[str, float] = {}
        
    def register_session(self, name: str, session: aiohttp.ClientSession) -> None:
        """Register a session for monitoring"""
        self._sessions[name] = session
        self._stats_history[name] = []
        self._request_counts[name] = 0
        self._last_check[name] = time.time()
        logger.info(f"Registered session '{name}' for connection pool monitoring")
        
    def unregister_session(self, name: str) -> None:
        """Unregister a session from monitoring"""
        if name in self._sessions:
            del self._sessions[name]
            del self._stats_history[name]
            del self._request_counts[name]
            del self._last_check[name]
            logger.info(f"Unregistered session '{name}' from monitoring")
            
    async def start(self) -> None:
        """Start monitoring connection pools"""
        if self._running:
            logger.warning("Connection pool monitor already running")
            return
            
        self._running = True
        self._monitoring_task = create_tracked_task(self._monitor_loop(), name="auto_tracked_task")
        logger.info(f"Started connection pool monitoring (interval: {self.check_interval}s)")
        
    async def stop(self) -> None:
        """Stop monitoring connection pools"""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped connection pool monitoring")
        
    async def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            try:
                await self._check_all_pools()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in connection pool monitor: {e}")
                await asyncio.sleep(self.check_interval)
                
    async def _check_all_pools(self) -> None:
        """Check all registered connection pools"""
        for name, session in self._sessions.items():
            try:
                stats = await self._get_pool_stats(name, session)
                self._record_stats(name, stats)
                self._check_alerts(name, stats)
                self._log_stats(name, stats)
            except Exception as e:
                logger.error(f"Error checking pool '{name}': {e}")
                
    async def _get_pool_stats(self, name: str, session: aiohttp.ClientSession) -> ConnectionStats:
        """Get statistics for a connection pool"""
        stats = ConnectionStats()
        
        try:
            if hasattr(session, '_connector') and session._connector:
                connector = session._connector
                
                # Get connection counts
                if hasattr(connector, '_limit'):
                    stats.total_connections = connector._limit
                    
                if hasattr(connector, '_acquired'):
                    stats.active_connections = len(connector._acquired)
                    
                if hasattr(connector, '_available'):
                    # Count idle connections
                    idle_count = 0
                    for key, connections in connector._available.items():
                        idle_count += len(connections)
                    stats.idle_connections = idle_count
                    
                if hasattr(connector, '_waiters'):
                    # Count pending connections
                    pending_count = 0
                    for key, waiters in connector._waiters.items():
                        pending_count += len(waiters)
                    stats.pending_connections = pending_count
                    
                # Calculate pool utilization
                if stats.total_connections > 0:
                    stats.pool_utilization = (stats.active_connections + stats.pending_connections) / stats.total_connections
                    
                # Calculate requests per second
                current_time = time.time()
                time_diff = current_time - self._last_check.get(name, current_time)
                if time_diff > 0:
                    request_count = self._request_counts.get(name, 0)
                    stats.requests_per_second = request_count / time_diff
                    self._request_counts[name] = 0  # Reset counter
                    self._last_check[name] = current_time
                    
        except Exception as e:
            logger.error(f"Error getting pool stats for '{name}': {e}")
            stats.errors.append(str(e))
            
        return stats
        
    def _record_stats(self, name: str, stats: ConnectionStats) -> None:
        """Record statistics in history"""
        if name not in self._stats_history:
            self._stats_history[name] = []
            
        history = self._stats_history[name]
        history.append(stats)
        
        # Trim history to size limit
        if len(history) > self.history_size:
            history.pop(0)
            
    def _check_alerts(self, name: str, stats: ConnectionStats) -> None:
        """Check if alerts should be triggered"""
        if stats.pool_utilization > self.alert_threshold:
            logger.warning(
                f"High connection pool utilization for '{name}': "
                f"{stats.pool_utilization:.1%} (threshold: {self.alert_threshold:.1%})"
            )
            
        if stats.pending_connections > 10:
            logger.warning(
                f"High pending connections for '{name}': "
                f"{stats.pending_connections} connections waiting"
            )
            
        if stats.errors:
            logger.error(
                f"Connection pool errors for '{name}': "
                f"{', '.join(stats.errors)}"
            )
            
    def _log_stats(self, name: str, stats: ConnectionStats) -> None:
        """Log connection pool statistics"""
        logger.info(
            f"Connection pool '{name}': "
            f"active={stats.active_connections}/{stats.total_connections}, "
            f"idle={stats.idle_connections}, "
            f"pending={stats.pending_connections}, "
            f"utilization={stats.pool_utilization:.1%}, "
            f"rps={stats.requests_per_second:.1f}"
        )
        
    def increment_request_count(self, name: str) -> None:
        """Increment request counter for a session"""
        if name in self._request_counts:
            self._request_counts[name] += 1
            
    def get_current_stats(self, name: str) -> Optional[ConnectionStats]:
        """Get the most recent stats for a session"""
        if name in self._stats_history and self._stats_history[name]:
            return self._stats_history[name][-1]
        return None
        
    def get_stats_summary(self, name: str, duration_minutes: int = 60) -> Dict[str, Any]:
        """Get summary statistics for a time period"""
        if name not in self._stats_history:
            return {}
            
        history = self._stats_history[name]
        if not history:
            return {}
            
        cutoff_time = time.time() - (duration_minutes * 60)
        recent_stats = [s for s in history if s.timestamp > cutoff_time]
        
        if not recent_stats:
            return {}
            
        # Calculate summary statistics
        summary = {
            'session_name': name,
            'duration_minutes': duration_minutes,
            'samples': len(recent_stats),
            'average_utilization': sum(s.pool_utilization for s in recent_stats) / len(recent_stats),
            'max_utilization': max(s.pool_utilization for s in recent_stats),
            'average_active_connections': sum(s.active_connections for s in recent_stats) / len(recent_stats),
            'max_active_connections': max(s.active_connections for s in recent_stats),
            'total_pending_connections': sum(s.pending_connections for s in recent_stats),
            'average_rps': sum(s.requests_per_second for s in recent_stats) / len(recent_stats),
            'error_count': sum(len(s.errors) for s in recent_stats),
            'last_check': datetime.fromtimestamp(recent_stats[-1].timestamp).isoformat()
        }
        
        return summary
        
    def get_all_summaries(self, duration_minutes: int = 60) -> Dict[str, Dict[str, Any]]:
        """Get summaries for all monitored sessions"""
        summaries = {}
        for name in self._sessions:
            summary = self.get_stats_summary(name, duration_minutes)
            if summary:
                summaries[name] = summary
        return summaries
        
    def export_stats(self, filepath: str) -> None:
        """Export all statistics to a JSON file"""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'sessions': {}
        }
        
        for name, history in self._stats_history.items():
            export_data['sessions'][name] = {
                'current_stats': self.get_current_stats(name).__dict__ if self.get_current_stats(name) else None,
                'summary_1h': self.get_stats_summary(name, 60),
                'summary_24h': self.get_stats_summary(name, 1440),
                'history_size': len(history)
            }
            
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
            
        logger.info(f"Exported connection pool stats to {filepath}")


# Global instance for easy access
_monitor_instance: Optional[ConnectionPoolMonitor] = None


def get_monitor() -> ConnectionPoolMonitor:
    """Get or create the global connection pool monitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ConnectionPoolMonitor()
    return _monitor_instance


async def start_monitoring() -> ConnectionPoolMonitor:
    """Start the global connection pool monitor"""
    monitor = get_monitor()
    await monitor.start()
    return monitor


async def stop_monitoring() -> None:
    """Stop the global connection pool monitor"""
    if _monitor_instance:
        await _monitor_instance.stop()
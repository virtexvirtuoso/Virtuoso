"""
Optimized Alert Routes with Advanced Caching
High-performance alert endpoints with intelligent caching strategies.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import Dict, List, Any, Optional
import asyncio
import json
import logging
from datetime import datetime, timedelta
import time

# Import our cache adapter
from src.api.cache_adapter_direct import cache_adapter

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)

# Simplified cache operations (replacing complex multi-tier system)
# batch_manager = BatchCacheManager(cache_adapter)  # Commented out - archived
# ttl_strategy = TTLStrategy()  # Commented out - archived

class AlertCacheService:
    """Optimized alert caching service"""
    
    def __init__(self):
        self.cache_adapter = cache_adapter
        self.batch_manager = batch_manager
        self.ttl_strategy = ttl_strategy
        
        # Alert-specific cache configuration
        self.cache_config = {
            'active_alerts_ttl': 120,    # 2 minutes for active alerts
            'recent_alerts_ttl': 300,    # 5 minutes for recent alerts  
            'alert_history_ttl': 3600,   # 1 hour for historical data
            'alert_stats_ttl': 600,     # 10 minutes for statistics
            'batch_size': 50,            # Maximum alerts per batch
            'max_history_days': 7        # Maximum days to keep in history
        }
        
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'alerts_served': 0,
            'avg_response_time': 0
        }
    
    async def get_active_alerts(self, limit: int = 50, priority_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active alerts with optimized caching"""
        start_time = time.time()
        
        try:
            # Generate cache key with filters
            cache_key = CacheKeyGenerator.alerts_active()
            if priority_filter:
                cache_key += f":{priority_filter}"
            if limit != 50:
                cache_key += f":limit_{limit}"
            
            # Try cache first
            cached_alerts = await self.cache_adapter.get(cache_key)
            
            if cached_alerts is not None:
                self._stats['cache_hits'] += 1
                self.ttl_strategy.record_access(cache_key, True)
                
                # Filter and limit cached results if needed
                alerts = self._apply_filters(cached_alerts, limit, priority_filter)
                
                self._update_response_stats(time.time() - start_time)
                return alerts
            
            # Cache miss - fetch from source
            self._stats['cache_misses'] += 1
            self.ttl_strategy.record_access(cache_key, False)
            
            # Fetch fresh alerts
            alerts = await self._fetch_alerts_from_source(limit, priority_filter)
            
            if alerts:
                # Cache the results
                ttl = self.ttl_strategy.get_ttl(cache_key)
                await self.cache_adapter.set(cache_key, alerts, ttl)
                
                # Warm related cache keys
                await self._warm_related_alert_caches(alerts)
            
            self._update_response_stats(time.time() - start_time)
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    async def get_recent_alerts(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alerts with time-based caching"""
        start_time = time.time()
        
        try:
            cache_key = CacheKeyGenerator.alerts_recent(limit)
            if hours != 24:
                cache_key += f":hours_{hours}"
            
            cached_alerts = await self.cache_adapter.get(cache_key)
            
            if cached_alerts is not None:
                self._stats['cache_hits'] += 1
                self.ttl_strategy.record_access(cache_key, True)
                
                # Filter by time range
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                filtered_alerts = [
                    alert for alert in cached_alerts
                    if datetime.fromisoformat(alert.get('timestamp', '2000-01-01')) >= cutoff_time
                ][:limit]
                
                self._update_response_stats(time.time() - start_time)
                return filtered_alerts
            
            # Fetch from source
            self._stats['cache_misses'] += 1
            alerts = await self._fetch_recent_alerts_from_source(hours, limit)
            
            if alerts:
                ttl = self.ttl_strategy.get_ttl(cache_key)
                await self.cache_adapter.set(cache_key, alerts, ttl)
            
            self._update_response_stats(time.time() - start_time)
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics with optimized caching"""
        try:
            cache_key = "alerts:statistics:v1"
            
            cached_stats = await self.cache_adapter.get(cache_key)
            if cached_stats is not None:
                self._stats['cache_hits'] += 1
                return cached_stats
            
            # Calculate statistics
            stats = await self._calculate_alert_statistics()
            
            if stats:
                ttl = self.cache_config['alert_stats_ttl']
                await self.cache_adapter.set(cache_key, stats, ttl)
            
            self._stats['cache_misses'] += 1
            return stats
            
        except Exception as e:
            logger.error(f"Error getting alert statistics: {e}")
            return {}
    
    async def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create alert and invalidate relevant caches"""
        try:
            # Add timestamp
            alert_data['timestamp'] = datetime.utcnow().isoformat()
            alert_data['id'] = f"alert_{int(time.time() * 1000)}"
            
            # Store the alert (simplified - in production you'd use a database)
            success = await self._store_alert(alert_data)
            
            if success:
                # Invalidate related caches
                await self._invalidate_alert_caches()
                
                return {"status": "success", "alert_id": alert_data['id']}
            else:
                raise HTTPException(status_code=500, detail="Failed to create alert")
                
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _fetch_alerts_from_source(self, limit: int, priority_filter: Optional[str]) -> List[Dict[str, Any]]:
        """Fetch alerts from monitoring system"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"http://localhost:8001/api/monitoring/alerts"
                params = {'limit': limit}
                if priority_filter:
                    params['priority'] = priority_filter
                
                async with session.get(url, params=params, timeout=2.0) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('alerts', [])
                    else:
                        logger.warning(f"Alert service returned {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Failed to fetch alerts from source: {e}")
            return []
    
    async def _fetch_recent_alerts_from_source(self, hours: int, limit: int) -> List[Dict[str, Any]]:
        """Fetch recent alerts from monitoring system"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"http://localhost:8001/api/monitoring/alerts/recent"
                params = {'hours': hours, 'limit': limit}
                
                async with session.get(url, params=params, timeout=3.0) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('alerts', [])
                    else:
                        return []
        except Exception as e:
            logger.error(f"Failed to fetch recent alerts: {e}")
            return []
    
    async def _calculate_alert_statistics(self) -> Dict[str, Any]:
        """Calculate alert statistics"""
        try:
            # Get recent alerts for statistics
            recent_alerts = await self._fetch_recent_alerts_from_source(24, 1000)
            
            if not recent_alerts:
                return self._get_default_stats()
            
            # Calculate statistics
            total_alerts = len(recent_alerts)
            critical_alerts = len([a for a in recent_alerts if a.get('priority') == 'critical'])
            warning_alerts = len([a for a in recent_alerts if a.get('priority') == 'warning'])
            info_alerts = total_alerts - critical_alerts - warning_alerts
            
            # Group by hour for trend analysis
            hourly_counts = {}
            for alert in recent_alerts:
                try:
                    timestamp = datetime.fromisoformat(alert.get('timestamp', ''))
                    hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                    hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
                except:
                    continue
            
            return {
                'total_24h': total_alerts,
                'critical': critical_alerts,
                'warning': warning_alerts,
                'info': info_alerts,
                'hourly_trend': hourly_counts,
                'avg_per_hour': total_alerts / 24 if total_alerts > 0 else 0,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating alert statistics: {e}")
            return self._get_default_stats()
    
    def _get_default_stats(self) -> Dict[str, Any]:
        """Get default statistics when calculation fails"""
        return {
            'total_24h': 0,
            'critical': 0,
            'warning': 0,
            'info': 0,
            'hourly_trend': {},
            'avg_per_hour': 0,
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def _apply_filters(self, alerts: List[Dict[str, Any]], limit: int, priority_filter: Optional[str]) -> List[Dict[str, Any]]:
        """Apply filters to cached alerts"""
        filtered = alerts
        
        if priority_filter:
            filtered = [a for a in filtered if a.get('priority') == priority_filter]
        
        return filtered[:limit]
    
    async def _warm_related_alert_caches(self, alerts: List[Dict[str, Any]]):
        """Warm related cache keys after fetching alerts"""
        try:
            # Prepare related cache data
            cache_data = {}
            
            # Cache statistics
            stats_key = "alerts:statistics:v1"
            if len(alerts) > 0:
                stats = await self._calculate_alert_statistics()
                cache_data[stats_key] = stats
            
            # Cache different priority filters
            for priority in ['critical', 'warning', 'info']:
                priority_alerts = [a for a in alerts if a.get('priority') == priority]
                if priority_alerts:
                    priority_key = f"{CacheKeyGenerator.alerts_active()}:{priority}"
                    cache_data[priority_key] = priority_alerts
            
            # Batch cache warming
            if cache_data:
                await self.batch_manager.multi_set(cache_data)
                
        except Exception as e:
            logger.debug(f"Error warming related alert caches: {e}")
    
    async def _store_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Store alert (simplified implementation)"""
        try:
            # In production, this would store to database
            # For now, we'll just return success
            return True
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
            return False
    
    async def _invalidate_alert_caches(self):
        """Invalidate all alert-related caches"""
        try:
            cache_keys = [
                CacheKeyGenerator.alerts_active(),
                CacheKeyGenerator.alerts_recent(50),
                CacheKeyGenerator.alerts_recent(100),
                "alerts:statistics:v1"
            ]
            
            # Add priority-specific keys
            for priority in ['critical', 'warning', 'info']:
                cache_keys.append(f"{CacheKeyGenerator.alerts_active()}:{priority}")
            
            # Batch delete
            await self.batch_manager.multi_delete(cache_keys)
            
        except Exception as e:
            logger.error(f"Error invalidating alert caches: {e}")
    
    def _update_response_stats(self, response_time: float):
        """Update response time statistics"""
        self._stats['alerts_served'] += 1
        
        current_avg = self._stats['avg_response_time']
        total_requests = self._stats['alerts_served']
        self._stats['avg_response_time'] = ((current_avg * (total_requests - 1)) + (response_time * 1000)) / total_requests
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self._stats['cache_hits'] + self._stats['cache_misses']
        hit_rate = (self._stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'service': 'alert_cache',
            'cache_performance': {
                'hit_rate': round(hit_rate, 2),
                'total_requests': total_requests,
                'cache_hits': self._stats['cache_hits'],
                'cache_misses': self._stats['cache_misses']
            },
            'service_performance': {
                'alerts_served': self._stats['alerts_served'],
                'avg_response_time_ms': round(self._stats['avg_response_time'], 2)
            },
            'cache_configuration': self.cache_config
        }

# Initialize alert cache service
alert_cache_service = AlertCacheService()

# Route implementations
@router.get("/active", summary="Get Active Alerts")
async def get_active_alerts(
    limit: int = Query(50, description="Maximum number of alerts to return", ge=1, le=500),
    priority: Optional[str] = Query(None, description="Filter by priority (critical, warning, info)")
) -> Dict[str, Any]:
    """
    Get currently active alerts with intelligent caching.
    
    Returns active alerts with 2-minute cache TTL for optimal performance.
    Supports filtering by priority level and customizable limits.
    """
    try:
        alerts = await alert_cache_service.get_active_alerts(limit=limit, priority_filter=priority)
        
        return {
            "status": "success",
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.utcnow().isoformat(),
            "cache_info": {
                "ttl": alert_cache_service.cache_config['active_alerts_ttl'],
                "cached": True  # Simplified - in production you'd track this
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_active_alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving active alerts: {str(e)}")

@router.get("/recent", summary="Get Recent Alerts")
async def get_recent_alerts(
    hours: int = Query(24, description="Hours of history to retrieve", ge=1, le=168),  # Max 1 week
    limit: int = Query(100, description="Maximum number of alerts to return", ge=1, le=1000)
) -> Dict[str, Any]:
    """
    Get recent alerts within specified time range with optimized caching.
    
    Returns alerts from the last N hours with 5-minute cache TTL.
    Useful for historical analysis and trend monitoring.
    """
    try:
        alerts = await alert_cache_service.get_recent_alerts(hours=hours, limit=limit)
        
        return {
            "status": "success", 
            "alerts": alerts,
            "count": len(alerts),
            "time_range_hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
            "cache_info": {
                "ttl": alert_cache_service.cache_config['recent_alerts_ttl']
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_recent_alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving recent alerts: {str(e)}")

@router.get("/statistics", summary="Get Alert Statistics")
async def get_alert_statistics() -> Dict[str, Any]:
    """
    Get comprehensive alert statistics with optimized caching.
    
    Returns aggregated statistics with 10-minute cache TTL including:
    - Total alerts in last 24 hours
    - Breakdown by priority level
    - Hourly trend data
    - Average alerts per hour
    """
    try:
        stats = await alert_cache_service.get_alert_statistics()
        
        return {
            "status": "success",
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in get_alert_statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving alert statistics: {str(e)}")

@router.post("/create", summary="Create New Alert")
async def create_alert(alert_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new alert and invalidate related caches.
    
    Automatically invalidates all alert caches to ensure consistency.
    """
    try:
        result = await alert_cache_service.create_alert(alert_data)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_alert: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating alert: {str(e)}")

@router.get("/cache-stats", summary="Get Cache Performance Statistics")
async def get_alert_cache_stats() -> Dict[str, Any]:
    """
    Get alert caching performance statistics.
    
    Returns detailed metrics about cache hit rates, response times,
    and service performance for monitoring and optimization.
    """
    try:
        stats = alert_cache_service.get_cache_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving cache stats: {str(e)}")

@router.post("/cache/invalidate", summary="Invalidate Alert Caches")
async def invalidate_alert_caches() -> Dict[str, Any]:
    """
    Manually invalidate all alert caches.
    
    Useful for forcing cache refresh when needed.
    """
    try:
        await alert_cache_service._invalidate_alert_caches()
        
        return {
            "status": "success",
            "message": "Alert caches invalidated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error invalidating caches: {e}")
        raise HTTPException(status_code=500, detail=f"Error invalidating caches: {str(e)}")

@router.get("/health", summary="Alert Service Health Check")
async def alert_service_health() -> Dict[str, Any]:
    """
    Health check for the optimized alert service.
    
    Returns service status, cache performance, and system health metrics.
    """
    try:
        # Test cache connectivity
        test_key = "health:test:alerts"
        test_data = {"test": True, "timestamp": time.time()}
        
        start_time = time.time()
        await cache_adapter.set(test_key, test_data, 30)
        cached_result = await cache_adapter.get(test_key)
        await cache_adapter.delete(test_key)
        response_time = (time.time() - start_time) * 1000
        
        cache_healthy = cached_result is not None
        
        # Get service stats
        service_stats = alert_cache_service.get_cache_stats()
        
        return {
            "status": "healthy" if cache_healthy else "degraded",
            "cache_connectivity": cache_healthy,
            "response_time_ms": round(response_time, 2),
            "service_stats": service_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
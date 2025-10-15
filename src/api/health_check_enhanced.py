"""
Enhanced Health Check Module for Production Monitoring
Provides comprehensive health status for all system components
"""
import asyncio
import time
import psutil
import redis
import pymemcache.client
from typing import Dict, Any
from datetime import datetime, timedelta

class EnhancedHealthCheck:
    def __init__(self, redis_host='localhost', memcached_host='localhost'):
        self.redis_host = redis_host
        self.memcached_host = memcached_host
        self.start_time = time.time()

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        try:
            r = redis.Redis(host=self.redis_host, port=6379, db=0,
                          socket_connect_timeout=1, socket_timeout=1)
            start = time.time()
            r.ping()
            latency = (time.time() - start) * 1000

            info = r.info()
            return {
                'status': 'healthy',
                'latency_ms': round(latency, 2),
                'used_memory_mb': round(info['used_memory'] / 1024 / 1024, 2),
                'connected_clients': info['connected_clients'],
                'ops_per_sec': info.get('instantaneous_ops_per_sec', 0)
            }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}

    async def check_memcached(self) -> Dict[str, Any]:
        """Check Memcached connectivity and stats"""
        try:
            client = pymemcache.client.Client((self.memcached_host, 11211),
                                             connect_timeout=1, timeout=1)
            start = time.time()
            client.set('health_check', '1', expire=60)
            client.get('health_check')
            latency = (time.time() - start) * 1000

            stats = client.stats()
            return {
                'status': 'healthy',
                'latency_ms': round(latency, 2),
                'hit_ratio': round(float(stats.get(b'get_hits', 0)) /
                                 max(float(stats.get(b'cmd_get', 1)), 1) * 100, 2),
                'total_items': int(stats.get(b'total_items', 0)),
                'bytes_used': int(stats.get(b'bytes', 0))
            }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}

    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system CPU, memory, and disk usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Check for resource warnings
            warnings = []
            if cpu_percent > 80:
                warnings.append(f"High CPU usage: {cpu_percent}%")
            if memory.percent > 85:
                warnings.append(f"High memory usage: {memory.percent}%")
            if disk.percent > 90:
                warnings.append(f"Low disk space: {disk.percent}% used")

            return {
                'status': 'healthy' if not warnings else 'warning',
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / 1024 / 1024 / 1024, 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
                'warnings': warnings
            }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}

    async def check_api_endpoints(self) -> Dict[str, Any]:
        """Check critical API endpoint availability"""
        endpoints = {
            'monitoring': 'http://localhost:8001/api/monitoring/status',
            'web_server': 'http://localhost:8003/health',
            'config_api': 'http://localhost:8002/api/config/status'
        }

        results = {}
        for name, url in endpoints.items():
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    start = time.time()
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                        latency = (time.time() - start) * 1000
                        results[name] = {
                            'status': 'healthy' if resp.status == 200 else 'degraded',
                            'status_code': resp.status,
                            'latency_ms': round(latency, 2)
                        }
            except Exception as e:
                results[name] = {'status': 'unhealthy', 'error': str(e)[:100]}

        return results

    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status of all components"""
        # Run all checks concurrently
        results = await asyncio.gather(
            self.check_redis(),
            self.check_memcached(),
            self.check_system_resources(),
            self.check_api_endpoints(),
            return_exceptions=True
        )

        redis_health = results[0] if not isinstance(results[0], Exception) else {'status': 'error', 'error': str(results[0])}
        memcached_health = results[1] if not isinstance(results[1], Exception) else {'status': 'error', 'error': str(results[1])}
        system_health = results[2] if not isinstance(results[2], Exception) else {'status': 'error', 'error': str(results[2])}
        api_health = results[3] if not isinstance(results[3], Exception) else {'status': 'error', 'error': str(results[3])}

        # Determine overall health
        all_statuses = [
            redis_health.get('status'),
            memcached_health.get('status'),
            system_health.get('status')
        ]

        if 'unhealthy' in all_statuses or 'error' in all_statuses:
            overall_status = 'unhealthy'
        elif 'warning' in all_statuses:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'

        uptime_seconds = int(time.time() - self.start_time)

        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': uptime_seconds,
            'uptime_human': str(timedelta(seconds=uptime_seconds)),
            'components': {
                'redis': redis_health,
                'memcached': memcached_health,
                'system': system_health,
                'api_endpoints': api_health
            },
            'version': '2.0.0',
            'environment': 'production'
        }

# FastAPI endpoint integration
from fastapi import APIRouter, Response

health_router = APIRouter()
health_checker = EnhancedHealthCheck()

@health_router.get("/health/detailed")
async def detailed_health_check(response: Response):
    """Comprehensive health check endpoint for monitoring systems"""
    health_data = await health_checker.get_comprehensive_health()

    # Set appropriate HTTP status based on health
    if health_data['status'] == 'unhealthy':
        response.status_code = 503
    elif health_data['status'] == 'degraded':
        response.status_code = 200  # Still return 200 for degraded to avoid false alarms

    return health_data

@health_router.get("/health/simple")
async def simple_health_check():
    """Simple health check for load balancers"""
    return {"status": "ok"}
from src.utils.task_tracker import create_tracked_task
"""
API Gateway - Priority 2 Implementation
Unified API gateway for all dashboard requests with:
- Request routing and load balancing
- Response caching at gateway level
- Rate limiting (100 requests/second)
- Error handling and fallbacks
- Request/response logging and metrics
- Circuit breaker integration

Performance Target: Sub-150ms response times with 70%+ cache hit rate
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List, Callable, Union
import asyncio
import aiohttp
import time
import logging
import json
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from functools import wraps
from urllib.parse import urlencode
from src.core.cache.multi_tier_cache import get_multi_tier_cache, MultiTierCache

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Token bucket rate limiter with per-client tracking
    Supports 100 requests/second with burst capability
    """
    
    def __init__(self, 
                 requests_per_second: int = 100,
                 burst_capacity: int = 200,
                 cleanup_interval: int = 300):
        """
        Initialize rate limiter
        
        Args:
            requests_per_second: Sustained rate limit
            burst_capacity: Maximum burst tokens
            cleanup_interval: Client cleanup interval in seconds
        """
        self.requests_per_second = requests_per_second
        self.burst_capacity = burst_capacity
        self.cleanup_interval = cleanup_interval
        
        # Per-client token buckets
        self.client_buckets = defaultdict(lambda: {
            'tokens': burst_capacity,
            'last_refill': time.time(),
            'total_requests': 0,
            'blocked_requests': 0
        })
        
        # Global rate tracking
        self.global_requests = deque()
        self._lock = threading.Lock()
        
        # Start cleanup task
        create_tracked_task(self._cleanup_task(), name="auto_tracked_task")
    
    async def _cleanup_task(self):
        """Periodic cleanup of inactive clients"""
        while True:
            await asyncio.sleep(self.cleanup_interval)
            current_time = time.time()
            with self._lock:
                inactive_clients = [
                    client for client, bucket in self.client_buckets.items()
                    if current_time - bucket['last_refill'] > self.cleanup_interval
                ]
                for client in inactive_clients:
                    del self.client_buckets[client]
                    
                if inactive_clients:
                    logger.debug(f"Cleaned up {len(inactive_clients)} inactive rate limit clients")
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request"""
        # Try X-Forwarded-For first (behind proxy)
        client_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if not client_ip:
            client_ip = request.headers.get('X-Real-IP', '')
        if not client_ip:
            client_ip = request.client.host if request.client else 'unknown'
        
        # Include user agent for better identification
        user_agent = request.headers.get('User-Agent', '')[:50]  # Truncate
        return f"{client_ip}:{hashlib.md5(user_agent.encode()).hexdigest()[:8]}"
    
    def _refill_bucket(self, bucket: Dict[str, Any], current_time: float):
        """Refill token bucket based on elapsed time"""
        elapsed = current_time - bucket['last_refill']
        tokens_to_add = elapsed * self.requests_per_second
        
        bucket['tokens'] = min(
            self.burst_capacity,
            bucket['tokens'] + tokens_to_add
        )
        bucket['last_refill'] = current_time
    
    async def check_rate_limit(self, request: Request) -> Dict[str, Any]:
        """
        Check if request is within rate limits
        
        Returns:
            Dict with 'allowed', 'tokens_remaining', 'retry_after' keys
        """
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        with self._lock:
            bucket = self.client_buckets[client_id]
            self._refill_bucket(bucket, current_time)
            
            bucket['total_requests'] += 1
            
            # Track global request rate
            self.global_requests.append(current_time)
            # Remove requests older than 1 second
            while self.global_requests and current_time - self.global_requests[0] > 1:
                self.global_requests.popleft()
            
            # Check if client has tokens
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return {
                    'allowed': True,
                    'tokens_remaining': int(bucket['tokens']),
                    'retry_after': 0,
                    'global_rate': len(self.global_requests)
                }
            else:
                bucket['blocked_requests'] += 1
                retry_after = 1.0 / self.requests_per_second
                return {
                    'allowed': False,
                    'tokens_remaining': 0,
                    'retry_after': retry_after,
                    'global_rate': len(self.global_requests)
                }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        current_time = time.time()
        with self._lock:
            total_clients = len(self.client_buckets)
            total_requests = sum(bucket['total_requests'] for bucket in self.client_buckets.values())
            total_blocked = sum(bucket['blocked_requests'] for bucket in self.client_buckets.values())
            
            # Calculate current global rate
            while self.global_requests and current_time - self.global_requests[0] > 1:
                self.global_requests.popleft()
            current_global_rate = len(self.global_requests)
            
            return {
                'total_clients': total_clients,
                'total_requests': total_requests,
                'total_blocked': total_blocked,
                'block_rate_percent': round((total_blocked / max(total_requests, 1)) * 100, 2),
                'current_global_rate_per_second': current_global_rate,
                'configured_rate_limit': self.requests_per_second,
                'burst_capacity': self.burst_capacity
            }


class CircuitBreaker:
    """
    Circuit breaker pattern for backend service protection
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 30,
                 success_threshold: int = 3):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            success_threshold: Successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def call(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with self._lock:
                # Check circuit state
                if self.state == 'OPEN':
                    if (self.last_failure_time and 
                        time.time() - self.last_failure_time > self.recovery_timeout):
                        self.state = 'HALF_OPEN'
                        self.success_count = 0
                        logger.info("Circuit breaker transitioning to HALF_OPEN")
                    else:
                        raise HTTPException(
                            status_code=503, 
                            detail="Service temporarily unavailable (Circuit breaker OPEN)"
                        )
            
            try:
                result = await func(*args, **kwargs)
                
                with self._lock:
                    if self.state == 'HALF_OPEN':
                        self.success_count += 1
                        if self.success_count >= self.success_threshold:
                            self.state = 'CLOSED'
                            self.failure_count = 0
                            logger.info("Circuit breaker closed after successful recovery")
                    elif self.state == 'CLOSED':
                        self.failure_count = max(0, self.failure_count - 1)
                
                return result
                
            except Exception as e:
                with self._lock:
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    
                    if self.failure_count >= self.failure_threshold:
                        self.state = 'OPEN'
                        logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
                
                raise
        
        return wrapper
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        with self._lock:
            return {
                'state': self.state,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'last_failure_time': self.last_failure_time,
                'failure_threshold': self.failure_threshold,
                'recovery_timeout': self.recovery_timeout
            }


class RequestLogger:
    """
    Request/response logging and metrics collection
    """
    
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.request_log = deque(maxlen=max_entries)
        self.metrics = defaultdict(int)
        self.response_times = deque(maxlen=1000)  # Keep last 1000 for average
        self._lock = threading.Lock()
    
    def log_request(self, 
                   method: str,
                   path: str,
                   client_ip: str,
                   start_time: float,
                   end_time: float,
                   status_code: int,
                   cache_hit: bool = False,
                   error: str = None):
        """Log request details"""
        response_time_ms = (end_time - start_time) * 1000
        
        with self._lock:
            log_entry = {
                'timestamp': datetime.fromtimestamp(start_time).isoformat(),
                'method': method,
                'path': path,
                'client_ip': client_ip,
                'response_time_ms': round(response_time_ms, 2),
                'status_code': status_code,
                'cache_hit': cache_hit,
                'error': error
            }
            
            self.request_log.append(log_entry)
            self.response_times.append(response_time_ms)
            
            # Update metrics
            self.metrics['total_requests'] += 1
            self.metrics[f'status_{status_code}'] += 1
            self.metrics['cache_hits' if cache_hit else 'cache_misses'] += 1
            
            if error:
                self.metrics['errors'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get request metrics summary"""
        with self._lock:
            if not self.response_times:
                return {'total_requests': 0}
            
            avg_response_time = sum(self.response_times) / len(self.response_times)
            p95_response_time = sorted(self.response_times)[int(len(self.response_times) * 0.95)]
            
            return {
                'total_requests': self.metrics['total_requests'],
                'cache_hit_rate_percent': round(
                    (self.metrics.get('cache_hits', 0) / max(self.metrics['total_requests'], 1)) * 100, 2
                ),
                'avg_response_time_ms': round(avg_response_time, 2),
                'p95_response_time_ms': round(p95_response_time, 2),
                'error_rate_percent': round(
                    (self.metrics.get('errors', 0) / max(self.metrics['total_requests'], 1)) * 100, 2
                ),
                'status_codes': {
                    k: v for k, v in self.metrics.items() 
                    if k.startswith('status_')
                },
                'cache_hits': self.metrics.get('cache_hits', 0),
                'cache_misses': self.metrics.get('cache_misses', 0)
            }
    
    def get_recent_requests(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent request logs"""
        with self._lock:
            return list(self.request_log)[-limit:]


class APIGateway:
    """
    Unified API Gateway for dashboard requests
    """
    
    def __init__(self, 
                 cache: MultiTierCache = None,
                 rate_limit_rps: int = 100,
                 enable_circuit_breaker: bool = True):
        """
        Initialize API Gateway
        
        Args:
            cache: Multi-tier cache instance
            rate_limit_rps: Requests per second limit
            enable_circuit_breaker: Enable circuit breaker protection
        """
        self.cache = cache or get_multi_tier_cache()
        self.rate_limiter = RateLimiter(requests_per_second=rate_limit_rps)
        self.request_logger = RequestLogger()
        self.circuit_breaker = CircuitBreaker() if enable_circuit_breaker else None
        
        # Backend service endpoints
        self.backends = {
            'primary': 'http://localhost:8003',
            'monitoring': 'http://localhost:8001',
            'fallback': 'http://localhost:8004'
        }
        
        # Route configuration
        self.route_config = {
            '/api/dashboard/data': {
                'backend': 'primary',
                'cache_ttl': 30,
                'data_type': 'dashboard'
            },
            # Removed /api/dashboard/mobile - use /api/mobile instead
            '/api/monitoring/status': {
                'backend': 'monitoring',
                'cache_ttl': 10,
                'data_type': 'monitoring'
            },
            '/api/signals': {
                'backend': 'primary',
                'cache_ttl': 60,
                'data_type': 'signals'
            }
        }
    
    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key for request"""
        path = request.url.path
        query = str(request.query_params)
        return f"gateway:{path}:{hashlib.md5(query.encode()).hexdigest()[:8]}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        return request.headers.get('X-Forwarded-For', 
               request.headers.get('X-Real-IP', 
               request.client.host if request.client else 'unknown'))
    
    async def _fetch_from_backend(self, 
                                 backend_url: str, 
                                 path: str, 
                                 params: Dict[str, Any] = None,
                                 timeout: int = 5) -> Dict[str, Any]:
        """Fetch data from backend service with timeout and error handling"""
        url = f"{backend_url}{path}"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Backend returned status {response.status}"
                        )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Backend timeout")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Backend error: {str(e)}")
    
    async def route_request(self, request: Request) -> JSONResponse:
        """
        Main request routing with caching, rate limiting, and error handling
        """
        start_time = time.time()
        path = request.url.path
        client_ip = self._get_client_ip(request)
        cache_hit = False
        error_msg = None
        
        try:
            # Rate limiting check
            rate_check = await self.rate_limiter.check_rate_limit(request)
            if not rate_check['allowed']:
                response = JSONResponse(
                    status_code=429,
                    content={
                        'error': 'Rate limit exceeded',
                        'retry_after': rate_check['retry_after'],
                        'tokens_remaining': rate_check['tokens_remaining']
                    }
                )
                response.headers['X-RateLimit-Limit'] = str(self.rate_limiter.requests_per_second)
                response.headers['X-RateLimit-Remaining'] = str(rate_check['tokens_remaining'])
                response.headers['Retry-After'] = str(int(rate_check['retry_after']))
                
                self.request_logger.log_request(
                    request.method, path, client_ip, start_time, time.time(), 429
                )
                return response
            
            # Check cache first
            cache_key = self._get_cache_key(request)
            cached_response = await self.cache.get(cache_key, 'gateway')
            
            if cached_response is not None:
                cache_hit = True
                response = JSONResponse(content=cached_response)
                response.headers['X-Cache'] = 'HIT'
                response.headers['X-Response-Time'] = str(round((time.time() - start_time) * 1000, 2))
                
                self.request_logger.log_request(
                    request.method, path, client_ip, start_time, time.time(), 200, cache_hit=True
                )
                return response
            
            # Route to backend
            route_info = self.route_config.get(path, {
                'backend': 'primary',
                'cache_ttl': 60,
                'data_type': 'default'
            })
            
            backend_url = self.backends.get(route_info['backend'], self.backends['primary'])
            
            # Apply circuit breaker if enabled
            fetch_func = self._fetch_from_backend
            if self.circuit_breaker:
                fetch_func = self.circuit_breaker.call(fetch_func)
            
            # Fetch from backend
            data = await fetch_func(
                backend_url, 
                path, 
                dict(request.query_params),
                timeout=10
            )
            
            # Cache the response
            await self.cache.set(
                cache_key, 
                data, 
                route_info['data_type'],
                force_l1=True  # Gateway responses should go to L1
            )
            
            response = JSONResponse(content=data)
            response.headers['X-Cache'] = 'MISS'
            response.headers['X-Backend'] = route_info['backend']
            response.headers['X-Response-Time'] = str(round((time.time() - start_time) * 1000, 2))
            
            self.request_logger.log_request(
                request.method, path, client_ip, start_time, time.time(), 200, cache_hit=False
            )
            return response
            
        except HTTPException as e:
            error_msg = str(e.detail)
            response = JSONResponse(
                status_code=e.status_code,
                content={'error': e.detail}
            )
            self.request_logger.log_request(
                request.method, path, client_ip, start_time, time.time(), 
                e.status_code, error=error_msg
            )
            return response
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gateway error for {path}: {e}")
            response = JSONResponse(
                status_code=500,
                content={'error': 'Internal gateway error'}
            )
            self.request_logger.log_request(
                request.method, path, client_ip, start_time, time.time(), 
                500, error=error_msg
            )
            return response
    
    async def get_gateway_metrics(self) -> Dict[str, Any]:
        """Get comprehensive gateway metrics"""
        cache_metrics = self.cache.get_performance_metrics()
        rate_limit_stats = self.rate_limiter.get_stats()
        request_metrics = self.request_logger.get_metrics()
        circuit_breaker_status = self.circuit_breaker.get_status() if self.circuit_breaker else None
        
        return {
            'gateway': {
                'status': 'operational',
                'uptime_seconds': time.time() - cache_metrics.get('start_time', time.time()),
                'version': '2.0.0'
            },
            'cache': cache_metrics,
            'rate_limiting': rate_limit_stats,
            'requests': request_metrics,
            'circuit_breaker': circuit_breaker_status,
            'backends': {
                backend: {'url': url, 'status': 'unknown'} 
                for backend, url in self.backends.items()
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive gateway health check"""
        health = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {}
        }
        
        # Check cache health
        try:
            cache_health = await self.cache.health_check()
            health['components']['cache'] = cache_health
            if cache_health['status'] != 'healthy':
                health['status'] = 'degraded'
        except Exception as e:
            health['components']['cache'] = {'status': 'unhealthy', 'error': str(e)}
            health['status'] = 'degraded'
        
        # Check backend services
        backend_status = {}
        for backend_name, backend_url in self.backends.items():
            try:
                start_time = time.time()
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
                    async with session.get(f"{backend_url}/health") as response:
                        response_time = (time.time() - start_time) * 1000
                        if response.status == 200:
                            backend_status[backend_name] = {
                                'status': 'healthy',
                                'response_time_ms': round(response_time, 2)
                            }
                        else:
                            backend_status[backend_name] = {
                                'status': 'unhealthy',
                                'status_code': response.status
                            }
                            if health['status'] == 'healthy':
                                health['status'] = 'degraded'
            except Exception as e:
                backend_status[backend_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                if health['status'] == 'healthy':
                    health['status'] = 'degraded'
        
        health['components']['backends'] = backend_status
        
        # Add circuit breaker status
        if self.circuit_breaker:
            health['components']['circuit_breaker'] = self.circuit_breaker.get_status()
        
        return health


# Global gateway instance
_gateway_instance: Optional[APIGateway] = None

def get_api_gateway() -> APIGateway:
    """Get global API gateway instance"""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = APIGateway()
    return _gateway_instance
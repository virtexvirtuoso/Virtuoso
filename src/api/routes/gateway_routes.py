"""
Gateway Routes - Priority 2 Implementation
FastAPI routes that integrate with the API Gateway system
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
import logging
from src.api.gateway import get_api_gateway, APIGateway

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gateway", tags=["gateway"])

async def get_gateway() -> APIGateway:
    """Dependency to get API Gateway instance"""
    return get_api_gateway()

@router.get("/health")
async def gateway_health_check(gateway: APIGateway = Depends(get_gateway)):
    """Gateway health check endpoint"""
    try:
        health = await gateway.health_check()
        status_code = 200 if health['status'] == 'healthy' else 503
        return JSONResponse(content=health, status_code=status_code)
    except Exception as e:
        logger.error(f"Gateway health check error: {e}")
        return JSONResponse(
            content={
                'status': 'unhealthy',
                'error': str(e)
            },
            status_code=503
        )

@router.get("/metrics")
async def gateway_metrics(gateway: APIGateway = Depends(get_gateway)):
    """Get comprehensive gateway performance metrics"""
    try:
        metrics = await gateway.get_gateway_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        logger.error(f"Gateway metrics error: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")

@router.get("/stats")
async def gateway_stats(gateway: APIGateway = Depends(get_gateway)):
    """Get gateway statistics summary"""
    try:
        metrics = await gateway.get_gateway_metrics()
        
        # Extract key statistics
        stats = {
            'performance': {
                'total_hit_rate_percent': metrics['cache'].get('total_hit_rate_percent', 0),
                'avg_response_time_ms': metrics['requests'].get('avg_response_time_ms', 0),
                'p95_response_time_ms': metrics['requests'].get('p95_response_time_ms', 0),
                'cache_performance_rating': metrics['cache'].get('performance_rating', 'UNKNOWN')
            },
            'traffic': {
                'total_requests': metrics['requests'].get('total_requests', 0),
                'current_rate_per_second': metrics['rate_limiting'].get('current_global_rate_per_second', 0),
                'blocked_requests': metrics['rate_limiting'].get('total_blocked', 0),
                'error_rate_percent': metrics['requests'].get('error_rate_percent', 0)
            },
            'cache_tiers': {
                'l1_hit_rate_percent': metrics['cache'].get('l1_hit_rate_percent', 0),
                'l2_hits': metrics['cache'].get('l2_hits', 0),
                'promotions': metrics['cache'].get('promotions', 0),
                'redis_available': metrics['cache'].get('redis_available', False),
                'memcached_available': metrics['cache'].get('memcached_available', False)
            },
            'backends': len(metrics.get('backends', {})),
            'circuit_breaker': metrics.get('circuit_breaker', {}).get('state', 'N/A')
        }
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"Gateway stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@router.post("/clear-cache")
async def clear_gateway_cache(pattern: str = "*", gateway: APIGateway = Depends(get_gateway)):
    """Clear gateway cache entries matching pattern"""
    try:
        cleared_count = await gateway.cache.clear_pattern(f"gateway:{pattern}")
        return JSONResponse(content={
            'status': 'success',
            'cleared_entries': cleared_count,
            'pattern': pattern
        })
    except Exception as e:
        logger.error(f"Gateway cache clear error: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

@router.get("/cache-status")
async def cache_status(gateway: APIGateway = Depends(get_gateway)):
    """Get detailed cache status across all tiers"""
    try:
        cache_health = await gateway.cache.health_check()
        performance_metrics = gateway.cache.get_performance_metrics()
        
        return JSONResponse(content={
            'health': cache_health,
            'performance': performance_metrics,
            'recommendations': _get_cache_recommendations(performance_metrics)
        })
        
    except Exception as e:
        logger.error(f"Cache status error: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting cache status: {str(e)}")

def _get_cache_recommendations(metrics: Dict[str, Any]) -> List[str]:
    """Generate cache optimization recommendations"""
    recommendations = []
    
    hit_rate = metrics.get('total_hit_rate_percent', 0)
    if hit_rate < 50:
        recommendations.append("Cache hit rate is below 50% - consider increasing TTL values")
    elif hit_rate < 70:
        recommendations.append("Cache hit rate could be improved - review caching strategy")
    
    avg_response = metrics.get('avg_l1_response_ms', 0)
    if avg_response > 10:
        recommendations.append("L1 cache response time is high - check Redis performance")
    
    if not metrics.get('redis_available', False):
        recommendations.append("Redis L1 cache is unavailable - performance is degraded")
    
    if not metrics.get('memcached_available', False):
        recommendations.append("Memcached L2 cache is unavailable - fallback to local cache")
    
    promotions = metrics.get('promotions', 0)
    total_requests = metrics.get('total_requests', 1)
    if promotions / total_requests > 0.1:
        recommendations.append("High promotion rate - consider adjusting L1 capacity")
    
    if not recommendations:
        recommendations.append("Cache performance is optimal")
    
    return recommendations

@router.api_route(
    "/proxy/{path:path}", 
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def gateway_proxy(request: Request, path: str, gateway: APIGateway = Depends(get_gateway)):
    """
    Universal proxy endpoint that routes requests through the gateway
    This allows any request to be processed with caching, rate limiting, etc.
    """
    # Reconstruct the original path
    original_path = f"/{path}"
    
    # Create a new request object with the original path
    scope = request.scope.copy()
    scope['path'] = original_path
    scope['raw_path'] = original_path.encode()
    
    # Create new request with modified scope
    proxy_request = Request(scope)
    
    # Route through gateway
    return await gateway.route_request(proxy_request)

# Dashboard-specific gateway routes
# TEMPORARILY DISABLED: Interfering with direct cache implementation
# @router.get("/dashboard/data")
# async def dashboard_data_via_gateway(request: Request, gateway: APIGateway = Depends(get_gateway)):
#     """Dashboard data endpoint via gateway with caching"""
#     return await gateway.route_request(request)

# Removed /dashboard/mobile alias route to avoid confusion
# Use /mobile instead (cleaner URL)

@router.get("/dashboard/signals")
async def signals_via_gateway(request: Request, gateway: APIGateway = Depends(get_gateway)):
    """Signals endpoint via gateway with caching"""
    return await gateway.route_request(request)

@router.get("/dashboard/overview")
async def overview_via_gateway(request: Request, gateway: APIGateway = Depends(get_gateway)):
    """Overview endpoint via gateway with caching"""
    return await gateway.route_request(request)
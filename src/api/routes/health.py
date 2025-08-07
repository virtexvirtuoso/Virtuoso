"""Independent health check endpoint."""

from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime
import psutil
import time

router = APIRouter()


@router.get("/health/system")
async def system_health() -> Dict[str, Any]:
    """Get system health independent of external services.
    
    Returns:
        System health status
    """
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get process info
    process = psutil.Process()
    process_info = {
        "pid": process.pid,
        "cpu_percent": process.cpu_percent(),
        "memory_mb": process.memory_info().rss / 1024 / 1024,
        "threads": process.num_threads(),
        "connections": len(process.connections())
    }
    
    # Check internal services
    services_status = {}
    
    # Check cache
    try:
        from pymemcache.client.base import Client
        mc = Client(('127.0.0.1', 11211))
        mc.get(b'test')
        mc.close()
        services_status["memcached"] = "healthy"
    except:
        services_status["memcached"] = "unavailable"
    
    # Check circuit breakers
    try:
        from src.core.resilience.circuit_breaker import get_all_circuit_states
        breakers = get_all_circuit_states()
        services_status["circuit_breakers"] = {
            "total": len(breakers),
            "open": sum(1 for b in breakers.values() if b["state"] == "open")
        }
    except:
        services_status["circuit_breakers"] = "not_initialized"
    
    # Overall health determination
    is_healthy = (
        cpu_percent < 90 and
        memory.percent < 90 and
        disk.percent < 90
    )
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - process.create_time(),
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent
        },
        "process": process_info,
        "services": services_status
    }


@router.get("/health/resilience")
async def resilience_health() -> Dict[str, Any]:
    """Get resilience system health.
    
    Returns:
        Resilience system status
    """
    try:
        from src.core.resilience.circuit_breaker import get_all_circuit_states
        from src.core.resilience.fallback_provider import get_fallback_provider
        
        breakers = get_all_circuit_states()
        fallback = get_fallback_provider()
        
        return {
            "status": "operational",
            "circuit_breakers": breakers,
            "fallback_system": fallback.get_health_status(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

"""
Health Check API Routes - Part of Phase 1: Emergency Stabilization
Provides HTTP endpoints for health monitoring integration
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def basic_health_check():
    """Basic health check endpoint - returns 200 if service is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "virtuoso_ccxt",
        "version": "1.0.0",
        "phase": "1_emergency_stabilization"
    }

@router.get("/health/quick")
async def quick_health_check():
    """Quick health check with minimal overhead"""
    timestamp = datetime.utcnow()
    checks = []
    
    # Quick memory check
    try:
        import psutil
        memory = psutil.virtual_memory()
        checks.append({
            "name": "memory",
            "status": "healthy" if memory.percent < 90 else "critical",
            "value": f"{memory.percent:.1f}%"
        })
    except Exception:
        checks.append({
            "name": "memory",
            "status": "unknown",
            "value": "check_failed"
        })
    
    # API response check
    checks.append({
        "name": "api_response",
        "status": "healthy",
        "value": "responding"
    })
    
    overall_status = "healthy"
    if any(check["status"] == "critical" for check in checks):
        overall_status = "critical"
    elif any(check["status"] == "unknown" for check in checks):
        overall_status = "warning"
    
    return {
        "overall_status": overall_status,
        "timestamp": timestamp.isoformat(),
        "checks": checks
    }
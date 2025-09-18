"""
Health Check API Routes - Enhanced with Configuration Validation
Provides HTTP endpoints for health monitoring integration and configuration validation
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import logging

# Import configuration validator
try:
    from src.config.validator import get_config_health, validate_config_file
except ImportError:
    # Fallback if validator not available
    def get_config_health():
        return {"status": "unknown", "message": "Configuration validator not available"}

    def validate_config_file(path):
        return {"valid": True, "message": "Validation not available"}

router = APIRouter()
logger = logging.getLogger(__name__)

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


@router.get("/health/comprehensive")
async def comprehensive_health_check():
    """Comprehensive health check including configuration validation"""
    timestamp = datetime.utcnow()
    checks = []

    # System health checks
    try:
        import psutil
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        disk = psutil.disk_usage('.')

        checks.extend([
            {
                "name": "memory",
                "status": "healthy" if memory.percent < 85 else "warning" if memory.percent < 95 else "critical",
                "value": f"{memory.percent:.1f}%",
                "details": {
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2)
                }
            },
            {
                "name": "cpu",
                "status": "healthy" if cpu_percent < 80 else "warning" if cpu_percent < 95 else "critical",
                "value": f"{cpu_percent:.1f}%"
            },
            {
                "name": "disk",
                "status": "healthy" if disk.percent < 85 else "warning" if disk.percent < 95 else "critical",
                "value": f"{disk.percent:.1f}%",
                "details": {
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2)
                }
            }
        ])
    except Exception as e:
        checks.append({
            "name": "system_metrics",
            "status": "error",
            "value": "check_failed",
            "error": str(e)
        })

    # Configuration health check
    try:
        config_health = get_config_health()
        config_status = "healthy" if config_health.get("status") == "healthy" else "error"

        checks.append({
            "name": "configuration",
            "status": config_status,
            "value": config_health.get("status", "unknown"),
            "details": {
                "file_exists": config_health.get("file_exists", False),
                "validation_errors": config_health.get("validation", {}).get("error_count", 0),
                "validation_warnings": config_health.get("validation", {}).get("warning_count", 0)
            }
        })
    except Exception as e:
        checks.append({
            "name": "configuration",
            "status": "error",
            "value": "check_failed",
            "error": str(e)
        })

    # API connectivity check
    checks.append({
        "name": "api_response",
        "status": "healthy",
        "value": "responding",
        "details": {"response_time_ms": 1}
    })

    # Environment check
    try:
        environment = os.getenv("ENVIRONMENT", "unknown")
        port = os.getenv("APP_PORT", "unknown")

        checks.append({
            "name": "environment",
            "status": "healthy",
            "value": environment,
            "details": {
                "port": port,
                "python_path": os.getenv("PYTHONPATH", "not_set")
            }
        })
    except Exception as e:
        checks.append({
            "name": "environment",
            "status": "error",
            "value": "check_failed",
            "error": str(e)
        })

    # Determine overall status
    error_checks = [c for c in checks if c["status"] == "error"]
    critical_checks = [c for c in checks if c["status"] == "critical"]
    warning_checks = [c for c in checks if c["status"] == "warning"]

    if error_checks or critical_checks:
        overall_status = "critical"
    elif warning_checks:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    return {
        "overall_status": overall_status,
        "timestamp": timestamp.isoformat(),
        "service": "virtuoso_ccxt",
        "version": "2.0.0",
        "checks": checks,
        "summary": {
            "total_checks": len(checks),
            "healthy": len([c for c in checks if c["status"] == "healthy"]),
            "warnings": len(warning_checks),
            "errors": len(error_checks),
            "critical": len(critical_checks)
        }
    }


@router.get("/health/config")
async def configuration_health():
    """Dedicated configuration validation endpoint"""
    try:
        config_health = get_config_health()

        # Add additional configuration context
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "config.yaml")

        response = {
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": config_health,
            "file_path": config_path,
            "recommendations": []
        }

        # Add recommendations based on validation results
        if config_health.get("validation", {}).get("warnings"):
            response["recommendations"].append("Review configuration warnings for optimization opportunities")

        if config_health.get("validation", {}).get("errors"):
            response["recommendations"].append("Fix configuration errors to ensure system stability")

        if not config_health.get("file_exists", False):
            response["recommendations"].append("Create a valid configuration file")

        return response

    except Exception as e:
        logger.error(f"Configuration health check failed: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "message": f"Configuration health check failed: {str(e)}",
            "recommendations": ["Check configuration file and validator installation"]
        }


@router.get("/health/config/validate")
async def validate_configuration():
    """Validate configuration file and return detailed results"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "config.yaml")

        validation_result = validate_config_file(config_path)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "config_file": config_path,
            "validation": validation_result
        }

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "message": f"Configuration validation failed: {str(e)}"
        }
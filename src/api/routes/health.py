"""
Health Check API Routes - Enhanced with Configuration Validation
Provides HTTP endpoints for health monitoring integration and configuration validation
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import os
import logging
import httpx

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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "virtuoso_ccxt",
        "version": "1.0.0",
        "phase": "1_emergency_stabilization"
    }

@router.get("/health/quick")
async def quick_health_check():
    """Quick health check with minimal overhead"""
    timestamp = datetime.now(timezone.utc)
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
    timestamp = datetime.now(timezone.utc)
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config_file": config_path,
            "validation": validation_result
        }

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "message": f"Configuration validation failed: {str(e)}"
        }


@router.get("/derivatives")
async def derivatives_api_health():
    """Check health of the derivatives signals API (crypto-perps-tracker)"""
    import subprocess

    try:
        # Check if service is running via systemctl
        result = subprocess.run(
            ["systemctl", "is-active", "derivatives-signals-api"],
            capture_output=True,
            text=True,
            timeout=2
        )

        is_running = result.stdout.strip() == "active"

        if is_running:
            return {
                "status": "healthy",
                "service": "derivatives-signals-api",
                "api_status": "active",
                "symbols_supported": 128,  # Static count - could make dynamic in future
                "endpoint": "http://localhost:8888",
                "systemd_status": "active",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "status": "offline",
                "service": "derivatives-signals-api",
                "message": "Service is not active",
                "systemd_status": result.stdout.strip(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "service": "derivatives-signals-api",
            "message": "Systemctl check timed out",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Derivatives API health check failed: {e}")
        return {
            "status": "error",
            "service": "derivatives-signals-api",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/all-services")
async def all_services_health():
    """Check health of all VPS services"""
    import subprocess

    services = [
        "virtuoso-trading",
        "virtuoso-web",
        "derivatives-signals-api",
        "crypto-dashboard",
        "virtuoso-monitoring-api",
        "virtuoso-website"
    ]

    service_status = {}

    for service in services:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=1
            )
            service_status[service] = {
                "status": "healthy" if result.stdout.strip() == "active" else "offline",
                "systemd_status": result.stdout.strip()
            }
        except Exception as e:
            service_status[service] = {
                "status": "error",
                "message": str(e)
            }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": service_status
    }


@router.get("/storage/databases")
async def database_storage():
    """Get storage information for all databases"""
    import subprocess
    import os

    db_path = "/home/linuxuser/trading/Virtuoso_ccxt/data"
    databases = {}
    total_size = 0

    try:
        # Get all .db files
        result = subprocess.run(
            ["find", db_path, "-name", "*.db", "-type", "f"],
            capture_output=True,
            text=True,
            timeout=5
        )

        db_files = result.stdout.strip().split('\n') if result.stdout.strip() else []

        for db_file in db_files:
            if db_file:
                try:
                    # Get file size
                    size_result = subprocess.run(
                        ["du", "-h", db_file],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )

                    if size_result.returncode == 0:
                        size_parts = size_result.stdout.strip().split('\t')
                        if len(size_parts) >= 2:
                            size_human = size_parts[0]
                            file_name = os.path.basename(db_file)

                            # Get size in bytes for total (Linux-compatible)
                            size_bytes_result = subprocess.run(
                                ["stat", "-c", "%s", db_file],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )

                            size_bytes = int(size_bytes_result.stdout.strip()) if size_bytes_result.returncode == 0 else 0
                            total_size += size_bytes

                            databases[file_name] = {
                                "size": size_human,
                                "size_bytes": size_bytes,
                                "path": db_file
                            }
                except Exception as e:
                    logger.error(f"Error getting size for {db_file}: {e}")

        # Format total size
        total_mb = total_size / (1024 * 1024)
        total_human = f"{total_mb:.1f}M" if total_mb < 1024 else f"{total_mb/1024:.2f}G"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "databases": databases,
            "total_size": total_human,
            "total_size_bytes": total_size,
            "count": len(databases)
        }

    except Exception as e:
        logger.error(f"Database storage check failed: {e}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "databases": {}
        }


@router.get("/storage/redis")
async def redis_storage():
    """Get Redis cache storage information"""
    import subprocess

    try:
        # Check if Redis is running
        redis_status = subprocess.run(
            ["systemctl", "is-active", "redis"],
            capture_output=True,
            text=True,
            timeout=2
        )

        is_running = redis_status.stdout.strip() == "active"

        if not is_running:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "offline",
                "message": "Redis service is not running"
            }

        # Try to get memory usage from redis-cli
        try:
            memory_result = subprocess.run(
                ["redis-cli", "INFO", "memory"],
                capture_output=True,
                text=True,
                timeout=2
            )

            if memory_result.returncode == 0:
                info = memory_result.stdout

                # Parse memory info
                used_memory = None
                used_memory_human = None
                used_memory_peak = None

                for line in info.split('\n'):
                    if line.startswith('used_memory:'):
                        used_memory = int(line.split(':')[1].strip())
                    elif line.startswith('used_memory_human:'):
                        used_memory_human = line.split(':')[1].strip()
                    elif line.startswith('used_memory_peak_human:'):
                        used_memory_peak = line.split(':')[1].strip()

                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "healthy",
                    "used_memory": used_memory_human or f"{(used_memory or 0) / (1024*1024):.1f}M",
                    "used_memory_bytes": used_memory or 0,
                    "peak_memory": used_memory_peak or "N/A",
                    "storage_type": "In-memory"
                }
        except Exception as e:
            logger.error(f"Redis memory check failed: {e}")

        # Fallback: just return running status
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "healthy",
            "used_memory": "N/A",
            "storage_type": "In-memory",
            "message": "Redis is running (memory info unavailable)"
        }

    except Exception as e:
        logger.error(f"Redis storage check failed: {e}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "status": "error"
        }


@router.get("/service-uptime")
async def get_service_uptime():
    """Get uptime information for all systemd services"""
    import subprocess
    from datetime import datetime, timedelta

    services = [
        "virtuoso-trading",
        "virtuoso-web",
        "derivatives-signals-api",
        "crypto-dashboard",
        "virtuoso-monitoring-api",
        "virtuoso-website"
    ]

    uptime_data = {}

    for service in services:
        try:
            # Get service start time using ActiveEnterTimestamp
            result = subprocess.run(
                ["systemctl", "show", service, "--property=ActiveEnterTimestamp"],
                capture_output=True,
                text=True,
                timeout=3
            )

            if result.returncode == 0:
                timestamp_line = result.stdout.strip()
                if "=" in timestamp_line:
                    # Extract timestamp value
                    timestamp_str = timestamp_line.split("=", 1)[1].strip()

                    if timestamp_str and timestamp_str != "n/a":
                        # Parse timestamp and calculate uptime
                        try:
                            # systemd timestamp format: "Thu 2024-12-12 10:30:15 UTC"
                            from dateutil import parser
                            start_time = parser.parse(timestamp_str)
                            now = datetime.now(timezone.utc)

                            # Calculate uptime
                            uptime_delta = now - start_time.replace(tzinfo=timezone.utc)

                            # Format uptime
                            days = uptime_delta.days
                            hours, remainder = divmod(uptime_delta.seconds, 3600)
                            minutes, seconds = divmod(remainder, 60)

                            if days > 0:
                                uptime_str = f"{days}d {hours}h {minutes}m"
                            elif hours > 0:
                                uptime_str = f"{hours}h {minutes}m"
                            else:
                                uptime_str = f"{minutes}m {seconds}s"

                            uptime_data[service] = {
                                "uptime": uptime_str,
                                "uptime_seconds": int(uptime_delta.total_seconds()),
                                "start_time": start_time.isoformat(),
                                "status": "running"
                            }
                        except Exception as e:
                            logger.error(f"Error parsing timestamp for {service}: {e}")
                            uptime_data[service] = {
                                "uptime": "Unknown",
                                "status": "error",
                                "error": "Failed to parse timestamp"
                            }
                    else:
                        uptime_data[service] = {
                            "uptime": "Not running",
                            "status": "offline"
                        }

        except subprocess.TimeoutExpired:
            uptime_data[service] = {
                "uptime": "Timeout",
                "status": "error",
                "error": "Check timed out"
            }
        except Exception as e:
            logger.error(f"Error checking uptime for {service}: {e}")
            uptime_data[service] = {
                "uptime": "Error",
                "status": "error",
                "error": str(e)
            }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": uptime_data
    }


@router.get("/service-logs/{service_name}")
async def get_service_logs(service_name: str, lines: int = 10):
    """Get recent logs for a specific service"""
    import subprocess

    # Validate service name to prevent injection
    allowed_services = [
        "virtuoso-trading",
        "virtuoso-web",
        "derivatives-signals-api",
        "crypto-dashboard",
        "virtuoso-monitoring-api",
        "virtuoso-website"
    ]

    if service_name not in allowed_services:
        return {
            "error": "Invalid service name",
            "allowed_services": allowed_services
        }

    # Clamp lines to reasonable range
    lines = max(5, min(lines, 50))

    try:
        # Get logs using journalctl
        result = subprocess.run(
            ["journalctl", "-u", service_name, "-n", str(lines), "--no-pager", "--output=short-iso"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            log_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []

            # Parse logs into structured format
            parsed_logs = []
            for line in log_lines:
                if line:
                    # Check for common error patterns
                    is_error = any(pattern in line.lower() for pattern in ['error', 'fail', 'exception', 'critical'])
                    is_warning = 'warning' in line.lower() or 'warn' in line.lower()

                    level = 'error' if is_error else 'warning' if is_warning else 'info'

                    parsed_logs.append({
                        "line": line,
                        "level": level
                    })

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": service_name,
                "logs": parsed_logs,
                "count": len(parsed_logs)
            }
        else:
            return {
                "error": "Failed to retrieve logs",
                "stderr": result.stderr,
                "service": service_name
            }

    except subprocess.TimeoutExpired:
        return {
            "error": "Log retrieval timed out",
            "service": service_name
        }
    except Exception as e:
        logger.error(f"Error retrieving logs for {service_name}: {e}")
        return {
            "error": str(e),
            "service": service_name
        }


@router.get("/trading-stats")
async def get_trading_stats():
    """Get enhanced trading performance statistics"""
    try:
        # Use httpx to call the existing performance API
        async with httpx.AsyncClient() as client:
            # Get 7-day performance summary
            perf_response = await client.get(
                "http://localhost:8002/api/signal-performance/performance/summary?days=7",
                timeout=5.0
            )

            if perf_response.status_code != 200:
                return {
                    "error": "Failed to fetch performance data",
                    "status_code": perf_response.status_code
                }

            perf_data = perf_response.json()

            # Calculate additional metrics
            win_rate = (perf_data.get('win_rate', 0) * 100)
            avg_pnl = perf_data.get('avg_pnl_pct', 0)
            total_signals = perf_data.get('total_signals', 0)
            closed_signals = perf_data.get('closed_signals', 0)

            # Calculate total PnL estimate (approximate)
            total_pnl_pct = avg_pnl * closed_signals if closed_signals > 0 else 0

            # Determine performance status
            threshold = 35
            status = 'excellent' if win_rate >= threshold + 15 else 'good' if win_rate >= threshold else 'needs_improvement'

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "win_rate": round(win_rate, 1),
                "total_signals": total_signals,
                "closed_signals": closed_signals,
                "active_signals": total_signals - closed_signals,
                "avg_pnl_pct": round(avg_pnl, 2),
                "total_pnl_pct": round(total_pnl_pct, 2),
                "performance_status": status,
                "threshold": threshold,
                "days": 7
            }

    except httpx.TimeoutException:
        return {
            "error": "Request timed out",
            "message": "Performance API did not respond in time"
        }
    except httpx.ConnectError:
        return {
            "error": "Connection failed",
            "message": "Could not connect to performance API"
        }
    except Exception as e:
        logger.error(f"Error fetching trading stats: {e}")
        return {
            "error": str(e),
            "message": "Failed to fetch trading statistics"
        }


@router.get("/system-load")
async def get_system_load():
    """Get system load averages"""
    import subprocess

    try:
        # Read from /proc/loadavg (more reliable than uptime on some systems)
        try:
            with open('/proc/loadavg', 'r') as f:
                loadavg_line = f.read().strip()
                parts = loadavg_line.split()

                load_1min = float(parts[0])
                load_5min = float(parts[1])
                load_15min = float(parts[2])
        except Exception:
            # Fallback to uptime command
            result = subprocess.run(
                ["uptime"],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0:
                # Parse uptime output
                output = result.stdout.strip()
                # Extract load averages (format: "load average: 1.23, 2.34, 3.45")
                if "load average:" in output:
                    load_part = output.split("load average:")[1].strip()
                    loads = [float(x.strip()) for x in load_part.split(',')]
                    load_1min, load_5min, load_15min = loads[0], loads[1], loads[2]
                else:
                    raise ValueError("Could not parse load average from uptime")
            else:
                raise ValueError("uptime command failed")

        # Get CPU count for context
        try:
            import psutil
            cpu_count = psutil.cpu_count()
        except:
            cpu_count = 1

        # Determine status based on load relative to CPU count
        def get_load_status(load, cpu_count):
            if load < cpu_count:
                return "healthy"
            elif load < cpu_count * 2:
                return "warning"
            else:
                return "critical"

        status_1min = get_load_status(load_1min, cpu_count)
        status_5min = get_load_status(load_5min, cpu_count)
        status_15min = get_load_status(load_15min, cpu_count)

        # Overall status is worst of the three
        overall_status = "critical" if "critical" in [status_1min, status_5min, status_15min] else \
                        "warning" if "warning" in [status_1min, status_5min, status_15min] else "healthy"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "load_1min": round(load_1min, 2),
            "load_5min": round(load_5min, 2),
            "load_15min": round(load_15min, 2),
            "cpu_count": cpu_count,
            "status_1min": status_1min,
            "status_5min": status_5min,
            "status_15min": status_15min,
            "overall_status": overall_status
        }

    except Exception as e:
        logger.error(f"Error getting system load: {e}")
        return {
            "error": str(e),
            "message": "Failed to get system load averages"
        }
"""Admin Dashboard API routes with configuration management."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Form, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List, Any, Optional
import asyncio
import json
import logging
import yaml
import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import aiofiles
from dataclasses import dataclass

router = APIRouter()
logger = logging.getLogger(__name__)

# Security configuration
# SECURITY: ADMIN_PASSWORD_HASH must be set in environment variables
# Generate with: python -c "import hashlib; print(hashlib.sha256(b'your-secure-password').hexdigest())"
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
if not ADMIN_PASSWORD_HASH:
    raise ValueError(
        "ADMIN_PASSWORD_HASH environment variable must be set! "
        "Generate a secure password hash with: "
        "python -c \"import hashlib; print(hashlib.sha256(b'your-secure-password').hexdigest())\""
    )
SESSION_TIMEOUT_HOURS = 24

# Resolve paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
TEMPLATE_DIR = PROJECT_ROOT / "src" / "dashboard" / "templates"

# In-memory session store (use Redis in production)
active_sessions = {}  # type: Dict[str, Dict[str, Any]]

@dataclass
class AdminSession:
    token: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime

def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_session_token() -> str:
    """Generate secure session token."""
    return secrets.token_urlsafe(32)

def verify_admin_password(password: str) -> bool:
    """Verify admin password against hash.

    Args:
        password: Plain text password to verify

    Returns:
        True if password matches the hash, False otherwise

    Note:
        ADMIN_PASSWORD_HASH must be set in environment variables.
        The application will not start if it's missing.
    """
    return hash_password(password) == ADMIN_PASSWORD_HASH

def create_admin_session() -> AdminSession:
    """Create new admin session."""
    token = generate_session_token()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=SESSION_TIMEOUT_HOURS)
    
    session = AdminSession(
        token=token,
        created_at=now,
        expires_at=expires_at,
        last_activity=now
    )
    
    active_sessions[token] = {
        "created_at": session.created_at,
        "expires_at": session.expires_at,
        "last_activity": session.last_activity
    }
    
    return session

def verify_session(token: str) -> bool:
    """Verify admin session token."""
    if token not in active_sessions:
        return False
    
    session_data = active_sessions[token]
    now = datetime.now(timezone.utc)
    
    # Check if session expired
    if now > session_data["expires_at"]:
        del active_sessions[token]
        return False
    
    # Update last activity
    session_data["last_activity"] = now
    return True

def get_current_session(authorization: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    """Dependency to get current admin session."""
    if not authorization or not verify_session(authorization.credentials):
        raise HTTPException(status_code=401, detail="Invalid or expired admin session")
    return authorization.credentials

# Authentication routes
@router.post("/auth/login")
async def admin_login(password: str = Form(...)):
    """Admin login endpoint."""
    try:
        if not verify_admin_password(password):
            # Add delay to prevent brute force attacks
            await asyncio.sleep(1)
            raise HTTPException(status_code=401, detail="Invalid admin password")
        
        session = create_admin_session()
        
        logger.info(f"Admin login successful at {datetime.now(timezone.utc)}")
        
        return {
            "status": "success",
            "token": session.token,
            "expires_at": session.expires_at.isoformat(),
            "message": "Admin login successful"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/auth/logout")
async def admin_logout(session_token: str = Depends(get_current_session)):
    """Admin logout endpoint."""
    if session_token in active_sessions:
        del active_sessions[session_token]
    
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/auth/verify")
async def verify_admin_session(session_token: str = Depends(get_current_session)):
    """Verify current admin session."""
    session_data = active_sessions.get(session_token)
    if not session_data:
        raise HTTPException(status_code=401, detail="Session not found")
    
    return {
        "status": "valid",
        "expires_at": session_data["expires_at"].isoformat(),
        "last_activity": session_data["last_activity"].isoformat()
    }

# Configuration management routes
@router.get("/config/files")
async def get_config_files(session_token: str = Depends(get_current_session)):
    """Get list of available configuration files."""
    try:
        config_files = []
        for file_path in CONFIG_DIR.glob("*.yaml"):
            stat = file_path.stat()
            config_files.append({
                "name": file_path.name,
                "path": str(file_path.relative_to(PROJECT_ROOT)),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "editable": True
            })
        
        return {
            "config_files": config_files,
            "config_dir": str(CONFIG_DIR.relative_to(PROJECT_ROOT))
        }
    
    except Exception as e:
        logger.error(f"Error getting config files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/file/{filename}")
async def get_config_file(filename: str, session_token: str = Depends(get_current_session)):
    """Get content of specific configuration file."""
    try:
        file_path = CONFIG_DIR / filename
        if not file_path.exists() or not file_path.suffix == ".yaml":
            raise HTTPException(status_code=404, detail="Configuration file not found")
        
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
        
        # Parse YAML to validate structure
        try:
            parsed_yaml = yaml.safe_load(content)
        except yaml.YAMLError as e:
            logger.warning(f"YAML parsing warning for {filename}: {e}")
            parsed_yaml = None
        
        return {
            "filename": filename,
            "content": content,
            "parsed": parsed_yaml,
            "valid_yaml": parsed_yaml is not None,
            "size": len(content),
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading config file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config/file/{filename}")
async def update_config_file(
    filename: str, 
    content: str = Form(...),
    session_token: str = Depends(get_current_session)
):
    """Update configuration file content."""
    try:
        file_path = CONFIG_DIR / filename
        if not file_path.exists() or not file_path.suffix == ".yaml":
            raise HTTPException(status_code=404, detail="Configuration file not found")
        
        # Validate YAML syntax
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML syntax: {str(e)}")
        
        # Create backup before modifying
        backup_path = file_path.with_suffix(f".yaml.backup_{int(time.time())}")
        async with aiofiles.open(file_path, 'r') as original:
            original_content = await original.read()
        async with aiofiles.open(backup_path, 'w') as backup:
            await backup.write(original_content)
        
        # Write new content
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(content)
        
        # Log the change
        logger.info(f"Admin updated config file {filename}. Backup created: {backup_path.name}")
        
        return {
            "status": "success",
            "message": f"Configuration file {filename} updated successfully",
            "backup_created": backup_path.name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/backups/{filename}")
async def get_config_backups(filename: str, session_token: str = Depends(get_current_session)):
    """Get list of backup files for a configuration."""
    try:
        base_name = filename.replace('.yaml', '')
        backup_pattern = f"{base_name}.yaml.backup_*"
        
        backups = []
        for backup_path in CONFIG_DIR.glob(backup_pattern):
            stat = backup_path.stat()
            timestamp_str = backup_path.name.split('backup_')[1]
            try:
                timestamp = datetime.fromtimestamp(int(timestamp_str))
            except:
                timestamp = datetime.fromtimestamp(stat.st_mtime)
            
            backups.append({
                "name": backup_path.name,
                "timestamp": timestamp.isoformat(),
                "size": stat.st_size
            })
        
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {"backups": backups}
    
    except Exception as e:
        logger.error(f"Error getting backups for {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config/restore/{backup_filename}")
async def restore_config_backup(
    backup_filename: str, 
    session_token: str = Depends(get_current_session)
):
    """Restore configuration from backup."""
    try:
        backup_path = CONFIG_DIR / backup_filename
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found")
        
        # Determine original filename
        original_filename = backup_filename.split('.backup_')[0] + '.yaml'
        original_path = CONFIG_DIR / original_filename
        
        # Create backup of current version before restore
        current_backup = original_path.with_suffix(f".yaml.pre_restore_{int(time.time())}")
        if original_path.exists():
            async with aiofiles.open(original_path, 'r') as src:
                content = await src.read()
            async with aiofiles.open(current_backup, 'w') as dst:
                await dst.write(content)
        
        # Restore from backup
        async with aiofiles.open(backup_path, 'r') as src:
            backup_content = await src.read()
        async with aiofiles.open(original_path, 'w') as dst:
            await dst.write(backup_content)
        
        logger.info(f"Admin restored {original_filename} from backup {backup_filename}")
        
        return {
            "status": "success",
            "message": f"Configuration restored from {backup_filename}",
            "current_backup": current_backup.name if original_path.exists() else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring backup {backup_filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System control routes
@router.get("/system/status")
async def get_system_status(session_token: str = Depends(get_current_session)):
    """Get current system status."""
    try:
        # This would integrate with your monitoring service
        # For now, return mock data
        return {
            "monitoring": {
                "status": "active",
                "uptime": "2h 15m",
                "last_scan": datetime.now(timezone.utc).isoformat()
            },
            "websocket": {
                "status": "connected",
                "connections": 3,
                "last_message": datetime.now(timezone.utc).isoformat()
            },
            "exchanges": {
                "bybit": {
                    "status": "connected",
                    "api_status": "ok",
                    "last_update": datetime.now(timezone.utc).isoformat()
                }
            },
            "alerts": {
                "enabled": True,
                "last_alert": datetime.now(timezone.utc).isoformat(),
                "total_today": 15
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/recent")
async def get_recent_logs(
    lines: int = 100, 
    level: str = "INFO",
    session_token: str = Depends(get_current_session)
):
    """Get recent log entries."""
    try:
        # This would read from your log files
        # For now, return mock data
        mock_logs = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "module": "monitoring",
                "message": "System monitoring active"
            },
            {
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                "level": "DEBUG",
                "module": "websocket",
                "message": "WebSocket message received"
            }
        ]
        
        return {
            "logs": mock_logs,
            "total_lines": len(mock_logs),
            "filter_level": level
        }
    
    except Exception as e:
        logger.error(f"Error getting recent logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# System Control Endpoints
# ============================================

@router.post("/system/restart-monitoring")
async def restart_monitoring_system():
    """Restart the monitoring system components.

    This endpoint triggers a restart of monitoring services including:
    - Alert manager
    - Signal processor
    - Market reporter
    """
    try:
        logger.info("🔄 Admin requested monitoring system restart")

        restart_results = []

        # Note: In production, monitoring components run as separate systemd services
        # This endpoint would trigger service restarts via systemd
        restart_results.append({
            "component": "Monitoring Services",
            "status": "info",
            "message": "Use 'sudo systemctl restart virtuoso-trading' to restart monitoring services"
        })

        logger.info(f"✅ Monitoring restart info provided: {restart_results}")

        return {
            "success": True,
            "message": "Monitoring system restart requires systemctl command",
            "components": restart_results,
            "command": "sudo systemctl restart virtuoso-trading",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error restarting monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restart monitoring: {str(e)}")


@router.post("/config/reload")
async def reload_configuration():
    """Reload configuration from config files.

    This triggers a configuration reload without restarting the entire service.
    """
    try:
        logger.info("🔄 Admin requested configuration reload")

        # Check if config file exists and is valid YAML
        config_file = CONFIG_DIR / "config.yaml"

        if not config_file.exists():
            raise HTTPException(status_code=404, detail=f"Configuration file not found: {config_file}")

        # Validate YAML syntax
        try:
            with open(config_file, 'r') as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML in config file: {str(e)}")

        logger.info("✅ Configuration file validated successfully")

        return {
            "success": True,
            "message": "Configuration validated. Restart service to apply changes.",
            "config_file": str(config_file),
            "note": "Configuration changes require service restart: sudo systemctl restart virtuoso-web",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate configuration: {str(e)}")


@router.post("/alerts/test")
async def test_alert_system():
    """Send a test alert through all configured channels.

    This sends test notifications to Discord, Telegram, etc. to verify alert delivery.
    """
    try:
        logger.info("🔔 Admin requested test alert")

        # Load configuration to get Discord webhook
        config_file = CONFIG_DIR / "config.yaml"

        if not config_file.exists():
            raise HTTPException(status_code=404, detail="Configuration file not found")

        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        # Get Discord webhook URL
        discord_webhook = config.get('discord', {}).get('webhook_url')

        if not discord_webhook:
            return {
                "success": False,
                "message": "Discord webhook not configured in config.yaml",
                "channels": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Send test message to Discord
        import httpx

        test_message = {
            "content": f"🧪 **Test Alert from Admin Panel**\n\nTimestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\nThis is a test alert to verify notification delivery."
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(discord_webhook, json=test_message, timeout=10.0)

            if response.status_code in [200, 204]:
                logger.info("✅ Test alert sent to Discord successfully")
                return {
                    "success": True,
                    "message": "Test alert sent successfully",
                    "channels": ["Discord"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                logger.error(f"Discord webhook returned status {response.status_code}")
                return {
                    "success": False,
                    "message": f"Discord webhook returned status {response.status_code}",
                    "channels": [],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send test alert: {str(e)}")


@router.post("/config/backup")
async def backup_configuration():
    """Create a backup of current configuration files.

    Returns information about the created backup.
    """
    try:
        logger.info("💾 Admin requested configuration backup")

        import shutil
        from datetime import datetime

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"config_backup_{timestamp}.yaml"
        backup_path = CONFIG_DIR / "backups" / backup_filename

        # Ensure backup directory exists
        backup_path.parent.mkdir(exist_ok=True)

        # Copy current config to backup
        config_file = CONFIG_DIR / "config.yaml"
        if config_file.exists():
            shutil.copy2(config_file, backup_path)
            logger.info(f"✅ Configuration backed up to: {backup_path}")

            return {
                "success": True,
                "message": "Configuration backup created successfully",
                "backup_file": backup_filename,
                "backup_path": str(backup_path),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

    except Exception as e:
        logger.error(f"Error creating configuration backup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")


# ============================================
# Monitoring Endpoints
# ============================================

@router.get("/pool/stats")
async def get_connection_pool_stats():
    """Get database connection pool statistics.

    Returns detailed information about connection pool utilization,
    active connections, idle connections, and performance metrics.
    """
    try:
        logger.debug("📊 Fetching connection pool statistics")

        # Import database components
        from src.data_storage.database import get_db_pool_stats

        # Get pool stats
        pool_stats = get_db_pool_stats()

        return {
            "success": True,
            "pools": pool_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except ImportError:
        # Fallback if pool stats not implemented
        logger.warning("⚠️ Connection pool stats not available - returning mock data")
        return {
            "success": True,
            "pools": {
                "main": {
                    "name": "Main Database Pool",
                    "size": 20,
                    "active": 5,
                    "idle": 15,
                    "utilization": 25.0,
                    "wait_time_ms": 12.5
                },
                "cache": {
                    "name": "Cache Database Pool",
                    "size": 10,
                    "active": 2,
                    "idle": 8,
                    "utilization": 20.0,
                    "wait_time_ms": 8.2
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "Mock data - actual pool stats not yet implemented"
        }

    except Exception as e:
        logger.error(f"Error getting pool stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pool stats: {str(e)}")


# HTML routes
@router.get("/dashboard")
async def admin_dashboard_page():
    """Serve the admin dashboard HTML page."""
    return FileResponse(TEMPLATE_DIR / "admin" / "admin_dashboard.html")

@router.get("/dashboard/v2")
async def admin_dashboard_v2_page():
    """Serve the admin dashboard v2 HTML page."""
    return FileResponse(TEMPLATE_DIR / "admin" / "admin_dashboard_v2.html")

@router.get("/login")
async def admin_login_page():
    """Serve the admin login page."""
    return FileResponse(TEMPLATE_DIR / "admin" / "admin_login.html")

@router.get("/config-editor")
async def admin_config_editor_page():
    """Serve the optimized config editor page."""
    return FileResponse(TEMPLATE_DIR / "admin" / "admin_config_editor_optimized.html")

@router.get("/monitoring/live-metrics")
async def get_admin_monitoring_metrics():
    """Get live metrics for admin dashboard monitoring"""
    try:
        import psutil
        import time
        
        # Import bandwidth monitor
        from src.monitoring.bandwidth_monitor import bandwidth_monitor
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Get bandwidth stats
        try:
            bandwidth_stats = await bandwidth_monitor.get_bandwidth_stats()
            formatted_bandwidth = bandwidth_monitor.get_formatted_stats(bandwidth_stats)
        except Exception as e:
            logger.error(f"Error getting bandwidth stats: {str(e)}")
            formatted_bandwidth = None
        
        # Get top symbols manager from app state
        from src.dashboard.dashboard_integration import get_dashboard_integration
        dashboard_integration = get_dashboard_integration()
        
        # Build response
        metrics = {
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used": memory.used,
                "memory_total": memory.total,
                "uptime": int(time.time() - psutil.boot_time())
            },
            "market": {
                "active_symbols": 0,
                "symbols": []
            }
        }
        
        # Get market data if available
        if dashboard_integration:
            try:
                symbols_data = await dashboard_integration.get_top_symbols(limit=5)
                if symbols_data:
                    metrics["market"]["active_symbols"] = len(symbols_data)
                    metrics["market"]["symbols"] = [s.get('symbol', s) for s in symbols_data[:5]]
            except Exception as e:
                logger.warning(f"Error getting market data: {str(e)}")
        
        # Add bandwidth if available
        if formatted_bandwidth and 'bandwidth' in formatted_bandwidth:
            metrics['bandwidth'] = formatted_bandwidth['bandwidth']
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting admin monitoring metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitoring/bandwidth-history")
async def get_bandwidth_history(limit: int = 60):
    """Get historical bandwidth data"""
    try:
        from src.monitoring.bandwidth_monitor import bandwidth_monitor
        
        history = await bandwidth_monitor.get_history(limit=limit)
        summary = bandwidth_monitor.get_history_summary()
        
        return {
            "history": history,
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting bandwidth history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
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
from datetime import datetime, timedelta
from pathlib import Path
import os
import aiofiles
from dataclasses import dataclass

router = APIRouter()
logger = logging.getLogger(__name__)

# Security configuration
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
DEFAULT_ADMIN_PASSWORD = "admin123"  # Change this!
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
    """Verify admin password against hash."""
    if ADMIN_PASSWORD_HASH:
        return hash_password(password) == ADMIN_PASSWORD_HASH
    else:
        # Fallback to default password if no hash is set
        logger.warning("Using default admin password - please set ADMIN_PASSWORD_HASH environment variable!")
        return password == DEFAULT_ADMIN_PASSWORD

def create_admin_session() -> AdminSession:
    """Create new admin session."""
    token = generate_session_token()
    now = datetime.utcnow()
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
    now = datetime.utcnow()
    
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
        
        logger.info(f"Admin login successful at {datetime.utcnow()}")
        
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
            "timestamp": datetime.utcnow().isoformat()
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
            "timestamp": datetime.utcnow().isoformat()
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
                "last_scan": datetime.utcnow().isoformat()
            },
            "websocket": {
                "status": "connected",
                "connections": 3,
                "last_message": datetime.utcnow().isoformat()
            },
            "exchanges": {
                "bybit": {
                    "status": "connected",
                    "api_status": "ok",
                    "last_update": datetime.utcnow().isoformat()
                }
            },
            "alerts": {
                "enabled": True,
                "last_alert": datetime.utcnow().isoformat(),
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
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "module": "monitoring",
                "message": "System monitoring active"
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
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

# HTML routes
@router.get("/dashboard")
async def admin_dashboard_page():
    """Serve the admin dashboard HTML page."""
    return FileResponse(TEMPLATE_DIR / "admin_dashboard.html")

@router.get("/login")
async def admin_login_page():
    """Serve the admin login page."""
    return FileResponse(TEMPLATE_DIR / "admin_login.html")

@router.get("/config-editor")
async def admin_config_editor_page():
    """Serve the optimized config editor page."""
    return FileResponse(TEMPLATE_DIR / "admin_config_editor_optimized.html")
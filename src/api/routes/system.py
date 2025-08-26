"""Consolidated System Routes: Monitoring, Admin, Debug & Configuration Management."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Form, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List, Any, Optional
from src.core.exchanges.manager import ExchangeManager
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import json
import logging
import yaml
import hashlib
import secrets
import time
import os
import aiofiles
import psutil
import aiomcache

router = APIRouter()
logger = logging.getLogger(__name__)

# Admin Security Configuration
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
DEFAULT_ADMIN_PASSWORD = "admin123"  # Change this!
SESSION_TIMEOUT_HOURS = 24

# Path Configuration
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

# =============================================================================
# DEPENDENCY FUNCTIONS
# =============================================================================

async def get_exchange_manager(request: Request) -> ExchangeManager:
    """Dependency to get exchange manager from app state"""
    if not hasattr(request.app.state, "exchange_manager"):
        raise HTTPException(status_code=503, detail="Exchange manager not initialized")
    return request.app.state.exchange_manager

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

# =============================================================================
# SYSTEM MONITORING ENDPOINTS
# =============================================================================

@router.get("/status")
async def get_system_status(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict:
    """Get overall system status including CPU, memory, disk usage and exchange status"""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Exchange status
        exchange_status = {}
        for exchange_id, exchange in exchange_manager.exchanges.items():
            try:
                status = await exchange.fetch_status()
                exchange_status[exchange_id] = {
                    'online': status.get('online', False),
                    'has_trading': status.get('has_trading', False),
                    'rate_limit': status.get('rate_limit', {}),
                    'timestamp': status.get('timestamp', int(time.time() * 1000))
                }
            except Exception as e:
                exchange_status[exchange_id] = {
                    'online': False,
                    'error': str(e)
                }
        
        return {
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_percent': disk.percent,
                'disk_free': disk.free
            },
            'exchanges': exchange_status,
            'timestamp': int(time.time() * 1000)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/config")
async def get_config(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict:
    """Get system configuration (excluding sensitive data)"""
    try:
        config = {
            'exchanges': {},
            'system': {
                'version': os.getenv('VERSION', '1.0.0'),
                'environment': os.getenv('ENVIRONMENT', 'production'),
                'log_level': os.getenv('LOG_LEVEL', 'INFO')
            }
        }
        
        # Get exchange configs (excluding API keys)
        for exchange_id, exchange in exchange_manager.exchanges.items():
            exchange_config = exchange.describe()
            # Remove sensitive data
            exchange_config.pop('apiKey', None)
            exchange_config.pop('secret', None)
            exchange_config.pop('password', None)
            config['exchanges'][exchange_id] = exchange_config
            
        return config
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/exchanges/status")
async def get_exchanges_status(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict:
    """Get detailed status for each exchange"""
    try:
        status = {}
        for exchange_id, exchange in exchange_manager.exchanges.items():
            try:
                # Get exchange status
                exchange_status = await exchange.fetch_status()
                
                # Get trading limits
                markets = await exchange.fetch_markets()
                trading_limits = {
                    market['symbol']: {
                        'min_amount': market.get('limits', {}).get('amount', {}).get('min'),
                        'max_amount': market.get('limits', {}).get('amount', {}).get('max'),
                        'min_price': market.get('limits', {}).get('price', {}).get('min'),
                        'max_price': market.get('limits', {}).get('price', {}).get('max'),
                        'min_cost': market.get('limits', {}).get('cost', {}).get('min'),
                        'max_cost': market.get('limits', {}).get('cost', {}).get('max')
                    }
                    for market in markets
                }
                
                status[exchange_id] = {
                    'online': exchange_status.get('online', False),
                    'trading_enabled': exchange_status.get('has_trading', False),
                    'rate_limits': exchange_status.get('rate_limit', {}),
                    'trading_limits': trading_limits,
                    'timestamp': exchange_status.get('timestamp', int(time.time() * 1000))
                }
                
            except Exception as e:
                status[exchange_id] = {
                    'online': False,
                    'error': str(e)
                }
                
        return status
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/performance")
async def get_performance_metrics() -> Dict:
    """Get system performance metrics"""
    try:
        # CPU metrics
        cpu_times = psutil.cpu_times()
        cpu_freq = psutil.cpu_freq()
        cpu_stats = psutil.cpu_stats()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk I/O metrics
        disk_io = psutil.disk_io_counters()
        
        # Network I/O metrics
        net_io = psutil.net_io_counters()
        
        return {
            'cpu': {
                'percent': psutil.cpu_percent(interval=1),
                'times': {
                    'user': cpu_times.user,
                    'system': cpu_times.system,
                    'idle': cpu_times.idle
                },
                'frequency': {
                    'current': cpu_freq.current,
                    'min': cpu_freq.min,
                    'max': cpu_freq.max
                },
                'stats': {
                    'ctx_switches': cpu_stats.ctx_switches,
                    'interrupts': cpu_stats.interrupts,
                    'soft_interrupts': cpu_stats.soft_interrupts,
                    'syscalls': cpu_stats.syscalls
                }
            },
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free,
                'swap': {
                    'total': swap.total,
                    'used': swap.used,
                    'free': swap.free,
                    'percent': swap.percent
                }
            },
            'disk_io': {
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count,
                'read_time': disk_io.read_time,
                'write_time': disk_io.write_time
            },
            'network_io': {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout,
                'dropin': net_io.dropin,
                'dropout': net_io.dropout
            },
            'timestamp': int(time.time() * 1000)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ADMIN AUTHENTICATION ENDPOINTS
# =============================================================================

@router.post("/admin/auth/login")
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

@router.post("/admin/auth/logout")
async def admin_logout(session_token: str = Depends(get_current_session)):
    """Admin logout endpoint."""
    if session_token in active_sessions:
        del active_sessions[session_token]
    
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/admin/auth/verify")
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

# =============================================================================
# ADMIN CONFIGURATION MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/admin/config/files")
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

@router.get("/admin/config/file/{filename}")
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

@router.post("/admin/config/file/{filename}")
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

@router.get("/admin/config/backups/{filename}")
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

@router.post("/admin/config/restore/{backup_filename}")
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

@router.get("/admin/system/status")
async def get_admin_system_status(session_token: str = Depends(get_current_session)):
    """Get current system status for admin dashboard."""
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

@router.get("/admin/logs/recent")
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

# =============================================================================
# ADMIN HTML ENDPOINTS
# =============================================================================

@router.get("/admin/dashboard")
async def admin_dashboard_page():
    """Serve the admin dashboard HTML page."""
    return FileResponse(TEMPLATE_DIR / "admin_dashboard.html")

@router.get("/admin/dashboard/v2")
async def admin_dashboard_v2_page():
    """Serve the admin dashboard v2 HTML page."""
    return FileResponse(TEMPLATE_DIR / "admin_dashboard_v2.html")

@router.get("/admin/login")
async def admin_login_page():
    """Serve the admin login page."""
    return FileResponse(TEMPLATE_DIR / "admin_login.html")

@router.get("/admin/config-editor")
async def admin_config_editor_page():
    """Serve the optimized config editor page."""
    return FileResponse(TEMPLATE_DIR / "admin_config_editor_optimized.html")

@router.get("/admin/monitoring/live-metrics")
async def get_admin_monitoring_metrics():
    """Get live metrics for admin dashboard monitoring"""
    try:
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

@router.get("/admin/monitoring/bandwidth-history")
async def get_bandwidth_history(limit: int = 60):
    """Get historical bandwidth data"""
    try:
        from src.monitoring.bandwidth_monitor import bandwidth_monitor
        
        history = await bandwidth_monitor.get_history(limit=limit)
        summary = bandwidth_monitor.get_history_summary()
        
        return {
            "history": history,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting bandwidth history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# DEBUG & DIAGNOSTICS ENDPOINTS
# =============================================================================

@router.get("/debug/test-cache")
async def test_cache() -> Dict[str, Any]:
    """Test various cache access methods"""
    results = {}
    
    # Test 1: Direct aiomcache
    try:
        client = aiomcache.Client('localhost', 11211)
        data = await client.get(b'analysis:signals')
        if data:
            signals = json.loads(data.decode())
            results['direct_aiomcache'] = len(signals.get('signals', []))
        else:
            results['direct_aiomcache'] = 0
        await client.close()
    except Exception as e:
        results['direct_aiomcache'] = f"error: {e}"
    
    # Test 2: New client each time
    try:
        async def get_with_new_client():
            c = aiomcache.Client('localhost', 11211)
            d = await c.get(b'analysis:signals')
            await c.close()
            return d
        
        data = await get_with_new_client()
        if data:
            signals = json.loads(data.decode())
            results['new_client'] = len(signals.get('signals', []))
        else:
            results['new_client'] = 0
    except Exception as e:
        results['new_client'] = f"error: {e}"
    
    # Test 3: Check event loop
    results['event_loop'] = str(asyncio.get_event_loop())
    results['loop_running'] = asyncio.get_event_loop().is_running()
    
    # Test 4: Raw test key
    try:
        client = aiomcache.Client('localhost', 11211)
        # First set a test value
        await client.set(b'test:debug', b'test_value', exptime=60)
        # Then get it back
        test_val = await client.get(b'test:debug')
        results['test_key'] = test_val.decode() if test_val else None
        await client.close()
    except Exception as e:
        results['test_key'] = f"error: {e}"
    
    # Test 5: List all keys (stats)
    try:
        client = aiomcache.Client('localhost', 11211)
        stats = await client.stats()
        results['cache_items'] = stats.get(b'curr_items', b'0').decode()
        await client.close()
    except Exception as e:
        results['cache_items'] = f"error: {e}"
    
    return results

@router.get("/debug/test-import")
async def test_import() -> Dict[str, Any]:
    """Test importing and using DirectCache"""
    from src.core.direct_cache import DirectCache
    
    # Test DirectCache
    signals = await DirectCache.get_signals()
    
    return {
        'DirectCache.get_signals': signals.get('count', 0),
        'client_class': str(DirectCache._client)
    }
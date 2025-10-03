from src.utils.task_tracker import create_tracked_task
"""Enhanced admin dashboard routes with real-time capabilities."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from typing import Dict, List, Any, Optional
import asyncio
import json
import logging
import yaml
import time
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles
from collections import deque
import psutil

from ..routes.admin import get_current_session, verify_admin_password, create_admin_session

router = APIRouter()
logger = logging.getLogger(__name__)

# Performance metrics cache
class MetricsCache:
    def __init__(self, max_history: int = 100):
        self.cpu_history = deque(maxlen=max_history)
        self.memory_history = deque(maxlen=max_history)
        self.api_latency = deque(maxlen=max_history)
        self.active_symbols = []
        self.last_update = time.time()
        
    def update(self):
        """Update system metrics."""
        now = time.time()
        self.cpu_history.append({
            "timestamp": now,
            "value": psutil.cpu_percent(interval=0.1)
        })
        self.memory_history.append({
            "timestamp": now,
            "value": psutil.virtual_memory().percent
        })
        self.last_update = now

metrics_cache = MetricsCache()

# WebSocket manager for real-time updates
class AdminWebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.authenticated_connections: Dict[WebSocket, str] = {}
        
    async def connect(self, websocket: WebSocket, token: str):
        """Connect authenticated WebSocket."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.authenticated_connections[websocket] = token
        logger.info(f"Admin WebSocket connected. Total: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        """Disconnect WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.authenticated_connections:
            del self.authenticated_connections[websocket]
        logger.info(f"Admin WebSocket disconnected. Total: {len(self.active_connections)}")
        
    async def broadcast_update(self, update_type: str, data: Any):
        """Broadcast update to all authenticated connections."""
        if not self.active_connections:
            return
            
        message = {
            "type": update_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to admin WebSocket: {e}")
                disconnected.append(connection)
                
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)

ws_manager = AdminWebSocketManager()

# Enhanced monitoring endpoints
@router.get("/monitoring/live-metrics")
async def get_live_metrics(session_token: str = Depends(get_current_session)):
    """Get live system performance metrics."""
    try:
        # Update metrics
        metrics_cache.update()
        
        # Get container stats if available
        from src.core.container import get_container
        container = get_container()
        
        market_stats = {}
        if container and hasattr(container, 'market_manager'):
            market_manager = container.market_manager
            active_symbols = list(market_manager.symbol_data.keys()) if hasattr(market_manager, 'symbol_data') else []
            market_stats = {
                "active_symbols": len(active_symbols),
                "symbols": active_symbols[:10],  # Top 10
                "websocket_connected": hasattr(market_manager, 'websocket_manager') and market_manager.websocket_manager.is_connected
            }
        
        # Get trading stats
        trading_stats = {}
        if container and hasattr(container, 'monitor'):
            monitor = container.monitor
            if hasattr(monitor, 'alert_manager'):
                trading_stats["total_alerts_today"] = len(monitor.alert_manager.alert_history)
                trading_stats["active_signals"] = monitor.monitoring_data.get("signal_count", 0)
        
        return {
            "system": {
                "cpu_percent": metrics_cache.cpu_history[-1]["value"] if metrics_cache.cpu_history else 0,
                "memory_percent": metrics_cache.memory_history[-1]["value"] if metrics_cache.memory_history else 0,
                "cpu_history": list(metrics_cache.cpu_history)[-20:],
                "memory_history": list(metrics_cache.memory_history)[-20:],
                "disk_usage": psutil.disk_usage('/').percent,
                "uptime": time.time() - psutil.boot_time()
            },
            "market": market_stats,
            "trading": trading_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting live metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trading/active-positions")
async def get_active_positions(session_token: str = Depends(get_current_session)):
    """Get active trading positions and signals."""
    try:
        from src.core.container import get_container
        container = get_container()
        
        positions = []
        signals = []
        
        if container and hasattr(container, 'monitor'):
            monitor = container.monitor
            
            # Get recent signals
            if hasattr(monitor, 'signal_history'):
                recent_signals = list(monitor.signal_history)[-10:]
                signals = [
                    {
                        "symbol": sig.get("symbol"),
                        "action": sig.get("action"),
                        "score": sig.get("score"),
                        "timestamp": sig.get("timestamp"),
                        "components": sig.get("components", {})
                    }
                    for sig in recent_signals
                ]
        
        return {
            "positions": positions,
            "signals": signals,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting active positions: {e}")
        return {"positions": [], "signals": [], "error": str(e)}

@router.post("/config/validate")
async def validate_config(
    filename: str = Form(...),
    content: str = Form(...),
    session_token: str = Depends(get_current_session)
):
    """Validate YAML configuration before saving."""
    try:
        # Parse YAML
        parsed = yaml.safe_load(content)
        
        # Specific validations based on filename
        validation_errors = []
        warnings = []
        
        if filename == "config.yaml":
            # Validate main config structure
            required_sections = ["system", "exchanges", "market", "analysis", "monitoring"]
            for section in required_sections:
                if section not in parsed:
                    validation_errors.append(f"Missing required section: {section}")
            
            # Validate exchange config
            if "exchanges" in parsed and "bybit" in parsed["exchanges"]:
                bybit = parsed["exchanges"]["bybit"]
                if not bybit.get("enabled"):
                    warnings.append("Bybit exchange is disabled")
                if not bybit.get("api_credentials", {}).get("api_key"):
                    warnings.append("Bybit API key not configured")
            
            # Validate monitoring alerts
            if "monitoring" in parsed and "alerts" in parsed["monitoring"]:
                alerts = parsed["monitoring"]["alerts"]
                if not alerts.get("enabled"):
                    warnings.append("Alerts are disabled")
                if not alerts.get("discord_webhook", {}).get("url"):
                    warnings.append("Discord webhook not configured")
        
        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "warnings": warnings,
            "parsed_sections": list(parsed.keys()) if isinstance(parsed, dict) else []
        }
        
    except yaml.YAMLError as e:
        return {
            "valid": False,
            "errors": [f"YAML syntax error: {str(e)}"],
            "warnings": [],
            "parsed_sections": []
        }
    except Exception as e:
        logger.error(f"Error validating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/test/{alert_type}")
async def test_alert_system(
    alert_type: str,
    session_token: str = Depends(get_current_session)
):
    """Test specific alert type."""
    try:
        from src.core.container import get_container
        container = get_container()
        
        if not container or not hasattr(container, 'monitor'):
            raise HTTPException(status_code=400, detail="Monitoring system not available")
        
        monitor = container.monitor
        if not hasattr(monitor, 'alert_manager'):
            raise HTTPException(status_code=400, detail="Alert manager not available")
        
        alert_manager = monitor.alert_manager
        
        # Create test alert based on type
        test_alerts = {
            "signal": {
                "type": "signal",
                "symbol": "BTCUSDT",
                "action": "BUY",
                "score": 75.5,
                "confidence": 85,
                "message": "Test signal alert from admin dashboard"
            },
            "whale": {
                "type": "whale_activity",
                "symbol": "BTCUSDT",
                "whale_type": "accumulation",
                "volume_usd": 5000000,
                "message": "Test whale alert: Large accumulation detected"
            },
            "system": {
                "type": "system",
                "severity": "warning",
                "component": "admin_test",
                "message": "Test system alert from admin dashboard"
            },
            "alpha": {
                "type": "alpha_opportunity",
                "symbol": "ETHUSDT",
                "alpha_value": 0.15,
                "confidence": 90,
                "pattern": "correlation_breakdown",
                "message": "Test alpha opportunity alert"
            }
        }
        
        if alert_type not in test_alerts:
            raise HTTPException(status_code=400, detail=f"Invalid alert type: {alert_type}")
        
        # Send test alert
        alert_data = test_alerts[alert_type]
        await alert_manager.send_alert(**alert_data)
        
        # Broadcast to admin WebSockets
        await ws_manager.broadcast_update("test_alert", {
            "alert_type": alert_type,
            "status": "sent",
            "alert_data": alert_data
        })
        
        return {
            "status": "success",
            "alert_type": alert_type,
            "message": f"Test {alert_type} alert sent successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error testing alert {alert_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/admin")
async def admin_websocket(websocket: WebSocket, token: str):
    """Enhanced admin WebSocket with authentication."""
    # Verify token
    if not verify_session(token):
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    await ws_manager.connect(websocket, token)
    
    try:
        # Send initial data
        metrics = await get_live_metrics(token)
        await websocket.send_json({
            "type": "initial_data",
            "data": metrics
        })
        
        # Start background task for periodic updates
        async def send_periodic_updates():
            while True:
                try:
                    # Send metrics every 5 seconds
                    metrics = await get_live_metrics(token)
                    await websocket.send_json({
                        "type": "metrics_update",
                        "data": metrics
                    })
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Error in periodic updates: {e}")
                    break
        
        update_task = create_tracked_task(send_periodic_updates(), name="auto_tracked_task")
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                
                # Handle different message types
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "get_logs":
                    # Send recent logs
                    # Implementation depends on your logging setup
                    pass
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    finally:
        update_task.cancel()
        ws_manager.disconnect(websocket)

@router.get("/optimization/suggestions")
async def get_optimization_suggestions(session_token: str = Depends(get_current_session)):
    """Get system optimization suggestions based on current performance."""
    try:
        suggestions = []
        
        # Check CPU usage
        cpu_avg = sum(m["value"] for m in list(metrics_cache.cpu_history)[-10:]) / 10 if metrics_cache.cpu_history else 0
        if cpu_avg > 80:
            suggestions.append({
                "type": "performance",
                "severity": "high",
                "title": "High CPU Usage",
                "description": f"Average CPU usage is {cpu_avg:.1f}%",
                "action": "Consider reducing active symbols or increasing scan intervals"
            })
        
        # Check memory usage
        mem_avg = sum(m["value"] for m in list(metrics_cache.memory_history)[-10:]) / 10 if metrics_cache.memory_history else 0
        if mem_avg > 85:
            suggestions.append({
                "type": "performance",
                "severity": "high",
                "title": "High Memory Usage",
                "description": f"Average memory usage is {mem_avg:.1f}%",
                "action": "Consider restarting the service or reducing data retention"
            })
        
        # Check config optimizations
        from src.core.container import get_container
        container = get_container()
        
        if container and hasattr(container, 'config_manager'):
            config = container.config_manager.config
            
            # Check WebSocket optimization
            if config.get("websocket", {}).get("channels", {}).get("trade", True):
                suggestions.append({
                    "type": "configuration",
                    "severity": "medium",
                    "title": "Trade Stream Optimization",
                    "description": "Trade WebSocket channel is active but may not be needed",
                    "action": "Disable trade channel if not using trade flow analysis"
                })
            
            # Check alpha scanning
            if config.get("alpha_scanning", {}).get("enabled", False):
                interval = config["alpha_scanning"].get("interval_minutes", 15)
                if interval < 10:
                    suggestions.append({
                        "type": "configuration",
                        "severity": "medium",
                        "title": "Alpha Scanning Frequency",
                        "description": f"Alpha scanning runs every {interval} minutes",
                        "action": "Consider increasing interval to reduce system load"
                    })
        
        return {
            "suggestions": suggestions,
            "system_health": {
                "cpu_ok": cpu_avg < 70,
                "memory_ok": mem_avg < 80,
                "overall": "healthy" if cpu_avg < 70 and mem_avg < 80 else "needs_attention"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting optimization suggestions: {e}")
        return {"suggestions": [], "error": str(e)}
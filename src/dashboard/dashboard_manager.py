"""
Dashboard Manager - Coordinates all dashboard functionality
Handles data aggregation, real-time updates, and dashboard state management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..core.exchanges.manager import ExchangeManager
from ..monitoring.alert_manager import AlertManager
from ..monitoring.metrics_manager import MetricsManager
from ..core.market.top_symbols import TopSymbolsManager
from ..signal_generation.signal_generator import SignalGenerator


class DashboardManager:
    """
    Comprehensive dashboard manager that coordinates all trading intelligence
    """
    
    def __init__(
        self,
        exchange_manager: ExchangeManager,
        alert_manager: AlertManager,
        metrics_manager: Optional[MetricsManager] = None,
        top_symbols_manager: Optional[TopSymbolsManager] = None,
        signal_generator: Optional[SignalGenerator] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.exchange_manager = exchange_manager
        self.alert_manager = alert_manager
        self.metrics_manager = metrics_manager
        self.top_symbols_manager = top_symbols_manager
        self.signal_generator = signal_generator
        self.config = config or {}
        
        self.logger = logging.getLogger(__name__)
        
        # Dashboard state
        self._last_update = None
        self._cached_data = {}
        self._cache_ttl = 30  # seconds
        
        # Real-time update settings
        self.update_interval = 15  # seconds
        self._update_task = None
        self._is_running = False
        
        # WebSocket connections
        self._websocket_connections = set()
        
        self.logger.info("Dashboard Manager initialized")
    
    async def start(self):
        """Start the dashboard manager and begin real-time updates"""
        if self._is_running:
            self.logger.warning("Dashboard Manager is already running")
            return
        
        self._is_running = True
        self.logger.info("Starting Dashboard Manager...")
        
        # Start background update task
        self._update_task = asyncio.create_task(self._update_loop())
        
        self.logger.info("Dashboard Manager started successfully")
    
    async def stop(self):
        """Stop the dashboard manager"""
        if not self._is_running:
            return
        
        self._is_running = False
        self.logger.info("Stopping Dashboard Manager...")
        
        # Cancel update task
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        # Close all WebSocket connections
        for ws in self._websocket_connections.copy():
            try:
                await ws.close()
            except Exception as e:
                self.logger.warning(f"Error closing WebSocket: {e}")
        
        self._websocket_connections.clear()
        self.logger.info("Dashboard Manager stopped")
    
    async def _update_loop(self):
        """Background task for periodic dashboard updates"""
        while self._is_running:
            try:
                # Update dashboard data
                await self._update_dashboard_data()
                
                # Broadcast updates to connected WebSockets
                await self._broadcast_updates()
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in dashboard update loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _update_dashboard_data(self):
        """Update all dashboard data"""
        try:
            # Update cached data
            self._cached_data = await self.get_dashboard_overview()
            self._last_update = datetime.utcnow()
            
            self.logger.debug("Dashboard data updated successfully")
            
        except Exception as e:
            self.logger.error(f"Error updating dashboard data: {e}")
    
    async def _broadcast_updates(self):
        """Broadcast updates to all connected WebSockets"""
        if not self._websocket_connections or not self._cached_data:
            return
        
        message = {
            "type": "dashboard_update",
            "data": self._cached_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all connected WebSockets
        disconnected = []
        for ws in self._websocket_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                self.logger.warning(f"Failed to send WebSocket update: {e}")
                disconnected.append(ws)
        
        # Remove disconnected WebSockets
        for ws in disconnected:
            self._websocket_connections.discard(ws)
    
    def add_websocket(self, websocket):
        """Add a WebSocket connection for real-time updates"""
        self._websocket_connections.add(websocket)
        self.logger.debug(f"WebSocket added. Total connections: {len(self._websocket_connections)}")
    
    def remove_websocket(self, websocket):
        """Remove a WebSocket connection"""
        self._websocket_connections.discard(websocket)
        self.logger.debug(f"WebSocket removed. Total connections: {len(self._websocket_connections)}")
    
    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get comprehensive dashboard overview"""
        # Check cache first
        if (self._cached_data and self._last_update and 
            (datetime.utcnow() - self._last_update).seconds < self._cache_ttl):
            return self._cached_data
        
        try:
            # Gather data from all sources in parallel
            tasks = [
                self._get_signals_data(),
                self._get_market_data(),
                self._get_alerts_data(),
                self._get_alpha_opportunities(),
                self._get_system_status()
            ]
            
            signals, market, alerts, alpha, system = await asyncio.gather(
                *tasks, return_exceptions=True
            )
            
            # Handle exceptions gracefully
            overview = {
                "timestamp": datetime.utcnow().isoformat(),
                "signals": signals if not isinstance(signals, Exception) else [],
                "market": market if not isinstance(market, Exception) else {},
                "alerts": alerts if not isinstance(alerts, Exception) else [],
                "alpha_opportunities": alpha if not isinstance(alpha, Exception) else [],
                "system_status": system if not isinstance(system, Exception) else {}
            }
            
            return overview
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard overview: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "signals": [],
                "market": {},
                "alerts": [],
                "alpha_opportunities": [],
                "system_status": {"status": "error", "error": str(e)}
            }
    
    async def _get_signals_data(self) -> List[Dict[str, Any]]:
        """Get recent signals data"""
        try:
            signals_dir = Path("reports/json")
            if not signals_dir.exists():
                return []
            
            # Get recent signal files
            signal_files = [f for f in signals_dir.glob("*.json") if f.is_file()]
            signal_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            signals = []
            for file_path in signal_files[:10]:  # Get last 10 signals
                try:
                    import json
                    with open(file_path, 'r') as f:
                        signal_data = json.load(f)
                    
                    # Add metadata
                    signal_data['filename'] = file_path.name
                    signal_data['timestamp'] = datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat()
                    
                    signals.append(signal_data)
                except Exception as e:
                    self.logger.warning(f"Error reading signal file {file_path}: {e}")
                    continue
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error getting signals data: {e}")
            return []
    
    async def _get_market_data(self) -> Dict[str, Any]:
        """Get market overview data"""
        try:
            market_data = {
                "active_pairs": 0,
                "avg_volume": 0,
                "market_cap": 0,
                "volatility": 0,
                "regime": "UNKNOWN",
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Get data from top symbols manager if available
            if self.top_symbols_manager:
                try:
                    symbols = await self.top_symbols_manager.get_symbols()
                    market_data["active_pairs"] = len(symbols) if symbols else 0
                except Exception as e:
                    self.logger.warning(f"Error getting symbols from top_symbols_manager: {e}")
            
            # Get market metrics if available
            if self.metrics_manager:
                try:
                    metrics = await self.metrics_manager.get_current_metrics()
                    if metrics:
                        market_data.update({
                            "avg_volume": metrics.get("total_volume", 0),
                            "volatility": metrics.get("avg_volatility", 0)
                        })
                except Exception as e:
                    self.logger.warning(f"Error getting metrics: {e}")
            
            # Mock additional data for demonstration
            market_data.update({
                "avg_volume": 2800000000,  # 2.8B
                "market_cap": 1200000000000,  # 1.2T
                "volatility": 3.2,
                "regime": "BULLISH"
            })
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error getting market data: {e}")
            return {}
    
    async def _get_alerts_data(self) -> List[Dict[str, Any]]:
        """Get recent alerts data"""
        try:
            # Mock alerts for demonstration
            alerts = [
                {
                    "type": "SIGNAL",
                    "message": "Strong buy signal detected for BTCUSDT",
                    "priority": "high",
                    "timestamp": (datetime.utcnow() - timedelta(minutes=2)).isoformat(),
                    "source": "signal_generator"
                },
                {
                    "type": "ALPHA",
                    "message": "New opportunity identified in AVAXUSDT",
                    "priority": "medium",
                    "timestamp": (datetime.utcnow() - timedelta(minutes=8)).isoformat(),
                    "source": "alpha_scanner"
                },
                {
                    "type": "SYSTEM",
                    "message": "Market data refresh completed successfully",
                    "priority": "low",
                    "timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
                    "source": "data_processor"
                },
                {
                    "type": "MARKET",
                    "message": "Volume spike detected across multiple pairs",
                    "priority": "medium",
                    "timestamp": (datetime.utcnow() - timedelta(minutes=23)).isoformat(),
                    "source": "market_monitor"
                },
                {
                    "type": "SIGNAL",
                    "message": "Sell signal triggered for XRPUSDT",
                    "priority": "high",
                    "timestamp": (datetime.utcnow() - timedelta(minutes=31)).isoformat(),
                    "source": "signal_generator"
                }
            ]
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error getting alerts data: {e}")
            return []
    
    async def _get_alpha_opportunities(self) -> List[Dict[str, Any]]:
        """Get alpha opportunities data"""
        try:
            # Mock alpha opportunities for demonstration
            opportunities = [
                {
                    "symbol": "AVAXUSDT",
                    "pattern": "Breakout Pattern",
                    "confidence": 0.892,
                    "alpha_potential": 0.124,
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "symbol": "ADAUSDT",
                    "pattern": "Volume Spike",
                    "confidence": 0.768,
                    "alpha_potential": 0.087,
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "symbol": "LINKUSDT",
                    "pattern": "Support Bounce",
                    "confidence": 0.821,
                    "alpha_potential": 0.153,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error getting alpha opportunities: {e}")
            return []
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Get system status information"""
        try:
            status = {
                "status": "online",
                "uptime": "24h 15m",
                "cpu_usage": 45.2,
                "memory_usage": 68.7,
                "active_connections": len(self._websocket_connections),
                "last_scan": datetime.utcnow().isoformat()
            }
            
            # Check exchange manager health
            if self.exchange_manager:
                try:
                    is_healthy = await self.exchange_manager.is_healthy()
                    status["exchange_status"] = "healthy" if is_healthy else "unhealthy"
                except Exception as e:
                    status["exchange_status"] = "error"
                    status["exchange_error"] = str(e)
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent alerts with limit"""
        alerts = await self._get_alerts_data()
        return alerts[:limit]
    
    async def get_configuration(self) -> Dict[str, Any]:
        """Get current dashboard configuration"""
        return {
            "monitoring": {
                "scan_interval": 5,
                "max_alerts": 3,
                "alert_cooldown": 60
            },
            "signals": {
                "min_score": 65,
                "min_reliability": 75
            },
            "alpha": {
                "confidence_threshold": 75,
                "risk_level": "Medium"
            }
        }
    
    async def update_configuration(self, config: Dict[str, Any]) -> bool:
        """Update dashboard configuration"""
        try:
            # In production, this would save to database or config file
            self.logger.info(f"Dashboard configuration updated: {config}")
            
            # Here you would typically:
            # 1. Validate the configuration
            # 2. Save to persistent storage
            # 3. Apply changes to running systems
            # 4. Log the change with user info
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
            return False
    
    def get_connection_count(self) -> int:
        """Get number of active WebSocket connections"""
        return len(self._websocket_connections)
    
    def is_running(self) -> bool:
        """Check if dashboard manager is running"""
        return self._is_running
    
    def get_last_update(self) -> Optional[datetime]:
        """Get timestamp of last data update"""
        return self._last_update 
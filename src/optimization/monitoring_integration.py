"""
Real-time monitoring integration for Optuna optimization.
Connects to existing Virtuoso monitoring infrastructure on ports 8001/8003.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import threading
import queue
import redis
import memcache
import requests
from pathlib import Path

from src.utils.logging_extensions import get_logger

logger = get_logger(__name__)


@dataclass
class OptimizationStatus:
    """Current optimization status for dashboard."""
    study_name: str
    status: str  # 'running', 'paused', 'completed', 'failed'
    progress: float  # 0-100%
    current_trial: int
    total_trials: int
    best_value: Optional[float]
    best_params: Dict[str, Any]
    elapsed_time_seconds: float
    estimated_remaining_seconds: Optional[float]
    resource_usage: Dict[str, float]
    recent_trials: List[Dict[str, Any]]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }


class OptimizationMonitor:
    """
    Real-time monitoring for Optuna optimization.
    Integrates with Virtuoso's existing monitoring infrastructure.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # API endpoints
        self.monitoring_api = config.get('monitoring_api', 'http://localhost:8001')
        self.dashboard_api = config.get('dashboard_api', 'http://localhost:8003')
        
        # Cache configuration
        self.cache_config = config.get('cache', {})
        self.cache_client = self._init_cache()
        
        # WebSocket configuration for real-time updates
        self.ws_enabled = config.get('websocket_enabled', True)
        self.ws_queue = queue.Queue() if self.ws_enabled else None
        
        # Monitoring state
        self.active_studies = {}
        self.monitoring_thread = None
        self.monitoring_active = False
        
        # Metrics buffer
        self.metrics_buffer = []
        self.buffer_size = config.get('buffer_size', 100)
        
        logger.info(f"Initialized optimization monitor (API: {self.monitoring_api})")
    
    def _init_cache(self) -> Optional[Any]:
        """Initialize cache client."""
        cache_type = self.cache_config.get('type', 'memcached')
        
        try:
            if cache_type == 'redis':
                client = redis.Redis(
                    host=self.cache_config.get('host', 'localhost'),
                    port=self.cache_config.get('port', 6379),
                    decode_responses=True
                )
                client.ping()  # Test connection
                logger.info("Connected to Redis cache")
                return client
            elif cache_type == 'memcached':
                client = memcache.Client(
                    [f"{self.cache_config.get('host', 'localhost')}:{self.cache_config.get('port', 11211)}"]
                )
                # Test connection
                client.set('test', 'test', time=1)
                logger.info("Connected to Memcached cache")
                return client
        except Exception as e:
            logger.warning(f"Cache connection failed: {e}")
            return None
    
    def start_monitoring(self, study_name: str, total_trials: int):
        """Start monitoring an optimization study."""
        self.active_studies[study_name] = {
            'start_time': datetime.now(),
            'total_trials': total_trials,
            'current_trial': 0,
            'status': 'running',
            'best_value': None,
            'best_params': {}
        }
        
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
        
        # Send initial status
        self._update_dashboard_status(study_name)
        
        logger.info(f"Started monitoring study: {study_name}")
    
    def stop_monitoring(self, study_name: str):
        """Stop monitoring a study."""
        if study_name in self.active_studies:
            self.active_studies[study_name]['status'] = 'completed'
            self._update_dashboard_status(study_name)
            del self.active_studies[study_name]
        
        if not self.active_studies:
            self.monitoring_active = False
        
        logger.info(f"Stopped monitoring study: {study_name}")
    
    def update_trial_progress(self, 
                             study_name: str, 
                             trial_number: int,
                             value: Optional[float],
                             params: Dict[str, Any],
                             state: str):
        """Update progress for a trial."""
        if study_name not in self.active_studies:
            return
        
        study_info = self.active_studies[study_name]
        study_info['current_trial'] = trial_number
        
        if value is not None and state == 'COMPLETE':
            if study_info['best_value'] is None or value > study_info['best_value']:
                study_info['best_value'] = value
                study_info['best_params'] = params
        
        # Add to recent trials
        if 'recent_trials' not in study_info:
            study_info['recent_trials'] = []
        
        study_info['recent_trials'].append({
            'trial': trial_number,
            'value': value,
            'state': state,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 10 trials
        study_info['recent_trials'] = study_info['recent_trials'][-10:]
        
        # Update dashboard
        self._update_dashboard_status(study_name)
        
        # Send to WebSocket if enabled
        if self.ws_enabled and self.ws_queue:
            self.ws_queue.put({
                'type': 'trial_update',
                'study': study_name,
                'trial': trial_number,
                'value': value,
                'state': state
            })
    
    def update_resource_metrics(self, 
                               study_name: str,
                               memory_gb: float,
                               cpu_percent: float):
        """Update resource usage metrics."""
        if study_name not in self.active_studies:
            return
        
        self.active_studies[study_name]['resource_usage'] = {
            'memory_gb': memory_gb,
            'cpu_percent': cpu_percent,
            'timestamp': datetime.now().isoformat()
        }
        
        # Buffer metrics
        self.metrics_buffer.append({
            'study': study_name,
            'memory_gb': memory_gb,
            'cpu_percent': cpu_percent,
            'timestamp': datetime.now()
        })
        
        # Trim buffer
        if len(self.metrics_buffer) > self.buffer_size:
            self.metrics_buffer = self.metrics_buffer[-self.buffer_size:]
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                # Update all active studies
                for study_name in list(self.active_studies.keys()):
                    self._update_dashboard_status(study_name)
                
                # Send aggregated metrics to monitoring API
                if self.metrics_buffer:
                    self._send_metrics_to_api()
                
                # Check for alerts
                self._check_alerts()
                
                time.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
    
    def _update_dashboard_status(self, study_name: str):
        """Update dashboard with current optimization status."""
        if study_name not in self.active_studies:
            return
        
        study_info = self.active_studies[study_name]
        
        # Calculate progress and estimates
        progress = (study_info['current_trial'] / study_info['total_trials'] * 100) 
        elapsed = (datetime.now() - study_info['start_time']).total_seconds()
        
        if study_info['current_trial'] > 0:
            avg_trial_time = elapsed / study_info['current_trial']
            remaining_trials = study_info['total_trials'] - study_info['current_trial']
            estimated_remaining = avg_trial_time * remaining_trials
        else:
            estimated_remaining = None
        
        status = OptimizationStatus(
            study_name=study_name,
            status=study_info['status'],
            progress=progress,
            current_trial=study_info['current_trial'],
            total_trials=study_info['total_trials'],
            best_value=study_info.get('best_value'),
            best_params=study_info.get('best_params', {}),
            elapsed_time_seconds=elapsed,
            estimated_remaining_seconds=estimated_remaining,
            resource_usage=study_info.get('resource_usage', {}),
            recent_trials=study_info.get('recent_trials', []),
            timestamp=datetime.now()
        )
        
        # Update cache
        self._update_cache(study_name, status)
        
        # Send to dashboard API
        self._send_to_dashboard_api(status)
    
    def _update_cache(self, study_name: str, status: OptimizationStatus):
        """Update cache with optimization status."""
        if not self.cache_client:
            return
        
        cache_key = f"optuna:status:{study_name}"
        cache_data = json.dumps(status.to_dict())
        
        try:
            if isinstance(self.cache_client, redis.Redis):
                # Set with 60 second TTL
                self.cache_client.setex(cache_key, 60, cache_data)
                
                # Also publish for real-time subscribers
                self.cache_client.publish(
                    "optuna:updates",
                    cache_data
                )
            elif isinstance(self.cache_client, memcache.Client):
                self.cache_client.set(cache_key, cache_data, time=60)
        except Exception as e:
            logger.warning(f"Cache update failed: {e}")
    
    def _send_to_dashboard_api(self, status: OptimizationStatus):
        """Send status update to dashboard API."""
        try:
            # Post to dashboard optimization endpoint
            response = requests.post(
                f"{self.dashboard_api}/api/optimization/status",
                json=status.to_dict(),
                timeout=5
            )
            
            if response.status_code != 200:
                logger.warning(f"Dashboard API returned {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            # API might not be running, which is okay
            pass
        except Exception as e:
            logger.warning(f"Dashboard API update failed: {e}")
    
    def _send_metrics_to_api(self):
        """Send aggregated metrics to monitoring API."""
        if not self.metrics_buffer:
            return
        
        try:
            # Aggregate metrics
            aggregated = {
                'timestamp': datetime.now().isoformat(),
                'studies': {},
                'resource_summary': {
                    'avg_memory_gb': 0,
                    'max_memory_gb': 0,
                    'avg_cpu_percent': 0,
                    'max_cpu_percent': 0
                }
            }
            
            # Group by study
            for metric in self.metrics_buffer:
                study = metric['study']
                if study not in aggregated['studies']:
                    aggregated['studies'][study] = []
                aggregated['studies'][study].append({
                    'memory_gb': metric['memory_gb'],
                    'cpu_percent': metric['cpu_percent'],
                    'timestamp': metric['timestamp'].isoformat()
                })
            
            # Calculate summary
            all_memory = [m['memory_gb'] for m in self.metrics_buffer]
            all_cpu = [m['cpu_percent'] for m in self.metrics_buffer]
            
            if all_memory:
                aggregated['resource_summary']['avg_memory_gb'] = sum(all_memory) / len(all_memory)
                aggregated['resource_summary']['max_memory_gb'] = max(all_memory)
            
            if all_cpu:
                aggregated['resource_summary']['avg_cpu_percent'] = sum(all_cpu) / len(all_cpu)
                aggregated['resource_summary']['max_cpu_percent'] = max(all_cpu)
            
            # Send to monitoring API
            response = requests.post(
                f"{self.monitoring_api}/api/monitoring/optimization",
                json=aggregated,
                timeout=5
            )
            
            if response.status_code == 200:
                # Clear buffer after successful send
                self.metrics_buffer = []
                
        except Exception as e:
            logger.warning(f"Monitoring API update failed: {e}")
    
    def _check_alerts(self):
        """Check for alert conditions."""
        alerts = []
        
        for study_name, study_info in self.active_studies.items():
            # Check for stalled optimization
            if study_info['current_trial'] > 0:
                elapsed = (datetime.now() - study_info['start_time']).total_seconds()
                avg_trial_time = elapsed / study_info['current_trial']
                
                # Alert if no progress in 10x average trial time
                if elapsed > avg_trial_time * 10:
                    alerts.append({
                        'study': study_name,
                        'type': 'stalled',
                        'message': f"Study {study_name} appears stalled"
                    })
            
            # Check resource usage
            resource_usage = study_info.get('resource_usage', {})
            if resource_usage:
                if resource_usage.get('memory_gb', 0) > 1.8:  # 90% of 2GB limit
                    alerts.append({
                        'study': study_name,
                        'type': 'high_memory',
                        'message': f"Study {study_name} using {resource_usage['memory_gb']:.2f}GB memory"
                    })
                
                if resource_usage.get('cpu_percent', 0) > 90:
                    alerts.append({
                        'study': study_name,
                        'type': 'high_cpu',
                        'message': f"Study {study_name} using {resource_usage['cpu_percent']:.1f}% CPU"
                    })
        
        # Send alerts
        for alert in alerts:
            self._send_alert(alert)
    
    def _send_alert(self, alert: Dict[str, Any]):
        """Send alert to monitoring system."""
        try:
            # Send to monitoring API
            response = requests.post(
                f"{self.monitoring_api}/api/alerts",
                json={
                    'source': 'optuna_optimization',
                    'severity': 'warning',
                    'alert': alert,
                    'timestamp': datetime.now().isoformat()
                },
                timeout=5
            )
            
            logger.warning(f"Alert sent: {alert['message']}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def get_optimization_dashboard_data(self) -> Dict[str, Any]:
        """Get formatted data for dashboard display."""
        dashboard_data = {
            'active_studies': [],
            'completed_studies': [],
            'resource_usage': {
                'current': {},
                'history': []
            },
            'performance_metrics': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Format active studies
        for study_name, study_info in self.active_studies.items():
            progress = (study_info['current_trial'] / study_info['total_trials'] * 100)
            
            dashboard_data['active_studies'].append({
                'name': study_name,
                'progress': progress,
                'current_trial': study_info['current_trial'],
                'total_trials': study_info['total_trials'],
                'best_value': study_info.get('best_value'),
                'status': study_info['status']
            })
        
        # Add resource usage
        if self.metrics_buffer:
            recent_metrics = self.metrics_buffer[-20:]  # Last 20 entries
            
            # Current usage (most recent)
            latest = recent_metrics[-1]
            dashboard_data['resource_usage']['current'] = {
                'memory_gb': latest['memory_gb'],
                'cpu_percent': latest['cpu_percent']
            }
            
            # History for charts
            dashboard_data['resource_usage']['history'] = [
                {
                    'timestamp': m['timestamp'].isoformat(),
                    'memory_gb': m['memory_gb'],
                    'cpu_percent': m['cpu_percent']
                }
                for m in recent_metrics
            ]
        
        return dashboard_data


class OptimizationDashboardIntegration:
    """
    Integration layer for optimization dashboard.
    Provides endpoints and WebSocket support for real-time updates.
    """
    
    def __init__(self, monitor: OptimizationMonitor):
        self.monitor = monitor
        self.websocket_clients = set()
    
    async def handle_websocket(self, websocket):
        """Handle WebSocket connection for real-time updates."""
        self.websocket_clients.add(websocket)
        
        try:
            # Send initial status
            await websocket.send_json({
                'type': 'initial',
                'data': self.monitor.get_optimization_dashboard_data()
            })
            
            # Handle incoming messages and send updates
            while True:
                # Check for updates in queue
                if self.monitor.ws_queue and not self.monitor.ws_queue.empty():
                    update = self.monitor.ws_queue.get()
                    await websocket.send_json({
                        'type': 'update',
                        'data': update
                    })
                
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.websocket_clients.discard(websocket)
    
    def get_api_routes(self):
        """Get FastAPI routes for optimization monitoring."""
        from fastapi import APIRouter, WebSocket
        
        router = APIRouter(prefix="/api/optimization", tags=["optimization"])
        
        @router.get("/status")
        async def get_optimization_status():
            """Get current optimization status."""
            return self.monitor.get_optimization_dashboard_data()
        
        @router.get("/studies")
        async def get_active_studies():
            """Get list of active studies."""
            return {
                'studies': list(self.monitor.active_studies.keys()),
                'count': len(self.monitor.active_studies)
            }
        
        @router.get("/metrics/{study_name}")
        async def get_study_metrics(study_name: str):
            """Get detailed metrics for a study."""
            if study_name in self.monitor.active_studies:
                return self.monitor.active_studies[study_name]
            return {'error': 'Study not found'}
        
        @router.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            await self.handle_websocket(websocket)
        
        return router
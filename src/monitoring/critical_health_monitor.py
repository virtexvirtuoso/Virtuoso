"""
Critical Health Monitor - Part of Phase 1: Emergency Stabilization
Implements comprehensive system health monitoring with alerting
"""

import asyncio
import json
import time
import psutil
import aiohttp
import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    value: Any
    threshold: Any
    message: str
    timestamp: datetime
    details: Optional[Dict] = None

@dataclass
class SystemHealth:
    overall_status: HealthStatus
    checks: List[HealthCheck]
    timestamp: datetime
    
    def has_critical_issues(self) -> bool:
        return any(check.status == HealthStatus.CRITICAL for check in self.checks)
    
    def has_warnings(self) -> bool:
        return any(check.status == HealthStatus.WARNING for check in self.checks)

class CriticalHealthMonitor:
    """
    Critical system health monitor with alerting capabilities
    Monitors key metrics that can cause system failures
    """
    
    def __init__(self):
        self.thresholds = {
            'api_response_time': 500,      # milliseconds
            'cache_hit_rate': 80,          # percentage
            'error_rate': 5,               # percentage
            'memory_usage': 85,            # percentage
            'trading_latency': 100,        # milliseconds
            'exchange_connection': True,    # boolean
            'disk_usage': 90,              # percentage
            'cpu_usage': 80,               # percentage
        }
        
        self.alert_cooldown = 300  # 5 minutes between alerts for same issue
        self.last_alerts = {}
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def continuous_health_check(self, interval: int = 30):
        """
        Continuous health monitoring loop
        """
        logger.info(f"Starting continuous health monitoring (interval: {interval}s)")
        
        while True:
            try:
                health_status = await self.check_all_systems()
                
                # Log overall status
                logger.info(f"Health check completed - Status: {health_status.overall_status.value}")
                
                # Trigger alerts for critical issues
                if health_status.has_critical_issues():
                    await self.trigger_critical_alerts(health_status)
                elif health_status.has_warnings():
                    await self.trigger_warning_alerts(health_status)
                    
                # Log detailed results
                self._log_health_details(health_status)
                
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
                
            await asyncio.sleep(interval)
    
    async def check_all_systems(self) -> SystemHealth:
        """
        Comprehensive system health check
        """
        timestamp = datetime.now(timezone.utc)
        checks = []
        
        # Run all health checks concurrently
        health_check_tasks = [
            self.check_api_latency(),
            self.check_cache_performance(),
            self.check_exchange_connectivity(),
            self.check_memory_usage(),
            self.check_disk_usage(),
            self.check_cpu_usage(),
            self.check_error_rates(),
            self.check_process_health(),
        ]
        
        try:
            check_results = await asyncio.gather(*health_check_tasks, return_exceptions=True)
            
            for result in check_results:
                if isinstance(result, Exception):
                    logger.error(f"Health check failed: {str(result)}")
                    checks.append(HealthCheck(
                        name="check_error",
                        status=HealthStatus.CRITICAL,
                        value=str(result),
                        threshold="none",
                        message=f"Health check failed: {str(result)}",
                        timestamp=timestamp
                    ))
                else:
                    checks.extend(result if isinstance(result, list) else [result])
                    
        except Exception as e:
            logger.error(f"Critical error in health check: {str(e)}")
            checks.append(HealthCheck(
                name="system_error",
                status=HealthStatus.CRITICAL,
                value=str(e),
                threshold="none",
                message=f"System error: {str(e)}",
                timestamp=timestamp
            ))
        
        # Determine overall status
        overall_status = self._determine_overall_status(checks)
        
        return SystemHealth(
            overall_status=overall_status,
            checks=checks,
            timestamp=timestamp
        )
    
    async def check_api_latency(self) -> List[HealthCheck]:
        """Check API endpoint response times"""
        checks = []
        endpoints = [
            ("main_api", "http://localhost:8003/health"),
            ("monitoring_api", "http://localhost:8001/api/monitoring/status"),
        ]
        
        for name, url in endpoints:
            try:
                start_time = time.time()
                async with self.session.get(url) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        status = HealthStatus.HEALTHY if latency_ms < self.thresholds['api_response_time'] else HealthStatus.WARNING
                        if latency_ms > self.thresholds['api_response_time'] * 2:
                            status = HealthStatus.CRITICAL
                    else:
                        status = HealthStatus.CRITICAL
                        
                    checks.append(HealthCheck(
                        name=f"{name}_latency",
                        status=status,
                        value=round(latency_ms, 2),
                        threshold=self.thresholds['api_response_time'],
                        message=f"{name} response time: {latency_ms:.2f}ms (status: {response.status})",
                        timestamp=datetime.now(timezone.utc)
                    ))
                    
            except Exception as e:
                checks.append(HealthCheck(
                    name=f"{name}_connectivity",
                    status=HealthStatus.CRITICAL,
                    value=str(e),
                    threshold="reachable",
                    message=f"{name} unreachable: {str(e)}",
                    timestamp=datetime.now(timezone.utc)
                ))
        
        return checks
    
    async def check_cache_performance(self) -> List[HealthCheck]:
        """Check cache hit rates and performance"""
        checks = []
        
        # Check Memcached
        try:
            reader, writer = await asyncio.open_connection('localhost', 11211)
            writer.write(b'stats\r\n')
            await writer.drain()
            
            stats_data = b''
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                stats_data += data
                if b'END\r\n' in data:
                    break
            
            writer.close()
            await writer.wait_closed()
            
            # Parse memcached stats
            stats = {}
            for line in stats_data.decode().split('\r\n'):
                if line.startswith('STAT'):
                    parts = line.split(' ')
                    if len(parts) >= 3:
                        stats[parts[1]] = parts[2]
            
            hits = int(stats.get('get_hits', 0))
            misses = int(stats.get('get_misses', 0))
            
            if hits + misses > 0:
                hit_rate = (hits / (hits + misses)) * 100
                status = HealthStatus.HEALTHY if hit_rate >= self.thresholds['cache_hit_rate'] else HealthStatus.WARNING
                if hit_rate < self.thresholds['cache_hit_rate'] - 20:
                    status = HealthStatus.CRITICAL
                    
                checks.append(HealthCheck(
                    name="memcached_hit_rate",
                    status=status,
                    value=round(hit_rate, 2),
                    threshold=self.thresholds['cache_hit_rate'],
                    message=f"Memcached hit rate: {hit_rate:.2f}% (hits: {hits}, misses: {misses})",
                    timestamp=datetime.now(timezone.utc),
                    details={"hits": hits, "misses": misses}
                ))
            else:
                checks.append(HealthCheck(
                    name="memcached_activity",
                    status=HealthStatus.WARNING,
                    value=0,
                    threshold=">0",
                    message="Memcached has no activity (no hits or misses)",
                    timestamp=datetime.now(timezone.utc)
                ))
                
        except Exception as e:
            checks.append(HealthCheck(
                name="memcached_connection",
                status=HealthStatus.CRITICAL,
                value=str(e),
                threshold="connected",
                message=f"Memcached connection failed: {str(e)}",
                timestamp=datetime.now(timezone.utc)
            ))
        
        # Check Redis (basic connectivity)
        try:
            reader, writer = await asyncio.open_connection('localhost', 6379)
            writer.write(b'PING\r\n')
            await writer.drain()
            
            response = await reader.read(1024)
            writer.close()
            await writer.wait_closed()
            
            if b'+PONG' in response:
                checks.append(HealthCheck(
                    name="redis_connectivity",
                    status=HealthStatus.HEALTHY,
                    value="connected",
                    threshold="connected",
                    message="Redis is responding to PING",
                    timestamp=datetime.now(timezone.utc)
                ))
            else:
                checks.append(HealthCheck(
                    name="redis_response",
                    status=HealthStatus.WARNING,
                    value=response.decode(),
                    threshold="PONG",
                    message=f"Redis unexpected response: {response.decode()}",
                    timestamp=datetime.now(timezone.utc)
                ))
                
        except Exception as e:
            checks.append(HealthCheck(
                name="redis_connection",
                status=HealthStatus.CRITICAL,
                value=str(e),
                threshold="connected",
                message=f"Redis connection failed: {str(e)}",
                timestamp=datetime.now(timezone.utc)
            ))
        
        return checks
    
    async def check_exchange_connectivity(self) -> List[HealthCheck]:
        """Check exchange API connectivity"""
        checks = []
        exchanges = [
            ("bybit", "https://api.bybit.com/v2/public/time"),
            ("binance", "https://api.binance.com/api/v3/ping"),
        ]
        
        for name, url in exchanges:
            try:
                start_time = time.time()
                async with self.session.get(url) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        status = HealthStatus.HEALTHY if latency_ms < 2000 else HealthStatus.WARNING
                        checks.append(HealthCheck(
                            name=f"{name}_connectivity",
                            status=status,
                            value=f"{response.status} ({latency_ms:.0f}ms)",
                            threshold="200",
                            message=f"{name} API responding: {response.status} in {latency_ms:.0f}ms",
                            timestamp=datetime.now(timezone.utc)
                        ))
                    else:
                        checks.append(HealthCheck(
                            name=f"{name}_status",
                            status=HealthStatus.WARNING,
                            value=response.status,
                            threshold="200",
                            message=f"{name} API returned status {response.status}",
                            timestamp=datetime.now(timezone.utc)
                        ))
                        
            except Exception as e:
                # Binance connectivity is optional
                status = HealthStatus.WARNING if name == "binance" else HealthStatus.CRITICAL
                checks.append(HealthCheck(
                    name=f"{name}_error",
                    status=status,
                    value=str(e),
                    threshold="reachable",
                    message=f"{name} API unreachable: {str(e)}",
                    timestamp=datetime.now(timezone.utc)
                ))
        
        return checks
    
    async def check_memory_usage(self) -> HealthCheck:
        """Check system memory usage"""
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        if memory_percent < self.thresholds['memory_usage']:
            status = HealthStatus.HEALTHY
        elif memory_percent < self.thresholds['memory_usage'] + 10:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.CRITICAL
            
        return HealthCheck(
            name="memory_usage",
            status=status,
            value=memory_percent,
            threshold=self.thresholds['memory_usage'],
            message=f"Memory usage: {memory_percent:.1f}% ({memory.used // 1024**3}GB/{memory.total // 1024**3}GB)",
            timestamp=datetime.now(timezone.utc),
            details={
                "used_gb": memory.used // 1024**3,
                "total_gb": memory.total // 1024**3,
                "available_gb": memory.available // 1024**3
            }
        )
    
    async def check_disk_usage(self) -> HealthCheck:
        """Check disk usage"""
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        if disk_percent < self.thresholds['disk_usage'] - 10:
            status = HealthStatus.HEALTHY
        elif disk_percent < self.thresholds['disk_usage']:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.CRITICAL
            
        return HealthCheck(
            name="disk_usage",
            status=status,
            value=disk_percent,
            threshold=self.thresholds['disk_usage'],
            message=f"Disk usage: {disk_percent:.1f}% ({disk.used // 1024**3}GB/{disk.total // 1024**3}GB)",
            timestamp=datetime.now(timezone.utc),
            details={
                "used_gb": disk.used // 1024**3,
                "total_gb": disk.total // 1024**3,
                "free_gb": disk.free // 1024**3
            }
        )
    
    async def check_cpu_usage(self) -> HealthCheck:
        """Check CPU usage"""
        # Get CPU usage over 1 second interval
        cpu_percent = psutil.cpu_percent(interval=1)
        
        if cpu_percent < self.thresholds['cpu_usage'] - 20:
            status = HealthStatus.HEALTHY
        elif cpu_percent < self.thresholds['cpu_usage']:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.CRITICAL
            
        return HealthCheck(
            name="cpu_usage",
            status=status,
            value=cpu_percent,
            threshold=self.thresholds['cpu_usage'],
            message=f"CPU usage: {cpu_percent:.1f}%",
            timestamp=datetime.now(timezone.utc),
            details={
                "cpu_count": psutil.cpu_count(),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        )
    
    async def check_error_rates(self) -> HealthCheck:
        """Check recent error rates from logs"""
        try:
            # This is a placeholder - would need to be adapted based on actual logging setup
            error_count = 0  # Would scan log files for recent errors
            
            # For now, return a healthy status
            return HealthCheck(
                name="error_rate",
                status=HealthStatus.HEALTHY,
                value=error_count,
                threshold=self.thresholds['error_rate'],
                message=f"Recent errors: {error_count} (monitoring not fully implemented)",
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return HealthCheck(
                name="error_monitoring",
                status=HealthStatus.WARNING,
                value=str(e),
                threshold="working",
                message=f"Error monitoring failed: {str(e)}",
                timestamp=datetime.now(timezone.utc)
            )
    
    async def check_process_health(self) -> List[HealthCheck]:
        """Check if critical processes are running"""
        checks = []
        critical_processes = ["main.py", "web_server.py"]
        
        for process_name in critical_processes:
            found = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if process_name in cmdline:
                        found = True
                        checks.append(HealthCheck(
                            name=f"process_{process_name.replace('.', '_')}",
                            status=HealthStatus.HEALTHY,
                            value=f"PID {proc.info['pid']}",
                            threshold="running",
                            message=f"{process_name} is running (PID: {proc.info['pid']})",
                            timestamp=datetime.now(timezone.utc)
                        ))
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not found:
                checks.append(HealthCheck(
                    name=f"process_{process_name.replace('.', '_')}",
                    status=HealthStatus.CRITICAL,
                    value="not running",
                    threshold="running",
                    message=f"{process_name} is not running",
                    timestamp=datetime.now(timezone.utc)
                ))
        
        return checks
    
    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """Determine overall system health status"""
        if any(check.status == HealthStatus.CRITICAL for check in checks):
            return HealthStatus.CRITICAL
        elif any(check.status == HealthStatus.WARNING for check in checks):
            return HealthStatus.WARNING
        elif all(check.status == HealthStatus.HEALTHY for check in checks):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    async def trigger_critical_alerts(self, health_status: SystemHealth):
        """Trigger alerts for critical issues"""
        critical_checks = [check for check in health_status.checks if check.status == HealthStatus.CRITICAL]
        
        for check in critical_checks:
            alert_key = f"critical_{check.name}"
            current_time = time.time()
            
            # Check cooldown period
            if alert_key in self.last_alerts:
                if current_time - self.last_alerts[alert_key] < self.alert_cooldown:
                    continue
            
            self.last_alerts[alert_key] = current_time
            logger.critical(f"CRITICAL ALERT: {check.message}")
            
            # Here you would integrate with actual alerting systems:
            # - Discord webhook
            # - Email notifications  
            # - Slack notifications
            # - PagerDuty
            await self._send_alert("CRITICAL", check)
    
    async def trigger_warning_alerts(self, health_status: SystemHealth):
        """Trigger alerts for warning issues"""
        warning_checks = [check for check in health_status.checks if check.status == HealthStatus.WARNING]
        
        for check in warning_checks:
            alert_key = f"warning_{check.name}"
            current_time = time.time()
            
            # Longer cooldown for warnings
            if alert_key in self.last_alerts:
                if current_time - self.last_alerts[alert_key] < self.alert_cooldown * 2:
                    continue
            
            self.last_alerts[alert_key] = current_time
            logger.warning(f"WARNING ALERT: {check.message}")
            await self._send_alert("WARNING", check)
    
    async def _send_alert(self, level: str, check: HealthCheck):
        """Send alert to configured channels"""
        # Placeholder for actual alerting implementation
        alert_data = {
            "level": level,
            "check_name": check.name,
            "message": check.message,
            "value": check.value,
            "threshold": check.threshold,
            "timestamp": check.timestamp.isoformat()
        }
        
        logger.info(f"Alert sent: {json.dumps(alert_data, indent=2)}")
    
    def _log_health_details(self, health_status: SystemHealth):
        """Log detailed health information"""
        status_summary = {
            "overall_status": health_status.overall_status.value,
            "timestamp": health_status.timestamp.isoformat(),
            "checks": {
                check.name: {
                    "status": check.status.value,
                    "value": check.value,
                    "message": check.message
                } for check in health_status.checks
            }
        }
        
        logger.info(f"Health Status: {json.dumps(status_summary, indent=2)}")

# Standalone execution
async def main():
    """Main function for running the health monitor"""
    print("🔍 Starting Virtuoso CCXT Critical Health Monitor")
    print("=" * 50)
    
    async with CriticalHealthMonitor() as monitor:
        try:
            # Run continuous monitoring
            await monitor.continuous_health_check(interval=30)
        except KeyboardInterrupt:
            print("\n⏹️  Health monitoring stopped by user")
        except Exception as e:
            print(f"❌ Health monitoring failed: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(main())
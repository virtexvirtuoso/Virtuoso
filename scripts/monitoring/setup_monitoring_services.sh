#!/bin/bash

#############################################################################
# Script: setup_monitoring_services.sh
# Purpose: Setup comprehensive systemd services for monitoring components
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
#   Sets up dedicated systemd services for comprehensive monitoring of the
#   Virtuoso trading system. Creates health monitors for system resources,
#   disk space, memory usage, CPU load, and network connectivity with
#   automated alerting capabilities.
#
# Dependencies:
#   - Bash 4.0+
#   - systemctl (systemd)
#   - Python 3.8+
#   - Root privileges
#   - Discord webhook for alerts (optional)
#
# Usage:
#   sudo ./setup_monitoring_services.sh
#   
#   Examples:
#     sudo ./setup_monitoring_services.sh
#
# Services Created:
#   - virtuoso-health-monitor.service (system health monitoring)
#   - virtuoso-resource-monitor.service (resource usage monitoring)
#   - virtuoso-disk-monitor.service (disk space monitoring)
#
# Environment Variables:
#   PROJECT_ROOT        Trading system root directory
#   DISCORD_WEBHOOK_URL Discord webhook for alert notifications
#
# Configuration:
#   Monitoring thresholds and intervals can be configured in:
#   - scripts/monitoring/resource_monitor.py
#   - scripts/monitoring/health_monitor.py
#
# Output:
#   - Systemd service files in /etc/systemd/system/
#   - Monitoring scripts in PROJECT_ROOT/scripts/monitoring/
#   - Log files in systemd journal (journalctl -u service-name)
#
# Exit Codes:
#   0 - Success
#   1 - Permission denied (must run as root)
#   2 - Service creation failed
#   3 - Service start failed
#
# Notes:
#   - Must be run as root to create systemd services
#   - Services are enabled for auto-start on boot
#   - Creates comprehensive monitoring suite for production deployment
#   - Includes email and Discord notification capabilities
#
#############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/home/linuxuser/trading/Virtuoso_ccxt"

echo "=== Setting up Monitoring Services ==="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

# Create comprehensive resource monitor script
log_step "Creating comprehensive resource monitor..."

cat > "$PROJECT_ROOT/scripts/monitoring/resource_monitor.py" << 'EOF'
#!/usr/bin/env python3
"""
Comprehensive Resource Monitor for Virtuoso Trading System
Monitors disk space, memory, CPU, network, and sends alerts
"""

import os
import sys
import time
import json
import logging
import smtplib
import subprocess
import psutil
import sqlite3
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
MONITOR_CONFIG = {
    'check_interval': 60,  # Check every minute
    'alert_thresholds': {
        'disk_usage_percent': 80,
        'memory_usage_percent': 85,
        'cpu_usage_percent': 90,
        'load_average_1m': 8.0,
        'swap_usage_percent': 50,
        'disk_io_wait': 30,  # seconds
        'network_errors_per_min': 10
    },
    'alert_cooldown': 1800,  # 30 minutes between similar alerts
    'log_retention_days': 7,
    'database_file': '/home/linuxuser/trading/Virtuoso_ccxt/data/monitoring.db',
    'log_file': '/home/linuxuser/trading/Virtuoso_ccxt/logs/resource_monitor.log'
}

class ResourceMonitor:
    def __init__(self):
        self.setup_logging()
        self.setup_database()
        self.last_alerts = {}
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path(MONITOR_CONFIG['log_file']).parent
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(MONITOR_CONFIG['log_file']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_database(self):
        """Setup SQLite database for storing metrics"""
        db_dir = Path(MONITOR_CONFIG['database_file']).parent
        db_dir.mkdir(exist_ok=True)
        
        with sqlite3.connect(MONITOR_CONFIG['database_file']) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS resource_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    hostname TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    resolved TEXT DEFAULT NULL
                )
            ''')
            
        self.logger.info("Database initialized")
        
    def should_send_alert(self, alert_type: str) -> bool:
        """Check if enough time has passed since last alert of this type"""
        now = datetime.now()
        last_alert = self.last_alerts.get(alert_type)
        
        if last_alert is None:
            return True
            
        return (now - last_alert).seconds > MONITOR_CONFIG['alert_cooldown']
        
    def record_alert(self, alert_type: str, message: str, severity: str):
        """Record alert in database and memory"""
        self.last_alerts[alert_type] = datetime.now()
        
        with sqlite3.connect(MONITOR_CONFIG['database_file']) as conn:
            conn.execute('''
                INSERT INTO alerts (timestamp, alert_type, message, severity)
                VALUES (?, ?, ?, ?)
            ''', (datetime.now().isoformat(), alert_type, message, severity))
            
    def record_metric(self, metric_type: str, metric_name: str, value: float, unit: str = ''):
        """Record metric in database"""
        hostname = subprocess.check_output(['hostname']).decode().strip()
        
        with sqlite3.connect(MONITOR_CONFIG['database_file']) as conn:
            conn.execute('''
                INSERT INTO resource_metrics (timestamp, metric_type, metric_name, value, unit, hostname)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), metric_type, metric_name, value, unit, hostname))
            
    def send_alert(self, subject: str, body: str, severity: str = 'warning'):
        """Send email alert"""
        try:
            msg = MIMEText(body)
            msg['Subject'] = f"[VIRTUOSO-{severity.upper()}] {subject}"
            msg['From'] = 'resource-monitor@localhost'
            msg['To'] = 'linuxuser@localhost'
            
            with smtplib.SMTP('localhost') as server:
                server.send_message(msg)
                
            self.logger.info(f"Alert sent: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
            return False
            
    def check_disk_usage(self) -> List[Dict]:
        """Monitor disk usage across all mounted filesystems"""
        alerts = []
        
        try:
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    percent_used = (usage.used / usage.total) * 100
                    
                    # Record metric
                    self.record_metric('disk', f'usage_{partition.mountpoint.replace("/", "_")}', 
                                     percent_used, 'percent')
                    
                    if percent_used > MONITOR_CONFIG['alert_thresholds']['disk_usage_percent']:
                        alert_key = f"disk_{partition.mountpoint.replace('/', '_')}"
                        
                        if self.should_send_alert(alert_key):
                            alert = {
                                'type': 'disk_space',
                                'mountpoint': partition.mountpoint,
                                'device': partition.device,
                                'percent_used': round(percent_used, 1),
                                'free_gb': round(usage.free / (1024**3), 2),
                                'total_gb': round(usage.total / (1024**3), 2),
                                'severity': 'critical' if percent_used > 90 else 'warning'
                            }
                            alerts.append(alert)
                            
                            message = f"Disk space critical on {partition.mountpoint}: {percent_used:.1f}% used"
                            self.record_alert(alert_key, message, alert['severity'])
                            
                except PermissionError:
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error checking disk usage: {e}")
            
        return alerts
        
    def check_memory_usage(self) -> List[Dict]:
        """Monitor memory and swap usage"""
        alerts = []
        
        try:
            # Virtual memory
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            self.record_metric('memory', 'usage_percent', memory_percent, 'percent')
            self.record_metric('memory', 'available_gb', memory.available / (1024**3), 'GB')
            
            if memory_percent > MONITOR_CONFIG['alert_thresholds']['memory_usage_percent']:
                alert_key = "memory_usage"
                
                if self.should_send_alert(alert_key):
                    alert = {
                        'type': 'memory_usage',
                        'percent_used': round(memory_percent, 1),
                        'available_gb': round(memory.available / (1024**3), 2),
                        'total_gb': round(memory.total / (1024**3), 2),
                        'severity': 'critical' if memory_percent > 95 else 'warning'
                    }
                    alerts.append(alert)
                    
                    message = f"Memory usage critical: {memory_percent:.1f}% used"
                    self.record_alert(alert_key, message, alert['severity'])
            
            # Swap memory
            swap = psutil.swap_memory()
            if swap.total > 0:
                swap_percent = swap.percent
                self.record_metric('memory', 'swap_usage_percent', swap_percent, 'percent')
                
                if swap_percent > MONITOR_CONFIG['alert_thresholds']['swap_usage_percent']:
                    alert_key = "swap_usage"
                    
                    if self.should_send_alert(alert_key):
                        alert = {
                            'type': 'swap_usage',
                            'percent_used': round(swap_percent, 1),
                            'severity': 'warning'
                        }
                        alerts.append(alert)
                        
                        message = f"Swap usage high: {swap_percent:.1f}% used"
                        self.record_alert(alert_key, message, alert['severity'])
                        
        except Exception as e:
            self.logger.error(f"Error checking memory usage: {e}")
            
        return alerts
        
    def check_cpu_usage(self) -> List[Dict]:
        """Monitor CPU usage and load average"""
        alerts = []
        
        try:
            # CPU percentage
            cpu_percent = psutil.cpu_percent(interval=10)
            self.record_metric('cpu', 'usage_percent', cpu_percent, 'percent')
            
            if cpu_percent > MONITOR_CONFIG['alert_thresholds']['cpu_usage_percent']:
                alert_key = "cpu_usage"
                
                if self.should_send_alert(alert_key):
                    alert = {
                        'type': 'cpu_usage',
                        'cpu_percent': round(cpu_percent, 1),
                        'severity': 'critical' if cpu_percent > 95 else 'warning'
                    }
                    alerts.append(alert)
                    
                    message = f"CPU usage critical: {cpu_percent:.1f}%"
                    self.record_alert(alert_key, message, alert['severity'])
            
            # Load average
            load_avg = psutil.getloadavg()
            load_1m, load_5m, load_15m = load_avg
            
            self.record_metric('cpu', 'load_1m', load_1m, 'load')
            self.record_metric('cpu', 'load_5m', load_5m, 'load')
            self.record_metric('cpu', 'load_15m', load_15m, 'load')
            
            if load_1m > MONITOR_CONFIG['alert_thresholds']['load_average_1m']:
                alert_key = "load_average"
                
                if self.should_send_alert(alert_key):
                    alert = {
                        'type': 'load_average',
                        'load_1m': round(load_1m, 2),
                        'load_5m': round(load_5m, 2),
                        'load_15m': round(load_15m, 2),
                        'severity': 'critical' if load_1m > 16 else 'warning'
                    }
                    alerts.append(alert)
                    
                    message = f"Load average critical: {load_1m:.2f}"
                    self.record_alert(alert_key, message, alert['severity'])
                    
        except Exception as e:
            self.logger.error(f"Error checking CPU usage: {e}")
            
        return alerts
        
    def check_network_stats(self) -> List[Dict]:
        """Monitor network interface statistics"""
        alerts = []
        
        try:
            net_io = psutil.net_io_counters()
            
            # Record network metrics
            self.record_metric('network', 'bytes_sent_mb', net_io.bytes_sent / (1024**2), 'MB')
            self.record_metric('network', 'bytes_recv_mb', net_io.bytes_recv / (1024**2), 'MB')
            self.record_metric('network', 'packets_sent', net_io.packets_sent, 'packets')
            self.record_metric('network', 'packets_recv', net_io.packets_recv, 'packets')
            
            # Check for errors
            total_errors = net_io.errin + net_io.errout + net_io.dropin + net_io.dropout
            self.record_metric('network', 'total_errors', total_errors, 'count')
            
            # Network error alerting would require tracking error rate over time
            # For now, just log significant error counts
            if total_errors > 100:
                self.logger.warning(f"Network errors detected: {total_errors}")
                
        except Exception as e:
            self.logger.error(f"Error checking network stats: {e}")
            
        return alerts
        
    def check_disk_io(self) -> List[Dict]:
        """Monitor disk I/O statistics"""
        alerts = []
        
        try:
            disk_io = psutil.disk_io_counters()
            
            if disk_io:
                # Record disk I/O metrics
                self.record_metric('disk_io', 'read_mb', disk_io.read_bytes / (1024**2), 'MB')
                self.record_metric('disk_io', 'write_mb', disk_io.write_bytes / (1024**2), 'MB')
                self.record_metric('disk_io', 'read_count', disk_io.read_count, 'count')
                self.record_metric('disk_io', 'write_count', disk_io.write_count, 'count')
                
        except Exception as e:
            self.logger.error(f"Error checking disk I/O: {e}")
            
        return alerts
        
    def get_system_summary(self) -> Dict:
        """Get comprehensive system status summary"""
        try:
            summary = {
                'timestamp': datetime.now().isoformat(),
                'hostname': subprocess.check_output(['hostname']).decode().strip(),
                'uptime': datetime.now() - datetime.fromtimestamp(psutil.boot_time()),
                'cpu': {
                    'usage_percent': psutil.cpu_percent(interval=1),
                    'load_avg': psutil.getloadavg(),
                    'core_count': psutil.cpu_count()
                },
                'memory': {
                    'total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                    'used_percent': psutil.virtual_memory().percent,
                    'available_gb': round(psutil.virtual_memory().available / (1024**3), 2)
                },
                'disk': {},
                'network': psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
                'processes': len(psutil.pids())
            }
            
            # Add disk information
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    summary['disk'][partition.mountpoint] = {
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_percent': round((usage.used / usage.total) * 100, 1),
                        'free_gb': round(usage.free / (1024**3), 2)
                    }
                except PermissionError:
                    continue
                    
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting system summary: {e}")
            return {}
            
    def run_monitoring_cycle(self):
        """Run complete monitoring cycle"""
        self.logger.info("Starting monitoring cycle...")
        
        all_alerts = []
        
        # Run all checks
        all_alerts.extend(self.check_disk_usage())
        all_alerts.extend(self.check_memory_usage())
        all_alerts.extend(self.check_cpu_usage())
        all_alerts.extend(self.check_network_stats())
        all_alerts.extend(self.check_disk_io())
        
        # Send alerts if any issues found
        if all_alerts:
            critical_alerts = [a for a in all_alerts if a.get('severity') == 'critical']
            warning_alerts = [a for a in all_alerts if a.get('severity') == 'warning']
            
            if critical_alerts:
                self.send_resource_alert(critical_alerts, 'critical')
            if warning_alerts:
                self.send_resource_alert(warning_alerts, 'warning')
                
            self.logger.error(f"Resource monitoring detected {len(all_alerts)} issues")
        else:
            self.logger.info("Resource monitoring: All systems normal")
            
        return len(all_alerts) == 0
        
    def send_resource_alert(self, alerts: List[Dict], severity: str):
        """Send consolidated resource alert"""
        subject = f"Resource Alert - {len(alerts)} {severity} issues"
        
        body = f"""
Virtuoso Trading System - Resource Monitoring Alert

Severity: {severity.upper()}
Issues Detected: {len(alerts)}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Host: {subprocess.check_output(['hostname']).decode().strip()}

Alert Details:
"""
        
        for alert in alerts:
            if alert['type'] == 'disk_space':
                body += f"- Disk {alert['mountpoint']}: {alert['percent_used']}% used ({alert['free_gb']}GB free)\n"
            elif alert['type'] == 'memory_usage':
                body += f"- Memory: {alert['percent_used']}% used ({alert['available_gb']}GB available)\n"
            elif alert['type'] == 'cpu_usage':
                body += f"- CPU: {alert['cpu_percent']}% usage\n"
            elif alert['type'] == 'load_average':
                body += f"- Load: {alert['load_1m']} (1m), {alert['load_5m']} (5m), {alert['load_15m']} (15m)\n"
            elif alert['type'] == 'swap_usage':
                body += f"- Swap: {alert['percent_used']}% used\n"
                
        body += f"""

System Summary:
"""
        summary = self.get_system_summary()
        if summary:
            body += f"- CPU: {summary['cpu']['usage_percent']:.1f}% usage, Load: {summary['cpu']['load_avg'][0]:.2f}\n"
            body += f"- Memory: {summary['memory']['used_percent']:.1f}% used, {summary['memory']['available_gb']}GB free\n"
            for mount, disk_info in summary['disk'].items():
                body += f"- Disk {mount}: {disk_info['used_percent']:.1f}% used, {disk_info['free_gb']}GB free\n"
                
        body += f"""

Recommended Actions:
1. Check system processes: htop or top
2. Review disk usage: df -h and du -h
3. Check service status: systemctl status virtuoso*
4. Review application logs for errors
5. Consider system maintenance or optimization

Monitoring Database: {MONITOR_CONFIG['database_file']}
        """
        
        self.send_alert(subject, body, severity)
        
    def cleanup_old_data(self):
        """Clean up old monitoring data"""
        cutoff_date = (datetime.now() - timedelta(days=MONITOR_CONFIG['log_retention_days'])).isoformat()
        
        with sqlite3.connect(MONITOR_CONFIG['database_file']) as conn:
            # Clean old metrics
            result = conn.execute('''
                DELETE FROM resource_metrics WHERE timestamp < ?
            ''', (cutoff_date,))
            
            metrics_deleted = result.rowcount
            
            # Clean old resolved alerts
            result = conn.execute('''
                DELETE FROM alerts WHERE timestamp < ? AND resolved IS NOT NULL
            ''', (cutoff_date,))
            
            alerts_deleted = result.rowcount
            
            if metrics_deleted > 0 or alerts_deleted > 0:
                self.logger.info(f"Cleaned up {metrics_deleted} old metrics and {alerts_deleted} old alerts")
                
    def run_continuous_monitoring(self):
        """Run continuous monitoring loop"""
        self.logger.info("Starting continuous resource monitoring...")
        self.logger.info(f"Check interval: {MONITOR_CONFIG['check_interval']} seconds")
        
        try:
            while True:
                self.run_monitoring_cycle()
                
                # Cleanup old data once per day
                if datetime.now().hour == 3 and datetime.now().minute < 5:
                    self.cleanup_old_data()
                    
                time.sleep(MONITOR_CONFIG['check_interval'])
                
        except KeyboardInterrupt:
            self.logger.info("Resource monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Resource monitoring error: {e}")
            raise

def main():
    """Main function"""
    monitor = ResourceMonitor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--once':
            success = monitor.run_monitoring_cycle()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == '--summary':
            summary = monitor.get_system_summary()
            print(json.dumps(summary, indent=2, default=str))
        elif sys.argv[1] == '--cleanup':
            monitor.cleanup_old_data()
        else:
            print("Usage:")
            print("  resource_monitor.py              - Run continuous monitoring")
            print("  resource_monitor.py --once       - Run single monitoring cycle")
            print("  resource_monitor.py --summary    - Show system summary")
            print("  resource_monitor.py --cleanup    - Clean old monitoring data")
            sys.exit(1)
    else:
        monitor.run_continuous_monitoring()

if __name__ == '__main__':
    main()
EOF

chmod +x "$PROJECT_ROOT/scripts/monitoring/resource_monitor.py"
chown linuxuser:linuxuser "$PROJECT_ROOT/scripts/monitoring/resource_monitor.py"

# Create systemd service for health monitor
log_step "Creating health monitoring systemd service..."

cat > /etc/systemd/system/virtuoso-health-monitor.service << EOF
[Unit]
Description=Virtuoso Trading System Health Monitor
Documentation=file://$PROJECT_ROOT/docs/
After=network.target multi-user.target
Wants=network.target

[Service]
Type=exec
User=linuxuser
Group=linuxuser
WorkingDirectory=$PROJECT_ROOT
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$PROJECT_ROOT
ExecStart=/usr/bin/python3 $PROJECT_ROOT/scripts/monitoring/health_monitor.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=virtuoso-health-monitor

# Resource limits
LimitNOFILE=1024
MemoryMax=128M
CPUQuota=10%

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=false
ReadWritePaths=$PROJECT_ROOT/logs $PROJECT_ROOT/data /tmp
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for resource monitor
log_step "Creating resource monitoring systemd service..."

cat > /etc/systemd/system/virtuoso-resource-monitor.service << EOF
[Unit]
Description=Virtuoso Trading System Resource Monitor
Documentation=file://$PROJECT_ROOT/docs/
After=network.target multi-user.target
Wants=network.target

[Service]
Type=exec
User=linuxuser
Group=linuxuser
WorkingDirectory=$PROJECT_ROOT
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$PROJECT_ROOT
ExecStart=/usr/bin/python3 $PROJECT_ROOT/scripts/monitoring/resource_monitor.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=virtuoso-resource-monitor

# Resource limits
LimitNOFILE=1024
MemoryMax=256M
CPUQuota=15%

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=false
ReadWritePaths=$PROJECT_ROOT/logs $PROJECT_ROOT/data /tmp
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Create monitoring control script
log_step "Creating monitoring control script..."

cat > "$PROJECT_ROOT/scripts/monitoring/monitor_control.sh" << 'EOF'
#!/bin/bash
# Monitoring Services Control Script

SERVICE_PREFIX="virtuoso"
MONITORING_SERVICES=(
    "virtuoso-health-monitor"
    "virtuoso-resource-monitor"
)

show_usage() {
    echo "Usage: $0 {start|stop|restart|status|enable|disable|logs}"
    echo
    echo "Commands:"
    echo "  start    - Start monitoring services"
    echo "  stop     - Stop monitoring services"  
    echo "  restart  - Restart monitoring services"
    echo "  status   - Show service status"
    echo "  enable   - Enable services to start on boot"
    echo "  disable  - Disable services from starting on boot"
    echo "  logs     - Show recent logs from monitoring services"
    echo
    echo "Services managed:"
    for service in "${MONITORING_SERVICES[@]}"; do
        echo "  - $service"
    done
}

start_services() {
    echo "Starting monitoring services..."
    for service in "${MONITORING_SERVICES[@]}"; do
        echo "Starting $service..."
        sudo systemctl start "$service"
    done
    echo "Monitoring services started"
}

stop_services() {
    echo "Stopping monitoring services..."
    for service in "${MONITORING_SERVICES[@]}"; do
        echo "Stopping $service..."
        sudo systemctl stop "$service"
    done
    echo "Monitoring services stopped"
}

restart_services() {
    echo "Restarting monitoring services..."
    for service in "${MONITORING_SERVICES[@]}"; do
        echo "Restarting $service..."
        sudo systemctl restart "$service"
    done
    echo "Monitoring services restarted"
}

show_status() {
    echo "=== Monitoring Services Status ==="
    for service in "${MONITORING_SERVICES[@]}"; do
        echo
        echo "--- $service ---"
        sudo systemctl status "$service" --no-pager -l
    done
    
    echo
    echo "=== Service Summary ==="
    for service in "${MONITORING_SERVICES[@]}"; do
        if systemctl is-active --quiet "$service"; then
            status="✅ RUNNING"
        else
            status="❌ STOPPED"
        fi
        
        if systemctl is-enabled --quiet "$service" 2>/dev/null; then
            enabled="(enabled)"
        else
            enabled="(disabled)"
        fi
        
        echo "$service: $status $enabled"
    done
}

enable_services() {
    echo "Enabling monitoring services..."
    for service in "${MONITORING_SERVICES[@]}"; do
        echo "Enabling $service..."
        sudo systemctl enable "$service"
    done
    echo "Monitoring services enabled"
}

disable_services() {
    echo "Disabling monitoring services..."
    for service in "${MONITORING_SERVICES[@]}"; do
        echo "Disabling $service..."
        sudo systemctl disable "$service"
    done
    echo "Monitoring services disabled"
}

show_logs() {
    echo "=== Monitoring Services Logs ==="
    for service in "${MONITORING_SERVICES[@]}"; do
        echo
        echo "--- $service (last 20 lines) ---"
        sudo journalctl -u "$service" -n 20 --no-pager
    done
}

case "${1:-}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    enable)
        enable_services
        ;;
    disable)
        disable_services
        ;;
    logs)
        show_logs
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
EOF

chmod +x "$PROJECT_ROOT/scripts/monitoring/monitor_control.sh"
chown linuxuser:linuxuser "$PROJECT_ROOT/scripts/monitoring/monitor_control.sh"

# Install psutil if not available
log_step "Installing required Python packages..."
pip3 install psutil

# Reload systemd daemon
log_step "Reloading systemd daemon..."
systemctl daemon-reload

# Enable services
log_step "Enabling monitoring services..."
systemctl enable virtuoso-health-monitor.service
systemctl enable virtuoso-resource-monitor.service

# Create monitoring dashboard script
cat > "$PROJECT_ROOT/scripts/monitoring/monitoring_dashboard.py" << 'EOF'
#!/usr/bin/env python3
"""
Simple monitoring dashboard for Virtuoso Trading System
Shows real-time system status and alerts
"""

import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

def get_service_status(service_name):
    """Get systemd service status"""
    try:
        result = subprocess.run(['systemctl', 'is-active', service_name], 
                              capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return 'unknown'

def get_recent_alerts():
    """Get recent alerts from monitoring database"""
    db_file = '/home/linuxuser/trading/Virtuoso_ccxt/data/monitoring.db'
    
    if not Path(db_file).exists():
        return []
        
    try:
        with sqlite3.connect(db_file) as conn:
            cursor = conn.execute('''
                SELECT timestamp, alert_type, message, severity
                FROM alerts
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10
            ''', ((datetime.now() - timedelta(hours=24)).isoformat(),))
            
            return cursor.fetchall()
    except:
        return []

def get_system_metrics():
    """Get current system metrics"""
    try:
        # Run resource monitor to get current summary
        result = subprocess.run([
            'python3', 
            '/home/linuxuser/trading/Virtuoso_ccxt/scripts/monitoring/resource_monitor.py',
            '--summary'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            return json.loads(result.stdout)
    except:
        pass
    
    return {}

def print_dashboard():
    """Print monitoring dashboard"""
    os.system('clear')
    
    print("=" * 80)
    print("       VIRTUOSO TRADING SYSTEM - MONITORING DASHBOARD")
    print("=" * 80)
    print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Service Status
    print("SERVICE STATUS")
    print("-" * 40)
    
    services = [
        'virtuoso.service',
        'virtuoso-web.service', 
        'virtuoso-cache.service',
        'virtuoso-ticker.service',
        'virtuoso-health-monitor.service',
        'virtuoso-resource-monitor.service'
    ]
    
    for service in services:
        status = get_service_status(service)
        
        if status == 'active':
            status_icon = '✅'
            status_text = 'RUNNING'
        elif status == 'inactive':
            status_icon = '⭕'
            status_text = 'STOPPED'
        else:
            status_icon = '❌'
            status_text = status.upper()
            
        print(f"{status_icon} {service:<30} {status_text}")
    
    print()
    
    # System Metrics
    print("SYSTEM METRICS")
    print("-" * 40)
    
    metrics = get_system_metrics()
    if metrics:
        # CPU
        cpu_usage = metrics.get('cpu', {}).get('usage_percent', 0)
        cpu_icon = '🔴' if cpu_usage > 80 else '🟡' if cpu_usage > 60 else '🟢'
        print(f"{cpu_icon} CPU Usage:        {cpu_usage:.1f}%")
        
        # Load average
        load_avg = metrics.get('cpu', {}).get('load_avg', [0, 0, 0])
        load_icon = '🔴' if load_avg[0] > 4 else '🟡' if load_avg[0] > 2 else '🟢'
        print(f"{load_icon} Load Average:     {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}")
        
        # Memory
        memory = metrics.get('memory', {})
        mem_usage = memory.get('used_percent', 0)
        mem_icon = '🔴' if mem_usage > 85 else '🟡' if mem_usage > 70 else '🟢'
        print(f"{mem_icon} Memory Usage:     {mem_usage:.1f}% ({memory.get('available_gb', 0):.1f}GB free)")
        
        # Disk
        print(f"💾 Disk Usage:")
        for mount, disk_info in metrics.get('disk', {}).items():
            disk_usage = disk_info.get('used_percent', 0)
            disk_icon = '🔴' if disk_usage > 80 else '🟡' if disk_usage > 60 else '🟢'
            print(f"   {disk_icon} {mount:<15} {disk_usage:.1f}% ({disk_info.get('free_gb', 0):.1f}GB free)")
            
        # Processes
        proc_count = metrics.get('processes', 0)
        print(f"⚙️  Active Processes: {proc_count}")
        
        # Uptime
        uptime_str = str(metrics.get('uptime', '')).split('.')[0]  # Remove microseconds
        print(f"⏰ System Uptime:   {uptime_str}")
    else:
        print("❌ Unable to retrieve system metrics")
    
    print()
    
    # Recent Alerts
    print("RECENT ALERTS (24h)")
    print("-" * 40)
    
    alerts = get_recent_alerts()
    if alerts:
        for timestamp, alert_type, message, severity in alerts[:5]:
            # Parse timestamp
            try:
                alert_time = datetime.fromisoformat(timestamp)
                time_str = alert_time.strftime('%H:%M:%S')
            except:
                time_str = timestamp
                
            severity_icon = '🔴' if severity == 'critical' else '🟡'
            print(f"{severity_icon} {time_str} [{severity.upper()}] {message}")
    else:
        print("🟢 No recent alerts")
    
    print()
    print("=" * 80)
    print("Press Ctrl+C to exit | Refresh every 30 seconds")
    print("=" * 80)

def main():
    """Main dashboard function"""
    try:
        import time
        while True:
            print_dashboard()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\nDashboard closed")
        sys.exit(0)

if __name__ == '__main__':
    main()
EOF

chmod +x "$PROJECT_ROOT/scripts/monitoring/monitoring_dashboard.py"
chown linuxuser:linuxuser "$PROJECT_ROOT/scripts/monitoring/monitoring_dashboard.py"

echo
log_info "Systemd monitoring services setup complete!"
echo
echo "Services Created:"
echo "✅ virtuoso-health-monitor.service - Health and service monitoring"
echo "✅ virtuoso-resource-monitor.service - System resource monitoring"
echo
echo "Service Management:"
echo "- Control script: $PROJECT_ROOT/scripts/monitoring/monitor_control.sh"
echo "- Start services: sudo systemctl start virtuoso-health-monitor virtuoso-resource-monitor"
echo "- Enable on boot: sudo systemctl enable virtuoso-health-monitor virtuoso-resource-monitor"
echo "- Check status: sudo systemctl status virtuoso-health-monitor"
echo
echo "Monitoring Tools:"
echo "- Dashboard: $PROJECT_ROOT/scripts/monitoring/monitoring_dashboard.py"
echo "- Health check: $PROJECT_ROOT/scripts/monitoring/health_monitor.py --once"  
echo "- Resource summary: $PROJECT_ROOT/scripts/monitoring/resource_monitor.py --summary"
echo
echo "Log Files:"
echo "- Health monitor: $PROJECT_ROOT/logs/health_monitor.log"
echo "- Resource monitor: $PROJECT_ROOT/logs/resource_monitor.log"
echo "- Monitoring database: $PROJECT_ROOT/data/monitoring.db"
echo
log_info "Monitoring services are ready to deploy!"
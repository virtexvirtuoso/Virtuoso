#!/usr/bin/env python3
"""
Production Health Monitor for Virtuoso Trading System
Monitors services, system resources, and sends email alerts
"""

import os
import sys
import time
import json
import logging
import smtplib
import subprocess
import psutil
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configuration
CONFIG = {
    'services': [
        'virtuoso.service',
        'virtuoso-web.service', 
        'virtuoso-cache.service',
        'virtuoso-ticker.service'
    ],
    'disk_threshold': 80,  # Alert when disk usage > 80%
    'memory_threshold': 85,  # Alert when memory usage > 85%
    'cpu_threshold': 90,    # Alert when CPU usage > 90%
    'load_threshold': 8.0,  # Alert when load average > 8.0
    'check_interval': 300,  # Check every 5 minutes
    'email': {
        'smtp_server': 'localhost',
        'smtp_port': 587,
        'from_email': 'virtuoso-monitor@localhost',
        'to_email': 'admin@localhost',  # Change this to your email
        'subject_prefix': '[VIRTUOSO ALERT]'
    },
    'paths': {
        'project_root': '/home/linuxuser/trading/Virtuoso_ccxt',
        'log_dir': '/home/linuxuser/trading/Virtuoso_ccxt/logs',
        'state_file': '/tmp/virtuoso_monitor_state.json'
    },
    'alert_cooldown': 1800  # 30 minutes between similar alerts
}

class HealthMonitor:
    def __init__(self):
        self.setup_logging()
        self.last_alerts = {}
        self.load_state()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = os.path.join(CONFIG['paths']['log_dir'], 'health_monitor.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_state(self):
        """Load previous state from file"""
        try:
            if os.path.exists(CONFIG['paths']['state_file']):
                with open(CONFIG['paths']['state_file'], 'r') as f:
                    state = json.load(f)
                    self.last_alerts = state.get('last_alerts', {})
        except Exception as e:
            self.logger.warning(f"Could not load state: {e}")
            
    def save_state(self):
        """Save current state to file"""
        try:
            state = {
                'last_alerts': self.last_alerts,
                'last_updated': datetime.now().isoformat()
            }
            with open(CONFIG['paths']['state_file'], 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save state: {e}")
            
    def should_send_alert(self, alert_type: str) -> bool:
        """Check if enough time has passed since last alert of this type"""
        now = datetime.now()
        last_alert = self.last_alerts.get(alert_type)
        
        if last_alert is None:
            return True
            
        last_alert_time = datetime.fromisoformat(last_alert)
        return (now - last_alert_time).seconds > CONFIG['alert_cooldown']
        
    def record_alert(self, alert_type: str):
        """Record that an alert was sent"""
        self.last_alerts[alert_type] = datetime.now().isoformat()
        self.save_state()
        
    def send_email_alert(self, subject: str, body: str, priority: str = 'normal'):
        """Send email alert"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = CONFIG['email']['from_email']
            msg['To'] = CONFIG['email']['to_email']
            msg['Subject'] = f"{CONFIG['email']['subject_prefix']} {priority.upper()}: {subject}"
            
            # Add timestamp and hostname to body
            hostname = subprocess.check_output(['hostname']).decode().strip()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            full_body = f"""
VIRTUOSO TRADING SYSTEM ALERT

Time: {timestamp}
Host: {hostname}
Priority: {priority.upper()}

{body}

--
Virtuoso Health Monitor
Project: {CONFIG['paths']['project_root']}
            """
            
            msg.attach(MIMEText(full_body, 'plain'))
            
            # Send email
            with smtplib.SMTP(CONFIG['email']['smtp_server'], CONFIG['email']['smtp_port']) as server:
                server.send_message(msg)
                
            self.logger.info(f"Email alert sent: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
            return False
            
    def check_service_status(self, service: str) -> Tuple[bool, str]:
        """Check if a systemd service is running"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True,
                text=True
            )
            
            status = result.stdout.strip()
            is_active = status == 'active'
            
            return is_active, status
            
        except Exception as e:
            return False, f"Error: {e}"
            
    def check_services(self) -> List[Dict]:
        """Check all configured services"""
        alerts = []
        
        for service in CONFIG['services']:
            is_active, status = self.check_service_status(service)
            
            if not is_active:
                alert_key = f"service_{service}"
                
                if self.should_send_alert(alert_key):
                    alert = {
                        'type': 'service_down',
                        'service': service,
                        'status': status,
                        'message': f"Service {service} is not active (status: {status})"
                    }
                    alerts.append(alert)
                    self.record_alert(alert_key)
                    
                self.logger.error(f"Service {service} is down: {status}")
            else:
                self.logger.debug(f"Service {service} is running")
                
        return alerts
        
    def check_disk_space(self) -> List[Dict]:
        """Check disk space usage"""
        alerts = []
        
        try:
            # Check all mounted filesystems
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    percent_used = (usage.used / usage.total) * 100
                    
                    if percent_used > CONFIG['disk_threshold']:
                        alert_key = f"disk_{partition.mountpoint.replace('/', '_')}"
                        
                        if self.should_send_alert(alert_key):
                            alert = {
                                'type': 'disk_space',
                                'mountpoint': partition.mountpoint,
                                'device': partition.device,
                                'percent_used': round(percent_used, 1),
                                'free_gb': round(usage.free / (1024**3), 2),
                                'total_gb': round(usage.total / (1024**3), 2),
                                'message': f"Disk space critical on {partition.mountpoint}: {percent_used:.1f}% used"
                            }
                            alerts.append(alert)
                            self.record_alert(alert_key)
                            
                        self.logger.warning(f"Disk space high on {partition.mountpoint}: {percent_used:.1f}%")
                        
                except PermissionError:
                    # Skip partitions we can't access
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error checking disk space: {e}")
            
        return alerts
        
    def check_memory_usage(self) -> List[Dict]:
        """Check memory usage"""
        alerts = []
        
        try:
            memory = psutil.virtual_memory()
            percent_used = memory.percent
            
            if percent_used > CONFIG['memory_threshold']:
                alert_key = "memory_usage"
                
                if self.should_send_alert(alert_key):
                    alert = {
                        'type': 'memory_usage',
                        'percent_used': round(percent_used, 1),
                        'available_gb': round(memory.available / (1024**3), 2),
                        'total_gb': round(memory.total / (1024**3), 2),
                        'message': f"Memory usage critical: {percent_used:.1f}% used"
                    }
                    alerts.append(alert)
                    self.record_alert(alert_key)
                    
                self.logger.warning(f"Memory usage high: {percent_used:.1f}%")
                
        except Exception as e:
            self.logger.error(f"Error checking memory usage: {e}")
            
        return alerts
        
    def check_cpu_usage(self) -> List[Dict]:
        """Check CPU usage and load average"""
        alerts = []
        
        try:
            # Check CPU percentage (average over 10 seconds)
            cpu_percent = psutil.cpu_percent(interval=10)
            
            if cpu_percent > CONFIG['cpu_threshold']:
                alert_key = "cpu_usage"
                
                if self.should_send_alert(alert_key):
                    alert = {
                        'type': 'cpu_usage',
                        'cpu_percent': round(cpu_percent, 1),
                        'message': f"CPU usage critical: {cpu_percent:.1f}%"
                    }
                    alerts.append(alert)
                    self.record_alert(alert_key)
                    
                self.logger.warning(f"CPU usage high: {cpu_percent:.1f}%")
                
            # Check load average
            load_avg = psutil.getloadavg()[0]  # 1-minute load average
            
            if load_avg > CONFIG['load_threshold']:
                alert_key = "load_average"
                
                if self.should_send_alert(alert_key):
                    alert = {
                        'type': 'load_average',
                        'load_1min': round(load_avg, 2),
                        'load_5min': round(psutil.getloadavg()[1], 2),
                        'load_15min': round(psutil.getloadavg()[2], 2),
                        'message': f"Load average critical: {load_avg:.2f}"
                    }
                    alerts.append(alert)
                    self.record_alert(alert_key)
                    
                self.logger.warning(f"Load average high: {load_avg:.2f}")
                
        except Exception as e:
            self.logger.error(f"Error checking CPU usage: {e}")
            
        return alerts
        
    def check_process_count(self) -> List[Dict]:
        """Check if critical processes are running"""
        alerts = []
        
        try:
            # Look for Python processes that might be our trading system
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'virtuoso' in cmdline.lower() or 'main.py' in cmdline:
                            python_processes.append({
                                'pid': proc.info['pid'],
                                'cmdline': cmdline
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            # Alert if no trading processes found
            if len(python_processes) == 0:
                alert_key = "no_trading_processes"
                
                if self.should_send_alert(alert_key):
                    alert = {
                        'type': 'no_processes',
                        'message': "No Virtuoso trading processes found running"
                    }
                    alerts.append(alert)
                    self.record_alert(alert_key)
                    
                self.logger.warning("No Virtuoso trading processes detected")
            else:
                self.logger.debug(f"Found {len(python_processes)} trading processes")
                
        except Exception as e:
            self.logger.error(f"Error checking processes: {e}")
            
        return alerts
        
    def generate_alert_summary(self, alerts: List[Dict]) -> str:
        """Generate a summary of all alerts"""
        if not alerts:
            return "System status: All checks passed"
            
        summary = f"CRITICAL ALERTS DETECTED ({len(alerts)} issues):\n\n"
        
        for i, alert in enumerate(alerts, 1):
            summary += f"{i}. {alert['message']}\n"
            
            # Add additional details based on alert type
            if alert['type'] == 'disk_space':
                summary += f"   Device: {alert['device']}\n"
                summary += f"   Free space: {alert['free_gb']} GB\n"
                
            elif alert['type'] == 'memory_usage':
                summary += f"   Available: {alert['available_gb']} GB\n"
                
            elif alert['type'] == 'load_average':
                summary += f"   Load (1m/5m/15m): {alert['load_1min']}/{alert['load_5min']}/{alert['load_15min']}\n"
                
            summary += "\n"
            
        summary += "RECOMMENDED ACTIONS:\n"
        summary += "1. Check system logs: journalctl -f\n"
        summary += "2. Check service status: systemctl status virtuoso*\n"
        summary += "3. Monitor resource usage: htop\n"
        summary += "4. Check disk space: df -h\n"
        summary += "5. Review application logs in /home/linuxuser/trading/Virtuoso_ccxt/logs/\n"
        
        return summary
        
    def run_health_check(self) -> bool:
        """Run complete health check and send alerts if needed"""
        self.logger.info("Starting health check...")
        
        all_alerts = []
        
        # Run all checks
        all_alerts.extend(self.check_services())
        all_alerts.extend(self.check_disk_space())
        all_alerts.extend(self.check_memory_usage())
        all_alerts.extend(self.check_cpu_usage())
        all_alerts.extend(self.check_process_count())
        
        # Send alerts if any issues found
        if all_alerts:
            critical_count = len([a for a in all_alerts if a['type'] in ['service_down', 'no_processes']])
            priority = 'critical' if critical_count > 0 else 'warning'
            
            subject = f"System Health Alert ({len(all_alerts)} issues)"
            body = self.generate_alert_summary(all_alerts)
            
            self.send_email_alert(subject, body, priority)
            self.logger.error(f"Health check failed: {len(all_alerts)} issues detected")
            
            return False
        else:
            self.logger.info("Health check passed: All systems normal")
            return True
            
    def run_continuous_monitoring(self):
        """Run continuous monitoring loop"""
        self.logger.info("Starting continuous health monitoring...")
        self.logger.info(f"Check interval: {CONFIG['check_interval']} seconds")
        self.logger.info(f"Alert cooldown: {CONFIG['alert_cooldown']} seconds")
        
        try:
            while True:
                self.run_health_check()
                time.sleep(CONFIG['check_interval'])
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")
            self.send_email_alert(
                "Health Monitor Error", 
                f"Health monitoring service encountered an error: {e}",
                'critical'
            )
            raise

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Run health check once and exit
        monitor = HealthMonitor()
        success = monitor.run_health_check()
        sys.exit(0 if success else 1)
    else:
        # Run continuous monitoring
        monitor = HealthMonitor()
        monitor.run_continuous_monitoring()

if __name__ == '__main__':
    main()
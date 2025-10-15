#!/usr/bin/env python3
"""
Disk Space Monitor for Virtuoso Trading System
Monitors disk usage and cleans up old backups automatically
"""

import os
import shutil
import subprocess
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging - use home directory if /var/log is not writable
log_file = '/var/log/disk_monitor.log'
try:
    # Try to create log file in /var/log
    with open(log_file, 'a'):
        pass
except PermissionError:
    # Fall back to home directory
    log_file = '/home/linuxuser/trading/Virtuoso_ccxt/logs/disk_monitor.log'
    os.makedirs('/home/linuxuser/trading/Virtuoso_ccxt/logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DiskMonitor:
    def __init__(self):
        self.trading_dir = Path("/home/linuxuser/trading")
        self.warning_threshold = 80  # % disk usage warning
        self.critical_threshold = 85  # % disk usage critical
        self.cleanup_threshold = 90  # % disk usage cleanup

    def get_disk_usage(self):
        """Get current disk usage percentage"""
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                usage_line = lines[1].split()
                usage_percent = int(usage_line[4].rstrip('%'))
                return usage_percent
        except Exception as e:
            logger.error(f"Failed to get disk usage: {e}")
            return None

    def get_large_backups(self):
        """Find large backup files and directories"""
        large_items = []

        # Check for backup directories
        for item in self.trading_dir.iterdir():
            if item.is_dir() and 'backup' in item.name.lower():
                try:
                    # Get directory size
                    result = subprocess.run(['du', '-sh', str(item)], capture_output=True, text=True)
                    if result.returncode == 0:
                        size_str = result.stdout.split()[0]
                        # Parse size (GB, MB)
                        if 'G' in size_str:
                            size_gb = float(size_str.rstrip('G'))
                            if size_gb > 5:  # Larger than 5GB
                                large_items.append({
                                    'path': str(item),
                                    'size': size_str,
                                    'size_gb': size_gb,
                                    'type': 'directory',
                                    'age_days': (datetime.now() - datetime.fromtimestamp(item.stat().st_mtime)).days
                                })
                except Exception as e:
                    logger.warning(f"Failed to check size of {item}: {e}")

        # Check for large backup files
        backup_patterns = ['*backup*.tar.gz', '*backup*.tar', '*backup*.zip']
        for pattern in backup_patterns:
            for backup_file in self.trading_dir.glob(pattern):
                try:
                    size_mb = backup_file.stat().st_size / (1024 * 1024)
                    if size_mb > 500:  # Larger than 500MB
                        large_items.append({
                            'path': str(backup_file),
                            'size': f"{size_mb:.1f}M",
                            'size_gb': size_mb / 1024,
                            'type': 'file',
                            'age_days': (datetime.now() - datetime.fromtimestamp(backup_file.stat().st_mtime)).days
                        })
                except Exception as e:
                    logger.warning(f"Failed to check size of {backup_file}: {e}")

        # Sort by size (largest first)
        large_items.sort(key=lambda x: x['size_gb'], reverse=True)
        return large_items

    def cleanup_old_backups(self, force=False):
        """Clean up old backup files automatically"""
        cleaned_space = 0
        large_backups = self.get_large_backups()

        logger.info(f"Found {len(large_backups)} large backup items")

        for backup in large_backups:
            # Remove backups older than 14 days or if forced
            if backup['age_days'] > 14 or force:
                try:
                    backup_path = Path(backup['path'])
                    if backup_path.exists():
                        if backup['type'] == 'directory':
                            logger.info(f"Removing old backup directory: {backup['path']} ({backup['size']}, {backup['age_days']} days old)")
                            shutil.rmtree(backup['path'])
                        else:
                            logger.info(f"Removing old backup file: {backup['path']} ({backup['size']}, {backup['age_days']} days old)")
                            backup_path.unlink()

                        cleaned_space += backup['size_gb']
                        logger.info(f"Freed {backup['size']} of disk space")

                except Exception as e:
                    logger.error(f"Failed to remove {backup['path']}: {e}")

        return cleaned_space

    def send_alert(self, level, message):
        """Send alert (can be extended to use email, Slack, etc.)"""
        logger.warning(f"DISK ALERT [{level}]: {message}")

        # Write alert to a file that can be monitored
        alert_file = Path("/tmp/disk_alert.json")
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'disk_usage': self.get_disk_usage()
        }

        try:
            with open(alert_file, 'w') as f:
                json.dump(alert_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write alert file: {e}")

    def monitor(self):
        """Main monitoring function"""
        disk_usage = self.get_disk_usage()

        if disk_usage is None:
            logger.error("Failed to get disk usage")
            return

        logger.info(f"Current disk usage: {disk_usage}%")

        if disk_usage >= self.cleanup_threshold:
            logger.warning(f"Disk usage critical ({disk_usage}%), initiating cleanup")
            self.send_alert("CRITICAL", f"Disk usage at {disk_usage}%, cleaning up old backups")

            # Force cleanup
            cleaned = self.cleanup_old_backups(force=True)
            new_usage = self.get_disk_usage()

            if cleaned > 0:
                logger.info(f"Cleanup completed: freed {cleaned:.1f}GB, disk usage now {new_usage}%")
                self.send_alert("INFO", f"Cleanup successful: freed {cleaned:.1f}GB, usage now {new_usage}%")
            else:
                self.send_alert("ERROR", f"Cleanup failed: no space freed, usage still at {new_usage}%")

        elif disk_usage >= self.critical_threshold:
            self.send_alert("CRITICAL", f"Disk usage at {disk_usage}%, cleanup needed soon")
            # Light cleanup of old backups
            self.cleanup_old_backups(force=False)

        elif disk_usage >= self.warning_threshold:
            self.send_alert("WARNING", f"Disk usage at {disk_usage}%, monitoring closely")

        # Always show large backups for awareness
        large_backups = self.get_large_backups()
        if large_backups:
            logger.info("Large backup items found:")
            for backup in large_backups[:5]:  # Show top 5
                logger.info(f"  {backup['path']}: {backup['size']} ({backup['age_days']} days old)")

if __name__ == "__main__":
    monitor = DiskMonitor()
    monitor.monitor()
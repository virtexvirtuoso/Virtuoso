#!/usr/bin/env python3
"""
Monitoring API Health Check and Auto-Recovery Script
===================================================

This script continuously monitors the monitoring API health and automatically
restarts it if it becomes unresponsive or crashes.
"""

import time
import logging
import requests
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/linuxuser/trading/Virtuoso_ccxt/logs/monitoring_health.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MonitoringHealthChecker:
    """Automated health checker for monitoring API."""

    def __init__(self):
        self.project_root = Path("/home/linuxuser/trading/Virtuoso_ccxt")
        self.check_interval = 60  # Check every minute
        self.failure_threshold = 3  # Restart after 3 consecutive failures
        self.consecutive_failures = 0
        self.last_restart = None
        self.min_restart_interval = 300  # Minimum 5 minutes between restarts

    def check_api_health(self) -> bool:
        """Check if monitoring API is responding."""
        ports_to_check = [8001, 8003, 8004, 8005]

        for port in ports_to_check:
            try:
                response = requests.get(
                    f"http://localhost:{port}/health",
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'healthy':
                        logger.debug(f"Health check passed on port {port}")
                        return True
            except requests.RequestException as e:
                logger.debug(f"Health check failed on port {port}: {e}")
                continue

        return False

    def check_process_running(self) -> bool:
        """Check if monitoring API process is running."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "monitoring_api.py"],
                capture_output=True,
                text=True
            )
            return bool(result.stdout.strip())
        except subprocess.SubprocessError:
            return False

    def restart_monitoring_api(self) -> bool:
        """Restart the monitoring API using our reliability script."""
        try:
            logger.info("Attempting to restart monitoring API...")

            # Use our reliability script
            script_path = self.project_root / "scripts" / "monitoring_reliability_fixes.py"
            python_path = self.project_root / "venv311" / "bin" / "python"

            # Stop first
            subprocess.run([
                str(python_path),
                str(script_path),
                "stop"
            ], cwd=str(self.project_root), timeout=30)

            time.sleep(5)

            # Start with reliability checks
            result = subprocess.run([
                str(python_path),
                str(script_path),
                "start"
            ], cwd=str(self.project_root), timeout=60)

            if result.returncode == 0:
                logger.info("Monitoring API restarted successfully")
                self.last_restart = datetime.now()
                return True
            else:
                logger.error(f"Failed to restart monitoring API (exit code: {result.returncode})")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Restart operation timed out")
            return False
        except Exception as e:
            logger.error(f"Error during restart: {e}")
            return False

    def should_restart(self) -> bool:
        """Determine if we should restart based on failure count and timing."""
        if self.consecutive_failures < self.failure_threshold:
            return False

        if self.last_restart:
            time_since_restart = (datetime.now() - self.last_restart).total_seconds()
            if time_since_restart < self.min_restart_interval:
                logger.warning(f"Skipping restart - too soon ({time_since_restart}s < {self.min_restart_interval}s)")
                return False

        return True

    def send_alert(self, message: str):
        """Send alert about monitoring API issues."""
        logger.error(f"ALERT: {message}")

        # Try to send to system webhook if available
        try:
            webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
            if webhook_url:
                payload = {
                    "content": f"🚨 Monitoring API Alert: {message}",
                    "embeds": [{
                        "title": "Monitoring API Issue",
                        "description": message,
                        "color": 15158332,  # Red
                        "timestamp": datetime.now().isoformat()
                    }]
                }
                requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            logger.warning(f"Failed to send alert webhook: {e}")

    def run_health_check_cycle(self):
        """Run a single health check cycle."""
        api_healthy = self.check_api_health()
        process_running = self.check_process_running()

        if api_healthy:
            if self.consecutive_failures > 0:
                logger.info(f"Monitoring API recovered after {self.consecutive_failures} failures")
                self.consecutive_failures = 0
            return True

        # API is not healthy
        self.consecutive_failures += 1
        logger.warning(f"Health check failed ({self.consecutive_failures}/{self.failure_threshold})")

        if not process_running:
            logger.error("Monitoring API process is not running")
            self.send_alert("Monitoring API process crashed")

        if self.should_restart():
            self.send_alert(f"Monitoring API unresponsive for {self.consecutive_failures} checks, restarting...")

            if self.restart_monitoring_api():
                self.consecutive_failures = 0
                return True
            else:
                self.send_alert("Failed to restart monitoring API")

        return False

    def run_continuous_monitoring(self):
        """Run continuous health monitoring."""
        logger.info("Starting continuous monitoring of Monitoring API")

        while True:
            try:
                self.run_health_check_cycle()
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Health monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in health check: {e}")
                time.sleep(self.check_interval)

    def run_single_check(self) -> bool:
        """Run a single health check and return status."""
        return self.run_health_check_cycle()


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Single check mode
        checker = MonitoringHealthChecker()
        healthy = checker.run_single_check()
        print(f"Monitoring API is {'healthy' if healthy else 'unhealthy'}")
        sys.exit(0 if healthy else 1)
    else:
        # Continuous monitoring mode
        checker = MonitoringHealthChecker()
        checker.run_continuous_monitoring()


if __name__ == "__main__":
    main()
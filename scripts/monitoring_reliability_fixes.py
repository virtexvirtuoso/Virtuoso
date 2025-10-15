#!/usr/bin/env python3
"""
Monitoring API Reliability Prevention Script
===========================================

This script implements comprehensive reliability improvements to prevent
monitoring API failures and port conflicts.
"""

import os
import socket
import subprocess
import sys
import time
import signal
import logging
from pathlib import Path
from typing import List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MonitoringReliabilityManager:
    """Manages monitoring API reliability and prevents common failures."""

    def __init__(self, project_root: str = "/home/linuxuser/trading/Virtuoso_ccxt"):
        self.project_root = Path(project_root)
        self.default_port = 8001
        self.fallback_ports = [8003, 8004, 8005, 8006]
        self.pid_file = self.project_root / "monitoring_api.pid"
        self.log_file = self.project_root / "logs" / "monitoring_api.log"

    def check_port_available(self, port: int) -> bool:
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', port))
                return True
        except OSError:
            return False

    def find_available_port(self) -> Optional[int]:
        """Find the first available port from default and fallback list."""
        all_ports = [self.default_port] + self.fallback_ports

        for port in all_ports:
            if self.check_port_available(port):
                logger.info(f"Found available port: {port}")
                return port

        logger.error("No available ports found!")
        return None

    def kill_conflicting_processes(self, port: int) -> bool:
        """Kill processes using the specified port."""
        try:
            # Find processes using the port
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True
            )

            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                logger.info(f"Found {len(pids)} processes using port {port}")

                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        time.sleep(1)
                        # Force kill if still running
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        logger.info(f"Killed process {pid}")
                    except (ValueError, ProcessLookupError):
                        continue

                time.sleep(2)  # Wait for cleanup
                return True

            return True

        except (subprocess.SubprocessError, OSError) as e:
            logger.warning(f"Could not kill conflicting processes: {e}")
            return False

    def cleanup_old_processes(self):
        """Clean up old monitoring API processes."""
        try:
            # Kill old monitoring API processes
            subprocess.run([
                "pkill", "-f", "monitoring_api.py"
            ], capture_output=True)

            # Clean up hanging bash processes
            subprocess.run([
                "pkill", "-f", "bash.*MONITORING_PORT"
            ], capture_output=True)

            logger.info("Cleaned up old processes")
            time.sleep(2)

        except subprocess.SubprocessError as e:
            logger.warning(f"Process cleanup failed: {e}")

    def create_pid_file(self, pid: int):
        """Create PID file for process management."""
        try:
            self.pid_file.parent.mkdir(exist_ok=True)
            with open(self.pid_file, 'w') as f:
                f.write(str(pid))
            logger.info(f"Created PID file: {self.pid_file}")
        except IOError as e:
            logger.error(f"Failed to create PID file: {e}")

    def read_pid_file(self) -> Optional[int]:
        """Read PID from file."""
        try:
            if self.pid_file.exists():
                with open(self.pid_file, 'r') as f:
                    return int(f.read().strip())
        except (IOError, ValueError):
            pass
        return None

    def is_process_running(self, pid: int) -> bool:
        """Check if process is still running."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def stop_monitoring_api(self):
        """Gracefully stop the monitoring API."""
        pid = self.read_pid_file()

        if pid and self.is_process_running(pid):
            logger.info(f"Stopping monitoring API (PID: {pid})")
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(5)

                # Force kill if still running
                if self.is_process_running(pid):
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(2)

                logger.info("Monitoring API stopped")
            except ProcessLookupError:
                logger.info("Process already stopped")

        # Clean up PID file
        if self.pid_file.exists():
            self.pid_file.unlink()

    def start_monitoring_api(self) -> bool:
        """Start monitoring API with reliability checks."""
        logger.info("Starting monitoring API with reliability checks...")

        # Step 1: Clean up old processes
        self.cleanup_old_processes()

        # Step 2: Find available port
        port = self.find_available_port()
        if not port:
            logger.error("Cannot start: no available ports")
            return False

        # Step 3: If using default port but it's occupied, try to free it
        if port != self.default_port:
            logger.info(f"Default port {self.default_port} not available, using {port}")
            if self.kill_conflicting_processes(self.default_port):
                if self.check_port_available(self.default_port):
                    port = self.default_port
                    logger.info(f"Freed default port {self.default_port}")

        # Step 4: Start the service
        env = os.environ.copy()
        env['MONITORING_PORT'] = str(port)

        try:
            # Ensure log directory exists
            self.log_file.parent.mkdir(exist_ok=True)

            # Start the monitoring API
            process = subprocess.Popen([
                str(self.project_root / "venv311" / "bin" / "python"),
                str(self.project_root / "src" / "monitoring_api.py")
            ],
            env=env,
            stdout=open(self.log_file, 'w'),
            stderr=subprocess.STDOUT,
            cwd=str(self.project_root)
            )

            # Create PID file
            self.create_pid_file(process.pid)

            # Wait a moment and check if it started successfully
            time.sleep(3)

            if process.poll() is None:
                logger.info(f"Monitoring API started successfully on port {port} (PID: {process.pid})")
                return True
            else:
                logger.error("Monitoring API failed to start")
                return False

        except Exception as e:
            logger.error(f"Failed to start monitoring API: {e}")
            return False

    def health_check(self) -> bool:
        """Perform health check on monitoring API."""
        import requests

        pid = self.read_pid_file()
        if not pid or not self.is_process_running(pid):
            logger.warning("Monitoring API process not running")
            return False

        # Try different ports
        ports_to_check = [self.default_port] + self.fallback_ports

        for port in ports_to_check:
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=5)
                if response.status_code == 200:
                    logger.info(f"Health check passed on port {port}")
                    return True
            except requests.RequestException:
                continue

        logger.warning("Health check failed on all ports")
        return False

    def restart_if_unhealthy(self):
        """Restart monitoring API if health check fails."""
        if not self.health_check():
            logger.info("Health check failed, restarting monitoring API...")
            self.stop_monitoring_api()
            time.sleep(2)
            return self.start_monitoring_api()
        return True


def main():
    """Main function for reliability management."""
    if len(sys.argv) < 2:
        print("Usage: python monitoring_reliability_fixes.py [start|stop|restart|health|fix]")
        sys.exit(1)

    manager = MonitoringReliabilityManager()
    command = sys.argv[1].lower()

    if command == "start":
        success = manager.start_monitoring_api()
        sys.exit(0 if success else 1)

    elif command == "stop":
        manager.stop_monitoring_api()
        sys.exit(0)

    elif command == "restart":
        manager.stop_monitoring_api()
        time.sleep(2)
        success = manager.start_monitoring_api()
        sys.exit(0 if success else 1)

    elif command == "health":
        healthy = manager.health_check()
        print("Monitoring API is", "healthy" if healthy else "unhealthy")
        sys.exit(0 if healthy else 1)

    elif command == "fix":
        # Emergency fix mode - force restart with cleanup
        logger.info("Emergency fix mode: cleaning up and restarting...")
        manager.cleanup_old_processes()
        manager.kill_conflicting_processes(manager.default_port)
        success = manager.start_monitoring_api()
        sys.exit(0 if success else 1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
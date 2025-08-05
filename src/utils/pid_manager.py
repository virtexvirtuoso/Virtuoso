"""
PID Management Utility for Virtuoso Trading System

Provides centralized process identification and management capabilities.
"""

import os
import sys
import psutil
import signal
import atexit
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PIDManager:
    """Manages process identification and lifecycle for the trading system."""
    
    def __init__(self, pid_file: str = "/tmp/virtuoso.pid"):
        """
        Initialize PID manager.
        
        Args:
            pid_file: Path to PID file (default: /tmp/virtuoso.pid)
        """
        self.pid_file = Path(pid_file)
        self.pid = os.getpid()
        self.process = psutil.Process(self.pid)
        
    def write_pid_file(self) -> None:
        """Write current PID to file and register cleanup."""
        try:
            # Check if another instance is running
            if self.pid_file.exists():
                existing_pid = int(self.pid_file.read_text().strip())
                if self._is_process_running(existing_pid):
                    raise RuntimeError(f"Another instance is already running with PID {existing_pid}")
                else:
                    logger.warning(f"Stale PID file found for non-existent process {existing_pid}, removing")
                    self.pid_file.unlink()
            
            # Write our PID
            self.pid_file.write_text(str(self.pid))
            logger.info(f"Written PID {self.pid} to {self.pid_file}")
            
            # Register cleanup
            atexit.register(self.cleanup)
            signal.signal(signal.SIGTERM, self._handle_signal)
            signal.signal(signal.SIGINT, self._handle_signal)
            
        except Exception as e:
            logger.error(f"Failed to write PID file: {e}")
            raise
            
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running."""
        try:
            process = psutil.Process(pid)
            # Check if it's our application
            cmdline = ' '.join(process.cmdline())
            return 'main.py' in cmdline or 'virtuoso' in cmdline.lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
            
    def _handle_signal(self, signum, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, cleaning up...")
        self.cleanup()
        sys.exit(0)
        
    def cleanup(self) -> None:
        """Remove PID file on exit."""
        try:
            if self.pid_file.exists() and int(self.pid_file.read_text().strip()) == self.pid:
                self.pid_file.unlink()
                logger.info(f"Removed PID file {self.pid_file}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
    def get_process_info(self) -> dict:
        """Get current process information."""
        try:
            return {
                'pid': self.pid,
                'name': self.process.name(),
                'status': self.process.status(),
                'cpu_percent': self.process.cpu_percent(interval=0.1),
                'memory_mb': self.process.memory_info().rss / 1024 / 1024,
                'memory_percent': self.process.memory_percent(),
                'num_threads': self.process.num_threads(),
                'create_time': self.process.create_time(),
                'cmdline': ' '.join(self.process.cmdline()),
            }
        except Exception as e:
            logger.error(f"Error getting process info: {e}")
            return {'pid': self.pid, 'error': str(e)}
            
    def is_healthy(self, max_memory_mb: int = 2048, max_cpu_percent: float = 90.0) -> bool:
        """
        Check if process is healthy based on resource usage.
        
        Args:
            max_memory_mb: Maximum memory usage in MB
            max_cpu_percent: Maximum CPU usage percentage
            
        Returns:
            True if healthy, False otherwise
        """
        try:
            info = self.get_process_info()
            memory_ok = info.get('memory_mb', 0) < max_memory_mb
            cpu_ok = info.get('cpu_percent', 0) < max_cpu_percent
            
            if not memory_ok:
                logger.warning(f"High memory usage: {info.get('memory_mb', 0):.1f}MB")
            if not cpu_ok:
                logger.warning(f"High CPU usage: {info.get('cpu_percent', 0):.1f}%")
                
            return memory_ok and cpu_ok
            
        except Exception as e:
            logger.error(f"Error checking process health: {e}")
            return False
            
    @staticmethod
    def find_running_instances() -> list:
        """Find all running instances of the trading system."""
        instances = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'main.py' in cmdline and 'virtuoso' in cmdline.lower():
                    instances.append({
                        'pid': proc.info['pid'],
                        'cmdline': cmdline,
                        'memory_mb': proc.memory_info().rss / 1024 / 1024,
                        'cpu_percent': proc.cpu_percent(interval=0.1)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return instances


# Singleton instance
_pid_manager: Optional[PIDManager] = None


def get_pid_manager(pid_file: str = "/tmp/virtuoso.pid") -> PIDManager:
    """Get or create the PID manager singleton."""
    global _pid_manager
    if _pid_manager is None:
        _pid_manager = PIDManager(pid_file)
    return _pid_manager
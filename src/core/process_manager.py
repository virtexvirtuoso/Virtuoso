#!/usr/bin/env python3
"""
Multi-Process Manager for Virtuoso CCXT Trading System
Optimized for 4-core Singapore VPS with fault isolation and resource optimization

This module implements a sophisticated process management system that:
- Distributes workload across 4 CPU cores
- Provides fault isolation between components
- Manages inter-process communication
- Monitors resource utilization per process
- Enables independent scaling of components
"""

import asyncio
import multiprocessing as mp
import signal
import sys
import time
import psutil
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor
from queue import Queue, Empty
import threading
from abc import ABC, abstractmethod


@dataclass
class ProcessConfig:
    """Configuration for individual process"""
    name: str
    target_function: Callable
    cpu_core: int
    memory_limit_mb: int
    priority: int  # -20 to 19, lower = higher priority
    restart_on_failure: bool = True
    max_restarts: int = 5
    restart_delay: float = 5.0
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)


class ProcessStatus:
    """Process status tracking"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RESTARTING = "restarting"


class ProcessWorker(ABC):
    """Abstract base class for process workers"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.shutdown_event = mp.Event()
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup process-specific logger"""
        logger = logging.getLogger(f"virtuoso.{self.name}")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f'%(asctime)s - {self.name} - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
        
    @abstractmethod
    async def run(self):
        """Main process logic - implement in subclasses"""
        pass
        
    def stop(self):
        """Signal process to shutdown"""
        self.shutdown_event.set()


class APIServerProcess(ProcessWorker):
    """Main API server process (Core 0)"""
    
    async def run(self):
        """Run FastAPI server on designated core"""
        import uvicorn
        from src.api.main import app
        
        self.logger.info(f"Starting API server on core {self.config.get('cpu_core', 0)}")
        
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=self.config.get('port', 8003),
            loop="asyncio",
            workers=1,  # Single worker per core
            access_log=False,  # Reduce I/O overhead
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        
        # Set CPU affinity
        psutil.Process().cpu_affinity([self.config.get('cpu_core', 0)])
        
        try:
            await server.serve()
        except Exception as e:
            self.logger.error(f"API server failed: {e}")
            raise


class MonitoringProcess(ProcessWorker):
    """Monitoring API process (Core 1)"""
    
    async def run(self):
        """Run monitoring API on designated core"""
        import uvicorn
        from src.api.monitoring import monitoring_app
        
        self.logger.info(f"Starting monitoring API on core {self.config.get('cpu_core', 1)}")
        
        config = uvicorn.Config(
            monitoring_app,
            host="0.0.0.0", 
            port=self.config.get('port', 8001),
            loop="asyncio",
            workers=1,
            access_log=False,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        
        # Set CPU affinity
        psutil.Process().cpu_affinity([self.config.get('cpu_core', 1)])
        
        try:
            await server.serve()
        except Exception as e:
            self.logger.error(f"Monitoring API failed: {e}")
            raise


class MarketDataProcess(ProcessWorker):
    """Market data collection process (Core 2)"""
    
    async def run(self):
        """Run market data collection on designated core"""
        from src.core.market.data_collector import MarketDataCollector
        from src.core.websocket_manager import WebSocketManager
        
        self.logger.info(f"Starting market data collection on core {self.config.get('cpu_core', 2)}")
        
        # Set CPU affinity
        psutil.Process().cpu_affinity([self.config.get('cpu_core', 2)])
        
        # Initialize components
        data_collector = MarketDataCollector()
        ws_manager = WebSocketManager()
        
        try:
            # Start WebSocket connections
            await ws_manager.start_all_connections()
            
            # Start data collection loop
            while not self.shutdown_event.is_set():
                await data_collector.collect_all_data()
                await asyncio.sleep(1)  # 1-second collection cycle
                
        except Exception as e:
            self.logger.error(f"Market data collection failed: {e}")
            raise
        finally:
            await ws_manager.stop_all_connections()


class AnalysisEngineProcess(ProcessWorker):
    """Analysis engine process (Core 3)"""
    
    async def run(self):
        """Run 6-dimensional analysis on designated core"""
        from src.core.analysis.six_dimensional_analyzer import SixDimensionalAnalyzer
        from src.signal_generation.signal_generator import SignalGenerator
        
        self.logger.info(f"Starting analysis engine on core {self.config.get('cpu_core', 3)}")
        
        # Set CPU affinity  
        psutil.Process().cpu_affinity([self.config.get('cpu_core', 3)])
        
        # Initialize components
        analyzer = SixDimensionalAnalyzer()
        signal_generator = SignalGenerator()
        
        try:
            # Analysis loop
            while not self.shutdown_event.is_set():
                # Run 6-dimensional analysis
                analysis_results = await analyzer.analyze_all_dimensions()
                
                # Generate trading signals
                signals = await signal_generator.generate_signals(analysis_results)
                
                # Brief pause to prevent CPU saturation
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Analysis engine failed: {e}")
            raise


class VirtuosoProcessManager:
    """
    Main process manager for 4-core Singapore VPS optimization
    
    Manages process lifecycle, resource allocation, and fault tolerance
    """
    
    def __init__(self):
        self.processes: Dict[str, mp.Process] = {}
        self.process_configs: Dict[str, ProcessConfig] = {}
        self.process_stats: Dict[str, Dict[str, Any]] = {}
        self.shutdown_event = mp.Event()
        self.manager_queue = mp.Queue()
        
        # Setup logging
        self.logger = logging.getLogger("virtuoso.process_manager")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - ProcessManager - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        # Initialize process configurations
        self._setup_process_configs()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _setup_process_configs(self):
        """Setup configurations for all processes"""
        
        self.process_configs = {
            'api_server': ProcessConfig(
                name='api_server',
                target_function=self._run_api_server,
                cpu_core=0,
                memory_limit_mb=2048,  # 2GB
                priority=-5,  # High priority
                kwargs={'port': 8003}
            ),
            
            'monitoring': ProcessConfig(
                name='monitoring',
                target_function=self._run_monitoring,
                cpu_core=1,
                memory_limit_mb=1024,  # 1GB
                priority=-3,  # Medium-high priority
                kwargs={'port': 8001}
            ),
            
            'market_data': ProcessConfig(
                name='market_data',
                target_function=self._run_market_data,
                cpu_core=2,
                memory_limit_mb=2048,  # 2GB
                priority=-10,  # Highest priority (critical for trading)
            ),
            
            'analysis': ProcessConfig(
                name='analysis',
                target_function=self._run_analysis,
                cpu_core=3,
                memory_limit_mb=2048,  # 2GB
                priority=-8,  # Very high priority
            )
        }
    
    def _run_api_server(self, **kwargs):
        """Entry point for API server process"""
        worker = APIServerProcess('api_server', kwargs)
        asyncio.run(worker.run())
        
    def _run_monitoring(self, **kwargs):
        """Entry point for monitoring process"""
        worker = MonitoringProcess('monitoring', kwargs)
        asyncio.run(worker.run())
        
    def _run_market_data(self, **kwargs):
        """Entry point for market data process"""
        worker = MarketDataProcess('market_data', kwargs)
        asyncio.run(worker.run())
        
    def _run_analysis(self, **kwargs):
        """Entry point for analysis process"""
        worker = AnalysisEngineProcess('analysis', kwargs)
        asyncio.run(worker.run())
    
    def start_all_processes(self):
        """Start all managed processes"""
        self.logger.info("Starting all Virtuoso processes on 4-core Singapore VPS")
        
        for name, config in self.process_configs.items():
            self.start_process(name)
            time.sleep(1)  # Staggered startup
            
        self.logger.info("All processes started successfully")
    
    def start_process(self, process_name: str) -> bool:
        """Start individual process"""
        if process_name in self.processes and self.processes[process_name].is_alive():
            self.logger.warning(f"Process {process_name} already running")
            return True
            
        config = self.process_configs.get(process_name)
        if not config:
            self.logger.error(f"No configuration found for process {process_name}")
            return False
            
        try:
            # Create process
            process = mp.Process(
                target=config.target_function,
                args=config.args,
                kwargs=config.kwargs,
                name=config.name
            )
            
            # Start process
            process.start()
            
            # Set process priority and CPU affinity (done in worker)
            try:
                proc = psutil.Process(process.pid)
                proc.nice(config.priority)
                self.logger.info(f"Set process {process_name} priority to {config.priority}")
            except Exception as e:
                self.logger.warning(f"Could not set priority for {process_name}: {e}")
            
            self.processes[process_name] = process
            self.process_stats[process_name] = {
                'status': ProcessStatus.STARTING,
                'start_time': time.time(),
                'restart_count': 0,
                'pid': process.pid
            }
            
            self.logger.info(f"Started process {process_name} (PID: {process.pid}) on core {config.cpu_core}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start process {process_name}: {e}")
            return False
    
    def stop_process(self, process_name: str, timeout: int = 30) -> bool:
        """Stop individual process gracefully"""
        if process_name not in self.processes:
            self.logger.warning(f"Process {process_name} not found")
            return True
            
        process = self.processes[process_name]
        if not process.is_alive():
            self.logger.info(f"Process {process_name} already stopped")
            return True
            
        self.logger.info(f"Stopping process {process_name}")
        
        try:
            # Graceful shutdown
            process.terminate()
            process.join(timeout)
            
            if process.is_alive():
                self.logger.warning(f"Force killing process {process_name}")
                process.kill()
                process.join(5)
                
            self.process_stats[process_name]['status'] = ProcessStatus.STOPPED
            del self.processes[process_name]
            
            self.logger.info(f"Process {process_name} stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping process {process_name}: {e}")
            return False
    
    def stop_all_processes(self):
        """Stop all managed processes"""
        self.logger.info("Stopping all Virtuoso processes")
        
        # Stop in reverse order for clean shutdown
        process_names = list(self.process_configs.keys())
        process_names.reverse()
        
        for name in process_names:
            self.stop_process(name)
            
        self.logger.info("All processes stopped")
    
    def monitor_processes(self):
        """Monitor process health and restart if needed"""
        while not self.shutdown_event.is_set():
            for name, process in list(self.processes.items()):
                if not process.is_alive():
                    self.logger.warning(f"Process {name} died, attempting restart")
                    
                    config = self.process_configs[name]
                    stats = self.process_stats[name]
                    
                    if (config.restart_on_failure and 
                        stats['restart_count'] < config.max_restarts):
                        
                        stats['restart_count'] += 1
                        stats['status'] = ProcessStatus.RESTARTING
                        
                        time.sleep(config.restart_delay)
                        self.start_process(name)
                    else:
                        self.logger.error(f"Process {name} failed permanently")
                        stats['status'] = ProcessStatus.FAILED
                        
            time.sleep(10)  # Check every 10 seconds
    
    def get_process_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get current process statistics"""
        stats = {}
        
        for name, process in self.processes.items():
            try:
                proc = psutil.Process(process.pid)
                stats[name] = {
                    'status': 'running' if process.is_alive() else 'stopped',
                    'pid': process.pid,
                    'cpu_percent': proc.cpu_percent(),
                    'memory_percent': proc.memory_percent(),
                    'memory_mb': proc.memory_info().rss / 1024 / 1024,
                    'threads': proc.num_threads(),
                    'cpu_affinity': proc.cpu_affinity(),
                    'restart_count': self.process_stats[name].get('restart_count', 0)
                }
            except (psutil.NoSuchProcess, KeyError):
                stats[name] = {
                    'status': 'not_found',
                    'pid': None
                }
                
        return stats
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully")
        self.shutdown_event.set()
        self.stop_all_processes()
        sys.exit(0)
    
    def run(self):
        """Main process manager loop"""
        try:
            # Start all processes
            self.start_all_processes()
            
            # Start monitoring thread
            monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
            monitor_thread.start()
            
            # Keep main thread alive
            while not self.shutdown_event.is_set():
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Process manager error: {e}")
        finally:
            self.stop_all_processes()


if __name__ == "__main__":
    # Initialize and run process manager
    manager = VirtuosoProcessManager()
    manager.run()
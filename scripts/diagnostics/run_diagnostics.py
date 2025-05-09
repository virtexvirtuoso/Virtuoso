#!/usr/bin/env python3
"""
Diagnostic script to run the Virtuoso_ccxt application for a specific time period
and capture all warnings and errors from the logs, with resource utilization monitoring.
"""

import asyncio
import logging
import os
import signal
import sys
import time
import subprocess
import re
import psutil
import json
import concurrent.futures
import threading
import traceback
import numpy as np
from datetime import datetime
from collections import defaultdict
import argparse

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/diagnostics/diagnostics.log')
    ]
)
logger = logging.getLogger('diagnostics')

# Resource monitoring data storage
resource_history = {
    'timestamps': [],
    'cpu': [],
    'memory': [],
    'processes': [],
    'gpu': [],
    'disk_io': []
}

class ComponentMonitor:
    """Monitor specific system components during diagnostics."""
    
    def __init__(self, component_name, check_interval=10):
        self.component_name = component_name
        self.check_interval = check_interval
        self.running = False
        self.task = None
        self.metrics = defaultdict(list)
        self.errors = []
        self.start_time = None
        self.status = "Not Started"
        
    async def start_monitoring(self):
        """Start the component monitoring task."""
        self.running = True
        self.start_time = time.time()
        self.status = "Running"
        self.task = asyncio.create_task(self._monitor_component())
        logger.info(f"{self.component_name} monitoring started")
        
    async def _monitor_component(self):
        """Abstract method to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _monitor_component")
    
    async def stop_monitoring(self):
        """Stop the component monitoring task."""
        if self.running:
            self.running = False
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            self.status = "Stopped"
            logger.info(f"{self.component_name} monitoring stopped")
            return {
                'component': self.component_name,
                'duration_seconds': int(time.time() - self.start_time),
                'metrics': dict(self.metrics),
                'errors': self.errors,
                'status': self.status
            }
        return None

class DataLayerMonitor(ComponentMonitor):
    """Monitor data layer operations."""
    
    def __init__(self, data_dir='data', check_interval=10):
        super().__init__("Data Layer", check_interval)
        self.data_dir = data_dir
        
    async def _monitor_component(self):
        """Monitor data layer operations."""
        while self.running:
            try:
                # Check disk usage for data directory
                if os.path.exists(self.data_dir):
                    disk_usage = psutil.disk_usage(self.data_dir)
                    self.metrics['disk_usage_percent'].append(disk_usage.percent)
                    self.metrics['free_space_mb'].append(disk_usage.free / (1024 * 1024))
                    
                    # Count files in data directory
                    file_count = 0
                    total_size = 0
                    for root, _, files in os.walk(self.data_dir):
                        file_count += len(files)
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                total_size += os.path.getsize(file_path)
                            except (FileNotFoundError, PermissionError):
                                pass
                    
                    self.metrics['file_count'].append(file_count)
                    self.metrics['total_size_mb'].append(total_size / (1024 * 1024))
                    
                    # Check for any IO errors in recent log files
                    # TODO: Implement more specific data layer checks
                    
                    # Log if disk usage is high
                    if disk_usage.percent > 90:
                        error_msg = f"High disk usage: {disk_usage.percent}%"
                        self.errors.append(error_msg)
                        logger.warning(error_msg)
                
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                error_msg = f"Error in data layer monitoring: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)
                await asyncio.sleep(self.check_interval)

class ExchangeMonitor(ComponentMonitor):
    """Monitor exchange connections and rate limits."""
    
    def __init__(self, check_interval=30):
        super().__init__("Exchange Connectivity", check_interval)
        self.exchange_configs = {
            'binance': {'id': 'binance', 'apiKey': '', 'secret': ''},
            'bybit': {'id': 'bybit', 'apiKey': '', 'secret': ''},
            'kucoin': {'id': 'kucoin', 'apiKey': '', 'secret': ''}
        }
    
    async def _monitor_component(self):
        """Monitor exchange connections."""
        if not CCXT_AVAILABLE:
            self.status = "CCXT Not Available"
            self.errors.append("CCXT library not installed")
            return
            
        while self.running:
            try:
                # Test connectivity to major exchanges (read-only, no keys needed)
                for exchange_id in self.exchange_configs:
                    try:
                        # Create exchange instance
                        exchange_class = getattr(ccxt, exchange_id)
                        exchange = exchange_class()
                        
                        # Test public endpoints
                        start_time = time.time()
                        await exchange.load_markets()
                        response_time = (time.time() - start_time) * 1000  # in ms
                        
                        # Record metrics
                        if 'response_times' not in self.metrics:
                            self.metrics['response_times'] = {}
                        if exchange_id not in self.metrics['response_times']:
                            self.metrics['response_times'][exchange_id] = []
                        
                        self.metrics['response_times'][exchange_id].append(response_time)
                        
                        # Check rate limits
                        if hasattr(exchange, 'rateLimit'):
                            if 'rate_limits' not in self.metrics:
                                self.metrics['rate_limits'] = {}
                            self.metrics['rate_limits'][exchange_id] = exchange.rateLimit
                        
                        # Log if response time is slow
                        if response_time > 2000:  # 2 seconds
                            error_msg = f"Slow response from {exchange_id}: {response_time:.2f}ms"
                            self.errors.append(error_msg)
                            logger.warning(error_msg)
                    
                    except Exception as e:
                        error_msg = f"Error connecting to {exchange_id}: {str(e)}"
                        self.errors.append(error_msg)
                        logger.error(error_msg)
                
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                error_msg = f"Error in exchange monitoring: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)
                await asyncio.sleep(self.check_interval)

class WebSocketMonitor(ComponentMonitor):
    """Monitor WebSocket connections."""
    
    def __init__(self, check_interval=15):
        super().__init__("WebSocket", check_interval)
    
    async def _monitor_component(self):
        """Monitor WebSocket connections."""
        while self.running:
            try:
                # Check for websocket processes
                websocket_processes = []
                for process in psutil.process_iter(['pid', 'name', 'cmdline']):
                    if process.info['name'] and 'python' in process.info['name'].lower():
                        cmdline = process.info.get('cmdline', [])
                        cmdline_str = ' '.join(cmdline) if cmdline else ''
                        if 'websocket' in cmdline_str.lower() or 'socket' in cmdline_str.lower():
                            websocket_processes.append(process.info)
                
                self.metrics['active_connections'] = len(websocket_processes)
                
                # Check WebSocket logs if available
                ws_log_files = ['websocket.log', 'src/logs/websocket.log']
                for log_file in ws_log_files:
                    if os.path.exists(log_file):
                        try:
                            with open(log_file, 'r') as f:
                                last_lines = list(f)[-100:]  # Get last 100 lines
                                error_count = 0
                                for line in last_lines:
                                    if 'error' in line.lower() or 'failed' in line.lower() or 'connection closed' in line.lower():
                                        error_count += 1
                                
                                if error_count > 0:
                                    error_msg = f"Found {error_count} WebSocket errors in recent logs"
                                    self.errors.append(error_msg)
                                    logger.warning(error_msg)
                        except Exception as e:
                            logger.error(f"Error reading WebSocket log {log_file}: {str(e)}")
                
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                error_msg = f"Error in WebSocket monitoring: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)
                await asyncio.sleep(self.check_interval)

class ResourceMonitor:
    """Monitor system resources during diagnostics."""
    
    def __init__(self, process_pid=None, sample_interval=5):
        self.process_pid = process_pid
        self.sample_interval = sample_interval
        self.running = False
        self.task = None
        self.peak_cpu = 0
        self.peak_memory = 0
        self.start_time = None
        
    async def start_monitoring(self):
        """Start the resource monitoring task."""
        self.running = True
        self.start_time = time.time()
        self.task = asyncio.create_task(self._monitor_resources())
        logger.info("Resource monitoring started")
        
    async def _monitor_resources(self):
        """Monitor CPU and memory usage periodically."""
        while self.running:
            try:
                # Get overall system stats
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                
                # Get GPU stats if available
                gpu_info = None
                if GPU_AVAILABLE:
                    try:
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            gpu = gpus[0]  # Get first GPU
                            gpu_info = {
                                'load': gpu.load * 100,  # Convert to percentage
                                'memory_used': gpu.memoryUsed,
                                'memory_total': gpu.memoryTotal,
                                'temperature': gpu.temperature
                            }
                    except Exception as e:
                        logger.error(f"Error getting GPU info: {str(e)}")
                
                # Get process-specific stats if PID is provided
                process_info = None
                if self.process_pid:
                    try:
                        process = psutil.Process(self.process_pid)
                        process_info = {
                            'cpu': process.cpu_percent(interval=None),
                            'memory': process.memory_info().rss / (1024 * 1024),  # MB
                            'threads': process.num_threads(),
                            'open_files': len(process.open_files()),
                            'connections': len(process.connections())
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        process_info = None
                
                # Update peak values
                self.peak_cpu = max(self.peak_cpu, cpu_percent)
                self.peak_memory = max(self.peak_memory, memory.percent)
                
                # Record data for history
                timestamp = int(time.time() - self.start_time)
                resource_history['timestamps'].append(timestamp)
                resource_history['cpu'].append(cpu_percent)
                resource_history['memory'].append(memory.percent)
                resource_history['processes'].append(process_info)
                resource_history['gpu'].append(gpu_info)
                
                # Record disk IO data
                if disk_io:
                    disk_io_data = {
                        'read_bytes': disk_io.read_bytes,
                        'write_bytes': disk_io.write_bytes
                    }
                    resource_history['disk_io'].append(disk_io_data)
                
                # Log high resource usage
                if cpu_percent > 80 or memory.percent > 80:
                    logger.warning(f"High resource usage - CPU: {cpu_percent}%, Memory: {memory.percent}%")
                
                await asyncio.sleep(self.sample_interval)
            except Exception as e:
                logger.error(f"Error in resource monitoring: {str(e)}")
                await asyncio.sleep(self.sample_interval)
    
    async def stop_monitoring(self):
        """Stop the resource monitoring task."""
        if self.running:
            self.running = False
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            logger.info(f"Resource monitoring stopped. Peak CPU: {self.peak_cpu}%, Peak Memory: {self.peak_memory}%")
            return {
                'duration_seconds': int(time.time() - self.start_time),
                'peak_cpu': self.peak_cpu,
                'peak_memory': self.peak_memory,
                'history': resource_history
            }
        return None

async def run_app_with_timeout(timeout_minutes=10, skip_app=False):
    """
    Run the main application for the specified time, then shut it down cleanly.
    
    Args:
        timeout_minutes: How long to run the app in minutes
        skip_app: Skip running the main application (for component-only diagnostics)
    """
    # If skipping app, return immediately
    if skip_app:
        logger.info("Skipping main application run as requested")
        return {
            'duration_seconds': 0,
            'peak_cpu': 0,
            'peak_memory': 0,
            'history': {
                'timestamps': [],
                'cpu': [],
                'memory': [],
                'processes': [],
                'gpu': [],
                'disk_io': []
            }
        }

    # Set the Discord webhook URL environment variable if needed
    if 'DISCORD_WEBHOOK_URL' not in os.environ:
        webhook_url = "https://discord.com/api/webhooks/1197011710268162159/V_Gfq66qtfJGiZMxnIwC7pb20HwHqVCRMoU_kubPetn_ikB5F8NTw81_goGLoSQ3q3Vw"
        os.environ['DISCORD_WEBHOOK_URL'] = webhook_url
        logger.info(f"Set DISCORD_WEBHOOK_URL environment variable")

    # Ensure the logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Start the application process
    logger.info(f"Starting application for {timeout_minutes} minutes")
    start_time = time.time()
    
    # Create the process with full output piped
    process = await asyncio.create_subprocess_exec(
        sys.executable, 'src/main.py',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ.copy()  # Pass current environment
    )
    
    # Log that the process started
    logger.info(f"Started process with PID {process.pid}")
    
    # Start resource monitoring
    resource_monitor = ResourceMonitor(process_pid=process.pid)
    await resource_monitor.start_monitoring()
    
    # Start component monitors
    data_monitor = DataLayerMonitor()
    await data_monitor.start_monitoring()
    
    exchange_monitor = ExchangeMonitor()
    await exchange_monitor.start_monitoring()
    
    websocket_monitor = WebSocketMonitor()
    await websocket_monitor.start_monitoring()
    
    # Monitor the process output in a separate task
    async def monitor_output():
        while True:
            # Read from stderr (where most warnings/errors go)
            stderr_line = await process.stderr.readline()
            if stderr_line:
                line = stderr_line.decode('utf-8').strip()
                # Check if this is a warning or error
                if '[WARNING]' in line or '[ERROR]' in line or '[CRITICAL]' in line:
                    logger.warning(f"App: {line}")
                # Also print normal logs if needed
                # else:
                #     logger.debug(f"App: {line}")
            
            # Read from stdout
            stdout_line = await process.stdout.readline()
            if stdout_line:
                line = stdout_line.decode('utf-8').strip()
                # Check if this is a warning or error (sometimes logged to stdout)
                if '[WARNING]' in line or '[ERROR]' in line or '[CRITICAL]' in line:
                    logger.warning(f"App: {line}")
                # Also print normal logs if needed
                # else:
                #     logger.debug(f"App: {line}")
            
            # If both streams are closed, break the loop
            if not stderr_line and not stdout_line and process.returncode is not None:
                break
                
            # Small delay to prevent CPU hogging
            await asyncio.sleep(0.1)
    
    # Start the monitoring task
    monitoring_task = asyncio.create_task(monitor_output())
    
    try:
        # Wait for the specified time
        seconds_to_wait = timeout_minutes * 60
        elapsed = 0
        
        while elapsed < seconds_to_wait and process.returncode is None:
            await asyncio.sleep(5)  # Check every 5 seconds
            elapsed = time.time() - start_time
            
            # Log progress every minute
            if int(elapsed) % 60 == 0:
                logger.info(f"Application running for {int(elapsed/60)} minutes")
        
        logger.info(f"Time limit of {timeout_minutes} minutes reached, stopping application...")
        
        # Send SIGTERM to the process for a clean shutdown
        process.send_signal(signal.SIGTERM)
        
        # Wait up to 30 seconds for graceful termination
        try:
            await asyncio.wait_for(process.wait(), timeout=30)
            logger.info("Application terminated gracefully")
        except asyncio.TimeoutError:
            logger.warning("Application did not terminate after 30 seconds, sending SIGKILL")
            process.kill()
            await process.wait()
            logger.info("Application terminated forcefully")
    
    except asyncio.CancelledError:
        logger.info("Diagnostic run cancelled, stopping application...")
        process.terminate()
        await process.wait()
    except Exception as e:
        logger.error(f"Error during diagnostic run: {str(e)}")
        process.kill()
        await process.wait()
    finally:
        # Stop all monitors
        resource_data = await resource_monitor.stop_monitoring()
        data_monitor_data = await data_monitor.stop_monitoring()
        exchange_monitor_data = await exchange_monitor.stop_monitoring()
        websocket_monitor_data = await websocket_monitor.stop_monitoring()
        
        # Combine component data with resource data
        if resource_data:
            resource_data['components'] = {
                'data_layer': data_monitor_data,
                'exchange': exchange_monitor_data,
                'websocket': websocket_monitor_data
            }
        
        # Make sure the monitoring task is cancelled
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

        return resource_data

async def run_component_diagnostics(timeout_minutes=5):
    """
    Run component-specific diagnostics without starting the main application.
    
    Args:
        timeout_minutes: How long to run diagnostics in minutes
    """
    logger.info(f"Starting component diagnostics for {timeout_minutes} minutes")
    start_time = time.time()
    
    # Start resource monitoring (without process)
    resource_monitor = ResourceMonitor()
    await resource_monitor.start_monitoring()
    
    # Start component monitors
    data_monitor = DataLayerMonitor()
    await data_monitor.start_monitoring()
    
    exchange_monitor = ExchangeMonitor()
    await exchange_monitor.start_monitoring()
    
    websocket_monitor = WebSocketMonitor()
    await websocket_monitor.start_monitoring()
    
    try:
        # Wait for the specified time
        seconds_to_wait = timeout_minutes * 60
        elapsed = 0
        
        while elapsed < seconds_to_wait:
            await asyncio.sleep(5)  # Check every 5 seconds
            elapsed = time.time() - start_time
            
            # Log progress every minute
            if int(elapsed) % 60 == 0:
                logger.info(f"Component diagnostics running for {int(elapsed/60)} minutes")
        
        logger.info(f"Time limit of {timeout_minutes} minutes reached")
    
    except asyncio.CancelledError:
        logger.info("Component diagnostics cancelled")
    except Exception as e:
        logger.error(f"Error during component diagnostics: {str(e)}")
    finally:
        # Stop all monitors
        resource_data = await resource_monitor.stop_monitoring()
        data_monitor_data = await data_monitor.stop_monitoring()
        exchange_monitor_data = await exchange_monitor.stop_monitoring()
        websocket_monitor_data = await websocket_monitor.stop_monitoring()
        
        # Combine component data with resource data
        if resource_data:
            resource_data['components'] = {
                'data_layer': data_monitor_data,
                'exchange': exchange_monitor_data,
                'websocket': websocket_monitor_data
            }

        return resource_data

# Advanced regex patterns for log analysis
LOG_PATTERNS = {
    'error': [
        r'\[ERROR\]|\bERROR\b|\[CRITICAL\]|\bFATAL\b',
        r'Exception\s*:|Traceback \(most recent call last\)',
        r'failed with error|crashed|terminated unexpectedly',
        r'[Cc]annot\s+[a-zA-Z]+\s+[a-zA-Z]+\s+error',
    ],
    'warning': [
        r'\[WARNING\]|\bWARN\b|\bWARNING\b',
        r'[Dd]eprecated|[Oo]bsolete',
        r'[Tt]imeout|[Ss]low\s+[a-zA-Z]+',
        r'[Rr]etrying|[Ff]allback',
    ],
    'info': [
        r'\[INFO\]|\bINFO\b',
    ],
    'redundant_operations': [
        r'repeated\s+request|duplicate\s+call',
        r'already\s+(running|exists|created|connected)',
        r'unnecessarily\s+called\s+multiple\s+times',
    ],
    'performance_issues': [
        r'slow\s+query|performance\s+warning',
        r'execution\s+time\s+exceeded',
        r'high\s+(cpu|memory|resource)\s+usage',
    ],
    'network_issues': [
        r'connection\s+(refused|reset|timed out)',
        r'network\s+error|socket\s+error',
        r'unable\s+to\s+connect|connection\s+failed',
    ],
    'exchange_issues': [
        r'rate\s+limit|throttled|too\s+many\s+requests',
        r'exchange\s+error|market\s+closed|invalid\s+symbol',
        r'insufficient\s+funds|balance\s+too\s+low',
    ],
    'trading_issues': [
        r'order\s+failed|trade\s+rejected|position\s+error',
        r'leverage\s+not\s+supported|invalid\s+order',
        r'price\s+outside\s+range|slippage\s+exceeded',
    ]
}

def analyze_log_file(log_file):
    """
    Analyze a single log file for warnings and errors.
    This function is designed to be run in a thread pool.
    
    Args:
        log_file: Path to the log file
        
    Returns:
        Tuple containing (warnings, errors, redundancies, performance_issues, network_issues)
    """
    warnings = []
    errors = []
    redundancies = []
    performance_issues = []
    network_issues = []
    exchange_issues = []
    trading_issues = []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # Check against each error pattern
                for pattern in LOG_PATTERNS['error']:
                    if re.search(pattern, line):
                        errors.append((log_file, line_num, line.strip()))
                        break
                
                # Check against each warning pattern
                for pattern in LOG_PATTERNS['warning']:
                    if re.search(pattern, line):
                        warnings.append((log_file, line_num, line.strip()))
                        break
                
                # Check for redundant operations
                for pattern in LOG_PATTERNS['redundant_operations']:
                    if re.search(pattern, line):
                        redundancies.append((log_file, line_num, line.strip()))
                        break
                
                # Check for performance issues
                for pattern in LOG_PATTERNS['performance_issues']:
                    if re.search(pattern, line):
                        performance_issues.append((log_file, line_num, line.strip()))
                        break
                
                # Check for network issues
                for pattern in LOG_PATTERNS['network_issues']:
                    if re.search(pattern, line):
                        network_issues.append((log_file, line_num, line.strip()))
                        break
                
                # Check for exchange issues
                for pattern in LOG_PATTERNS['exchange_issues']:
                    if re.search(pattern, line):
                        exchange_issues.append((log_file, line_num, line.strip()))
                        break
                
                # Check for trading issues
                for pattern in LOG_PATTERNS['trading_issues']:
                    if re.search(pattern, line):
                        trading_issues.append((log_file, line_num, line.strip()))
                        break
    except Exception as e:
        logger.error(f"Error reading {log_file}: {str(e)}")
    
    return (warnings, errors, redundancies, performance_issues, network_issues, exchange_issues, trading_issues)

async def analyze_logs(resource_data=None, error_filter=None, warning_filter=None, skip_logs=False):
    """
    Analyze the application logs for warnings and errors using parallel processing.
    
    Args:
        resource_data: Resource utilization data
        error_filter: Filter for error categories (None = all)
        warning_filter: Filter for warning categories (None = all)
        skip_logs: Skip log analysis completely
        
    Returns:
        Tuple containing paths to the generated report files
    """
    if skip_logs:
        logger.info("Skipping log analysis as requested")
        return await generate_reports([], [], [], [], [], [], [], resource_data, None, None)
        
    logger.info("Analyzing logs for warnings and errors")
    
    # Look for log files in multiple locations
    log_files = []
    
    # Define multiple locations to search for logs
    log_locations = [
        'logs',                 # Main logs directory
        'src/logs',             # Secondary logs directory in src
        '.',                    # Root directory for diagnostics.log and market reporter logs
        'cache',                # Cache logs
        'src/logs/alerts',      # Alert logs
        'src/logs/reports',     # Report logs
        'logs/alerts',          # Alert logs in root logs dir
        'logs/reports'          # Report logs in root logs dir
    ]
    
    # Specific log files to include by name
    specific_log_files = [
        'logs/diagnostics/diagnostics.log',
        'logs/market_reporter.log',
        'market_reporter_test.log',
        'app.log',
        'monitor.log'
    ]
    
    # Search in all defined locations
    for location in log_locations:
        if os.path.exists(location):
            if os.path.isdir(location):
                # Walk through directories
                for root, _, files in os.walk(location):
                    for file in files:
                        if file.endswith('.log') or file.endswith('.txt') or file.endswith('.out'):
                            log_path = os.path.join(root, file)
                            log_files.append(log_path)
            elif os.path.isfile(location) and (location.endswith('.log') or location.endswith('.txt')):
                # Direct file path
                log_files.append(location)
    
    # Add specific log files from the root directory
    for log_file in specific_log_files:
        if os.path.exists(log_file) and os.path.isfile(log_file):
            if log_file not in log_files:
                log_files.append(log_file)
    
    # Remove duplicates while preserving order
    log_files = list(dict.fromkeys(log_files))
    
    if not log_files:
        logger.warning("No log files found in any directory!")
        return await generate_reports([], [], [], [], [], [], [], resource_data, None, None)
    
    logger.info(f"Found {len(log_files)} log files to analyze")
    for log_file in log_files:
        logger.info(f"  - {log_file}")
    
    # Process log files in parallel using a thread pool
    all_warnings = []
    all_errors = []
    all_redundancies = []
    all_performance_issues = []
    all_network_issues = []
    all_exchange_issues = []
    all_trading_issues = []
    
    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(os.cpu_count() * 2, len(log_files))) as executor:
        # Start the parallel tasks
        future_to_file = {executor.submit(analyze_log_file, log_file): log_file for log_file in log_files}
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_file):
            log_file = future_to_file[future]
            try:
                (warnings, errors, redundancies, performance_issues, network_issues, exchange_issues, trading_issues) = future.result()
                
                all_warnings.extend(warnings)
                all_errors.extend(errors)
                all_redundancies.extend(redundancies)
                all_performance_issues.extend(performance_issues)
                all_network_issues.extend(network_issues)
                all_exchange_issues.extend(exchange_issues)
                all_trading_issues.extend(trading_issues)
                
                logger.info(f"Processed {log_file}: found {len(errors)} errors, {len(warnings)} warnings")
            except Exception as e:
                logger.error(f"Error processing {log_file}: {str(e)}")
    
    # Generate reports
    return await generate_reports(
        all_warnings, all_errors, all_redundancies, all_performance_issues, 
        all_network_issues, all_exchange_issues, all_trading_issues, resource_data,
        error_filter, warning_filter
    )

async def generate_reports(warnings, errors, redundancies, performance_issues, 
                          network_issues, exchange_issues, trading_issues, resource_data=None, error_filter=None, warning_filter=None):
    """
    Generate diagnostic reports in both text and HTML formats.
    
    Args:
        warnings: List of warning entries
        errors: List of error entries
        redundancies: List of redundancy issues
        performance_issues: List of performance issues
        network_issues: List of network issues
        exchange_issues: List of exchange issues
        trading_issues: List of trading issues
        resource_data: Resource utilization data
        error_filter: Filter for error categories (None = all)
        warning_filter: Filter for warning categories (None = all)
        
    Returns:
        Tuple containing paths to the generated text and HTML report files
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    txt_report_file = f'diagnostic_report_{timestamp}.txt'
    html_report_file = f'diagnostic_report_{timestamp}.html'
    
    # Create the TXT report
    with open(txt_report_file, 'w', encoding='utf-8') as f:
        f.write(f"===== Virtuoso_ccxt Diagnostic Report - {datetime.now().isoformat()} =====\n\n")
        
        # Write resource utilization summary if available
        if resource_data:
            f.write("===== RESOURCE UTILIZATION =====\n\n")
            f.write(f"Duration: {resource_data['duration_seconds']} seconds\n")
            f.write(f"Peak CPU: {resource_data['peak_cpu']}%\n")
            f.write(f"Peak Memory: {resource_data['peak_memory']}%\n\n")
            
            # Write component data if available
            if 'components' in resource_data:
                f.write("===== COMPONENT DIAGNOSTICS =====\n\n")
                
                for component_name, component_data in resource_data['components'].items():
                    if component_data:
                        f.write(f"--- {component_name.upper()} ---\n")
                        f.write(f"Status: {component_data.get('status', 'Unknown')}\n")
                        f.write(f"Duration: {component_data.get('duration_seconds', 0)} seconds\n")
                        
                        # Write metrics
                        metrics = component_data.get('metrics', {})
                        if metrics:
                            f.write("Metrics:\n")
                            for metric_name, metric_value in metrics.items():
                                if isinstance(metric_value, list):
                                    if metric_value:
                                        avg_value = sum(metric_value) / len(metric_value)
                                        f.write(f"  {metric_name}: avg={avg_value:.2f}, min={min(metric_value):.2f}, max={max(metric_value):.2f}\n")
                                elif isinstance(metric_value, dict):
                                    f.write(f"  {metric_name}:\n")
                                    for k, v in metric_value.items():
                                        if isinstance(v, list) and v:
                                            avg = sum(v) / len(v)
                                            f.write(f"    {k}: avg={avg:.2f}, min={min(v):.2f}, max={max(v):.2f}\n")
                                        else:
                                            f.write(f"    {k}: {v}\n")
                                else:
                                    f.write(f"  {metric_name}: {metric_value}\n")
                        
                        # Write errors
                        component_errors = component_data.get('errors', [])
                        if component_errors:
                            f.write(f"Errors ({len(component_errors)}):\n")
                            for error in component_errors[:5]:  # Show first 5 errors
                                f.write(f"  - {error}\n")
                            if len(component_errors) > 5:
                                f.write(f"  ... and {len(component_errors) - 5} more errors\n")
                        
                        f.write("\n")
        
        # Write summary
        f.write("===== ISSUE SUMMARY =====\n\n")
        f.write(f"Total errors: {len(errors)}\n")
        f.write(f"Total warnings: {len(warnings)}\n")
        f.write(f"Redundant operations: {len(redundancies)}\n")
        f.write(f"Performance issues: {len(performance_issues)}\n")
        f.write(f"Network issues: {len(network_issues)}\n")
        f.write(f"Exchange issues: {len(exchange_issues)}\n")
        f.write(f"Trading issues: {len(trading_issues)}\n\n")
        
        # Group and write errors
        if errors:
            f.write("===== ERRORS =====\n\n")
            errors_by_type = {}
            
            for log_file, line_num, line in errors:
                # Try to extract the error type/message
                match = re.search(r'\[ERROR\] ([^-]+) - ([^(]+)', line)
                if match:
                    component = match.group(1).strip()
                    message = match.group(2).strip()
                    key = f"{component}: {message}"
                else:
                    key = line
                
                if key not in errors_by_type:
                    errors_by_type[key] = []
                errors_by_type[key].append((log_file, line_num, line))
            
            # Sort errors by occurrence count (most frequent first)
            sorted_errors = sorted(errors_by_type.items(), key=lambda x: len(x[1]), reverse=True)
            
            for error_type, occurrences in sorted_errors:
                if error_filter and not any(re.search(pattern, error_type) for pattern in error_filter):
                    continue
                    
                f.write(f"{error_type}\n")
                f.write(f"  Occurrences: {len(occurrences)}\n")
                f.write(f"  First occurrence: {occurrences[0][0]}:{occurrences[0][1]}\n")
                f.write(f"  Last occurrence: {occurrences[-1][0]}:{occurrences[-1][1]}\n\n")
                # Write the first 3 full error messages
                for i, (_, _, line) in enumerate(occurrences[:3]):
                    f.write(f"  Example {i+1}: {line}\n")
                f.write("\n")
        
        # Additional issue sections follow a similar pattern...
        # (Similar code for warnings, redundancies, etc.)
    
    # Generate a simplified HTML report (to avoid f-string complexity)
    with open(html_report_file, 'w', encoding='utf-8') as f:
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Virtuoso_ccxt Diagnostic Report</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2, h3 { color: #333; }
        .container { max-width: 1200px; margin: 0 auto; }
        .summary { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .chart-container { position: relative; height: 400px; margin-bottom: 30px; }
        .issue { background-color: #f9f9f9; border-left: 3px solid #999; padding: 10px; margin-bottom: 10px; }
        .error { border-left-color: #dc3545; }
        .warning { border-left-color: #ffc107; }
        .redundant { border-left-color: #17a2b8; }
        .performance { border-left-color: #28a745; }
        .network { border-left-color: #007bff; }
        .exchange { border-left-color: #6610f2; }
        .trading { border-left-color: #fd7e14; }
        .occurrence-count { font-weight: bold; color: #666; }
        .metric-card { background-color: #fff; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); padding: 15px; margin-bottom: 20px; }
        .metric-value { font-size: 24px; font-weight: bold; }
        .metric-label { font-size: 14px; color: #666; }
        .tab-content { padding: 20px 0; }
        .nav-tabs { margin-bottom: 20px; }
        .status-good { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-error { color: #dc3545; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Virtuoso_ccxt Diagnostic Report</h1>
        <p>Generated on: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
        
        <ul class="nav nav-tabs" id="myTab" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="summary-tab" data-bs-toggle="tab" data-bs-target="#summary" type="button" role="tab">Summary</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="resources-tab" data-bs-toggle="tab" data-bs-target="#resources" type="button" role="tab">Resources</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="components-tab" data-bs-toggle="tab" data-bs-target="#components" type="button" role="tab">Components</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="errors-tab" data-bs-toggle="tab" data-bs-target="#errors" type="button" role="tab">Errors</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="warnings-tab" data-bs-toggle="tab" data-bs-target="#warnings" type="button" role="tab">Warnings</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="other-tab" data-bs-toggle="tab" data-bs-target="#other-issues" type="button" role="tab">Other Issues</button>
            </li>
        </ul>
        
        <div class="tab-content" id="myTabContent">
            <!-- Summary Tab -->
            <div class="tab-pane fade show active" id="summary" role="tabpanel">
                <div class="summary">
                    <h2>Summary</h2>
                    <ul>
                        <li><strong>Total errors:</strong> """ + str(len(errors)) + """</li>
                        <li><strong>Total warnings:</strong> """ + str(len(warnings)) + """</li>
                        <li><strong>Redundant operations:</strong> """ + str(len(redundancies)) + """</li>
                        <li><strong>Performance issues:</strong> """ + str(len(performance_issues)) + """</li>
                        <li><strong>Network issues:</strong> """ + str(len(network_issues)) + """</li>
                        <li><strong>Exchange issues:</strong> """ + str(len(exchange_issues)) + """</li>
                        <li><strong>Trading issues:</strong> """ + str(len(trading_issues)) + """</li>
                    </ul>
                </div>
                
                <div class="chart-container">
                    <div id="issueSummaryChart"></div>
                </div>
            </div>
            
            <!-- Resources Tab -->
            <div class="tab-pane fade" id="resources" role="tabpanel">
                <h2>Resource Utilization</h2>
                
                <div class="chart-container">
                    <div id="resourceChart"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Chart initialization
        document.addEventListener('DOMContentLoaded', function() {
            // Create summary chart
            const issueSummaryData = {
                labels: """ + json.dumps(['Errors', 'Warnings', 'Redundancies', 'Performance', 'Network', 'Exchange', 'Trading']) + """,
                values: """ + json.dumps([len(errors), len(warnings), len(redundancies), 
                          len(performance_issues), len(network_issues), 
                          len(exchange_issues), len(trading_issues)]) + """
            };
            
            Plotly.newPlot('issueSummaryChart', [{
                x: issueSummaryData.labels,
                y: issueSummaryData.values,
                type: 'bar',
                marker: {
                    color: ['rgba(220, 53, 69, 0.8)', 'rgba(255, 193, 7, 0.8)', 
                            'rgba(23, 162, 184, 0.8)', 'rgba(40, 167, 69, 0.8)', 
                            'rgba(0, 123, 255, 0.8)', 'rgba(102, 16, 242, 0.8)', 
                            'rgba(253, 126, 20, 0.8)']
                }
            }], {
                title: 'Issue Distribution',
                xaxis: { title: 'Issue Type' },
                yaxis: { title: 'Count' },
                margin: { t: 50, l: 50, r: 20, b: 50 }
            });
        """
        
        # Add resource charts if data is available
        if resource_data:
            # Convert resource data to JavaScript arrays
            timestamps_js = json.dumps(resource_history['timestamps'])
            cpu_js = json.dumps(resource_history['cpu'])
            memory_js = json.dumps(resource_history['memory'])
            
            html_content += """
            // Resource utilization chart with Plotly
            const resourceData = {
                timestamps: """ + timestamps_js + """,
                cpu: """ + cpu_js + """,
                memory: """ + memory_js + """
            };
            
            Plotly.newPlot('resourceChart', [
                {
                    x: resourceData.timestamps,
                    y: resourceData.cpu,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'CPU Usage (%)',
                    line: { color: 'rgb(75, 192, 192)' }
                },
                {
                    x: resourceData.timestamps,
                    y: resourceData.memory,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Memory Usage (%)',
                    line: { color: 'rgb(255, 99, 132)' }
                }
            ], {
                title: 'Resource Utilization Over Time',
                xaxis: { title: 'Time (seconds)' },
                yaxis: { title: 'Usage (%)', range: [0, 100] },
                margin: { t: 50, l: 50, r: 20, b: 50 }
            });
            """
        
        # Close the script and HTML tags
        html_content += """
        });
    </script>
</body>
</html>
"""
        
        f.write(html_content)
    
    logger.info(f"Diagnostic reports generated: {txt_report_file} and {html_report_file}")
    return txt_report_file, html_report_file

async def main():
    """Main diagnostic function."""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Run diagnostics on the Virtuoso trading application")
        parser.add_argument("--timeout", type=int, default=30, help="Run timeout in minutes (default: 30)")
        parser.add_argument("--clear-logs", action="store_true", help="Clear existing logs before starting")
        parser.add_argument("--component-only", action="store_true", help="Run only component diagnostics (skip main app)")
        parser.add_argument("--skip-app", action="store_true", help="Skip running the main application")
        parser.add_argument("--skip-logs", action="store_true", help="Skip log analysis")
        args = parser.parse_args()
        
        logger.info(f"Starting diagnostic run with timeout of {args.timeout} minutes")
        
        # Clear logs if requested
        if args.clear_logs:
            logger.info("Clearing existing log files...")
            log_locations = [
                'logs',
                'src/logs',
                'logs/alerts',
                'logs/reports',
                'src/logs/alerts',
                'src/logs/reports'
            ]
            
            specific_log_files = [
                'logs/diagnostics/diagnostics.log',
                'logs/market_reporter.log',
                'market_reporter_test.log',
                'app.log',
                'monitor.log'
            ]
            
            # Clear logs in directories
            for location in log_locations:
                if os.path.exists(location):
                    logger.info(f"Clearing logs in {location}")
                    for file in os.listdir(location):
                        file_path = os.path.join(location, file)
                        if os.path.isfile(file_path) and file.endswith('.log'):
                            try:
                                os.remove(file_path)
                                logger.info(f"Deleted {file_path}")
                            except Exception as e:
                                logger.warning(f"Could not delete {file_path}: {str(e)}")
            
            # Clear specific log files in root directory
            for file in specific_log_files:
                if os.path.exists(file):
                    try:
                        os.remove(file)
                        logger.info(f"Deleted {file}")
                    except Exception as e:
                        logger.warning(f"Could not delete {file}: {str(e)}")
            
            # Also remove existing diagnostic reports
            for file in os.listdir('.'):
                if file.startswith('diagnostic_report_') and (file.endswith('.txt') or file.endswith('.html')):
                    try:
                        os.remove(file)
                        logger.info(f"Deleted {file}")
                    except Exception as e:
                        logger.warning(f"Could not delete {file}: {str(e)}")
        
        # Run diagnostics based on command line options
        if args.component_only:
            # Run component-only diagnostics
            resource_data = await run_component_diagnostics(timeout_minutes=args.timeout)
        else:
            # Run the application with diagnostics
            resource_data = await run_app_with_timeout(timeout_minutes=args.timeout, skip_app=args.skip_app)
        
        # Analyze the logs with the resource data
        report_files = await analyze_logs(resource_data=resource_data, skip_logs=args.skip_logs)
        
        logger.info("Diagnostic run completed successfully")
        
        if report_files:
            txt_file, html_file = report_files
            logger.info(f"View the diagnostic reports at:")
            logger.info(f"- Text report: {txt_file}")
            logger.info(f"- HTML report: {html_file}")
    
    except Exception as e:
        logger.error(f"Error during diagnostic run: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 
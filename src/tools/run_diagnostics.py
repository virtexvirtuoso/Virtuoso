from src.utils.task_tracker import create_tracked_task
#!/usr/bin/env python3
"""
Optimized diagnostic script to run the Virtuoso_ccxt application with focus on
capturing redundancies in the market monitor flow.
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
import pandas as pd
from datetime import datetime
from collections import defaultdict, Counter
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('diagnostics.log')
    ]
)
logger = logging.getLogger('diagnostics')

# Resource monitoring data storage
resource_history = {
    'timestamps': [],
    'cpu': [],
    'memory': [],
    'processes': []
}

# Enhanced patterns for market monitor redundancies
MARKET_MONITOR_PATTERNS = {
    'duplicate_data_fetch': [
        r'Fetch(ing|ed).*market data for (\w+)',
        r'Refresh(ing|ed) components for (\w+)',
    ],
    'websocket_issues': [
        r'Error updating (ticker|orderbook|trades) from WebSocket',
        r'WebSocket.*connection (closed|lost|dropped)',
    ],
    'rate_limiting': [
        r'Rate limit.*exceed', 
        r'Too many requests',
    ],
    'cache_issues': [
        r'Symbol (\w+) not in cache',
        r'Retrieved \d+ OHLCV records for (\w+)',
        r'Already fetched data for (\w+) recently',
        r'Cache miss for (\w+)',
    ],
    'redundant_initializations': [
        r'Initialized MarketMonitor for',
        r'(\w+) initialized with monitoring metrics',
        r'Started monitoring tasks',
    ],
    'api_calls': [
        r'Making API call to fetch (ticker|orderbook|trades|kline)',
        r'REST call for (\w+)',
        r'API call success for (\w+)',
    ]
}

# Enhanced log patterns for general analysis
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
        r'fetch(ing|ed) .* data',
        r'Symbol .* not in cache',
        r'Retrieved \d+ OHLCV records',
        r'Initializ(ing|ed) MarketMonitor',
    ],
    'performance_issues': [
        r'slow\s+query|performance\s+warning',
        r'execution\s+time\s+exceeded',
        r'high\s+(cpu|memory|resource)\s+usage',
        r'[Ss]low .* refresh',
        r'[Tt]aking too long',
        r'Performance bottleneck',
    ],
    'network_issues': [
        r'connection\s+(refused|reset|timed out)',
        r'network\s+error|socket\s+error',
        r'unable\s+to\s+connect|connection\s+failed',
        r'[Ww]ebSocket .* (error|disconnect)',
        r'API .* (error|failure)',
    ],
    'market_monitor_issues': [
        r'Error updating .* from WebSocket',
        r'Missing component',
        r'MarketMonitor.*error',
        r'MarketMonitor.*not available',
        r'MarketDataManager.*error',
        r'WebSocketManager.*error',
    ]
}

# Log sequence tracking
class SequenceTracker:
    """Track sequences of log operations to identify redundant patterns."""
    
    def __init__(self):
        self.sequences = defaultdict(list)
        self.current_sequence = []
        self.symbol_operations = defaultdict(list)
        self.operation_counts = Counter()
        self.redundant_patterns = []
        self.sequence_window = 10  # Number of operations to consider in a sequence
    
    def add_operation(self, operation, symbol=None, timestamp=None, log_file=None, line_num=None):
        """Add an operation to the tracking."""
        op_data = {
            'operation': operation,
            'symbol': symbol,
            'timestamp': timestamp,
            'source': f"{log_file}:{line_num}" if log_file else None
        }
        
        # Add to current sequence
        self.current_sequence.append(op_data)
        if len(self.current_sequence) > self.sequence_window:
            self.current_sequence.pop(0)
        
        # Add to symbol-specific operations
        if symbol:
            self.symbol_operations[symbol].append(op_data)
        
        # Count operation
        self.operation_counts[operation] += 1
    
    def analyze_sequences(self):
        """Analyze the collected sequences for redundancies."""
        redundancy_types = []
        
        # Check for repeated fetch sequences
        for symbol, operations in self.symbol_operations.items():
            fetch_times = []
            for i, op in enumerate(operations):
                if 'fetch' in op['operation'].lower() or 'refresh' in op['operation'].lower():
                    fetch_times.append((i, op))
            
            # Find fetch operations that happen too close together
            for i in range(1, len(fetch_times)):
                time_diff = fetch_times[i][1]['timestamp'] - fetch_times[i-1][1]['timestamp']
                # If fetches are within 5 seconds of each other
                if time_diff < 5:
                    redundancy_types.append((
                        'repeated_fetch',
                        symbol,
                        f"Repeated fetches for {symbol} within {time_diff}s",
                        fetch_times[i-1][1]['source'],
                        fetch_times[i][1]['source']
                    ))
        
        # Check for excessive initialization 
        init_ops = [(op, i) for i, op in enumerate(self.current_sequence) if 'initializ' in op['operation'].lower()]
        if len(init_ops) > 2:
            redundancy_types.append((
                'excessive_initialization',
                None,
                f"Excessive initialization detected ({len(init_ops)} times)",
                init_ops[0][0]['source'],
                init_ops[-1][0]['source']
            ))
            
        # Find most frequent operations
        common_ops = self.operation_counts.most_common(5)
        for op, count in common_ops:
            if count > 10:  # Arbitrary threshold for "too frequent"
                redundancy_types.append((
                    'frequent_operation',
                    None,
                    f"Operation '{op}' performed excessively ({count} times)",
                    None,
                    None
                ))
                
        return redundancy_types

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
        self.task = create_tracked_task(self._monitor_resources(), name="auto_tracked_task")
        logger.info("Resource monitoring started")
        
    async def _monitor_resources(self):
        """Monitor CPU and memory usage periodically."""
        while self.running:
            try:
                # Get overall system stats
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                
                # Get process-specific stats if PID is provided
                process_info = None
                if self.process_pid:
                    try:
                        process = psutil.Process(self.process_pid)
                        process_info = {
                            'cpu': process.cpu_percent(interval=None),
                            'memory': process.memory_info().rss / (1024 * 1024),  # MB
                            'threads': process.num_threads()
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

async def run_app_with_timeout(timeout_minutes=10):
    """
    Run the main application for the specified time, then shut it down cleanly.
    
    Args:
        timeout_minutes: How long to run the app in minutes
    """
    # Set the Discord webhook URL environment variable if needed
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')
    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL environment variable not set")
    else:
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
                # Also track market monitor related logs to check for redundancies
                elif any(pattern in line for pattern in [
                    'MarketMonitor', 'WebSocket', 'market data', 'fetch_market_data',
                    'refresh_components', 'cache'
                ]):
                    logger.info(f"Monitor: {line}")
            
            # Read from stdout
            stdout_line = await process.stdout.readline()
            if stdout_line:
                line = stdout_line.decode('utf-8').strip()
                # Check if this is a warning or error (sometimes logged to stdout)
                if '[WARNING]' in line or '[ERROR]' in line or '[CRITICAL]' in line:
                    logger.warning(f"App: {line}")
                # Also track market monitor related logs
                elif any(pattern in line for pattern in [
                    'MarketMonitor', 'WebSocket', 'market data', 'fetch_market_data',
                    'refresh_components', 'cache'
                ]):
                    logger.info(f"Monitor: {line}")
            
            # If both streams are closed, break the loop
            if not stderr_line and not stdout_line and process.returncode is not None:
                break
                
            # Small delay to prevent CPU hogging
            await asyncio.sleep(0.1)
    
    # Start the monitoring task
    monitoring_task = create_tracked_task(monitor_output(), name="auto_tracked_task")
    
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
        # Stop resource monitoring
        resource_data = await resource_monitor.stop_monitoring()
        
        # Make sure the monitoring task is cancelled
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

        return resource_data

async def analyze_market_monitor_logs(log_files):
    """
    Specialized analysis for market monitor redundancies.
    
    Args:
        log_files: List of log files to analyze
    
    Returns:
        Dict with analysis results
    """
    logger.info("Analyzing market monitor redundancies")
    
    # Initialize results
    results = {
        'duplicate_fetches': {},
        'redundant_initializations': [],
        'websocket_issues': [],
        'cache_metrics': {},
        'api_call_frequencies': {},
        'sequence_redundancies': []
    }
    
    # Track timestamps of operations by symbol
    fetch_timestamps = defaultdict(list)
    init_timestamps = []
    
    # Initialize sequence tracker
    sequence_tracker = SequenceTracker()
    
    # Process each log file
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Try to extract timestamp from the line
                    timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', line)
                    timestamp = None
                    if timestamp_match:
                        try:
                            timestamp_str = timestamp_match.group(1)
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').timestamp()
                        except ValueError:
                            try:
                                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S').timestamp()
                            except ValueError:
                                pass
                    
                    # Check for market data fetches with symbol
                    for pattern in MARKET_MONITOR_PATTERNS['duplicate_data_fetch']:
                        match = re.search(pattern, line)
                        if match and len(match.groups()) > 1:
                            symbol = match.group(2)
                            if timestamp:
                                fetch_timestamps[symbol].append((timestamp, log_file, line_num, line))
                            
                            # Add to sequence tracker
                            sequence_tracker.add_operation(
                                f"fetch_data_{match.group(1)}", 
                                symbol, 
                                timestamp, 
                                log_file, 
                                line_num
                            )
                    
                    # Check for initializations
                    for pattern in MARKET_MONITOR_PATTERNS['redundant_initializations']:
                        if re.search(pattern, line):
                            if timestamp:
                                init_timestamps.append((timestamp, log_file, line_num, line))
                            
                            # Add to sequence tracker
                            sequence_tracker.add_operation(
                                "initialization", 
                                None, 
                                timestamp, 
                                log_file, 
                                line_num
                            )
                    
                    # Check for WebSocket issues
                    for pattern in MARKET_MONITOR_PATTERNS['websocket_issues']:
                        if re.search(pattern, line):
                            results['websocket_issues'].append((log_file, line_num, line))
                            
                            # Add to sequence tracker
                            sequence_tracker.add_operation(
                                "websocket_issue", 
                                None, 
                                timestamp, 
                                log_file, 
                                line_num
                            )
                    
                    # Check for cache operations
                    for pattern in MARKET_MONITOR_PATTERNS['cache_issues']:
                        match = re.search(pattern, line)
                        if match and len(match.groups()) > 0:
                            symbol = match.group(1)
                            if symbol not in results['cache_metrics']:
                                results['cache_metrics'][symbol] = {
                                    'hits': 0,
                                    'misses': 0,
                                    'examples': []
                                }
                            
                            if 'not in cache' in line or 'Cache miss' in line:
                                results['cache_metrics'][symbol]['misses'] += 1
                                if len(results['cache_metrics'][symbol]['examples']) < 3:
                                    results['cache_metrics'][symbol]['examples'].append((log_file, line_num, line))
                            else:
                                results['cache_metrics'][symbol]['hits'] += 1
                            
                            # Add to sequence tracker
                            cache_op = "cache_miss" if 'not in cache' in line or 'Cache miss' in line else "cache_hit"
                            sequence_tracker.add_operation(
                                cache_op, 
                                symbol, 
                                timestamp, 
                                log_file, 
                                line_num
                            )
                    
                    # Check for API calls
                    for pattern in MARKET_MONITOR_PATTERNS['api_calls']:
                        match = re.search(pattern, line)
                        if match and len(match.groups()) > 0:
                            data_type = match.group(1)
                            if data_type not in results['api_call_frequencies']:
                                results['api_call_frequencies'][data_type] = 0
                            results['api_call_frequencies'][data_type] += 1
                            
                            # Add to sequence tracker
                            sequence_tracker.add_operation(
                                f"api_call_{data_type}", 
                                None, 
                                timestamp, 
                                log_file, 
                                line_num
                            )
        except Exception as e:
            logger.error(f"Error analyzing {log_file}: {str(e)}")
    
    # Analyze duplicate fetches
    for symbol, timestamps in fetch_timestamps.items():
        # Sort by timestamp
        timestamps.sort(key=lambda x: x[0])
        
        # Find redundant fetches (within 5 seconds)
        redundant_fetches = []
        for i in range(1, len(timestamps)):
            time_diff = timestamps[i][0] - timestamps[i-1][0]
            if time_diff < 5:  # 5 seconds threshold
                redundant_fetches.append((timestamps[i-1], timestamps[i], time_diff))
        
        if redundant_fetches:
            results['duplicate_fetches'][symbol] = {
                'count': len(redundant_fetches),
                'examples': redundant_fetches[:3]  # First 3 examples
            }
    
    # Analyze redundant initializations
    if len(init_timestamps) > 3:  # Arbitrary threshold
        results['redundant_initializations'] = {
            'count': len(init_timestamps),
            'examples': init_timestamps[:3]  # First 3 examples
        }
    
    # Analyze sequence redundancies
    results['sequence_redundancies'] = sequence_tracker.analyze_sequences()
    
    return results

async def analyze_logs(resource_data=None, error_filter=None, warning_filter=None):
    """
    Analyze the application logs for warnings, errors, and redundancies.
    
    Args:
        resource_data: Resource utilization data
        error_filter: Filter for error categories (None = all)
        warning_filter: Filter for warning categories (None = all)
    """
    logger.info("Analyzing logs for warnings, errors, and redundancies")
    
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
        'diagnostics.log',
        'market_reporter.log',
        'market_reporter_test.log',
        'app.log',
        'indicators.log',
        'websocket.log',
        'error.log'            # Added error.log to ensure we capture errors
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
        return
    
    logger.info(f"Found {len(log_files)} log files to analyze")
    for log_file in log_files:
        logger.info(f"  - {log_file}")
    
    # Extract warnings and errors with advanced categorization
    warnings = []
    errors = []
    redundancies = []
    performance_issues = []
    network_issues = []
    
    # Standard log analysis
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                logger.info(f"Analyzing {log_file}")
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
        except Exception as e:
            logger.error(f"Error reading {log_file}: {str(e)}")
    
    # Market monitor specific analysis
    market_monitor_analysis = await analyze_market_monitor_logs(log_files)
    
    # Generate the report both in TXT and HTML formats
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    txt_report_file = f'diagnostic_report_{timestamp}.txt'
    html_report_file = f'diagnostic_report_{timestamp}.html'
    market_visualization_file = f'market_monitor_redundancies_{timestamp}.html'
    
    # Create the TXT report
    with open(txt_report_file, 'w', encoding='utf-8') as f:
        f.write(f"===== Virtuoso_ccxt Diagnostic Report - {datetime.now().isoformat()} =====\n\n")
        
        # Write resource utilization summary if available
        if resource_data:
            f.write("===== RESOURCE UTILIZATION =====\n\n")
            f.write(f"Duration: {resource_data['duration_seconds']} seconds\n")
            f.write(f"Peak CPU: {resource_data['peak_cpu']}%\n")
            f.write(f"Peak Memory: {resource_data['peak_memory']}%\n\n")
        
        # Write summary
        f.write(f"Total errors: {len(errors)}\n")
        f.write(f"Total warnings: {len(warnings)}\n")
        f.write(f"Redundant operations: {len(redundancies)}\n")
        f.write(f"Performance issues: {len(performance_issues)}\n")
        f.write(f"Network issues: {len(network_issues)}\n\n")
        
        # Market Monitor Redundancies Summary
        f.write("===== MARKET MONITOR REDUNDANCIES =====\n\n")
        
        # Duplicate fetches
        if market_monitor_analysis['duplicate_fetches']:
            f.write("== Duplicate Data Fetches ==\n\n")
            for symbol, data in market_monitor_analysis['duplicate_fetches'].items():
                f.write(f"Symbol: {symbol}\n")
                f.write(f"  Redundant fetch count: {data['count']}\n")
                f.write("  Examples:\n")
                for prev, curr, time_diff in data['examples']:
                    f.write(f"    {prev[2]}:{prev[3]}\n")
                    f.write(f"    {curr[2]}:{curr[3]} (within {time_diff:.2f}s)\n\n")
            f.write("\n")
        
        # Redundant initializations
        if market_monitor_analysis['redundant_initializations']:
            f.write("== Redundant Initializations ==\n\n")
            init_data = market_monitor_analysis['redundant_initializations']
            f.write(f"  Total initializations: {init_data['count']}\n")
            f.write("  Examples:\n")
            for timestamp, log_file, line_num, line in init_data['examples']:
                f.write(f"    {log_file}:{line_num} - {line}\n")
            f.write("\n")
        
        # WebSocket issues
        if market_monitor_analysis['websocket_issues']:
            f.write("== WebSocket Issues ==\n\n")
            f.write(f"  Total WebSocket issues: {len(market_monitor_analysis['websocket_issues'])}\n")
            f.write("  Examples:\n")
            for log_file, line_num, line in market_monitor_analysis['websocket_issues'][:5]:
                f.write(f"    {log_file}:{line_num} - {line}\n")
            f.write("\n")
        
        # Cache metrics
        if market_monitor_analysis['cache_metrics']:
            f.write("== Cache Metrics ==\n\n")
            for symbol, metrics in market_monitor_analysis['cache_metrics'].items():
                hits = metrics['hits']
                misses = metrics['misses']
                total = hits + misses
                hit_rate = hits / total * 100 if total > 0 else 0
                
                f.write(f"Symbol: {symbol}\n")
                f.write(f"  Cache hits: {hits}\n")
                f.write(f"  Cache misses: {misses}\n")
                f.write(f"  Hit rate: {hit_rate:.1f}%\n")
                
                if misses > 0 and metrics['examples']:
                    f.write("  Example cache misses:\n")
                    for log_file, line_num, line in metrics['examples']:
                        f.write(f"    {log_file}:{line_num} - {line}\n")
                f.write("\n")
        
        # API call frequencies
        if market_monitor_analysis['api_call_frequencies']:
            f.write("== API Call Frequencies ==\n\n")
            for data_type, count in market_monitor_analysis['api_call_frequencies'].items():
                f.write(f"  {data_type}: {count} calls\n")
            f.write("\n")
        
        # Sequence redundancies
        if market_monitor_analysis['sequence_redundancies']:
            f.write("== Redundant Operation Sequences ==\n\n")
            for redundancy_type, symbol, description, first_source, last_source in market_monitor_analysis['sequence_redundancies']:
                f.write(f"  Type: {redundancy_type}\n")
                if symbol:
                    f.write(f"  Symbol: {symbol}\n")
                f.write(f"  Description: {description}\n")
                if first_source:
                    f.write(f"  First occurrence: {first_source}\n")
                if last_source:
                    f.write(f"  Last occurrence: {last_source}\n")
                f.write("\n")
        
        # Write errors (more important)
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
            
            # Write grouped errors
            for error_type, occurrences in errors_by_type.items():
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
            
            f.write("\n")
        
        # Continue with the rest of your standard report generation...
        
    # Create the market monitor visualization HTML report
    with open(market_visualization_file, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
        <html>
        <head>
            <title>Market Monitor Redundancy Analysis</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .chart-container { height: 400px; margin-bottom: 30px; }
                .section { margin-bottom: 30px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
            </style>
        </head>
        <body>
            <h1>Market Monitor Redundancy Analysis</h1>
            
            <div class="section">
                <h2>Duplicate Data Fetches by Symbol</h2>
                <div class="chart-container">
                    <canvas id="duplicateFetchesChart"></canvas>
                </div>
            </div>
            
            <div class="section">
                <h2>Cache Performance by Symbol</h2>
                <div class="chart-container">
                    <canvas id="cachePerformanceChart"></canvas>
                </div>
            </div>
            
            <div class="section">
                <h2>API Call Distribution</h2>
                <div class="chart-container">
                    <canvas id="apiCallsChart"></canvas>
                </div>
            </div>
            
            <script>
        """)
        
        # Generate chart data for duplicate fetches
        symbols = []
        counts = []
        for symbol, data in market_monitor_analysis['duplicate_fetches'].items():
            symbols.append(symbol)
            counts.append(data['count'])
        
        f.write(f"""
                // Duplicate Fetches Chart
                new Chart(document.getElementById('duplicateFetchesChart'), {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(symbols)},
                        datasets: [{{
                            label: 'Number of Duplicate Fetches',
                            data: {json.dumps(counts)},
                            backgroundColor: 'rgba(255, 99, 132, 0.7)',
                            borderColor: 'rgb(255, 99, 132)',
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Count'
                                }}
                            }}
                        }}
                    }}
                }});
        """)
        
        # Generate chart data for cache performance
        cache_symbols = []
        hits = []
        misses = []
        for symbol, metrics in market_monitor_analysis['cache_metrics'].items():
            cache_symbols.append(symbol)
            hits.append(metrics['hits'])
            misses.append(metrics['misses'])
        
        f.write(f"""
                // Cache Performance Chart
                new Chart(document.getElementById('cachePerformanceChart'), {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(cache_symbols)},
                        datasets: [
                            {{
                                label: 'Cache Hits',
                                data: {json.dumps(hits)},
                                backgroundColor: 'rgba(75, 192, 192, 0.7)',
                                borderColor: 'rgb(75, 192, 192)',
                                borderWidth: 1
                            }},
                            {{
                                label: 'Cache Misses',
                                data: {json.dumps(misses)},
                                backgroundColor: 'rgba(255, 99, 132, 0.7)',
                                borderColor: 'rgb(255, 99, 132)',
                                borderWidth: 1
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Count'
                                }}
                            }}
                        }}
                    }}
                }});
        """)
        
        # Generate chart data for API calls
        api_types = []
        api_counts = []
        for data_type, count in market_monitor_analysis['api_call_frequencies'].items():
            api_types.append(data_type)
            api_counts.append(count)
        
        f.write(f"""
                // API Calls Chart
                new Chart(document.getElementById('apiCallsChart'), {{
                    type: 'pie',
                    data: {{
                        labels: {json.dumps(api_types)},
                        datasets: [{{
                            data: {json.dumps(api_counts)},
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.7)',
                                'rgba(54, 162, 235, 0.7)',
                                'rgba(255, 206, 86, 0.7)',
                                'rgba(75, 192, 192, 0.7)',
                                'rgba(153, 102, 255, 0.7)'
                            ]
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false
                    }}
                }});
            </script>
        </body>
        </html>
        """)
    
    logger.info(f"Diagnostic reports generated:")
    logger.info(f"  - Text report: {txt_report_file}")
    logger.info(f"  - HTML report: {html_report_file}")
    logger.info(f"  - Market monitor visualization: {market_visualization_file}")
    
    return txt_report_file, html_report_file, market_visualization_file

async def main():
    """Main diagnostic function."""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Run diagnostics on the Virtuoso trading application")
        parser.add_argument("--timeout", type=int, default=30, help="Run timeout in minutes (default: 30)")
        parser.add_argument("--clear-logs", action="store_true", help="Clear existing logs before starting")
        parser.add_argument("--analyze-only", action="store_true", help="Only analyze existing logs without running the app")
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
                'diagnostics.log',
                'market_reporter.log',
                'market_reporter_test.log',
                'app.log',
                'indicators.log',
                'websocket.log',
                'error.log'
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
                if file.startswith('diagnostic_report_') or file.startswith('market_monitor_redundancies_'):
                    if file.endswith('.txt') or file.endswith('.html'):
                        try:
                            os.remove(file)
                            logger.info(f"Deleted {file}")
                        except Exception as e:
                            logger.warning(f"Could not delete {file}: {str(e)}")
        
        # Skip running the app if analyze-only mode is requested
        resource_data = None
        if not args.analyze_only:
            # Run the application for specified minutes
            logger.info("Running application and collecting data...")
            resource_data = await run_app_with_timeout(timeout_minutes=args.timeout)
        else:
            logger.info("Analyze-only mode: skipping application execution")
        
        # Analyze the logs with the resource data
        logger.info("Analyzing logs for redundancies in market monitor flow...")
        report_files = await analyze_logs(resource_data=resource_data)
        
        logger.info("Diagnostic run completed successfully")
        
        if report_files:
            txt_file, html_file, market_viz_file = report_files
            logger.info(f"View the diagnostic reports at:")
            logger.info(f"- Text report: {txt_file}")
            logger.info(f"- HTML report: {html_file}")
            logger.info(f"- Market monitor visualization: {market_viz_file}")
    
    except Exception as e:
        logger.error(f"Error during diagnostic run: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 
"""
Optimized Logging Configuration for Virtuoso Trading System
Provides high-performance async logging with intelligent filtering and structured output.
"""

import os
import sys
import json
import logging
import logging.config
import logging.handlers
import asyncio
import queue
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import contextvars
import psutil

# Context variables for request tracking
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id')
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('user_id')
trade_session_var: contextvars.ContextVar[str] = contextvars.ContextVar('trade_session')

@dataclass
class LogMetrics:
    """Structured log metrics for performance monitoring."""
    timestamp: float
    level: str
    logger_name: str
    message: str
    module: str
    function: str
    line_number: int
    thread_name: str
    process_id: int
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    request_id: Optional[str] = None
    trade_session: Optional[str] = None
    execution_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

class AsyncLogHandler(logging.Handler):
    """High-performance async log handler that doesn't block the main thread."""
    
    def __init__(self, target_handler: logging.Handler, queue_size: int = 10000):
        super().__init__()
        self.target_handler = target_handler
        self.log_queue = queue.Queue(maxsize=queue_size)
        self.worker_thread = None
        self.shutdown_event = threading.Event()
        self._start_worker()
    
    def _start_worker(self):
        """Start the background worker thread for processing logs."""
        self.worker_thread = threading.Thread(
            target=self._process_logs,
            name="AsyncLogWorker",
            daemon=True
        )
        self.worker_thread.start()
    
    def _process_logs(self):
        """Background worker that processes log records."""
        while not self.shutdown_event.is_set():
            try:
                # Process batch of log records for efficiency
                records_batch = []
                deadline = time.time() + 0.1  # 100ms batch window
                
                while time.time() < deadline and len(records_batch) < 50:
                    try:
                        record = self.log_queue.get(timeout=0.01)
                        if record is None:  # Shutdown signal
                            return
                        records_batch.append(record)
                    except queue.Empty:
                        break
                
                # Process the batch
                for record in records_batch:
                    self.target_handler.emit(record)
                    
            except Exception as e:
                # Fallback to stderr if logging fails
                print(f"Async log handler error: {e}", file=sys.stderr)
    
    def emit(self, record):
        """Queue log record for async processing."""
        try:
            self.log_queue.put_nowait(record)
        except queue.Full:
            # Drop logs if queue is full (better than blocking)
            pass
    
    def close(self):
        """Shutdown the async handler."""
        self.shutdown_event.set()
        self.log_queue.put(None)  # Shutdown signal
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        self.target_handler.close()
        super().close()

class StructuredFormatter(logging.Formatter):
    """JSON-structured formatter for machine-readable logs."""
    
    def __init__(self, include_metrics: bool = True):
        super().__init__()
        self.include_metrics = include_metrics
        
    def format(self, record):
        """Format log record as structured JSON."""
        # Build base log entry
        try:
            iso_timestamp = datetime.fromtimestamp(record.created).isoformat()
        except (ImportError, AttributeError):
            # Fallback for shutdown issues
            iso_timestamp = f"{record.created:.3f}"
            
        log_data = {
            'timestamp': record.created,
            'iso_timestamp': iso_timestamp,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.threadName,
            'process': record.process
        }
        
        # Add context variables
        try:
            log_data['request_id'] = request_id_var.get()
        except LookupError:
            pass
            
        try:
            log_data['trade_session'] = trade_session_var.get()
        except LookupError:
            pass
        
        # Add system metrics for errors and above
        if self.include_metrics and record.levelno >= logging.WARNING:
            try:
                process = psutil.Process()
                log_data['metrics'] = {
                    'memory_mb': process.memory_info().rss / 1024 / 1024,
                    'cpu_percent': process.cpu_percent(),
                    'open_files': len(process.open_files()),
                    'threads': process.num_threads()
                }
            except Exception:
                pass
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data, default=str)

class ColoredPerformanceFormatter(logging.Formatter):
    """Enhanced formatter with colors for critical errors and warnings."""
    
    # Enhanced color codes with more visual impact
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green  
        'WARNING': '\033[1;33m',  # Bold Yellow
        'ERROR': '\033[1;31m',    # Bold Red
        'CRITICAL': '\033[1;37;41m',  # Bold White on Red background
        'RESET': '\033[0m'        # Reset color
    }
    
    # Background colors for extra emphasis on critical issues
    BG_COLORS = {
        'ERROR': '\033[41m',      # Red background
        'CRITICAL': '\033[1;41m', # Bold Red background
    }
    
    def format(self, record):
        """Fast formatting with human-readable timestamps and colors."""
        # Convert Unix timestamp to human-readable format with full date
        try:
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        except (ImportError, AttributeError):
            # Fallback for shutdown issues
            timestamp = f"{record.created:.3f}"
        
        # Get color for level
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS['RESET']
        
        # Special formatting for errors and critical
        if record.levelno >= logging.ERROR:
            # Add background color and make the entire message stand out
            bg_color = self.BG_COLORS.get(record.levelname, '')
            if record.levelno >= logging.CRITICAL:
                # Critical errors get extra visual treatment
                formatted_msg = f"🚨 CRITICAL: {record.getMessage()}"
                return f"{timestamp} {bg_color}{level_color}[{record.levelname}]{reset_color} {level_color}{record.name}{reset_color} - {bg_color}{level_color}{formatted_msg}{reset_color} ({record.filename}:{record.lineno})"
            else:
                # Regular errors get red highlighting
                formatted_msg = f"❌ ERROR: {record.getMessage()}"
                return f"{timestamp} {level_color}[{record.levelname}]{reset_color} {record.name} - {level_color}{formatted_msg}{reset_color} ({record.filename}:{record.lineno})"
        elif record.levelno >= logging.WARNING:
            # Warnings get yellow highlighting
            formatted_msg = f"⚠️  WARNING: {record.getMessage()}"
            return f"{timestamp} {level_color}[{record.levelname}]{reset_color} {record.name} - {level_color}{formatted_msg}{reset_color} ({record.filename}:{record.lineno})"
        else:
            # Normal formatting for INFO and DEBUG
            return f"{timestamp} {level_color}[{record.levelname}]{reset_color} {record.name} - {record.getMessage()} ({record.filename}:{record.lineno})"

class PerformanceFormatter(logging.Formatter):
    """Optimized formatter with minimal overhead (no colors for file logs)."""
    
    def format(self, record):
        """Fast formatting with human-readable timestamps."""
        # Convert Unix timestamp to human-readable format with full date
        try:
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        except (ImportError, AttributeError):
            # Fallback for shutdown issues
            timestamp = f"{record.created:.3f}"
        
        # Add visual indicators for errors without colors (for file logs)
        if record.levelno >= logging.CRITICAL:
            formatted_msg = f"🚨 CRITICAL: {record.getMessage()}"
        elif record.levelno >= logging.ERROR:
            formatted_msg = f"❌ ERROR: {record.getMessage()}"
        elif record.levelno >= logging.WARNING:
            formatted_msg = f"⚠️  WARNING: {record.getMessage()}"
        else:
            formatted_msg = record.getMessage()
            
        return f"{timestamp} [{record.levelname}] {record.name} - {formatted_msg} ({record.filename}:{record.lineno})"

class IntelligentFilter(logging.Filter):
    """Smart filter that reduces log noise while preserving important information."""
    
    def __init__(self):
        super().__init__()
        self.seen_messages = {}
        self.rate_limits = {
            'api_call': {'interval': 10, 'max_count': 5},  # Max 5 API call logs per 10 seconds
            'websocket': {'interval': 30, 'max_count': 3}, # Max 3 websocket logs per 30 seconds
            'cache_update': {'interval': 5, 'max_count': 2} # Max 2 cache update logs per 5 seconds
        }
    
    def filter(self, record):
        """Apply intelligent filtering logic."""
        message = record.getMessage().lower()
        current_time = time.time()
        
        # Always allow errors and above
        if record.levelno >= logging.ERROR:
            return True
        
        # Rate limit repetitive messages
        for category, limits in self.rate_limits.items():
            if category in message:
                key = f"{category}_{record.name}"
                if key not in self.seen_messages:
                    self.seen_messages[key] = {'count': 0, 'first_seen': current_time}
                
                msg_data = self.seen_messages[key]
                
                # Reset counter if interval passed
                if current_time - msg_data['first_seen'] > limits['interval']:
                    msg_data['count'] = 0
                    msg_data['first_seen'] = current_time
                
                msg_data['count'] += 1
                
                # Block if over limit
                if msg_data['count'] > limits['max_count']:
                    return False
        
        # Filter out known noisy patterns
        noisy_patterns = [
            'processing 1 websocket candles',
            'updated cache for',
            'making request to https://api.bybit.com',
            'response from https://api.bybit.com'
        ]
        
        if record.levelno == logging.DEBUG:
            for pattern in noisy_patterns:
                if pattern in message:
                    # Allow 1 in 10 of these debug messages
                    return hash(message) % 10 == 0
        
        return True

class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """File handler that compresses old log files to save space."""
    
    def doRollover(self):
        """Override to add compression."""
        super().doRollover()
        
        # Compress the rolled over file
        if self.backupCount > 0:
            import gzip
            import shutil
            
            old_file = f"{self.baseFilename}.1"
            compressed_file = f"{old_file}.gz"
            
            try:
                with open(old_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(old_file)
            except Exception as e:
                # Log compression failure to stderr
                print(f"Failed to compress log file: {e}", file=sys.stderr)

def configure_optimized_logging(
    log_level: str = "INFO",
    enable_async: bool = True,
    enable_structured: bool = False,
    enable_compression: bool = True,
    enable_intelligent_filtering: bool = True
) -> None:
    """
    Configure optimized logging system.
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_async: Use async logging for better performance
        enable_structured: Use JSON structured logging
        enable_compression: Compress old log files
        enable_intelligent_filtering: Apply smart filtering to reduce noise
    """
    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Choose formatters
    if enable_structured:
        file_formatter = StructuredFormatter()
        console_formatter = StructuredFormatter(include_metrics=False)
    else:
        file_formatter = PerformanceFormatter()  # No colors for file logs
        console_formatter = ColoredPerformanceFormatter()  # Colors for console
    
    # Choose file handler
    handler_class = CompressedRotatingFileHandler if enable_compression else logging.handlers.RotatingFileHandler
    
    # Create handlers
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(getattr(logging, log_level))
    
    file_handler = handler_class(
        filename='logs/app.log',
        maxBytes=5*1024*1024,  # 5MB (smaller for faster rotation)
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    error_handler = handler_class(
        filename='logs/error.log',
        maxBytes=1*1024*1024,  # 1MB
        backupCount=30,
        encoding='utf-8'
    )
    error_handler.setFormatter(file_formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Apply intelligent filtering
    if enable_intelligent_filtering:
        smart_filter = IntelligentFilter()
        file_handler.addFilter(smart_filter)
        console_handler.addFilter(smart_filter)
    
    # Wrap with async handlers if enabled
    if enable_async:
        file_handler = AsyncLogHandler(file_handler)
        error_handler = AsyncLogHandler(error_handler)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Optimize third-party loggers
    noisy_loggers = {
        'urllib3': logging.WARNING,
        'websockets': logging.WARNING,
        'asyncio': logging.WARNING,
        'ccxt': logging.WARNING,
        'aiohttp.client': logging.WARNING,
        'matplotlib': logging.WARNING,
        'requests': logging.WARNING,
        'PIL': logging.WARNING
    }
    
    for logger_name, level in noisy_loggers.items():
        logging.getLogger(logger_name).setLevel(level)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Optimized logging configured: async={enable_async}, structured={enable_structured}, compression={enable_compression}")

# Context managers for request tracking
class log_context:
    """Context manager for adding request tracking to logs."""
    
    def __init__(self, request_id: str = None, trade_session: str = None):
        self.request_id = request_id or f"req_{int(time.time()*1000)}"
        self.trade_session = trade_session
        self.tokens = []
    
    def __enter__(self):
        self.tokens.append(request_id_var.set(self.request_id))
        if self.trade_session:
            self.tokens.append(trade_session_var.set(self.trade_session))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for token in reversed(self.tokens):
            token.var.reset(token)

def get_log_stats() -> Dict[str, Any]:
    """Get logging system statistics."""
    stats = {
        'handlers': {},
        'loggers': {},
        'total_records': 0
    }
    
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler_name = handler.__class__.__name__
        stats['handlers'][handler_name] = {
            'level': handler.level,
            'formatter': handler.formatter.__class__.__name__ if handler.formatter else None
        }
        
        if isinstance(handler, AsyncLogHandler):
            stats['handlers'][handler_name]['queue_size'] = handler.log_queue.qsize()
    
    return stats 
"""Logging configuration utility."""

import os
import logging
import logging.config
import logging.handlers
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and improved formatting."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[41m',  # Red background
        'RESET': '\033[0m'      # Reset color
    }
    
    def format(self, record):
        # Save original values
        levelname = record.levelname
        message = record.msg
        
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{levelname}{self.COLORS['RESET']}"
        
        # Add timestamp with milliseconds
        record.created_fmt = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Format the message
        formatted = super().format(record)
        
        # Restore original values
        record.levelname = levelname
        record.msg = message
        
        return formatted

class ErrorFormatter(ColoredFormatter):
    """Enhanced formatter specifically for error logging with detailed context."""
    
    def format(self, record):
        # Save original values
        original_msg = record.msg
        
        # Add error context
        if isinstance(record.msg, Exception):
            error_details = {
                'exception_type': record.exc_info[0].__name__ if record.exc_info else type(record.msg).__name__,
                'message': str(record.msg),
                'stack_trace': self.formatException(record.exc_info) if record.exc_info else None,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                'thread': record.threadName,
                'process': record.process
            }
            
            # Format error message with detailed context
            record.msg = f"""
ERROR DETAILS:
Type: {error_details['exception_type']}
Location: {error_details['module']}.{error_details['function']}:{error_details['line']}
Thread/Process: {error_details['thread']}/{error_details['process']}
Message: {error_details['message']}
Stack Trace:
{error_details['stack_trace'] if error_details['stack_trace'] else 'No stack trace available'}
"""
        
        # Format with parent class
        formatted = super().format(record)
        
        # Restore original message
        record.msg = original_msg
        
        return formatted

class ErrorContextFilter(logging.Filter):
    """Filter that adds additional context to error records."""
    
    def filter(self, record):
        if record.levelno >= logging.ERROR:
            # Add system metrics
            import psutil
            try:
                process = psutil.Process()
                record.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                record.cpu_percent = process.cpu_percent()
                record.open_files = len(process.open_files())
                record.threads = process.num_threads()
            except Exception:
                pass
                
            # Add timestamp details
            from datetime import datetime
            dt = datetime.fromtimestamp(record.created)
            record.iso_timestamp = dt.isoformat()
            
            # Add request context if available
            try:
                import contextvars
                request_id = contextvars.ContextVar('request_id').get()
                record.request_id = request_id
            except Exception:
                record.request_id = None
                
        return True

def configure_logging(config: Dict[str, Any] = None) -> None:
    """Configure logging with improved formatting and handlers.
    
    Args:
        config: Optional logging configuration dictionary. If not provided,
               uses default enhanced configuration.
    """
    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Default enhanced logging configuration
    default_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'colored_console': {
                '()': ColoredFormatter,
                'format': '%(created_fmt)s [%(levelname)s] %(name)s - %(message)s (%(filename)s:%(lineno)d)'
            },
            'file': {
                'format': '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s (%(filename)s:%(lineno)d)',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'error_file': {
                '()': ErrorFormatter,
                'format': '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s\n%(message)s\n',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'colored_console',
                'level': 'DEBUG',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'file',
                'filename': 'logs/app.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'level': 'DEBUG'
            },
            'error_file': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'formatter': 'error_file',
                'filename': 'logs/error.log',
                'when': 'midnight',
                'interval': 1,
                'backupCount': 30,
                'encoding': 'utf-8',
                'level': 'ERROR',
                'filters': ['error_context_filter']
            },
            'critical_file': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'formatter': 'error_file',
                'filename': 'logs/critical.log',
                'when': 'midnight',
                'interval': 1,
                'backupCount': 90,
                'encoding': 'utf-8',
                'level': 'CRITICAL'
            }
        },
        'filters': {
            'error_context_filter': {
                '()': 'src.utils.logging_config.ErrorContextFilter'
            }
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'file', 'error_file', 'critical_file']
        },
                    'loggers': {
            'urllib3': {'level': 'WARNING'},
            'websockets': {'level': 'WARNING'},
            'asyncio': {'level': 'WARNING'},
            'ccxt': {'level': 'WARNING'},
            # Suppress aiohttp SSL cleanup timeout messages (harmless)
            'aiohttp.client': {'level': 'WARNING'},
            # Silence matplotlib's verbose debug logs
            'matplotlib': {'level': 'WARNING'},
            'matplotlib.font_manager': {'level': 'INFO'},
            'matplotlib.backends': {'level': 'WARNING'},
            'matplotlib.ticker': {'level': 'WARNING'}
        }
    }
    
    try:
        # Use provided config or fall back to default enhanced config
        logging_config = config.get('logging', default_config) if config else default_config
        logging.config.dictConfig(logging_config)
        
        logger = logging.getLogger(__name__)
        logger.info("Enhanced logging configured successfully")
        
    except Exception as e:
        # Set up basic colored logging if configuration fails
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColoredFormatter(
            '%(created_fmt)s [%(levelname)s] %(name)s - %(message)s (%(filename)s:%(lineno)d)'
        ))
        
        logging.basicConfig(
            level=logging.DEBUG,
            handlers=[console_handler]
        )
        
        logger = logging.getLogger(__name__)
        logger.error(f"Error configuring logging: {str(e)}")
        logger.info("Using basic colored logging configuration") 
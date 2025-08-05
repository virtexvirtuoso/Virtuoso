"""
Systemd-compatible logging configuration for Virtuoso Trading System.

This module ensures that logging works properly when running under systemd,
with output going to both systemd journal and log files.
"""

import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

def ensure_logging_configured():
    """
    Ensure logging is properly configured for systemd environment.
    
    This function checks if logging handlers are configured and sets them up
    if they're missing. It's designed to work with systemd's journal.
    """
    root_logger = logging.getLogger()
    
    # Check if handlers are already configured
    if len(root_logger.handlers) > 0:
        # Verify console handler exists
        has_console = any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout 
                         for h in root_logger.handlers)
        if has_console:
            return  # Already configured properly
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG)
    
    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s (%(filename)s:%(lineno)d)',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s (%(filename)s:%(lineno)d)',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler - MUST use sys.stdout for systemd
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG)
    
    # File handler for app.log
    file_handler = logging.handlers.RotatingFileHandler(
        filename='logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        filename='logs/error.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setFormatter(file_formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Configure third-party loggers to reduce noise
    noisy_loggers = {
        'urllib3': logging.WARNING,
        'websockets': logging.WARNING,
        'asyncio': logging.WARNING,
        'ccxt': logging.WARNING,
        'aiohttp': logging.WARNING,
        'matplotlib': logging.WARNING,
    }
    
    for logger_name, level in noisy_loggers.items():
        logging.getLogger(logger_name).setLevel(level)
    
    # Force flush to ensure output
    for handler in root_logger.handlers:
        if hasattr(handler, 'flush'):
            handler.flush()
    
    # Log that we've configured logging
    logger = logging.getLogger(__name__)
    logger.info("Systemd-compatible logging configured successfully")
    logger.info(f"Handlers: {[type(h).__name__ for h in root_logger.handlers]}")
    logger.info(f"Log files: logs/app.log, logs/error.log")


def check_systemd_environment() -> bool:
    """Check if we're running under systemd."""
    # Check for systemd-specific environment variables
    return any([
        'INVOCATION_ID' in os.environ,
        'JOURNAL_STREAM' in os.environ,
        'SYSTEMD_EXEC_PID' in os.environ,
    ])


if __name__ == "__main__":
    import os
    # Test the logging configuration
    ensure_logging_configured()
    
    logger = logging.getLogger("test")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    print(f"Running under systemd: {check_systemd_environment()}")
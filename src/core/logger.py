import logging
from typing import Optional

class Logger:
    """
    Custom logger wrapper that avoids duplicate log handlers.
    When the application has already configured logging globally,
    this class will use the existing logger without adding more handlers.
    """
    
    # Track loggers that have already been configured by this class
    _configured_loggers = set()
    
    @classmethod
    def is_root_configured(cls) -> bool:
        """Check if root logger is already configured with handlers."""
        return len(logging.getLogger().handlers) > 0
    
    def __init__(self, name: str, level: Optional[str] = None):
        self.logger = logging.getLogger(name)
        
        # Set level if provided, otherwise don't change the level
        if level:
            log_level = getattr(logging, level.upper())
            self.logger.setLevel(log_level)
        
        # Only add handlers if this logger hasn't been configured by this class
        # AND the root logger doesn't have handlers (which would indicate global config)
        if name not in self._configured_loggers and not self.is_root_configured():
            # Add console handler if no handlers exist
            if not self.logger.handlers:
                console_handler = logging.StreamHandler()
                if level:
                    console_handler.setLevel(log_level)
                
                # Create formatter
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                console_handler.setFormatter(formatter)
                
                self.logger.addHandler(console_handler)
            
            # Mark this logger as configured
            self._configured_loggers.add(name)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def critical(self, msg: str):
        self.logger.critical(msg)

    def isEnabledFor(self, level: int) -> bool:
        """Check if logger is enabled for the specified level."""
        return self.logger.isEnabledFor(level)
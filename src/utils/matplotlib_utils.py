"""Matplotlib utilities for configuration and log management."""

import logging

def silence_matplotlib_logs():
    """Silence matplotlib's verbose debug logs, especially font manager logs.
    
    This utility function sets appropriate log levels for matplotlib modules
    to prevent excessive debug output in logs, particularly from the font_manager
    which can be very verbose during font discovery.
    
    Usage:
        from src.utils.matplotlib_utils import silence_matplotlib_logs
        
        # Call at the beginning of scripts that use matplotlib
        silence_matplotlib_logs()
    """
    # Set log levels for matplotlib modules
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.font_manager').setLevel(logging.INFO)
    logging.getLogger('matplotlib.backends').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.ticker').setLevel(logging.WARNING)
    
    # Log that we've silenced these loggers
    logger = logging.getLogger(__name__)
    logger.debug("Matplotlib verbose logging has been silenced") 
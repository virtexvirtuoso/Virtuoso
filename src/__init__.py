"""
Virtuoso Trading System package initialization.

This module is loaded automatically when any part of the src package is imported.
It configures core logging settings to ensure clean logs without verbose debug messages.
"""

import logging

# Silence matplotlib logs before any matplotlib imports
def silence_matplotlib_logs():
    """Silence matplotlib's verbose debug logs, especially font manager logs.
    
    This function sets appropriate log levels for matplotlib modules
    to prevent excessive debug output in logs.
    """
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.font_manager').setLevel(logging.INFO)
    logging.getLogger('matplotlib.backends').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.ticker').setLevel(logging.WARNING)

# Apply matplotlib silencing immediately when src is imported
silence_matplotlib_logs()

# Register version
__version__ = "1.0.0"

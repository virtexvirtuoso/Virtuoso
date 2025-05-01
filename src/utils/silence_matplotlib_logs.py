"""
Utility to silence verbose matplotlib font_manager debug logs.

This module provides a function to silence the verbose debug logs from 
matplotlib's font_manager module, which can be very noisy.
"""

import logging

def silence_matplotlib_font_logs():
    """
    Silence the verbose debug logs from matplotlib.font_manager.
    
    This sets the logging level for matplotlib.font_manager to INFO,
    which prevents the debug-level messages about font discovery from
    appearing in the logs.
    
    Call this function before importing matplotlib or after importing
    but before using any plotting functions.
    """
    # Set matplotlib.font_manager logger to INFO level
    logging.getLogger('matplotlib.font_manager').setLevel(logging.INFO)
    
    # Additional matplotlib modules that might produce verbose logs
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.backends').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.ticker').setLevel(logging.WARNING) 
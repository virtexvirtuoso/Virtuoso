"""
Test package initialization.

This module is automatically loaded when tests are run and configures
specific test environment settings like silencing verbose debug logs.
"""

import logging

# Silence matplotlib logs for all tests
def silence_matplotlib_logs():
    """Silence matplotlib's verbose debug logs, especially font manager logs."""
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.font_manager').setLevel(logging.INFO)
    logging.getLogger('matplotlib.backends').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.ticker').setLevel(logging.WARNING)

# Apply silencing immediately when tests package is imported
silence_matplotlib_logs()

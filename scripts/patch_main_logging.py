#!/usr/bin/env python3
"""
Patch main.py to ensure logging works properly with systemd.
"""

import os
import sys

def create_logging_patch():
    """Create a patch for main.py to fix logging."""
    
    patch_content = '''
# Add after the logging configuration section (around line 100)

# IMPORTANT: Ensure logging is properly configured for systemd
# This is a failsafe to ensure handlers are present
from src.utils.systemd_logging import ensure_logging_configured
ensure_logging_configured()

# Verify logging is working
_test_logger = logging.getLogger(__name__)
_test_logger.debug("Logging verification: DEBUG level active")
_test_logger.info("Logging verification: Handlers configured = %d", len(logging.getLogger().handlers))

'''
    
    print("Logging patch created. Add this after the logging configuration in main.py:")
    print("-" * 60)
    print(patch_content)
    print("-" * 60)
    
    # Also create a simpler fix that can be added to main.py
    simple_fix = '''# Add this function near the top of main.py after imports

def verify_logging():
    """Verify logging is properly configured."""
    import sys
    root_logger = logging.getLogger()
    
    # If no handlers, add a basic console handler
    if len(root_logger.handlers) == 0:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
        ))
        console_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.DEBUG)
        
        # Also add file handler
        from pathlib import Path
        Path("logs").mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler('logs/app.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s (%(filename)s:%(lineno)d)'
        ))
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        
        logging.getLogger(__name__).warning("Had to configure logging manually - check configuration")

# Then call it after the logging configuration section:
verify_logging()
'''
    
    print("\nOr use this simpler fix:")
    print("-" * 60)
    print(simple_fix)
    print("-" * 60)

if __name__ == "__main__":
    create_logging_patch()
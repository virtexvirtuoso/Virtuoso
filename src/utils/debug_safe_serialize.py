#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script for safe_json_serialize
"""

import sys
import os
import logging
import importlib
import inspect

# Configure logging for debug
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Force reload to get the latest changes
if 'src.utils.json_encoder' in sys.modules:
    logger.debug("Reloading json_encoder module")
    importlib.reload(sys.modules['src.utils.json_encoder'])

from src.utils.json_encoder import safe_json_serialize

# Print the source code of safe_json_serialize
logger.debug(f"Source code of safe_json_serialize:\n{inspect.getsource(safe_json_serialize)}")

def main():
    # Create an un-serializable object (a function)
    def cannot_serialize():
        pass
    
    # Test case 1: With default
    fallback = '"fallback"'
    logger.debug(f"Before call: default='{fallback}'")
    result = safe_json_serialize(cannot_serialize, default=fallback)
    
    logger.debug(f"Input default: '{fallback}' (type: {type(fallback)})")
    logger.debug(f"Output result: '{result}' (type: {type(result)})")
    logger.debug(f"Result equals default? {result == fallback}")
    
    # Test case 2: Without default
    result2 = safe_json_serialize(cannot_serialize)
    logger.debug(f"Output result (no default): '{result2}'")

if __name__ == "__main__":
    main() 
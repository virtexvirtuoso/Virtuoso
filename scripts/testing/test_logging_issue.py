#!/usr/bin/env python3
"""Diagnostic script to test logging functionality in the running environment."""

import os
import sys
import logging
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_logging():
    """Test logging functionality."""
    print(f"\n{'='*60}")
    print(f"LOGGING DIAGNOSTIC TEST - {datetime.now()}")
    print(f"{'='*60}\n")
    
    # 1. Check environment
    print("1. Environment Check:")
    print(f"   - Working Directory: {os.getcwd()}")
    print(f"   - Python Version: {sys.version}")
    print(f"   - Process ID: {os.getpid()}")
    
    # 2. Check log directory
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    print(f"\n2. Log Directory Check:")
    print(f"   - Log Directory: {os.path.abspath(log_dir)}")
    print(f"   - Directory Exists: {os.path.exists(log_dir)}")
    if os.path.exists(log_dir):
        print(f"   - Directory Writable: {os.access(log_dir, os.W_OK)}")
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
        print(f"   - Log Files Found: {len(log_files)}")
    
    # 3. Import and check logging config
    print("\n3. Import Logging Configuration:")
    try:
        from src.config.manager import ConfigManager
        from src.utils.logging_config import configure_logging
        print("   - Successfully imported logging modules")
        
        # Load config
        config_manager = ConfigManager()
        config = config_manager.config
        print(f"   - Loaded configuration")
        
        # Check logging config
        if 'logging' in config:
            print(f"   - Logging config found in configuration")
            handlers = config['logging'].get('handlers', {})
            print(f"   - Handlers configured: {list(handlers.keys())}")
            for handler_name, handler_config in handlers.items():
                if 'filename' in handler_config:
                    print(f"     - {handler_name}: {handler_config['filename']}")
        
    except Exception as e:
        print(f"   - Error loading config: {e}")
    
    # 4. Check current logging setup
    print("\n4. Current Logging Setup:")
    root_logger = logging.getLogger()
    print(f"   - Root Logger Level: {logging.getLevelName(root_logger.level)}")
    print(f"   - Root Logger Handlers: {len(root_logger.handlers)}")
    
    for i, handler in enumerate(root_logger.handlers):
        print(f"\n   Handler {i+1}:")
        print(f"     - Type: {type(handler).__name__}")
        print(f"     - Level: {logging.getLevelName(handler.level)}")
        if hasattr(handler, 'stream'):
            print(f"     - Stream: {handler.stream}")
        if hasattr(handler, 'baseFilename'):
            print(f"     - File: {handler.baseFilename}")
            print(f"     - File Exists: {os.path.exists(handler.baseFilename)}")
    
    # 5. Test logging output
    print("\n5. Test Logging Output:")
    
    # Configure logging if not already configured
    if len(root_logger.handlers) == 0:
        print("   - No handlers found, configuring logging...")
        try:
            configure_logging(config)
            print("   - Logging configured")
        except Exception as e:
            print(f"   - Error configuring logging: {e}")
    
    # Test each log level
    test_logger = logging.getLogger('test_diagnostic')
    test_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    print(f"\n   Writing test messages at {test_timestamp}:")
    test_logger.debug(f"TEST DEBUG MESSAGE - {test_timestamp}")
    print("   - Wrote DEBUG message")
    
    test_logger.info(f"TEST INFO MESSAGE - {test_timestamp}")
    print("   - Wrote INFO message")
    
    test_logger.warning(f"TEST WARNING MESSAGE - {test_timestamp}")
    print("   - Wrote WARNING message")
    
    test_logger.error(f"TEST ERROR MESSAGE - {test_timestamp}")
    print("   - Wrote ERROR message")
    
    # Force flush all handlers
    for handler in root_logger.handlers:
        if hasattr(handler, 'flush'):
            handler.flush()
    
    # 6. Check if messages were written
    print("\n6. Verifying Log Files:")
    time.sleep(0.5)  # Give time for write
    
    log_files_to_check = ['app.log', 'error.log']
    for log_file in log_files_to_check:
        log_path = os.path.join(log_dir, log_file)
        if os.path.exists(log_path):
            print(f"\n   {log_file}:")
            print(f"     - Path: {log_path}")
            print(f"     - Size: {os.path.getsize(log_path)} bytes")
            
            # Check for our test message
            try:
                with open(log_path, 'r') as f:
                    # Read last 1000 chars
                    f.seek(max(0, os.path.getsize(log_path) - 1000))
                    last_content = f.read()
                    if test_timestamp in last_content:
                        print(f"     - ✓ Test message found!")
                    else:
                        print(f"     - ✗ Test message NOT found")
                        print(f"     - Last log entry: {last_content.strip().split(chr(10))[-1][:100]}...")
            except Exception as e:
                print(f"     - Error reading file: {e}")
    
    print(f"\n{'='*60}")
    print("DIAGNOSTIC COMPLETE")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    test_logging()
#!/usr/bin/env python3
"""Script to diagnose and potentially fix logging issues in the running process."""

import sys
import os
import logging
import psutil
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def diagnose_and_fix_logging():
    """Diagnose logging issues and attempt to fix them."""
    print("\n" + "="*60)
    print("LOGGING RUNTIME DIAGNOSIS")
    print("="*60 + "\n")
    
    # Find the main process
    target_pid = None
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'src/main.py' in ' '.join(cmdline):
                target_pid = proc.info['pid']
                print(f"Found main process: PID {target_pid}")
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if not target_pid:
        print("ERROR: Could not find main.py process")
        return
    
    # Check current logging setup
    print("\n1. Current Logging Configuration:")
    root_logger = logging.getLogger()
    print(f"   - Root Logger Level: {logging.getLevelName(root_logger.level)}")
    print(f"   - Number of Handlers: {len(root_logger.handlers)}")
    
    if len(root_logger.handlers) == 0:
        print("   ⚠️  WARNING: No handlers configured!")
        
        print("\n2. Attempting to reconfigure logging...")
        
        # Try to import and apply the configuration
        try:
            from src.config.manager import ConfigManager
            from src.utils.optimized_logging import configure_optimized_logging
            
            print("   - Imported configuration modules")
            
            # Configure optimized logging
            configure_optimized_logging(
                log_level="DEBUG",
                enable_async=True,
                enable_structured=False,
                enable_compression=True,
                enable_intelligent_filtering=True
            )
            
            print("   - Applied optimized logging configuration")
            
            # Verify the fix
            root_logger = logging.getLogger()
            print(f"\n3. Updated Configuration:")
            print(f"   - Root Logger Level: {logging.getLevelName(root_logger.level)}")
            print(f"   - Number of Handlers: {len(root_logger.handlers)}")
            
            for i, handler in enumerate(root_logger.handlers):
                print(f"\n   Handler {i+1}:")
                print(f"     - Type: {type(handler).__name__}")
                print(f"     - Level: {logging.getLevelName(handler.level)}")
                if hasattr(handler, 'baseFilename'):
                    print(f"     - File: {handler.baseFilename}")
            
            # Test logging
            print("\n4. Testing logging output...")
            test_logger = logging.getLogger('runtime_fix')
            test_time = time.strftime('%Y-%m-%d %H:%M:%S')
            
            test_logger.debug(f"RUNTIME FIX: Debug test at {test_time}")
            test_logger.info(f"RUNTIME FIX: Info test at {test_time}")
            test_logger.warning(f"RUNTIME FIX: Warning test at {test_time}")
            test_logger.error(f"RUNTIME FIX: Error test at {test_time}")
            
            print("   - Test messages sent")
            
            # Force flush
            for handler in root_logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            print("\n✅ Logging reconfiguration complete!")
            
        except Exception as e:
            print(f"   ❌ ERROR: Failed to reconfigure logging: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        print("\n   ✓ Handlers are configured")
        for i, handler in enumerate(root_logger.handlers):
            print(f"\n   Handler {i+1}:")
            print(f"     - Type: {type(handler).__name__}")
            print(f"     - Level: {logging.getLevelName(handler.level)}")
            if hasattr(handler, 'stream'):
                print(f"     - Stream: {handler.stream}")
            if hasattr(handler, 'baseFilename'):
                print(f"     - File: {handler.baseFilename}")
    
    print("\n" + "="*60)
    print("DIAGNOSIS COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    diagnose_and_fix_logging()
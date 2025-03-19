#!/usr/bin/env python3
"""Script to run all manual test cases sequentially."""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("TestRunner")

def run_test_script(script_path: str):
    """Run a test script and report the result."""
    logger.info(f"Running test script: {script_path}")
    
    try:
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=False
        )
        
        # Check if the script ran successfully
        if result.returncode == 0:
            logger.info(f"✅ Test script {script_path} completed successfully")
            
            # Print the output (optional)
            logger.info("Output:")
            for line in result.stdout.splitlines():
                logger.info(f"    {line}")
            
            return True
        else:
            logger.error(f"❌ Test script {script_path} failed with exit code {result.returncode}")
            logger.error("Error output:")
            for line in result.stderr.splitlines():
                logger.error(f"    {line}")
            
            logger.error("Standard output:")
            for line in result.stdout.splitlines():
                logger.error(f"    {line}")
            
            return False
    
    except Exception as e:
        logger.error(f"❌ Error running test script {script_path}: {str(e)}")
        return False

def main():
    """Run all test scripts."""
    logger.info("Starting test run...")
    
    # Get the directory containing this script
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # Define the test scripts to run
    test_scripts = [
        script_dir / "test_alert_deduplication.py",
        script_dir / "test_signal_gen_integration.py"
    ]
    
    # Run each test script
    success_count = 0
    for script in test_scripts:
        if run_test_script(str(script)):
            success_count += 1
    
    # Report summary
    total_tests = len(test_scripts)
    logger.info(f"Test run completed: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        logger.info("🎉 All tests passed! The alert deduplication appears to be working correctly.")
    else:
        logger.warning(f"⚠️ {total_tests - success_count} tests failed. Please check the logs for details.")
    
    return 0 if success_count == total_tests else 1

if __name__ == "__main__":
    sys.exit(main()) 
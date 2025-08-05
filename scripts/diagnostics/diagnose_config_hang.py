#!/usr/bin/env python3
"""
Diagnose the config loading hang issue.
Add detailed logging to understand where the system is getting stuck.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up very detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s (%(filename)s:%(lineno)d)',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_yaml_loading():
    """Test if YAML loading is the issue."""
    logger.info("Testing YAML loading...")
    
    try:
        import yaml
        logger.info(f"PyYAML version: {yaml.__version__}")
        
        # Try to load the config file directly
        config_path = project_root / "config" / "config.yaml"
        logger.info(f"Looking for config at: {config_path}")
        
        if not config_path.exists():
            logger.error(f"Config file not found at {config_path}")
            return False
            
        logger.info("Config file exists, attempting to read...")
        
        # Read raw content first
        with open(config_path, 'r') as f:
            content = f.read()
        logger.info(f"Config file size: {len(content)} bytes")
        
        # Try to parse YAML
        logger.info("Parsing YAML content...")
        start_time = time.time()
        
        config = yaml.load(content, Loader=yaml.SafeLoader)
        
        parse_time = time.time() - start_time
        logger.info(f"YAML parsed successfully in {parse_time:.3f}s")
        logger.info(f"Config has {len(config)} top-level keys")
        
        return True
        
    except Exception as e:
        logger.error(f"YAML loading failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_config_manager_init():
    """Test ConfigManager initialization."""
    logger.info("\nTesting ConfigManager initialization...")
    
    try:
        # Import with timing
        logger.info("Importing ConfigManager...")
        start_time = time.time()
        
        from src.config.manager import ConfigManager
        
        import_time = time.time() - start_time
        logger.info(f"ConfigManager imported in {import_time:.3f}s")
        
        # Create instance with timing
        logger.info("Creating ConfigManager instance...")
        start_time = time.time()
        
        config_manager = ConfigManager()
        
        init_time = time.time() - start_time
        logger.info(f"ConfigManager initialized in {init_time:.3f}s")
        
        # Check config
        if hasattr(config_manager, 'config') and config_manager.config:
            logger.info(f"Config loaded successfully with {len(config_manager.config)} sections")
            for section in config_manager.config.keys():
                logger.info(f"  - {section}")
        else:
            logger.error("Config not loaded properly")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"ConfigManager initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_env_variable_processing():
    """Test environment variable processing."""
    logger.info("\nTesting environment variable processing...")
    
    try:
        from src.config.manager import ConfigManager
        
        # Test env var processing
        test_cases = [
            ("${TEST_VAR:default_value}", "default_value"),
            ("${MISSING_VAR}", "${MISSING_VAR}"),
            ("$TEST_VAR", "$TEST_VAR"),
            ("normal_string", "normal_string"),
        ]
        
        for test_input, expected in test_cases:
            result = ConfigManager._process_env_variables(test_input)
            logger.info(f"  {test_input} -> {result} (expected: {expected})")
            
        return True
        
    except Exception as e:
        logger.error(f"Env variable processing failed: {str(e)}")
        return False


async def test_bybit_init_isolated():
    """Test Bybit initialization in isolation."""
    logger.info("\nTesting Bybit initialization in isolation...")
    
    try:
        from src.core.exchanges.bybit import BybitExchange
        from src.config.manager import ConfigManager
        
        # Get config
        config = ConfigManager().config
        bybit_config = config['exchanges']['bybit']
        
        logger.info("Creating BybitExchange instance...")
        exchange = BybitExchange(bybit_config)
        
        logger.info("Initializing exchange with 10s timeout...")
        start_time = time.time()
        
        # Use asyncio.timeout for Python 3.11
        try:
            async with asyncio.timeout(10.0):
                result = await exchange.initialize()
                
        except asyncio.TimeoutError:
            logger.error("Exchange initialization timed out!")
            return False
            
        init_time = time.time() - start_time
        
        if result:
            logger.info(f"✅ Exchange initialized successfully in {init_time:.2f}s")
        else:
            logger.error(f"❌ Exchange initialization failed after {init_time:.2f}s")
            
        # Clean up
        await exchange.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Bybit initialization test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all diagnostic tests."""
    logger.info("=" * 80)
    logger.info("Config Loading Diagnostic Tool")
    logger.info("=" * 80)
    
    # Test 1: YAML loading
    yaml_ok = test_yaml_loading()
    
    # Test 2: ConfigManager init
    config_ok = test_config_manager_init()
    
    # Test 3: Env variable processing
    env_ok = test_env_variable_processing()
    
    # Test 4: Bybit initialization
    bybit_ok = await test_bybit_init_isolated()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSTIC SUMMARY:")
    logger.info("=" * 80)
    logger.info(f"YAML Loading: {'✅ PASS' if yaml_ok else '❌ FAIL'}")
    logger.info(f"ConfigManager: {'✅ PASS' if config_ok else '❌ FAIL'}")
    logger.info(f"Env Variables: {'✅ PASS' if env_ok else '❌ FAIL'}")
    logger.info(f"Bybit Init: {'✅ PASS' if bybit_ok else '❌ FAIL'}")
    
    if all([yaml_ok, config_ok, env_ok, bybit_ok]):
        logger.info("\n✅ All tests passed! The issue might be in the main initialization flow.")
        logger.info("Next step: Add more logging to main.py initialization sequence.")
    else:
        logger.info("\n❌ Some tests failed. Check the errors above for details.")


if __name__ == "__main__":
    asyncio.run(main())
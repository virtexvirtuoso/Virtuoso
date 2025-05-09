#!/usr/bin/env python3
"""Test script to verify environment variables are loaded correctly."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def check_env_variables():
    """Check that critical environment variables are loaded."""
    env_path = Path(__file__).parent / "config" / "env" / ".env"
    logger.info(f"Loading environment variables from: {env_path}")
    
    # Load environment variables from the specific path
    load_result = load_dotenv(dotenv_path=env_path)
    
    if not load_result:
        logger.error(f"Failed to load .env file from {env_path}")
        return False
    
    logger.info(f"Successfully loaded .env file from {env_path}")
    
    # Critical environment variables to check
    critical_vars = [
        'BYBIT_API_KEY',
        'BYBIT_API_SECRET',
        'INFLUXDB_URL',
        'INFLUXDB_TOKEN',
        'INFLUXDB_ORG',
        'INFLUXDB_BUCKET',
        'DISCORD_WEBHOOK_URL'
    ]
    
    # Check each variable
    missing_vars = []
    for var in critical_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values in logs
            if 'API_KEY' in var or 'API_SECRET' in var or 'TOKEN' in var:
                masked_value = value[:5] + '...' + value[-5:] if len(value) > 10 else '***'
                logger.info(f"✅ {var} = {masked_value}")
            else:
                logger.info(f"✅ {var} is set")
        else:
            logger.error(f"❌ {var} is not set")
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing critical environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("All critical environment variables are correctly loaded")
    return True

if __name__ == "__main__":
    logger.info("Testing environment variable loading")
    success = check_env_variables()
    
    if success:
        logger.info("Environment configuration test passed ✓")
        sys.exit(0)
    else:
        logger.error("Environment configuration test failed ✗")
        sys.exit(1) 
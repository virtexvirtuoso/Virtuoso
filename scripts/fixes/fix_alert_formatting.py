#!/usr/bin/env python3
"""
Alert formatting diagnostic script.

This script diagnoses and tests the alert formatting functions
that were experiencing errors:
1. "year 57283 is out of range" timestamp error
2. "numpy.float64 has no attribute 'get'" error in PDF generation

Execute this script to verify the issues are fixed.
"""

import os
import sys
import asyncio
import numpy as np
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import alert manager - will fail if not run from project root
try:
    from src.monitoring.alert_manager import AlertManager
    from src.core.reporting.pdf_generator import ReportGenerator
except ImportError:
    print("Error: Run this script from the project root directory")
    print("Example: python scripts/fixes/fix_alert_formatting.py")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)

logger = logging.getLogger("alert_diagnostic")

async def test_timestamp_formatting():
    """Test timestamp formatting in AlertManager."""
    logger.info("=== Testing Timestamp Formatting ===")
    
    # Create minimal config
    config = {
        'monitoring': {
            'alerts': {
                'discord': {
                    'webhook_url': 'https://discord.com/api/webhooks/example'
                }
            }
        }
    }
    
    # Create alert manager
    alert_manager = AlertManager(config)
    
    # Create signal data with problematic timestamp
    signal_data = {
        'symbol': 'TESTUSDT',
        'score': 75.5,
        'signal': 'BULLISH',
        'price': 42.42,
        'timestamp': int(datetime.now().timestamp() * 1000 * 1000),  # Very large timestamp
        'components': {
            'technical': 65.3,
            'volume': 82.1,
            'orderbook': 70.2,
            'orderflow': 77.8,
            'sentiment': 68.5,
            'price_structure': 60.1
        },
        'buy_threshold': 65.0,
        'sell_threshold': 35.0
    }
    
    # Test formatting without actually sending
    try:
        logger.info(f"Testing with problematic timestamp: {signal_data['timestamp']}")
        webhook_msg = alert_manager._format_enhanced_confluence_alert(signal_data)
        logger.info("Successfully formatted alert with fixed timestamp handling!")
        return True
    except Exception as e:
        logger.error(f"Error formatting alert: {str(e)}")
        return False

async def test_numpy_component_handling():
    """Test handling of numpy values in components."""
    logger.info("=== Testing Numpy Component Handling ===")
    
    # Create components with numpy values
    components = {
        'technical': np.float64(65.3),
        'volume': np.float64(82.1),
        'orderbook': np.float64(70.2),
        'orderflow': np.float64(77.8),
        'sentiment': np.float64(68.5),
        'price_structure': np.float64(60.1)
    }
    
    # Create PDF generator
    pdf_generator = ReportGenerator()
    
    # Test component chart generation
    try:
        logger.info(f"Testing with numpy components: {components}")
        output_dir = "exports"
        os.makedirs(output_dir, exist_ok=True)
        chart_path = pdf_generator._create_component_chart(components, output_dir)
        if chart_path:
            logger.info(f"Successfully created component chart: {chart_path}")
            return True
        else:
            logger.warning("Chart generation didn't error but returned None")
            return False
    except Exception as e:
        logger.error(f"Error creating component chart: {str(e)}")
        return False

async def main():
    """Run diagnostic tests."""
    logger.info("Starting alert formatting diagnostic tests")
    
    # Test timestamp formatting
    timestamp_test_passed = await test_timestamp_formatting()
    
    # Test numpy component handling
    numpy_test_passed = await test_numpy_component_handling()
    
    # Report results
    logger.info("=== Diagnostic Test Results ===")
    logger.info(f"Timestamp formatting test: {'PASSED' if timestamp_test_passed else 'FAILED'}")
    logger.info(f"Numpy component handling test: {'PASSED' if numpy_test_passed else 'FAILED'}")
    
    if timestamp_test_passed and numpy_test_passed:
        logger.info("All tests passed! The fixes are working correctly.")
    else:
        logger.warning("Some tests failed. The fixes may not be complete.")

if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python3
"""
Test script to verify the fixes for:
1. numpy.float64 handling in PDF component charts
2. Timestamp formatting in enhanced confluence alerts
"""

import os
import sys
import asyncio
import logging
import numpy as np
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)

logger = logging.getLogger("test_fixes")

# Import necessary modules
try:
    from src.monitoring.alert_manager import AlertManager
    from src.core.reporting.pdf_generator import ReportGenerator
except ImportError:
    logger.error("Failed to import required modules. Make sure you're running from the project root.")
    sys.exit(1)

async def test_numpy_components():
    """Test handling of numpy values in component charts."""
    logger.info("=== Testing numpy.float64 handling in component charts ===")
    
    # Create components with numpy values
    components = {
        'technical': np.float64(52.03729111614121),
        'volume': np.float64(61.65485177212527),
        'orderbook': np.float64(78.73732463803513),
        'orderflow': np.float64(72.41596999935265),
        'sentiment': np.float64(66.17837776017078),
        'price_structure': np.float64(50.171855756243524)
    }
    
    logger.info(f"Components with numpy.float64 values: {components}")
    
    # Create PDF generator
    pdf_generator = ReportGenerator()
    
    # Test component chart generation
    try:
        output_dir = "exports"
        os.makedirs(output_dir, exist_ok=True)
        
        chart_path = pdf_generator._create_component_chart(components, output_dir)
        if chart_path and os.path.exists(chart_path):
            logger.info(f"✅ Successfully created component chart: {chart_path}")
            return True
        else:
            logger.error("❌ Failed to create component chart")
            return False
    except Exception as e:
        logger.error(f"❌ Error creating component chart: {str(e)}")
        return False

async def test_timestamp_formatting():
    """Test timestamp formatting in AlertManager."""
    logger.info("=== Testing timestamp formatting in enhanced confluence alerts ===")
    
    # Create minimal config for AlertManager
    config = {
        'monitoring': {
            'alerts': {
                'discord': {
                    'webhook_url': 'https://discord.com/api/webhooks/example'
                }
            }
        }
    }
    
    # Create AlertManager instance
    alert_manager = AlertManager(config)
    
    # Create test case with problematic timestamp (microseconds)
    problematic_timestamp = int(datetime.now().timestamp() * 1000000)  # microseconds
    
    # Create test signal data
    signal_data = {
        'symbol': 'TESTUSDT',
        'score': 75.5,
        'timestamp': problematic_timestamp,
        'components': {
            'technical': np.float64(65.3),
            'volume': np.float64(82.1),
            'orderbook': np.float64(70.2),
            'orderflow': np.float64(77.8),
            'sentiment': np.float64(68.5),
            'price_structure': np.float64(60.1)
        },
        'buy_threshold': 65.0,
        'sell_threshold': 35.0
    }
    
    logger.info(f"Testing with problematic timestamp: {problematic_timestamp}")
    
    # Test the _format_enhanced_confluence_alert method
    try:
        webhook_msg = alert_manager._format_enhanced_confluence_alert(signal_data)
        if webhook_msg and isinstance(webhook_msg, dict):
            logger.info(f"✅ Successfully formatted alert with timestamp: {webhook_msg.get('title', '')}")
            return True
        else:
            logger.error("❌ Failed to format alert (invalid response)")
            return False
    except Exception as e:
        logger.error(f"❌ Error formatting alert: {str(e)}")
        return False

async def main():
    """Run the test script."""
    logger.info("Starting test script for fixes")
    
    # Test component chart with numpy values
    numpy_test_result = await test_numpy_components()
    
    # Test timestamp formatting
    timestamp_test_result = await test_timestamp_formatting()
    
    # Print summary
    logger.info("=== Test Results ===")
    logger.info(f"numpy.float64 handling: {'✅ PASSED' if numpy_test_result else '❌ FAILED'}")
    logger.info(f"Timestamp formatting: {'✅ PASSED' if timestamp_test_result else '❌ FAILED'}")
    
    if numpy_test_result and timestamp_test_result:
        logger.info("✅ All fixes are working correctly!")
        return 0
    else:
        logger.error("❌ Some fixes didn't work properly. See log for details.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 
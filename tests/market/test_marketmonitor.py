#!/usr/bin/env python3
"""
Simple test script for MarketMonitor.check_system_health method
"""

import logging
import asyncio
import unittest.mock

from src.monitoring.monitor import MarketMonitor

async def test_check_system_health():
    """Test MarketMonitor.check_system_health method with component parameter"""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()
    
    # Create mock objects
    mock_config = {}
    mock_exchange_manager = unittest.mock.MagicMock()
    mock_metrics_manager = unittest.mock.MagicMock()
    
    # Create MarketMonitor instance
    mm = MarketMonitor(
        logger=logger,
        config=mock_config,
        exchange_manager=mock_exchange_manager,
        metrics_manager=mock_metrics_manager
    )
    
    try:
        # Test with component parameter
        print("Testing check_system_health with 'memory' component...")
        memory_result = await mm.check_system_health(component='memory')
        print(f"Memory health check result: {memory_result}")
        
        # Test without component parameter
        print("\nTesting check_system_health with no component (full check)...")
        full_result = await mm.check_system_health()
        print(f"Full health check status: {full_result['status']}")
        print(f"Components checked: {list(full_result['components'].keys())}")
        
        print("\nTest completed successfully!")
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_check_system_health()) 
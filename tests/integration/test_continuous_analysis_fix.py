#!/usr/bin/env python3
"""
Test script to verify that the ContinuousAnalysisManager initialization fix works correctly.
This script simulates the initialization flow and checks if the conditions would be satisfied.
"""
import sys
import os
import asyncio
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_initialization_flow():
    """Test the initialization flow to ensure market_data_manager is properly initialized"""
    logger.info("Testing initialization flow...")
    
    try:
        # Import the initialize_components function
        from main import initialize_components
        
        # Initialize components
        logger.info("Initializing components...")
        components = await initialize_components()
        
        # Check that both confluence_analyzer and market_data_manager are in the components
        confluence_analyzer = components.get('confluence_analyzer')
        market_data_manager = components.get('market_data_manager')
        
        logger.info(f"confluence_analyzer available: {confluence_analyzer is not None}")
        logger.info(f"market_data_manager available: {market_data_manager is not None}")
        
        # Test the condition that would be checked in the lifespan function
        condition_satisfied = confluence_analyzer and market_data_manager
        
        if condition_satisfied:
            logger.info("✅ SUCCESS: Both components are available, ContinuousAnalysisManager would start")
            logger.info(f"ContinuousAnalysisManager would be initialized with confluence_analyzer={confluence_analyzer is not None} and market_data_manager={market_data_manager is not None}")
        else:
            logger.error("❌ FAILURE: Missing components, ContinuousAnalysisManager would NOT start")
            logger.error(f"confluence_analyzer={confluence_analyzer is not None}, market_data_manager={market_data_manager is not None}")
        
        return condition_satisfied
        
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main test function"""
    logger.info("🔍 Testing ContinuousAnalysisManager initialization fix...")
    
    success = await test_initialization_flow()
    
    if success:
        logger.info("🎉 Test PASSED: Fix should resolve the initialization issue")
        return 0
    else:
        logger.error("❌ Test FAILED: Fix may not resolve the issue")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
#!/usr/bin/env python3
"""
Debug script to test correlation API functions directly.
"""

import asyncio
import sys
import logging
from src.api.routes.correlation import get_live_signal_matrix

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_correlation_functions():
    """Test the correlation functions directly."""
    try:
        logger.info("🧪 Testing correlation functions...")
        
        # Test the live matrix function
        result = await get_live_signal_matrix()
        
        logger.info("✅ Live matrix test successful!")
        logger.info(f"📊 Result keys: {list(result.keys())}")
        
        if "live_matrix" in result:
            matrix = result["live_matrix"]
            logger.info(f"📈 Matrix symbols: {len(matrix)}")
            
            # Show sample data
            if matrix:
                first_symbol = next(iter(matrix.keys()))
                logger.info(f"🔍 Sample symbol: {first_symbol}")
                logger.info(f"🔍 Sample data: {matrix[first_symbol]}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error testing correlation functions: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🚀 Starting Correlation API Debug Test")
    result = asyncio.run(test_correlation_functions())
    
    if result:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed!")
        sys.exit(1) 
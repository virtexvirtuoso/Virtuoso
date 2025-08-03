#!/usr/bin/env python3
"""
Test script to check for JavaScript errors in mobile dashboard.
This script simulates what the mobile dashboard JavaScript does.
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8003"

async def test_mobile_data_flow():
    """Test the data flow that mobile dashboard JavaScript uses."""
    
    logger.info("Starting mobile dashboard JavaScript flow simulation...")
    
    async with aiohttp.ClientSession() as session:
        # 1. Test the primary endpoint used by mobile dashboard
        logger.info("\n1. Testing /api/dashboard/mobile-data endpoint...")
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/mobile-data") as response:
                data = await response.json()
                logger.info(f"Response status: {response.status}")
                
                # Check confluence scores
                confluence_scores = data.get('confluence_scores', [])
                logger.info(f"Confluence scores count: {len(confluence_scores)}")
                
                if confluence_scores:
                    logger.info("Sample confluence score structure:")
                    sample = confluence_scores[0]
                    logger.info(json.dumps(sample, indent=2))
                    
                    # Validate score structure
                    required_fields = ['symbol', 'score', 'price', 'change_24h', 'components']
                    missing_fields = [field for field in required_fields if field not in sample]
                    if missing_fields:
                        logger.warning(f"Missing fields in confluence score: {missing_fields}")
                    else:
                        logger.info("✓ All required fields present")
                        
                    # Check component values
                    components = sample.get('components', {})
                    if all(comp == 50.0 for comp in components.values()):
                        logger.warning("⚠ All component values are default (50.0)")
                    else:
                        logger.info("✓ Component values are calculated")
                else:
                    logger.error("✗ No confluence scores returned!")
                    
        except Exception as e:
            logger.error(f"Error testing mobile-data endpoint: {e}")
            
        # 2. Test the direct confluence scores endpoint
        logger.info("\n2. Testing /api/dashboard/confluence-scores endpoint...")
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/confluence-scores") as response:
                scores = await response.json()
                logger.info(f"Direct confluence scores count: {len(scores)}")
                
                if scores:
                    # Compare with mobile data
                    logger.info("Comparing direct scores with mobile data...")
                    direct_symbols = {s['symbol'] for s in scores}
                    mobile_symbols = {s['symbol'] for s in confluence_scores}
                    
                    if direct_symbols != mobile_symbols:
                        logger.warning(f"Symbol mismatch - Direct: {direct_symbols}, Mobile: {mobile_symbols}")
                    else:
                        logger.info("✓ Symbols match between endpoints")
                        
        except Exception as e:
            logger.error(f"Error testing confluence-scores endpoint: {e}")
            
        # 3. Simulate the JavaScript update cycle
        logger.info("\n3. Simulating JavaScript update cycle...")
        for i in range(3):
            logger.info(f"\nUpdate cycle {i+1}/3")
            try:
                async with session.get(f"{BASE_URL}/api/dashboard/mobile-data") as response:
                    data = await response.json()
                    confluence_scores = data.get('confluence_scores', [])
                    
                    if confluence_scores:
                        # Log what the JavaScript would display
                        logger.info("JavaScript would render:")
                        for score in confluence_scores[:3]:  # First 3 symbols
                            symbol = score.get('symbol', 'UNKNOWN')
                            score_val = score.get('score', 50)
                            price = score.get('price', 0)
                            change = score.get('change_24h', 0)
                            
                            # Determine color class (like JavaScript does)
                            if score_val >= 60:
                                color = "GREEN (bullish)"
                            elif score_val >= 40:
                                color = "YELLOW (neutral)"
                            else:
                                color = "RED (bearish)"
                                
                            logger.info(f"  {symbol}: {score_val:.2f} [{color}] - ${price:.2f} ({change:+.2f}%)")
                    else:
                        logger.warning("  No scores to display - spinner would continue")
                        
            except Exception as e:
                logger.error(f"Error in update cycle {i+1}: {e}")
                
            await asyncio.sleep(2)  # Simulate JavaScript's 5-second interval
            
        # 4. Check for potential JavaScript issues
        logger.info("\n4. Checking for potential JavaScript issues...")
        
        # Test error scenarios
        logger.info("Testing error handling...")
        
        # Test with invalid endpoint (to see error handling)
        try:
            async with session.get(f"{BASE_URL}/api/invalid-endpoint") as response:
                if response.status == 404:
                    logger.info("✓ 404 errors would be caught by JavaScript error handler")
        except:
            pass
            
        # Test CORS (if running from different origin)
        logger.info("\nChecking CORS headers...")
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/mobile-data") as response:
                cors_headers = {
                    'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin', 'Not set'),
                    'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods', 'Not set')
                }
                logger.info(f"CORS headers: {cors_headers}")
                
                if cors_headers['Access-Control-Allow-Origin'] == 'Not set':
                    logger.warning("⚠ CORS headers not set - may cause issues if dashboard on different domain")
                else:
                    logger.info("✓ CORS headers present")
                    
        except Exception as e:
            logger.error(f"Error checking CORS: {e}")

async def main():
    """Run all tests."""
    logger.info("Mobile Dashboard JavaScript Simulation Test")
    logger.info("=" * 50)
    await test_mobile_data_flow()
    logger.info("\n" + "=" * 50)
    logger.info("Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
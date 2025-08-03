#!/usr/bin/env python3
"""Test script to diagnose confluence score issues in mobile dashboard."""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8003"

async def test_mobile_data_endpoint():
    """Test the mobile-data endpoint."""
    logger.info("Testing /api/dashboard/mobile-data endpoint...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/mobile-data") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Response status: {data.get('status', 'unknown')}")
                    
                    # Check confluence scores
                    confluence_scores = data.get('confluence_scores', [])
                    logger.info(f"Number of confluence scores: {len(confluence_scores)}")
                    
                    if confluence_scores:
                        logger.info("Sample confluence scores:")
                        for i, score in enumerate(confluence_scores[:3]):
                            logger.info(f"  {i+1}. {score.get('symbol', 'N/A')}: {score.get('score', 0)}")
                            components = score.get('components', {})
                            if components:
                                logger.info(f"     Components: {json.dumps(components, indent=6)}")
                    else:
                        logger.warning("No confluence scores found in response!")
                    
                    # Check market overview
                    market_overview = data.get('market_overview', {})
                    logger.info(f"Market overview: {json.dumps(market_overview, indent=2)}")
                    
                    # Check top movers
                    top_movers = data.get('top_movers', {})
                    logger.info(f"Top gainers: {len(top_movers.get('gainers', []))}")
                    logger.info(f"Top losers: {len(top_movers.get('losers', []))}")
                    
                else:
                    logger.error(f"Error response: {response.status}")
                    text = await response.text()
                    logger.error(f"Response body: {text}")
                    
        except Exception as e:
            logger.error(f"Error testing mobile-data endpoint: {e}")

async def test_direct_endpoint():
    """Test the mobile-data-direct endpoint."""
    logger.info("\nTesting /api/dashboard/mobile-data-direct endpoint...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/mobile-data-direct") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Response status: {data.get('status', 'unknown')}")
                    
                    # Check confluence scores
                    confluence_scores = data.get('confluence_scores', [])
                    logger.info(f"Number of confluence scores: {len(confluence_scores)}")
                    
                    if confluence_scores:
                        logger.info("Sample confluence scores from direct endpoint:")
                        for i, score in enumerate(confluence_scores[:3]):
                            logger.info(f"  {i+1}. {score.get('symbol', 'N/A')}: {score.get('score', 0)}")
                    else:
                        logger.warning("No confluence scores found in direct response!")
                        
                else:
                    logger.error(f"Error response: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error testing direct endpoint: {e}")

async def test_confluence_scores_endpoint():
    """Test the confluence-scores endpoint."""
    logger.info("\nTesting /api/dashboard/confluence-scores endpoint...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/confluence-scores") as response:
                if response.status == 200:
                    data = await response.json()
                    scores = data.get('scores', [])
                    logger.info(f"Number of scores: {data.get('count', 0)}")
                    
                    if scores:
                        logger.info("Confluence scores with components:")
                        for score in scores[:3]:
                            logger.info(f"  {score.get('symbol', 'N/A')}: {score.get('score', 0)}")
                            logger.info(f"    Components: {json.dumps(score.get('components', {}), indent=6)}")
                    else:
                        logger.warning("No scores found!")
                        
                else:
                    logger.error(f"Error response: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error testing confluence-scores endpoint: {e}")

async def test_dashboard_overview():
    """Test the dashboard overview endpoint."""
    logger.info("\nTesting /api/dashboard/overview endpoint...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/overview") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Dashboard status: {data.get('status', 'unknown')}")
                    logger.info(f"Signals: {json.dumps(data.get('signals', {}), indent=2)}")
                    logger.info(f"System status: {json.dumps(data.get('system_status', {}), indent=2)}")
                else:
                    logger.error(f"Error response: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error testing overview endpoint: {e}")

async def test_debug_components():
    """Test the debug-components endpoint."""
    logger.info("\nTesting /api/dashboard/debug-components endpoint...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/debug-components") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Available components: {data.get('available_components', [])}")
                    logger.info(f"Has integration: {data.get('has_integration', False)}")
                    logger.info(f"Has dashboard data: {data.get('has_dashboard_data', False)}")
                    logger.info(f"Signal count: {data.get('signal_count', 0)}")
                else:
                    logger.error(f"Error response: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error testing debug-components endpoint: {e}")

async def main():
    """Run all tests."""
    logger.info("Starting confluence score diagnostic tests...")
    logger.info(f"Testing against: {BASE_URL}")
    logger.info("=" * 60)
    
    # Run all tests
    await test_dashboard_overview()
    await test_mobile_data_endpoint()
    await test_direct_endpoint()
    await test_confluence_scores_endpoint()
    await test_debug_components()
    
    logger.info("=" * 60)
    logger.info("Diagnostic tests completed.")

if __name__ == "__main__":
    asyncio.run(main())
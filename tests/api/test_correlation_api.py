#!/usr/bin/env python3
"""
Test script for the Correlation API endpoints.
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CorrelationAPITester:
    """Test the correlation API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    async def test_all_endpoints(self):
        """Test all correlation API endpoints."""
        endpoints = [
            "/api/correlation/matrix",
            "/api/correlation/signal-correlations", 
            "/api/correlation/asset-correlations",
            "/api/correlation/heatmap-data",
            "/api/correlation/live-matrix"
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                await self.test_endpoint(session, endpoint)
    
    async def test_endpoint(self, session: aiohttp.ClientSession, endpoint: str):
        """Test a specific endpoint."""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing endpoint: {endpoint}")
            logger.info(f"{'='*60}")
            
            url = f"{self.base_url}{endpoint}"
            
            async with session.get(url) as response:
                status = response.status
                data = await response.json()
                
                logger.info(f"Status: {status}")
                logger.info(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                if status == 200:
                    self.analyze_response(endpoint, data)
                else:
                    logger.error(f"Error response: {data}")
                    
        except Exception as e:
            logger.error(f"Error testing {endpoint}: {e}")
    
    def analyze_response(self, endpoint: str, data: Dict[str, Any]):
        """Analyze the response data."""
        try:
            if "/matrix" in endpoint:
                matrix_data = data.get("matrix_data", {})
                logger.info(f"Matrix symbols: {len(matrix_data)}")
                
                if matrix_data:
                    first_symbol = next(iter(matrix_data.keys()))
                    signal_types = list(matrix_data[first_symbol].keys())
                    logger.info(f"Signal types: {signal_types}")
                    
                    # Show sample data
                    if len(signal_types) > 0:
                        sample_signal = signal_types[0]
                        sample_data = matrix_data[first_symbol][sample_signal]
                        logger.info(f"Sample signal data: {sample_data}")
            
            elif "/correlations" in endpoint:
                correlations = data.get("signal_correlations", data.get("asset_correlations", {}))
                logger.info(f"Correlation matrix size: {len(correlations)}")
                
                if correlations:
                    # Show correlation strength
                    stats = data.get("statistics", {})
                    if stats:
                        logger.info(f"Correlation stats: {stats}")
            
            elif "/heatmap" in endpoint:
                matrix = data.get("correlation_matrix", [])
                labels = data.get("labels", [])
                logger.info(f"Heatmap dimensions: {len(matrix)}x{len(matrix[0]) if matrix else 0}")
                logger.info(f"Labels: {labels}")
            
            elif "/live-matrix" in endpoint:
                live_matrix = data.get("live_matrix", {})
                performance = data.get("performance_metrics", {})
                logger.info(f"Live matrix symbols: {len(live_matrix)}")
                logger.info(f"Performance metrics: {performance}")
                
        except Exception as e:
            logger.error(f"Error analyzing response: {e}")

async def main():
    """Main test function."""
    tester = CorrelationAPITester()
    
    logger.info("🚀 Starting Correlation API Tests")
    logger.info("Make sure the Virtuoso server is running on localhost:8000")
    
    await tester.test_all_endpoints()
    
    logger.info("\n✅ Correlation API tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 
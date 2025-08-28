#!/usr/bin/env python3
"""
Test script to verify enhanced API integration
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timezone

async def test_enhanced_endpoints():
    """Test the enhanced API endpoints"""
    
    base_url = "http://localhost:8000"
    endpoints = [
        "/api/enhanced/health",
        "/api/enhanced/metrics", 
        "/api/enhanced/status"
    ]
    
    async with aiohttp.ClientSession() as session:
        print("Testing Enhanced API Endpoints")
        print("=" * 50)
        
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            print(f"\n📍 Testing: {url}")
            
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    status = response.status
                    data = await response.json()
                    
                    if status == 200:
                        print(f"✅ Status: {status}")
                        print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
                    else:
                        print(f"⚠️ Status: {status}")
                        print(f"   Response: {data}")
                        
            except aiohttp.ClientError as e:
                print(f"❌ Connection error: {e}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n" + "=" * 50)
        print("Enhanced API Integration Test Complete")
        
        # Test standard endpoints too
        print("\nTesting Standard Endpoints:")
        standard_endpoints = [
            "/api/health",
            "/docs"
        ]
        
        for endpoint in standard_endpoints:
            url = f"{base_url}{endpoint}"
            print(f"\n📍 Testing: {url}")
            
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    status = response.status
                    print(f"{'✅' if status == 200 else '⚠️'} Status: {status}")
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    print(f"🚀 Starting Enhanced API Integration Test")
    print(f"⏰ Time: {datetime.now(timezone.utc).isoformat()}")
    
    asyncio.run(test_enhanced_endpoints())
#!/usr/bin/env python3
"""Test the /health endpoint to verify it handles errors gracefully."""

import asyncio
import aiohttp
import json
import sys

async def test_health_endpoint(port=8000):
    """Test the health endpoint."""
    url = f"http://localhost:{port}/health"
    
    print(f"Testing health endpoint at {url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                status = response.status
                data = await response.json()
                
                print(f"\nStatus Code: {status}")
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if status == 200:
                    print("\n✅ Health check returned 200 OK")
                    if data.get('status') == 'healthy':
                        print("   All components are healthy")
                    elif data.get('status') == 'degraded':
                        print("   System is degraded but operational")
                        if 'unhealthy_components' in data:
                            print(f"   Unhealthy components: {', '.join(data['unhealthy_components'])}")
                elif status == 503:
                    print("\n⚠️  Health check returned 503 Service Unavailable")
                    print("   System is unhealthy")
                elif status == 500:
                    print("\n❌ Health check returned 500 Internal Server Error")
                    print("   This should not happen with the fixed implementation!")
                else:
                    print(f"\n❓ Unexpected status code: {status}")
                    
        except aiohttp.ClientConnectorError:
            print(f"\n❌ Could not connect to {url}")
            print("   Make sure the application is running")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error testing health endpoint: {e}")
            sys.exit(1)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    asyncio.run(test_health_endpoint(port))
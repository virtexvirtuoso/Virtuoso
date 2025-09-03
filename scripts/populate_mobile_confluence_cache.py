#!/usr/bin/env python3
"""Direct API call to populate confluence cache through internal endpoint."""

import requests
import json
import time

def populate_confluence_cache_via_api():
    """Populate confluence cache by making internal API calls to trigger caching."""
    
    # Make a call to the mobile-data endpoint to see current state
    print("🔍 Testing current mobile-data endpoint...")
    
    try:
        response = requests.get('http://localhost:8003/api/dashboard/mobile-data', timeout=10)
        if response.status_code == 200:
            data = response.json()
            current_count = len(data.get('confluence_scores', []))
            print(f"📊 Current confluence scores: {current_count}")
            
            if current_count == 0:
                print("⚠️ No confluence scores found - this is the issue we're fixing")
                
                # Create manual cache entries using requests to an internal endpoint
                # We'll add this endpoint to the service
                print("🔧 Attempting to populate cache via internal mechanisms...")
                
                # Since the service has aiomcache working, let's trigger analysis
                # by making calls that should populate the cache
                
                # First, try to access confluence analysis for specific symbols
                test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
                
                for symbol in test_symbols:
                    try:
                        # Try the confluence analysis endpoint if it exists
                        conf_url = f'http://localhost:8003/api/dashboard/confluence-analysis/{symbol}'
                        conf_response = requests.get(conf_url, timeout=5)
                        print(f"📊 Confluence analysis for {symbol}: {conf_response.status_code}")
                        
                        if conf_response.status_code == 200:
                            conf_data = conf_response.json()
                            print(f"   Analysis data: {list(conf_data.keys())}")
                    except Exception as e:
                        print(f"   Error for {symbol}: {e}")
                
            else:
                print(f"✅ Found {current_count} confluence scores - cache is working!")
                
        else:
            print(f"❌ Mobile endpoint returned status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing mobile endpoint: {e}")
    
    # Test accessing the endpoint multiple times to see if cache populates
    print("\n🔄 Testing cache population over time...")
    for i in range(3):
        try:
            time.sleep(5)  # Wait 5 seconds
            response = requests.get('http://localhost:8003/api/dashboard/mobile-data', timeout=10)
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('confluence_scores', []))
                print(f"Attempt {i+1}: {count} confluence scores")
            else:
                print(f"Attempt {i+1}: HTTP {response.status_code}")
        except Exception as e:
            print(f"Attempt {i+1}: Error - {e}")

if __name__ == "__main__":
    print("🚀 Starting confluence cache population test...")
    populate_confluence_cache_via_api()
    print("✅ Cache population test completed")
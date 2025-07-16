#!/usr/bin/env python3
"""
Test script to validate all contango API endpoints.
Shows examples of how to use each endpoint for different use cases.
"""

import asyncio
import aiohttp
import json
import time

class ContangoAPITester:
    """Test all contango API endpoints"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        
    async def test_all_endpoints(self):
        """Test all contango API endpoints"""
        print("🧪 TESTING CONTANGO API ENDPOINTS")
        print("=" * 60)
        
        endpoints = [
            {
                "name": "Comprehensive Futures Premium Analysis",
                "url": f"{self.base_url}/api/market/futures-premium",
                "params": {"symbols": "BTC/USDT,ETH/USDT,SOL/USDT"},
                "description": "Multi-symbol analysis with detailed breakdown"
            },
            {
                "name": "Quick Contango Status (Dashboard)",
                "url": f"{self.base_url}/api/market/contango-status",
                "params": {},
                "description": "Simplified status for dashboard widgets"
            },
            {
                "name": "Term Structure Analysis",
                "url": f"{self.base_url}/api/market/term-structure",
                "params": {"symbol": "BTC/USDT"},
                "description": "Advanced term structure for trading insights"
            },
                         {
                 "name": "Individual Symbol Analysis",
                 "url": f"{self.base_url}/api/market/futures-premium/BTCUSDT",
                 "params": {},
                 "description": "Single symbol contango analysis"
             },
             {
                 "name": "COMPREHENSIVE Symbol Analysis",
                 "url": f"{self.base_url}/api/market/analysis/BTCUSDT",
                 "params": {"exchange_id": "bybit"},
                 "description": "Complete symbol analysis - ALL DATA IN ONE ENDPOINT (NEW!)"
             }
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                await self.test_endpoint(session, endpoint)
                
    async def test_endpoint(self, session, endpoint):
        """Test a single endpoint"""
        print(f"\n🔗 TESTING: {endpoint['name']}")
        print(f"📋 Description: {endpoint['description']}")
        print(f"🌐 URL: {endpoint['url']}")
        
        try:
            async with session.get(endpoint['url'], params=endpoint['params'], timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Status: {response.status} OK")
                    
                    # Show key fields from response
                    if 'contango_status' in data:
                        print(f"📊 Contango Status: {data['contango_status']}")
                    if 'contango_analysis' in data:
                        analysis = data['contango_analysis']
                        print(f"📊 Premium: {analysis.get('spot_premium', 'N/A')}")
                        print(f"📊 Status: {analysis.get('contango_status', 'N/A')}")
                    if 'data' in data and 'contango_status' in data['data']:
                        print(f"📊 Market Status: {data['data']['contango_status']}")
                        print(f"📊 Average Premium: {data['data'].get('average_premium', 'N/A')}")
                                         if 'display' in data:
                         display = data['display']
                         print(f"🎨 Display: {display.get('badge_text', 'N/A')}")
                     if 'summary' in data:
                         summary = data['summary']
                         print(f"📊 Summary: {summary.get('price', 'N/A')} ({summary.get('price_change', 'N/A')})")
                         print(f"🎯 Risk Level: {summary.get('risk_level', 'N/A')}")
                     if 'metadata' in data:
                         metadata = data['metadata']
                         print(f"📈 Data Completeness: {metadata.get('analysis_completeness', 0):.1f}%")
                         print(f"🔄 Data Sources: {metadata.get('data_sources_count', 0)}/5")
                        
                elif response.status == 503:
                    print(f"⚠️  Status: {response.status} - Service Unavailable (API server not running)")
                else:
                    print(f"❌ Status: {response.status}")
                    
        except aiohttp.ClientConnectorError:
            print(f"❌ Connection Error: API server not running at {self.base_url}")
        except Exception as e:
            print(f"❌ Error: {e}")
            
    def print_usage_examples(self):
        """Print usage examples for each endpoint"""
        print("\n📖 CONTANGO API USAGE EXAMPLES")
        print("=" * 60)
        
        examples = [
            {
                "use_case": "Dashboard Widget (Quick Status)",
                "endpoint": "GET /api/market/contango-status",
                "curl": "curl 'http://localhost:8000/api/market/contango-status'",
                "response_example": {
                    "contango_status": "BACKWARDATION",
                    "market_sentiment": "BEARISH_POSITIONING",
                    "display": {"emoji": "📉", "badge_text": "📉 BACKWARDATION"}
                }
            },
            {
                "use_case": "Single Symbol Analysis",
                "endpoint": "GET /api/market/futures-premium/{symbol}",
                "curl": "curl 'http://localhost:8000/api/market/futures-premium/BTCUSDT'",
                "response_example": {
                    "contango_analysis": {
                        "spot_premium": "-0.0451%",
                        "contango_status": "NEUTRAL"
                    },
                    "alerts": {"has_alerts": False}
                }
            },
            {
                "use_case": "Multi-Symbol Analysis",
                "endpoint": "GET /api/market/futures-premium",
                "curl": "curl 'http://localhost:8000/api/market/futures-premium?symbols=BTC/USDT,ETH/USDT'",
                "response_example": {
                    "data": {
                        "average_premium": "-0.0471%",
                        "contango_status": "NEUTRAL"
                    }
                }
                         },
             {
                 "use_case": "Advanced Trading Analysis",
                 "endpoint": "GET /api/market/term-structure",
                 "curl": "curl 'http://localhost:8000/api/market/term-structure?symbol=BTC/USDT'",
                 "response_example": {
                     "analysis": {
                         "market_structure": "NEUTRAL",
                         "funding_pressure": 0.01
                     }
                 }
             },
             {
                 "use_case": "COMPREHENSIVE Symbol Analysis (ALL-IN-ONE)",
                 "endpoint": "GET /api/market/analysis/{symbol}",
                 "curl": "curl 'http://localhost:8000/api/market/analysis/BTCUSDT?exchange_id=bybit'",
                 "response_example": {
                     "analysis": {
                         "market_data": {"price": 107876.90, "price_change_percent_24h": -0.5},
                         "contango": {"contango_status": "NEUTRAL", "spot_premium": "-0.0451%"},
                         "orderbook": {"volume_imbalance": 5.2},
                         "risk_assessment": {"risk_level": "LOW"}
                     },
                     "summary": {"price": "$107,876.90", "risk_level": "LOW"},
                     "metadata": {"analysis_completeness": 80.0}
                 }
             }
        ]
        
        for example in examples:
            print(f"\n🎯 USE CASE: {example['use_case']}")
            print(f"🔗 Endpoint: {example['endpoint']}")
            print(f"💻 cURL: {example['curl']}")
            print(f"📝 Example Response:")
            print(json.dumps(example['response_example'], indent=2))

async def main():
    """Main test runner"""
    tester = ContangoAPITester()
    
    # Test all endpoints (will show connection errors if server not running)
    await tester.test_all_endpoints()
    
    # Show usage examples regardless of server status
    tester.print_usage_examples()
    
    print(f"\n🚀 SUMMARY: COMPLETE CONTANGO API COVERAGE")
    print("=" * 60)
         print("✅ 5 endpoints available for different use cases:")
     print("   📊 Multi-symbol analysis: /api/market/futures-premium")
     print("   🎯 Single symbol analysis: /api/market/futures-premium/{symbol}")
     print("   🚀 Dashboard status: /api/market/contango-status")
     print("   📈 Advanced analysis: /api/market/term-structure")
     print("   🌟 COMPREHENSIVE analysis: /api/market/analysis/{symbol} (ALL-IN-ONE!)")
    print("\n🌐 Start API server with: PYTHONPATH=src python3 -m uvicorn api.main:app --port 8000")

if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python3
"""
Test the resilience mechanisms with simulated failures.
"""

import asyncio
import aiohttp
import sys
import time
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_health_endpoints():
    """Test the health check endpoints."""
    print("\n" + "=" * 60)
    print("🏥 Testing Health Check Endpoints")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test system health endpoint
        try:
            async with session.get("http://localhost:8001/api/health/system") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print("\n✅ System Health Endpoint:")
                    print(f"  Status: {data.get('status')}")
                    print(f"  CPU: {data.get('system', {}).get('cpu_percent')}%")
                    print(f"  Memory: {data.get('system', {}).get('memory_percent')}%")
                    print(f"  Services: {json.dumps(data.get('services', {}), indent=2)}")
                else:
                    print(f"❌ System health endpoint returned {resp.status}")
        except Exception as e:
            print(f"❌ System health endpoint error: {e}")
        
        # Test resilience health endpoint
        try:
            async with session.get("http://localhost:8001/api/health/resilience") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print("\n✅ Resilience Health Endpoint:")
                    print(f"  Status: {data.get('status')}")
                    
                    breakers = data.get('circuit_breakers', {})
                    if breakers:
                        print("  Circuit Breakers:")
                        for name, state in breakers.items():
                            print(f"    - {name}: {state.get('state')} (failures: {state.get('failure_count')})")
                    
                    fallback = data.get('fallback_system', {})
                    if fallback:
                        print(f"  Fallback Cache: {fallback.get('cached_files')} files")
                else:
                    print(f"❌ Resilience health endpoint returned {resp.status}")
        except Exception as e:
            print(f"❌ Resilience health endpoint error: {e}")


async def test_ticker_with_failures():
    """Test ticker endpoint with simulated failures."""
    print("\n" + "=" * 60)
    print("🔧 Testing Ticker Endpoint Resilience")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test normal operation
        print("\n1️⃣ Testing normal operation...")
        try:
            async with session.get("http://localhost:8001/api/market/ticker/BTCUSDT") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Normal ticker response: {data.get('symbol')} @ ${data.get('price')}")
                    print(f"   Status: {data.get('status')}")
                else:
                    print(f"⚠️ Ticker returned {resp.status}")
        except Exception as e:
            print(f"❌ Ticker error: {e}")
        
        # Simulate multiple failures to trigger circuit breaker
        print("\n2️⃣ Simulating multiple failures...")
        for i in range(5):
            try:
                # Use an invalid symbol to trigger failures
                async with session.get("http://localhost:8001/api/market/ticker/INVALID_SYMBOL_XXX") as resp:
                    print(f"   Attempt {i+1}: Status {resp.status}")
                    await asyncio.sleep(0.5)
            except:
                pass
        
        # Check if circuit breaker is open
        print("\n3️⃣ Checking circuit breaker state...")
        try:
            async with session.get("http://localhost:8001/api/health/resilience") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    breakers = data.get('circuit_breakers', {})
                    for name, state in breakers.items():
                        if 'ticker' in name:
                            print(f"✅ Circuit breaker '{name}': {state.get('state')}")
        except Exception as e:
            print(f"❌ Could not check circuit state: {e}")
        
        # Test fallback mechanism
        print("\n4️⃣ Testing fallback mechanism...")
        try:
            async with session.get("http://localhost:8001/api/market/ticker/ETHUSDT") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('status') in ['cached', 'fallback']:
                        print(f"✅ Fallback active: {data.get('symbol')} using {data.get('status')} data")
                    else:
                        print(f"📊 Got live data: {data.get('symbol')} @ ${data.get('price')}")
                else:
                    print(f"⚠️ Ticker returned {resp.status}")
        except Exception as e:
            print(f"❌ Ticker error: {e}")


async def test_dashboard_resilience():
    """Test dashboard endpoints with degraded service."""
    print("\n" + "=" * 60)
    print("📊 Testing Dashboard Resilience")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test dashboard overview
        print("\n1️⃣ Testing dashboard overview...")
        try:
            async with session.get("http://localhost:8001/api/dashboard/overview") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get('status')
                    if status == 'degraded':
                        print(f"✅ Dashboard in degraded mode (expected)")
                        print(f"   Message: {data.get('message')}")
                    elif status in ['initializing', 'error']:
                        print(f"⚠️ Dashboard status: {status}")
                        print(f"   Message: {data.get('message')}")
                    else:
                        print(f"✅ Dashboard operational: {status}")
                else:
                    print(f"❌ Dashboard overview returned {resp.status}")
        except Exception as e:
            print(f"❌ Dashboard overview error: {e}")
        
        # Test symbols endpoint
        print("\n2️⃣ Testing symbols endpoint...")
        try:
            async with session.get("http://localhost:8001/api/dashboard/symbols") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    symbols = data.get('symbols', [])
                    if symbols:
                        print(f"✅ Got {len(symbols)} symbols")
                        for sym in symbols[:3]:
                            print(f"   - {sym.get('symbol')}: Score {sym.get('confluence_score')}")
                    else:
                        print("⚠️ No symbols returned (may be using fallback)")
                else:
                    print(f"❌ Symbols endpoint returned {resp.status}")
        except Exception as e:
            print(f"❌ Symbols endpoint error: {e}")


async def simulate_recovery():
    """Simulate recovery after circuit breaker timeout."""
    print("\n" + "=" * 60)
    print("🔄 Testing Recovery Mechanism")
    print("=" * 60)
    
    print("\nWaiting 30 seconds for circuit breaker recovery timeout...")
    for i in range(30, 0, -5):
        print(f"  {i} seconds remaining...")
        await asyncio.sleep(5)
    
    async with aiohttp.ClientSession() as session:
        # Check circuit breaker state after timeout
        print("\n1️⃣ Checking circuit breaker state after timeout...")
        try:
            async with session.get("http://localhost:8001/api/health/resilience") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    breakers = data.get('circuit_breakers', {})
                    for name, state in breakers.items():
                        status = state.get('state')
                        if status == 'half_open':
                            print(f"✅ Circuit '{name}' in HALF_OPEN state (testing recovery)")
                        elif status == 'closed':
                            print(f"✅ Circuit '{name}' CLOSED (recovered)")
                        else:
                            print(f"⚠️ Circuit '{name}' still {status}")
        except Exception as e:
            print(f"❌ Could not check circuit state: {e}")
        
        # Test normal operation after recovery
        print("\n2️⃣ Testing normal operation after recovery...")
        try:
            async with session.get("http://localhost:8001/api/market/ticker/BTCUSDT") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('status') == 'success':
                        print(f"✅ Service recovered: {data.get('symbol')} @ ${data.get('price')}")
                    else:
                        print(f"⚠️ Still using fallback: {data.get('status')}")
                else:
                    print(f"❌ Ticker returned {resp.status}")
        except Exception as e:
            print(f"❌ Ticker error: {e}")


async def main():
    """Main test execution."""
    print("=" * 60)
    print("🚀 Resilience Testing Suite")
    print("=" * 60)
    print("\nThis will test the resilience mechanisms:")
    print("- Circuit breakers")
    print("- Fallback data providers")
    print("- Health check endpoints")
    print("- Recovery mechanisms")
    
    # Run tests
    await test_health_endpoints()
    await test_ticker_with_failures()
    await test_dashboard_resilience()
    
    # Optional: Test recovery
    print("\n" + "=" * 60)
    print("Would you like to test the recovery mechanism?")
    print("This will wait 30 seconds for circuit breaker timeout.")
    print("=" * 60)
    
    response = input("Test recovery? (y/n): ").strip().lower()
    if response == 'y':
        await simulate_recovery()
    
    print("\n" + "=" * 60)
    print("✅ Resilience Testing Complete!")
    print("=" * 60)
    print("\n📝 Summary:")
    print("- Health endpoints provide system status without external dependencies")
    print("- Circuit breakers protect against cascading failures")
    print("- Fallback mechanisms provide degraded service when APIs fail")
    print("- Recovery mechanisms automatically restore service")


if __name__ == "__main__":
    asyncio.run(main())
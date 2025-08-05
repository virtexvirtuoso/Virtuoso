#!/usr/bin/env python3
"""
Test Bybit API endpoints directly to diagnose timeout issues
"""
import asyncio
import aiohttp
import time
import json
from datetime import datetime

class BybitAPITester:
    def __init__(self):
        self.base_url = "https://api.bybit.com"
        self.endpoints = [
            ("/v5/market/tickers", {"category": "linear", "symbol": "BTCUSDT"}),
            ("/v5/market/tickers", {"category": "linear", "symbol": "ETHUSDT"}),
            ("/v5/market/tickers", {"category": "linear", "symbol": "SUIUSDT"}),
            ("/v5/market/kline", {"category": "linear", "symbol": "BTCUSDT", "interval": "5", "limit": "200"}),
            ("/v5/market/orderbook/L2", {"category": "linear", "symbol": "BTCUSDT", "limit": "25"}),
            ("/v5/market/recent-trade", {"category": "linear", "symbol": "BTCUSDT", "limit": "20"}),
        ]
        
    async def test_endpoint(self, session, endpoint, params, timeout_seconds):
        """Test a single endpoint with specified timeout"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            async with session.get(url, params=params, timeout=timeout) as response:
                data = await response.json()
                elapsed = time.time() - start_time
                
                return {
                    "endpoint": endpoint,
                    "params": params,
                    "status": "success",
                    "status_code": response.status,
                    "elapsed": elapsed,
                    "ret_code": data.get("retCode", "N/A"),
                    "ret_msg": data.get("retMsg", "N/A"),
                    "data_size": len(json.dumps(data))
                }
                
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            return {
                "endpoint": endpoint,
                "params": params,
                "status": "timeout",
                "elapsed": elapsed,
                "timeout": timeout_seconds
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "endpoint": endpoint,
                "params": params,
                "status": "error",
                "elapsed": elapsed,
                "error": str(e)
            }
    
    async def test_with_different_timeouts(self):
        """Test endpoints with various timeout settings"""
        timeout_configs = [
            {"name": "aggressive", "timeout": 5, "connector_settings": {"limit": 10, "force_close": False}},
            {"name": "moderate", "timeout": 10, "connector_settings": {"limit": 20, "force_close": False}},
            {"name": "relaxed", "timeout": 15, "connector_settings": {"limit": 30, "force_close": False}},
            {"name": "patient", "timeout": 30, "connector_settings": {"limit": 50, "force_close": False}},
        ]
        
        results = []
        
        for config in timeout_configs:
            print(f"\n{'='*60}")
            print(f"Testing with {config['name']} timeout: {config['timeout']}s")
            print(f"{'='*60}")
            
            connector = aiohttp.TCPConnector(
                limit=config['connector_settings']['limit'],
                force_close=config['connector_settings']['force_close'],
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30
            )
            
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = []
                for endpoint, params in self.endpoints:
                    task = self.test_endpoint(session, endpoint, params, config['timeout'])
                    tasks.append(task)
                
                endpoint_results = await asyncio.gather(*tasks)
                
                config_result = {
                    "config": config['name'],
                    "timeout": config['timeout'],
                    "results": endpoint_results
                }
                results.append(config_result)
                
                # Print summary
                for result in endpoint_results:
                    status = result['status']
                    elapsed = result['elapsed']
                    endpoint = result['endpoint']
                    symbol = result['params'].get('symbol', 'N/A')
                    
                    status_emoji = "✅" if status == "success" else "❌"
                    print(f"{status_emoji} {endpoint} ({symbol}): {elapsed:.2f}s - {status}")
        
        return results
    
    async def test_concurrent_requests(self):
        """Test how concurrent requests affect response times"""
        print(f"\n{'='*60}")
        print("Testing concurrent request patterns")
        print(f"{'='*60}")
        
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            force_close=False,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Test 1: Sequential requests
            print("\n1. Sequential requests (baseline):")
            sequential_times = []
            for endpoint, params in self.endpoints[:3]:
                result = await self.test_endpoint(session, endpoint, params, 10)
                sequential_times.append(result['elapsed'])
                print(f"   {endpoint}: {result['elapsed']:.2f}s")
            
            # Test 2: Concurrent requests
            print("\n2. Concurrent requests (parallel):")
            tasks = []
            for endpoint, params in self.endpoints[:3]:
                task = self.test_endpoint(session, endpoint, params, 10)
                tasks.append(task)
            
            concurrent_results = await asyncio.gather(*tasks)
            for result in concurrent_results:
                print(f"   {result['endpoint']}: {result['elapsed']:.2f}s")
            
            # Test 3: Burst requests (simulate high load)
            print("\n3. Burst requests (10 concurrent to same endpoint):")
            burst_tasks = []
            endpoint, params = self.endpoints[0]  # Use tickers endpoint
            for _ in range(10):
                task = self.test_endpoint(session, endpoint, params, 10)
                burst_tasks.append(task)
            
            burst_results = await asyncio.gather(*burst_tasks)
            burst_times = [r['elapsed'] for r in burst_results]
            print(f"   Min: {min(burst_times):.2f}s, Max: {max(burst_times):.2f}s, Avg: {sum(burst_times)/len(burst_times):.2f}s")
            
    async def run_tests(self):
        """Run all tests"""
        print(f"Bybit API Direct Test - {datetime.now()}")
        print(f"Testing from local environment to diagnose timeout issues")
        
        # Test different timeout configurations
        timeout_results = await self.test_with_different_timeouts()
        
        # Test concurrent request patterns
        await self.test_concurrent_requests()
        
        # Analyze results
        print(f"\n{'='*60}")
        print("ANALYSIS AND RECOMMENDATIONS")
        print(f"{'='*60}")
        
        # Find optimal timeout
        successful_configs = []
        for config_result in timeout_results:
            success_count = sum(1 for r in config_result['results'] if r['status'] == 'success')
            total_count = len(config_result['results'])
            success_rate = success_count / total_count * 100
            
            if success_rate >= 90:
                successful_configs.append({
                    'name': config_result['config'],
                    'timeout': config_result['timeout'],
                    'success_rate': success_rate
                })
        
        if successful_configs:
            optimal = min(successful_configs, key=lambda x: x['timeout'])
            print(f"\n✅ Recommended timeout: {optimal['timeout']}s ({optimal['name']})")
            print(f"   Success rate: {optimal['success_rate']:.1f}%")
        else:
            print("\n⚠️  No configuration achieved 90%+ success rate")
            print("   Consider implementing retry logic and circuit breakers")
        
        # Identify problematic endpoints
        print("\n📊 Endpoint Performance Summary:")
        endpoint_times = {}
        for config_result in timeout_results:
            for result in config_result['results']:
                endpoint = result['endpoint']
                if endpoint not in endpoint_times:
                    endpoint_times[endpoint] = []
                if result['status'] == 'success':
                    endpoint_times[endpoint].append(result['elapsed'])
        
        for endpoint, times in endpoint_times.items():
            if times:
                avg_time = sum(times) / len(times)
                print(f"   {endpoint}: avg {avg_time:.2f}s")
                if avg_time > 5:
                    print(f"      ⚠️  Consider caching or reducing frequency")

if __name__ == "__main__":
    tester = BybitAPITester()
    asyncio.run(tester.run_tests())
#!/usr/bin/env python3
"""
Comprehensive debug script to understand Bybit timeout root causes
"""

import asyncio
import aiohttp
import time
import json
import traceback
import socket
import ssl
from datetime import datetime
from typing import Dict, List, Any

class BybitDebugger:
    def __init__(self):
        self.base_url = "https://api.bybit.com"
        self.results = []
        self.timeout_patterns = {}
        
    async def test_dns_resolution(self):
        """Test DNS resolution speed and results"""
        print("\n" + "="*60)
        print("1. DNS RESOLUTION TEST")
        print("="*60)
        
        try:
            start = time.time()
            # Get IP addresses
            result = socket.getaddrinfo('api.bybit.com', 443, socket.AF_INET)
            dns_time = time.time() - start
            
            ips = list(set([r[4][0] for r in result]))
            print(f"✅ DNS Resolution Time: {dns_time:.3f}s")
            print(f"   Resolved IPs: {', '.join(ips)}")
            
            # Test reverse DNS
            for ip in ips[:1]:  # Test first IP
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                    print(f"   Reverse DNS: {ip} -> {hostname}")
                except:
                    print(f"   Reverse DNS: {ip} -> (failed)")
                    
            return {"success": True, "dns_time": dns_time, "ips": ips}
        except Exception as e:
            print(f"❌ DNS Resolution Failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_ssl_handshake(self):
        """Test SSL/TLS handshake"""
        print("\n" + "="*60)
        print("2. SSL/TLS HANDSHAKE TEST")
        print("="*60)
        
        try:
            context = ssl.create_default_context()
            
            start = time.time()
            reader, writer = await asyncio.open_connection(
                'api.bybit.com', 443, ssl=context
            )
            ssl_time = time.time() - start
            
            # Get SSL info
            ssl_obj = writer.get_extra_info('ssl_object')
            if ssl_obj:
                print(f"✅ SSL Handshake Time: {ssl_time:.3f}s")
                print(f"   Protocol: {ssl_obj.version()}")
                print(f"   Cipher: {ssl_obj.cipher()}")
            
            writer.close()
            await writer.wait_closed()
            
            return {"success": True, "ssl_time": ssl_time}
        except Exception as e:
            print(f"❌ SSL Handshake Failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_connection_pooling(self):
        """Test connection pool behavior"""
        print("\n" + "="*60)
        print("3. CONNECTION POOL BEHAVIOR TEST")
        print("="*60)
        
        # Test with different pool configurations
        configs = [
            {"limit": 10, "limit_per_host": 5, "name": "Conservative"},
            {"limit": 50, "limit_per_host": 20, "name": "Moderate"},
            {"limit": 100, "limit_per_host": 50, "name": "Aggressive"},
        ]
        
        results = []
        for config in configs:
            connector = aiohttp.TCPConnector(
                limit=config["limit"],
                limit_per_host=config["limit_per_host"],
                force_close=True,
                enable_cleanup_closed=True
            )
            
            async with aiohttp.ClientSession(connector=connector) as session:
                print(f"\nTesting {config['name']} config (limit={config['limit']}, per_host={config['limit_per_host']}):")
                
                # Make parallel requests
                tasks = []
                for i in range(5):
                    url = f"{self.base_url}/v5/market/tickers"
                    params = {"category": "linear", "symbol": "BTCUSDT"}
                    tasks.append(self._timed_request(session, url, params, f"Request {i+1}"))
                
                start = time.time()
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                total_time = time.time() - start
                
                success_count = sum(1 for r in responses if isinstance(r, dict) and r.get("success"))
                print(f"   Total Time: {total_time:.2f}s")
                print(f"   Success Rate: {success_count}/5")
                
                # Check connector stats
                print(f"   Connector Stats:")
                print(f"     - Limit: {connector.limit}")
                print(f"     - Limit per host: {connector.limit_per_host}")
                # print(f"     - Connections: (not available in this version)")
                
                results.append({
                    "config": config["name"],
                    "total_time": total_time,
                    "success_rate": f"{success_count}/5"
                })
        
        return results
    
    async def test_endpoint_performance(self):
        """Test individual endpoint performance"""
        print("\n" + "="*60)
        print("4. ENDPOINT PERFORMANCE TEST")
        print("="*60)
        
        endpoints = [
            ("v5/market/tickers", {"category": "linear", "symbol": "BTCUSDT"}),
            ("v5/market/kline", {"category": "linear", "symbol": "BTCUSDT", "interval": "1", "limit": "200"}),
            ("v5/market/orderbook", {"category": "linear", "symbol": "BTCUSDT"}),
            ("v5/market/recent-trade", {"category": "linear", "symbol": "BTCUSDT"}),
            ("v5/market/open-interest", {"category": "linear", "symbol": "BTCUSDT", "intervalTime": "1h"}),
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint, params in endpoints:
                print(f"\nTesting /{endpoint}:")
                
                # Test with different timeouts
                timeouts = [5, 10, 20, 30]
                for timeout in timeouts:
                    result = await self._test_with_timeout(session, endpoint, params, timeout)
                    
                    status = "✅" if result["success"] else "❌"
                    print(f"   Timeout {timeout}s: {status} ({result['time']:.2f}s) - {result['message']}")
                    
                    # Track timeout patterns
                    if not result["success"] and "timeout" in result["message"].lower():
                        if endpoint not in self.timeout_patterns:
                            self.timeout_patterns[endpoint] = []
                        self.timeout_patterns[endpoint].append(timeout)
    
    async def test_request_timing_breakdown(self):
        """Detailed timing breakdown of a request"""
        print("\n" + "="*60)
        print("5. REQUEST TIMING BREAKDOWN")
        print("="*60)
        
        url = f"{self.base_url}/v5/market/tickers"
        params = {"category": "linear", "symbol": "BTCUSDT"}
        
        trace_config = aiohttp.TraceConfig()
        timings = {}
        
        async def on_request_start(session, trace_config_ctx, params):
            timings['request_start'] = time.time()
        
        async def on_connection_create_start(session, trace_config_ctx, params):
            timings['connection_create_start'] = time.time()
        
        async def on_connection_create_end(session, trace_config_ctx, params):
            timings['connection_create_end'] = time.time()
        
        async def on_request_end(session, trace_config_ctx, params):
            timings['request_end'] = time.time()
        
        trace_config.on_request_start.append(on_request_start)
        trace_config.on_connection_create_start.append(on_connection_create_start)
        trace_config.on_connection_create_end.append(on_connection_create_end)
        trace_config.on_request_end.append(on_request_end)
        
        async with aiohttp.ClientSession(trace_configs=[trace_config]) as session:
            try:
                timings['start'] = time.time()
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    timings['headers_received'] = time.time()
                    data = await response.json()
                    timings['body_received'] = time.time()
                
                # Calculate durations
                if 'connection_create_start' in timings and 'connection_create_end' in timings:
                    conn_time = timings['connection_create_end'] - timings['connection_create_start']
                    print(f"✅ Connection Creation: {conn_time:.3f}s")
                
                if 'request_start' in timings and 'headers_received' in timings:
                    ttfb = timings['headers_received'] - timings['request_start']
                    print(f"   Time to First Byte: {ttfb:.3f}s")
                
                if 'headers_received' in timings and 'body_received' in timings:
                    download_time = timings['body_received'] - timings['headers_received']
                    print(f"   Body Download: {download_time:.3f}s")
                
                total_time = timings['body_received'] - timings['start']
                print(f"   Total Request Time: {total_time:.3f}s")
                
                # Response details
                print(f"\n   Response Details:")
                print(f"   - Status: {response.status}")
                print(f"   - Content Length: {response.headers.get('Content-Length', 'Unknown')}")
                print(f"   - Server: {response.headers.get('Server', 'Unknown')}")
                
                return {"success": True, "timings": timings}
                
            except asyncio.TimeoutError:
                print(f"❌ Request timed out after 30s")
                return {"success": False, "error": "timeout"}
            except Exception as e:
                print(f"❌ Request failed: {e}")
                return {"success": False, "error": str(e)}
    
    async def test_concurrent_requests(self):
        """Test behavior under concurrent load"""
        print("\n" + "="*60)
        print("6. CONCURRENT REQUEST STRESS TEST")
        print("="*60)
        
        async with aiohttp.ClientSession() as session:
            # Test different concurrency levels
            for concurrent in [1, 5, 10, 20]:
                print(f"\nTesting with {concurrent} concurrent requests:")
                
                tasks = []
                for i in range(concurrent):
                    url = f"{self.base_url}/v5/market/tickers"
                    params = {"category": "linear", "symbol": f"BTCUSDT"}
                    tasks.append(self._timed_request(session, url, params, f"R{i+1}"))
                
                start = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                total_time = time.time() - start
                
                success = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
                timeouts = sum(1 for r in results if isinstance(r, dict) and not r.get("success"))
                errors = sum(1 for r in results if isinstance(r, Exception))
                
                avg_time = total_time / concurrent
                print(f"   Total Time: {total_time:.2f}s")
                print(f"   Average Time: {avg_time:.2f}s")
                print(f"   Success: {success}/{concurrent}")
                print(f"   Timeouts: {timeouts}/{concurrent}")
                print(f"   Errors: {errors}/{concurrent}")
                
                # Add delay between tests
                await asyncio.sleep(2)
    
    async def _timed_request(self, session, url, params, label="Request"):
        """Helper to make timed request"""
        try:
            start = time.time()
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                data = await response.json()
                elapsed = time.time() - start
                success = data.get("retCode") == 0
                return {
                    "success": success,
                    "time": elapsed,
                    "label": label,
                    "message": data.get("retMsg", "OK")
                }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "time": 10.0,
                "label": label,
                "message": "Timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "time": time.time() - start,
                "label": label,
                "message": str(e)
            }
    
    async def _test_with_timeout(self, session, endpoint, params, timeout):
        """Test endpoint with specific timeout"""
        url = f"{self.base_url}/{endpoint}"
        try:
            start = time.time()
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                data = await response.json()
                elapsed = time.time() - start
                return {
                    "success": data.get("retCode") == 0,
                    "time": elapsed,
                    "message": data.get("retMsg", "OK")
                }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "time": timeout,
                "message": f"Timeout after {timeout}s"
            }
        except Exception as e:
            return {
                "success": False,
                "time": time.time() - start,
                "message": str(e)
            }
    
    async def run_all_tests(self):
        """Run all diagnostic tests"""
        print("\n" + "="*60)
        print(" BYBIT CONNECTION DIAGNOSTICS")
        print(" Started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*60)
        
        # Run tests
        await self.test_dns_resolution()
        await self.test_ssl_handshake()
        await self.test_connection_pooling()
        await self.test_endpoint_performance()
        await self.test_request_timing_breakdown()
        await self.test_concurrent_requests()
        
        # Summary
        print("\n" + "="*60)
        print(" SUMMARY OF FINDINGS")
        print("="*60)
        
        if self.timeout_patterns:
            print("\n⚠️  Timeout Patterns Detected:")
            for endpoint, timeouts in self.timeout_patterns.items():
                print(f"   {endpoint}: Consistently times out at {min(timeouts)}s")
        
        print("\n📊 Recommendations based on findings will be provided after analysis.")

if __name__ == "__main__":
    debugger = BybitDebugger()
    asyncio.run(debugger.run_all_tests())
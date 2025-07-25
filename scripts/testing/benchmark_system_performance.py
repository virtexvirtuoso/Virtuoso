#!/usr/bin/env python3
"""
System Performance Benchmark for Trading Bot
Compare this computer vs VPS performance
"""

import time
import asyncio
import aiohttp
import numpy as np
import platform
import psutil
import json
from datetime import datetime
import talib
import pandas as pd

class SystemBenchmark:
    def __init__(self):
        self.results = {
            "system_info": {},
            "network_tests": {},
            "cpu_tests": {},
            "memory_tests": {},
            "trading_specific": {},
            "timestamp": datetime.now().isoformat()
        }
    
    def get_system_info(self):
        """Collect system information"""
        print("📊 Collecting System Information...")
        self.results["system_info"] = {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else "N/A",
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "python_version": platform.python_version()
        }
    
    async def test_bybit_latency(self):
        """Test network latency to Bybit API"""
        print("\n🌐 Testing Bybit API Latency...")
        
        endpoints = [
            ("Market Data", "https://api.bybit.com/v5/market/time"),
            ("Orderbook", "https://api.bybit.com/v5/market/orderbook?category=spot&symbol=BTCUSDT"),
            ("Kline", "https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=1m&limit=200"),
        ]
        
        async with aiohttp.ClientSession() as session:
            for name, url in endpoints:
                latencies = []
                
                for i in range(5):
                    start = time.perf_counter()
                    try:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            await response.json()
                            latency = (time.perf_counter() - start) * 1000
                            latencies.append(latency)
                    except Exception as e:
                        print(f"  ❌ Error testing {name}: {e}")
                        latencies.append(None)
                    
                    if i < 4:  # Don't sleep after last request
                        await asyncio.sleep(0.5)
                
                valid_latencies = [l for l in latencies if l is not None]
                if valid_latencies:
                    self.results["network_tests"][name] = {
                        "min_ms": round(min(valid_latencies), 2),
                        "avg_ms": round(sum(valid_latencies) / len(valid_latencies), 2),
                        "max_ms": round(max(valid_latencies), 2),
                        "success_rate": f"{len(valid_latencies)}/{len(latencies)}"
                    }
                    print(f"  ✅ {name}: {self.results['network_tests'][name]['avg_ms']}ms avg")
    
    def test_cpu_performance(self):
        """Test CPU performance with trading-relevant calculations"""
        print("\n💻 Testing CPU Performance...")
        
        # Test 1: TA-Lib indicator calculations
        print("  📈 Testing TA-Lib performance...")
        prices = np.random.randn(10000) * 100 + 50000  # Simulate BTC prices
        
        start = time.perf_counter()
        for _ in range(100):
            rsi = talib.RSI(prices, timeperiod=14)
            macd = talib.MACD(prices, fastperiod=12, slowperiod=26, signalperiod=9)
            bbands = talib.BBANDS(prices, timeperiod=20)
        talib_time = time.perf_counter() - start
        
        # Test 2: NumPy calculations
        print("  🔢 Testing NumPy performance...")
        data = np.random.randn(1000, 1000)
        
        start = time.perf_counter()
        for _ in range(100):
            result = np.dot(data, data.T)
            eigenvalues = np.linalg.eigvals(result[:100, :100])
        numpy_time = time.perf_counter() - start
        
        # Test 3: Pandas operations
        print("  📊 Testing Pandas performance...")
        df = pd.DataFrame(np.random.randn(10000, 10), 
                         columns=[f'col_{i}' for i in range(10)])
        
        start = time.perf_counter()
        for _ in range(100):
            rolling_mean = df.rolling(window=20).mean()
            grouped = df.groupby(df.index // 100).agg(['mean', 'std'])
        pandas_time = time.perf_counter() - start
        
        self.results["cpu_tests"] = {
            "talib_100_iterations_ms": round(talib_time * 1000, 2),
            "numpy_100_iterations_ms": round(numpy_time * 1000, 2),
            "pandas_100_iterations_ms": round(pandas_time * 1000, 2),
            "total_cpu_score": round(1000 / (talib_time + numpy_time + pandas_time), 2)
        }
        print(f"  ✅ CPU Score: {self.results['cpu_tests']['total_cpu_score']}")
    
    async def test_concurrent_requests(self):
        """Test concurrent API request handling"""
        print("\n🔄 Testing Concurrent Request Performance...")
        
        url = "https://api.bybit.com/v5/market/time"
        concurrent_counts = [1, 5, 10, 20]
        
        async with aiohttp.ClientSession() as session:
            for count in concurrent_counts:
                start = time.perf_counter()
                
                tasks = []
                for _ in range(count):
                    tasks.append(session.get(url))
                
                try:
                    responses = await asyncio.gather(*tasks)
                    for response in responses:
                        await response.json()
                        response.close()
                    
                    total_time = (time.perf_counter() - start) * 1000
                    avg_time = total_time / count
                    
                    self.results["trading_specific"][f"concurrent_{count}_requests"] = {
                        "total_ms": round(total_time, 2),
                        "avg_ms": round(avg_time, 2)
                    }
                    print(f"  ✅ {count} concurrent requests: {round(avg_time, 2)}ms avg")
                except Exception as e:
                    print(f"  ❌ Error with {count} concurrent requests: {e}")
    
    def test_memory_operations(self):
        """Test memory allocation and operations"""
        print("\n🧠 Testing Memory Performance...")
        
        # Test large array operations
        start = time.perf_counter()
        arrays = []
        for i in range(50):
            # Simulate market data storage
            arr = np.random.randn(1000, 100)  # 1000 candles, 100 features
            arrays.append(arr)
        
        # Simulate data processing
        for arr in arrays:
            processed = np.mean(arr, axis=0)
            std = np.std(arr, axis=0)
        
        memory_time = time.perf_counter() - start
        
        self.results["memory_tests"] = {
            "large_array_ops_ms": round(memory_time * 1000, 2),
            "current_memory_usage_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2)
        }
        print(f"  ✅ Memory operations: {self.results['memory_tests']['large_array_ops_ms']}ms")
    
    def generate_report(self):
        """Generate comparison report"""
        print("\n" + "="*60)
        print("📋 PERFORMANCE BENCHMARK REPORT")
        print("="*60)
        
        # System Info
        print("\n🖥️  System Information:")
        for key, value in self.results["system_info"].items():
            print(f"  • {key}: {value}")
        
        # Network Performance
        print("\n🌐 Network Performance to Bybit:")
        for endpoint, metrics in self.results["network_tests"].items():
            print(f"  • {endpoint}: {metrics['avg_ms']}ms average latency")
        
        # CPU Performance
        print("\n💻 CPU Performance:")
        print(f"  • TA-Lib calculations: {self.results['cpu_tests']['talib_100_iterations_ms']}ms")
        print(f"  • Overall CPU Score: {self.results['cpu_tests']['total_cpu_score']} (higher is better)")
        
        # Trading Specific
        print("\n🔄 Concurrent Request Handling:")
        for test, metrics in self.results["trading_specific"].items():
            print(f"  • {test}: {metrics['avg_ms']}ms per request")
        
        # VPS Comparison
        print("\n" + "="*60)
        print("🎯 EXPECTED VPS PERFORMANCE COMPARISON")
        print("="*60)
        
        current_latency = self.results["network_tests"].get("Market Data", {}).get("avg_ms", 500)
        
        print(f"\n📊 Your Current Setup:")
        print(f"  • Bybit API Latency: {current_latency}ms")
        print(f"  • CPU Score: {self.results['cpu_tests']['total_cpu_score']}")
        
        print(f"\n🚀 Expected Singapore VPS Performance:")
        print(f"  • Bybit API Latency: ~12-15ms (***{round(current_latency/12)}x faster***)")
        print(f"  • CPU Score: ~50-150 (varies by VPS tier)")
        
        print(f"\n💡 Recommendations:")
        if current_latency > 100:
            print("  ⚠️  Your latency is HIGH - VPS will provide SIGNIFICANT improvement")
            print("  ✅ Recommended: Vultr $24/month (4GB RAM) in Singapore")
        else:
            print("  ✅ Your latency is already good - VPS mainly for 24/7 uptime")
        
        # Save results
        filename = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Full results saved to: {filename}")

async def main():
    print("🚀 Starting System Performance Benchmark...")
    print("This will test your computer's performance for trading bot operations\n")
    
    benchmark = SystemBenchmark()
    
    # Run all tests
    benchmark.get_system_info()
    await benchmark.test_bybit_latency()
    benchmark.test_cpu_performance()
    benchmark.test_memory_operations()
    await benchmark.test_concurrent_requests()
    
    # Generate report
    benchmark.generate_report()
    
    print("\n✅ Benchmark complete! Run this same script on your VPS to compare.")

if __name__ == "__main__":
    asyncio.run(main())
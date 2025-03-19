import os
import sys
import time
import gc
import psutil
import tracemalloc
import asyncio
import matplotlib.pyplot as plt
import numpy as np
from functools import wraps
from dotenv import load_dotenv
from datetime import datetime
from memory_profiler import profile as memory_profile

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

class MemoryProfiler:
    """Memory profiler for tracking memory usage over time."""
    
    def __init__(self, interval=1.0, output_file=None):
        """Initialize the memory profiler.
        
        Args:
            interval (float): Time interval between measurements in seconds
            output_file (str): File to save the results to
        """
        self.interval = interval
        self.output_file = output_file or f"memory_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.process = psutil.Process()
        self.measurements = []
        self.running = False
        self._task = None
    
    async def start(self):
        """Start the memory profiler."""
        if self.running:
            print("Memory profiler is already running")
            return
        
        self.running = True
        self.measurements = []
        
        print(f"Memory profiler started. Sampling every {self.interval} seconds.")
        print(f"Results will be saved to {self.output_file}")
        
        # Start the profiler as a separate task
        self._task = asyncio.create_task(self._profile_memory())
    
    async def stop(self):
        """Stop the memory profiler and save results."""
        if not self.running:
            print("Memory profiler is not running")
            return
        
        self.running = False
        if self._task:
            await self._task
        
        # Save results
        self._save_results()
        
        print(f"Memory profiler stopped. {len(self.measurements)} samples collected.")
        return self.measurements
    
    async def _profile_memory(self):
        """Continuously profile memory usage."""
        # Initial collection of garbage
        gc.collect()
        
        start_time = time.time()
        
        while self.running:
            # Collect current memory usage
            memory_info = self.process.memory_info()
            
            # Record the measurement
            self.measurements.append({
                'timestamp': time.time() - start_time,
                'rss': memory_info.rss,  # Resident Set Size
                'vms': memory_info.vms,  # Virtual Memory Size
                'shared': getattr(memory_info, 'shared', 0),  # Shared memory
                'data': getattr(memory_info, 'data', 0),  # Data segment
                'uss': getattr(memory_info, 'uss', 0),  # Unique Set Size (Linux only)
                'pss': getattr(memory_info, 'pss', 0),  # Proportional Set Size (Linux only)
            })
            
            # Wait for the next measurement
            await asyncio.sleep(self.interval)
    
    def _save_results(self):
        """Save the measurements to a CSV file."""
        if not self.measurements:
            print("No measurements to save")
            return
        
        import pandas as pd
        
        # Convert to DataFrame and save
        df = pd.DataFrame(self.measurements)
        df.to_csv(self.output_file, index=False)
        print(f"Memory profile saved to {self.output_file}")
        
        # Create a plot
        self.plot(f"{os.path.splitext(self.output_file)[0]}.png")
    
    def plot(self, output_file=None):
        """Plot the memory usage over time."""
        if not self.measurements:
            print("No measurements to plot")
            return
        
        import pandas as pd
        
        # Convert to DataFrame
        df = pd.DataFrame(self.measurements)
        
        # Create the plot
        plt.figure(figsize=(12, 6))
        
        # Convert bytes to MB for better visualization
        plt.plot(df['timestamp'], df['rss'] / (1024 * 1024), label='RSS (MB)')
        plt.plot(df['timestamp'], df['vms'] / (1024 * 1024), label='VMS (MB)')
        
        if all(df['uss'] > 0):  # Only if available
            plt.plot(df['timestamp'], df['uss'] / (1024 * 1024), label='USS (MB)')
        
        plt.title('Memory Usage Over Time')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Memory (MB)')
        plt.legend()
        plt.grid(True)
        
        # Save the plot if requested
        if output_file:
            plt.savefig(output_file)
            print(f"Memory plot saved to {output_file}")
        
        plt.close()

def memory_profiled(func):
    """Decorator to profile the memory usage of a function using memory_profiler."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Apply the memory_profile decorator
        profiled_func = memory_profile(func)
        return profiled_func(*args, **kwargs)
    return wrapper

async def trace_memory_usage(async_func, *args, **kwargs):
    """Profile memory allocation for a specific async function using tracemalloc."""
    # Start tracing memory allocations
    tracemalloc.start()
    
    # Take snapshot before
    snapshot1 = tracemalloc.take_snapshot()
    
    # Call the function
    result = await async_func(*args, **kwargs)
    
    # Take snapshot after
    snapshot2 = tracemalloc.take_snapshot()
    
    # Stop tracing
    tracemalloc.stop()
    
    # Compare snapshots
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    print(f"\nMemory allocation for {async_func.__name__}:")
    for stat in top_stats[:20]:  # Show top 20 allocations
        print(stat)
    
    return result

async def profile_monitor_memory(symbol="BTC/USDT", duration=60):
    """Profile memory usage of the market monitor over time."""
    from src.config.manager import ConfigManager
    from src.core.exchanges.manager import ExchangeManager
    from src.monitoring.monitor import MarketMonitor
    
    print(f"Setting up memory profiling for market monitor, symbol={symbol}, duration={duration}s")
    
    # Initialize config manager
    config_manager = ConfigManager()
    config_manager.load_default_config()
    
    # Initialize exchange manager
    exchange_manager = ExchangeManager(config_manager)
    await exchange_manager.initialize()
    
    # Initialize market monitor
    market_monitor = MarketMonitor(
        exchange_manager=exchange_manager,
        config_manager=config_manager
    )
    
    await market_monitor.initialize()
    print("Market monitor initialized successfully")
    
    # Start memory profiler
    memory_profiler = MemoryProfiler(interval=1.0, 
                                    output_file=f"memory_profile_{symbol.replace('/', '')}.csv")
    await memory_profiler.start()
    
    try:
        # Run the monitor for the specified duration
        print(f"Running market monitor for {duration} seconds...")
        
        # Initial market data fetch
        market_data = await market_monitor.fetch_market_data(symbol)
        
        # Analyze repeatedly to see memory growth
        start_time = time.time()
        analysis_count = 0
        
        while time.time() - start_time < duration:
            # Analyze market
            analysis = await market_monitor.analyze_market(symbol, market_data)
            analysis_count += 1
            
            # Print progress every 5 analyses
            if analysis_count % 5 == 0:
                current_memory = psutil.Process().memory_info().rss / (1024 * 1024)
                elapsed = time.time() - start_time
                print(f"Completed {analysis_count} analyses in {elapsed:.1f}s, " 
                      f"current memory: {current_memory:.1f} MB")
            
            # Small delay between analyses
            await asyncio.sleep(0.5)
            
            # Occasionally refresh market data
            if analysis_count % 10 == 0:
                market_data = await market_monitor.fetch_market_data(symbol)
    
    finally:
        # Stop memory profiler
        await memory_profiler.stop()
        
        # Clean up
        await market_monitor.shutdown()

async def profile_memory_per_component():
    """Profile memory usage of individual components."""
    from src.config.manager import ConfigManager
    from src.core.exchanges.manager import ExchangeManager
    from src.monitoring.monitor import MarketMonitor
    from src.monitoring.market_reporter import MarketReporter
    from src.monitoring.alert_manager import AlertManager
    
    print("Profiling memory usage per component...")
    
    # Start tracemalloc
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()
    
    # Initialize config manager
    config_manager = ConfigManager()
    config_manager.load_default_config()
    
    # Profile each component separately
    
    # 1. Exchange Manager
    print("\n1. Initializing Exchange Manager...")
    exchange_manager = ExchangeManager(config_manager)
    await exchange_manager.initialize()
    snapshot2 = tracemalloc.take_snapshot()
    print_memory_diff(snapshot1, snapshot2, "Exchange Manager Initialization")
    snapshot1 = snapshot2
    
    # 2. Market Monitor
    print("\n2. Initializing Market Monitor...")
    market_monitor = MarketMonitor(
        exchange_manager=exchange_manager,
        config_manager=config_manager
    )
    await market_monitor.initialize()
    snapshot2 = tracemalloc.take_snapshot()
    print_memory_diff(snapshot1, snapshot2, "Market Monitor Initialization")
    snapshot1 = snapshot2
    
    # 3. Market Reporter
    print("\n3. Initializing Market Reporter...")
    market_reporter = MarketReporter(
        exchange_manager=exchange_manager,
        config_manager=config_manager
    )
    await market_reporter.initialize()
    snapshot2 = tracemalloc.take_snapshot()
    print_memory_diff(snapshot1, snapshot2, "Market Reporter Initialization")
    snapshot1 = snapshot2
    
    # 4. Alert Manager
    print("\n4. Initializing Alert Manager...")
    alert_manager = AlertManager(
        exchange_manager=exchange_manager,
        config_manager=config_manager
    )
    await alert_manager.initialize()
    snapshot2 = tracemalloc.take_snapshot()
    print_memory_diff(snapshot1, snapshot2, "Alert Manager Initialization")
    
    # Stop tracemalloc
    tracemalloc.stop()
    
    # Clean up
    await alert_manager.shutdown()
    await market_reporter.shutdown()
    await market_monitor.shutdown()
    await exchange_manager.shutdown()

def print_memory_diff(snapshot1, snapshot2, label):
    """Print memory difference between two snapshots."""
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    print(f"\nTop 10 memory allocations for {label}:")
    total_diff = sum(stat.size_diff for stat in top_stats)
    print(f"Total: {total_diff / 1024 / 1024:.2f} MB")
    
    for stat in top_stats[:10]:
        print(f"{stat.size_diff / 1024:.1f} KB: {stat}")

def identify_memory_leaks(iterations=10, symbol="BTC/USDT"):
    """Run a specific operation multiple times to identify memory leaks."""
    import gc
    from src.config.manager import ConfigManager
    from src.core.exchanges.manager import ExchangeManager
    from src.monitoring.monitor import MarketMonitor
    
    async def run_test():
        # Initialize components
        config_manager = ConfigManager()
        config_manager.load_default_config()
        
        exchange_manager = ExchangeManager(config_manager)
        await exchange_manager.initialize()
        
        market_monitor = MarketMonitor(
            exchange_manager=exchange_manager,
            config_manager=config_manager
        )
        
        await market_monitor.initialize()
        
        # Run the operation multiple times
        memory_usage = []
        for i in range(iterations):
            # Force garbage collection
            gc.collect()
            
            # Get initial memory
            initial_memory = psutil.Process().memory_info().rss
            
            # Run operation
            market_data = await market_monitor.fetch_market_data(symbol)
            analysis = await market_monitor.analyze_market(symbol, market_data)
            
            # Get final memory
            final_memory = psutil.Process().memory_info().rss
            memory_diff = final_memory - initial_memory
            
            memory_usage.append({
                'iteration': i + 1,
                'initial_memory': initial_memory,
                'final_memory': final_memory,
                'memory_diff': memory_diff
            })
            
            print(f"Iteration {i+1}/{iterations}: Memory diff: {memory_diff/1024/1024:.2f} MB")
            await asyncio.sleep(0.5)  # Small delay between iterations
        
        # Clean up
        await market_monitor.shutdown()
        await exchange_manager.shutdown()
        
        return memory_usage
    
    memory_data = asyncio.run(run_test())
    
    # Plot the results
    iterations = [data['iteration'] for data in memory_data]
    memory_diffs = [data['memory_diff'] / (1024 * 1024) for data in memory_data]
    
    plt.figure(figsize=(10, 6))
    plt.plot(iterations, memory_diffs, marker='o')
    plt.xlabel('Iteration')
    plt.ylabel('Memory Difference (MB)')
    plt.title('Memory Growth Over Iterations')
    plt.grid(True)
    plt.savefig('memory_leak_analysis.png')
    plt.close()
    
    # Analyze for potential leaks
    if all(diff > 0 for diff in memory_diffs):
        print("\nPOTENTIAL MEMORY LEAK DETECTED: Memory consistently increases across iterations")
    elif sum(memory_diffs) > 10:  # Arbitrary threshold of 10MB
        print("\nPOSSIBLE MEMORY LEAK: Total memory growth is significant")
    else:
        print("\nNo obvious memory leak detected")
    
    return memory_data

async def main():
    """Main entry point for memory profiling."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Memory profiling for the Virtuoso Trading application")
    parser.add_argument("--component", choices=['monitor', 'reporter', 'all'], 
                      default='all', help="Component to profile")
    parser.add_argument("--symbol", default="BTC/USDT", help="Symbol to use for profiling")
    parser.add_argument("--duration", type=int, default=60, 
                      help="Duration in seconds for monitoring")
    parser.add_argument("--leak-test", action="store_true", 
                      help="Run memory leak detection test")
    
    args = parser.parse_args()
    
    if args.leak_test:
        print("Running memory leak detection test...")
        identify_memory_leaks(iterations=20, symbol=args.symbol)
        return
    
    if args.component in ['monitor', 'all']:
        await profile_monitor_memory(args.symbol, args.duration)
    
    if args.component in ['all']:
        await profile_memory_per_component()

if __name__ == "__main__":
    # Run the memory profiler
    asyncio.run(main()) 
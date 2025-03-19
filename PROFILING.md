# Performance Profiling Tools for Virtuoso Trading

This directory contains a set of profiling tools to help identify performance bottlenecks, memory leaks, and optimization opportunities in the Virtuoso Trading application.

## Available Tools

1. **run_profiling.py** - Main profiling script that runs all profiling tools and generates a summary report
2. **profile_app.py** - CPU profiling for the main application
3. **profile_market_monitor.py** - Specialized profiling for the MarketMonitor component
4. **profile_memory.py** - Memory usage profiling and leak detection

## Prerequisites

Make sure you have all required dependencies installed:

```bash
pip install psutil memory_profiler matplotlib numpy pandas
```

## Quick Start

The simplest way to profile the application is to use the main profiling script:

```bash
./run_profiling.py
```

This will:
1. Run CPU profiling on the main application
2. Profile the market monitor for BTC/USDT
3. Run memory profiling
4. Check for memory leaks
5. Generate a comprehensive summary report

## Advanced Usage

### Profiling Specific Symbols

To profile specific trading pairs:

```bash
./run_profiling.py --symbols BTC/USDT ETH/USDT SOL/USDT
```

### Adjusting Profiling Duration

Change the duration of each profiling run:

```bash
./run_profiling.py --duration 120  # 2 minutes per run
```

### Selective Profiling

Skip certain profiling steps:

```bash
./run_profiling.py --skip-cpu  # Skip CPU profiling
./run_profiling.py --skip-memory  # Skip memory profiling
./run_profiling.py --skip-leak-test  # Skip memory leak testing
```

## Individual Tools

You can also run each profiling tool individually:

### CPU Profiling

```bash
# Profile the main application
./profile_app.py --main

# Profile a specific module
./profile_app.py --module src.monitoring.monitor

# Analyze existing profile data
./profile_app.py --analyze profile_results.prof
```

### Market Monitor Profiling

```bash
# Profile the market monitor for a specific symbol
./profile_market_monitor.py --symbol BTC/USDT
```

### Memory Profiling

```bash
# Profile memory usage of the market monitor
./profile_memory.py --component monitor --symbol BTC/USDT --duration 60

# Profile memory usage of all components
./profile_memory.py --component all

# Run memory leak detection test
./profile_memory.py --leak-test
```

## Understanding Profile Results

### CPU Profile Results (.prof files)

CPU profiling results are saved as `.prof` files that can be analyzed with Python's built-in `pstats` module:

```python
import pstats
from pstats import SortKey

# Load the profile data
p = pstats.Stats('profile_results.prof')

# Sort by cumulative time and print top 20 functions
p.strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(20)

# Sort by total time
p.sort_stats(SortKey.TIME).print_stats(20)

# Sort by call count
p.sort_stats(SortKey.CALLS).print_stats(20)
```

You can also visualize the profile data with tools like:
- **snakeviz**: `pip install snakeviz && snakeviz profile_results.prof`
- **gprof2dot**: `pip install gprof2dot && gprof2dot -f pstats profile_results.prof | dot -Tpng -o profile.png`

### Memory Profile Results

Memory profiling results are saved as CSV files and PNG visualizations. Look for:

1. **Steady increase** in memory usage, which could indicate a memory leak
2. **Spikes** in memory usage during certain operations
3. **High baseline** memory usage that could be optimized

## Common Bottlenecks to Look For

1. **Synchronous API calls** that block the event loop
2. **Excessive data processing** in real-time components
3. **Redundant calculations** that could be cached
4. **Large object allocations** in frequently called methods
5. **Inefficient loops** or algorithms with poor complexity
6. **Excessive string concatenation** or format operations
7. **Database or I/O operations** in critical paths

## Optimization Strategies

Based on profiling results, consider these optimization approaches:

1. **Caching**: Cache frequently accessed data or calculation results
2. **Lazy Loading**: Defer loading of resources until needed
3. **Batch Processing**: Process data in batches instead of individually
4. **Asynchronous Operations**: Use async/await for I/O-bound operations
5. **Data Structure Optimization**: Choose appropriate data structures
6. **Algorithm Improvements**: Replace inefficient algorithms
7. **Resource Pooling**: Reuse expensive resources like connections
8. **Reduce Memory Footprint**: Minimize object creation in hot paths
9. **Concurrent Processing**: Use threading or multiprocessing where appropriate

## Interpreting Results

When analyzing profile results, focus on:

1. **Functions with high cumulative time**: These are bottlenecks in the application
2. **Functions called many times**: These might benefit from optimization even if each call is fast
3. **Memory growth patterns**: Look for consistent growth that could indicate a leak
4. **Spikes in resource usage**: These could indicate inefficient operations

Remember to profile after making optimizations to verify improvements. 
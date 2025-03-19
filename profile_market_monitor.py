import cProfile
import pstats
import io
import os
import sys
import asyncio
import time
from pstats import SortKey
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def profile_async_function(async_func, *args, **kwargs):
    """Profile an async function."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(async_func(*args, **kwargs))
    
    profiler.disable()
    
    # Print stats to console
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(SortKey.CUMULATIVE)
    ps.print_stats(50)
    print(s.getvalue())
    
    # Save the results
    output_file = f"profile_{async_func.__name__}.prof"
    ps.dump_stats(output_file)
    print(f"Profile data written to {output_file}")
    
    return result

async def setup_market_monitor():
    """Set up the market monitor for profiling."""
    from src.config.manager import ConfigManager
    from src.core.exchanges.manager import ExchangeManager
    from src.monitoring.monitor import MarketMonitor
    
    print("Setting up market monitor for profiling...")
    
    # Initialize config manager
    config_manager = ConfigManager()
    config_manager.load_default_config()
    
    # Initialize exchange manager
    exchange_manager = ExchangeManager(config_manager)
    await exchange_manager.initialize()
    
    # Initialize market monitor with minimal components
    market_monitor = MarketMonitor(
        exchange_manager=exchange_manager,
        config_manager=config_manager
    )
    
    await market_monitor.initialize()
    print("Market monitor initialized successfully")
    
    return market_monitor

async def profile_monitor_fetch_data(market_monitor, symbol="BTC/USDT"):
    """Profile the fetch_data method of market monitor."""
    print(f"Profiling fetch_data for {symbol}...")
    start_time = time.time()
    
    data = await market_monitor.fetch_market_data(symbol)
    
    duration = time.time() - start_time
    print(f"fetch_market_data executed in {duration:.4f} seconds")
    
    return data

async def profile_monitor_analysis(market_monitor, symbol="BTC/USDT"):
    """Profile the analyze_market method of market monitor."""
    print(f"Profiling analyze_market for {symbol}...")
    
    start_time = time.time()
    market_data = await market_monitor.fetch_market_data(symbol)
    
    # Start the actual profiling for the analysis part
    profiler = cProfile.Profile()
    profiler.enable()
    
    analysis = await market_monitor.analyze_market(symbol, market_data)
    
    profiler.disable()
    
    duration = time.time() - start_time
    print(f"Total analyze_market process executed in {duration:.4f} seconds")
    
    # Print and save stats
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(SortKey.CUMULATIVE)
    ps.print_stats(50)
    print(s.getvalue())
    
    output_file = "profile_analyze_market.prof"
    ps.dump_stats(output_file)
    print(f"Profile data written to {output_file}")
    
    return analysis

async def profile_monitor_indicator_calculation(market_monitor, symbol="BTC/USDT"):
    """Profile the indicator calculation methods."""
    print(f"Profiling indicator calculations for {symbol}...")
    
    market_data = await market_monitor.fetch_market_data(symbol)
    
    # Get the indicator modules
    indicators = market_monitor.indicators
    
    # Profile each indicator calculation
    for indicator_name, indicator in indicators.items():
        print(f"\nProfiling {indicator_name} indicator...")
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        start_time = time.time()
        
        # Try to calculate the indicator
        try:
            result = await market_monitor._calculate_indicator(indicator, market_data)
            duration = time.time() - start_time
            print(f"{indicator_name} calculated in {duration:.4f} seconds")
        except Exception as e:
            print(f"Error calculating {indicator_name}: {str(e)}")
            continue
        
        profiler.disable()
        
        # Print and save stats
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats(SortKey.CUMULATIVE)
        ps.print_stats(30)
        print(s.getvalue())
        
        output_file = f"profile_indicator_{indicator_name}.prof"
        ps.dump_stats(output_file)
        print(f"Profile data written to {output_file}")

def visualize_profiling_results(prof_file, output_file=None, show_plot=True):
    """Visualize profiling results as a horizontal bar chart."""
    # Load the stats
    stats = pstats.Stats(prof_file)
    
    # Get the function stats
    function_stats = []
    for func, (cc, nc, tt, ct, callers) in stats.stats.items():
        # Extract the function name
        _, line, name = func
        full_name = f"{name} (line {line})"
        
        # Add the stats
        function_stats.append({
            'name': full_name,
            'calls': cc,
            'cum_time': ct,
            'tot_time': tt
        })
    
    # Sort by cumulative time
    function_stats.sort(key=lambda x: x['cum_time'], reverse=True)
    
    # Take the top 20 functions
    top_functions = function_stats[:20]
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 12))
    
    # Extract data for plotting
    names = [f"{func['name']} ({func['calls']} calls)" for func in top_functions]
    cum_times = [func['cum_time'] for func in top_functions]
    tot_times = [func['tot_time'] for func in top_functions]
    
    # Create the horizontal bar chart
    y_pos = np.arange(len(names))
    ax.barh(y_pos, cum_times, align='center', label='Cumulative Time')
    ax.barh(y_pos, tot_times, align='center', label='Total Time', alpha=0.5)
    
    # Set labels and title
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names)
    ax.invert_yaxis()  # Labels read top-to-bottom
    ax.set_xlabel('Time (seconds)')
    ax.set_title('Function Execution Time Profile')
    ax.legend()
    
    plt.tight_layout()
    
    # Save the chart if requested
    if output_file:
        plt.savefig(output_file)
        print(f"Chart saved to {output_file}")
    
    # Show the chart if requested
    if show_plot:
        plt.show()

async def main():
    """Main profiling script."""
    # Set up the market monitor
    market_monitor = await setup_market_monitor()
    
    # Profile different components
    symbols = ["BTC/USDT", "ETH/USDT"]
    
    for symbol in symbols:
        print(f"\n{'='*50}")
        print(f"Profiling for {symbol}")
        print(f"{'='*50}\n")
        
        # Profile data fetching
        profile_async_function(profile_monitor_fetch_data, market_monitor, symbol)
        
        # Profile market analysis
        await profile_monitor_analysis(market_monitor, symbol)
        
        # Profile indicator calculations
        await profile_monitor_indicator_calculation(market_monitor, symbol)
    
    # Visualize the results
    for filename in os.listdir('.'):
        if filename.endswith('.prof'):
            print(f"\nVisualizing {filename}")
            visualize_profiling_results(
                filename, 
                output_file=f"{os.path.splitext(filename)[0]}.png",
                show_plot=False
            )

if __name__ == "__main__":
    # Run the profiling script
    asyncio.run(main()) 
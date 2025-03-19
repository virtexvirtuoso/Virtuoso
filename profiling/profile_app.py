import cProfile
import pstats
import io
import os
import sys
import time
from contextlib import contextmanager
from pstats import SortKey

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

@contextmanager
def profiled(output_file=None, lines=50, sort_by=SortKey.CUMULATIVE):
    """Context manager for profiling a block of code."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        yield
    finally:
        profiler.disable()
        
        # Print stats to console
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats(sort_by)
        ps.print_stats(lines)
        print(s.getvalue())
        
        # If an output file is specified, save the results
        if output_file:
            ps.dump_stats(output_file)
            print(f"Profile data written to {output_file}")

def profile_main():
    """Profile the main application code."""
    from src.main import main
    import asyncio
    
    # Profile the main application function
    with profiled(output_file="profile_results.prof", lines=100):
        # Use asyncio.run to run the async main function
        asyncio.run(main())

def profile_with_time_tracking(func_name, *args, **kwargs):
    """Profile a specific function with detailed timing."""
    from src.monitoring.performance import PerformanceMonitor
    
    monitor = PerformanceMonitor()
    
    # Import the module dynamically
    parts = func_name.split('.')
    module_name = '.'.join(parts[:-1])
    function_name = parts[-1]
    
    module = __import__(module_name, fromlist=[function_name])
    func = getattr(module, function_name)
    
    # Use the monitor to track performance
    start_time = time.time()
    result = func(*args, **kwargs)
    duration = time.time() - start_time
    
    # Record the metrics
    monitor.record_function_call(func_name)
    monitor.record_execution_time(func_name, duration)
    
    print(f"Function {func_name} executed in {duration:.4f} seconds")
    return result

def analyze_profile_results(profile_file="profile_results.prof"):
    """Analyze and print the profile results in a readable format."""
    if not os.path.exists(profile_file):
        print(f"Profile file {profile_file} not found")
        return
    
    # Load the stats
    stats = pstats.Stats(profile_file)
    
    # Print various sorted views
    print("\n\nTop functions by cumulative time:")
    stats.sort_stats(SortKey.CUMULATIVE).print_stats(30)
    
    print("\n\nTop functions by total time:")
    stats.sort_stats(SortKey.TIME).print_stats(30)
    
    print("\n\nTop functions by call count:")
    stats.sort_stats(SortKey.CALLS).print_stats(30)
    
    # Strip directories for a cleaner view
    print("\n\nStripped view (no directory paths):")
    stats.strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(30)

def profile_specific_module(module_path, output_file=None):
    """Profile a specific module by importing it."""
    if output_file is None:
        module_name = module_path.split('.')[-1]
        output_file = f"profile_{module_name}.prof"
    
    with profiled(output_file=output_file):
        __import__(module_path)
    
    analyze_profile_results(output_file)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Profile the Virtuoso Trading application")
    
    # Add command line arguments
    parser.add_argument("--main", action="store_true", help="Profile the main application")
    parser.add_argument("--module", type=str, help="Profile a specific module")
    parser.add_argument("--function", type=str, help="Profile a specific function")
    parser.add_argument("--analyze", type=str, help="Analyze an existing profile data file")
    
    args = parser.parse_args()
    
    if args.main:
        profile_main()
    elif args.module:
        profile_specific_module(args.module)
    elif args.function:
        # This would need additional arguments for the function parameters
        print(f"Profiling function {args.function} - args would be needed")
    elif args.analyze:
        analyze_profile_results(args.analyze)
    else:
        # Default to profiling main
        profile_main() 
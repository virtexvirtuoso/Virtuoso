#!/usr/bin/env python3
"""
Comprehensive Profiling Suite for Virtuoso Trading

This script provides a convenient way to run all profiling tools to identify
performance bottlenecks, memory leaks, and optimization opportunities.
"""

import os
import sys
import time
import argparse
import subprocess
import json
from datetime import datetime

def setup_profile_directory():
    """Create a profile results directory with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    profile_dir = f"profile_results_{timestamp}"
    os.makedirs(profile_dir, exist_ok=True)
    return profile_dir

def run_cpu_profiling(profile_dir, symbols=None, duration=60):
    """Run CPU profiling on the application."""
    if symbols is None:
        symbols = ["BTC/USDT"]
    
    print("\n" + "="*80)
    print("Starting CPU Profiling")
    print("="*80)
    
    # Run the main profiling script
    print("\nRunning general application profiling...")
    subprocess.run([
        sys.executable, 
        "profile_app.py", 
        "--main"
    ], check=True)
    
    # Move results to profile directory
    if os.path.exists("profile_results.prof"):
        os.rename("profile_results.prof", f"{profile_dir}/profile_app.prof")
        
    # Run the market monitor profiling for each symbol
    for symbol in symbols:
        safe_symbol = symbol.replace("/", "")
        print(f"\nRunning market monitor profiling for {symbol}...")
        
        subprocess.run([
            sys.executable, 
            "profile_market_monitor.py", 
            "--symbol", symbol
        ], check=True)
        
        # Move any generated .prof and .png files to the profile directory
        for filename in os.listdir("."):
            if filename.endswith((".prof", ".png")) and filename.startswith("profile_"):
                os.rename(filename, f"{profile_dir}/{filename}")
    
    print("\nCPU profiling completed.")

def run_memory_profiling(profile_dir, symbols=None, duration=60, leak_test=True):
    """Run memory profiling on the application."""
    if symbols is None:
        symbols = ["BTC/USDT"]
    
    print("\n" + "="*80)
    print("Starting Memory Profiling")
    print("="*80)
    
    # Run memory profiling for each symbol
    for symbol in symbols:
        safe_symbol = symbol.replace("/", "")
        print(f"\nRunning memory profiling for {symbol}...")
        
        subprocess.run([
            sys.executable, 
            "profile_memory.py", 
            "--component", "monitor",
            "--symbol", symbol,
            "--duration", str(duration)
        ], check=True)
    
    # Run component-specific memory profiling
    print("\nRunning component-specific memory profiling...")
    subprocess.run([
        sys.executable, 
        "profile_memory.py", 
        "--component", "all"
    ], check=True)
    
    # Run memory leak test if requested
    if leak_test:
        print("\nRunning memory leak detection test...")
        subprocess.run([
            sys.executable, 
            "profile_memory.py", 
            "--leak-test"
        ], check=True)
    
    # Move any generated files to the profile directory
    for filename in os.listdir("."):
        if filename.endswith((".csv", ".png")) and (
            filename.startswith("memory_profile_") or
            filename == "memory_leak_analysis.png"
        ):
            os.rename(filename, f"{profile_dir}/{filename}")
    
    print("\nMemory profiling completed.")

def generate_summary_report(profile_dir):
    """Generate a summary report of all profiling results."""
    print("\n" + "="*80)
    print("Generating Summary Report")
    print("="*80)
    
    summary_file = f"{profile_dir}/profiling_summary.md"
    
    with open(summary_file, "w") as f:
        f.write("# Virtuoso Trading Profiling Summary\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # CPU Profiling summary
        f.write("## CPU Profiling Results\n\n")
        
        cpu_prof_files = [file for file in os.listdir(profile_dir) if file.endswith(".prof")]
        if cpu_prof_files:
            for prof_file in cpu_prof_files:
                f.write(f"### {prof_file}\n\n")
                
                # Run pstats to get the top functions
                try:
                    output = subprocess.check_output([
                        sys.executable, 
                        "-c", 
                        f"import pstats; p = pstats.Stats('{profile_dir}/{prof_file}'); "
                        f"p.strip_dirs().sort_stats('cumulative').print_stats(20)"
                    ], universal_newlines=True)
                    
                    # Extract just the stats table
                    if "ncalls" in output:
                        stats_table = output.split("ncalls")[1]
                        stats_table = "ncalls" + stats_table.split("\n\n")[0]
                        f.write("```\n" + stats_table + "\n```\n\n")
                except:
                    f.write("*Error processing profile file*\n\n")
        else:
            f.write("*No CPU profiling results found*\n\n")
        
        # Memory Profiling summary
        f.write("## Memory Profiling Results\n\n")
        
        memory_csv_files = [file for file in os.listdir(profile_dir) if file.endswith(".csv")]
        if memory_csv_files:
            for csv_file in memory_csv_files:
                f.write(f"### {csv_file}\n\n")
                
                # Add link to the corresponding PNG
                png_file = csv_file.replace(".csv", ".png")
                if os.path.exists(f"{profile_dir}/{png_file}"):
                    f.write(f"![Memory Profile]({png_file})\n\n")
                else:
                    f.write("*No visualization available*\n\n")
        else:
            f.write("*No memory profiling results found*\n\n")
        
        # Recommendations section
        f.write("## Recommendations\n\n")
        f.write("Based on the profiling results, consider these optimization opportunities:\n\n")
        f.write("1. *Automated recommendations will be added in future versions*\n")
        f.write("2. Check the functions with highest cumulative time in CPU profiles\n")
        f.write("3. Look for memory growth patterns in memory profile graphs\n")
        f.write("4. Examine memory leak detection results for potential issues\n\n")
        
        f.write("## Next Steps\n\n")
        f.write("1. Review the detailed profile results in the individual files\n")
        f.write("2. Target the most time-consuming functions for optimization\n")
        f.write("3. Address any memory leaks identified by the memory profiler\n")
        f.write("4. Consider caching frequently used data\n")
        f.write("5. Implement async operations where possible\n")
    
    print(f"Summary report generated: {summary_file}")
    return summary_file

def main():
    """Main entry point for the profiling suite."""
    parser = argparse.ArgumentParser(description="Comprehensive Profiling Suite for Virtuoso Trading")
    
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT"], 
                      help="Symbols to profile (e.g. BTC/USDT ETH/USDT)")
    parser.add_argument("--duration", type=int, default=60, 
                      help="Duration for each profiling run in seconds")
    parser.add_argument("--skip-cpu", action="store_true", 
                      help="Skip CPU profiling")
    parser.add_argument("--skip-memory", action="store_true", 
                      help="Skip memory profiling")
    parser.add_argument("--skip-leak-test", action="store_true", 
                      help="Skip memory leak testing")
    
    args = parser.parse_args()
    
    start_time = time.time()
    print(f"Starting comprehensive profiling with symbols: {', '.join(args.symbols)}")
    
    # Create a profile results directory
    profile_dir = setup_profile_directory()
    print(f"Profile results will be saved to: {profile_dir}")
    
    # Run profiling tools
    if not args.skip_cpu:
        run_cpu_profiling(profile_dir, args.symbols, args.duration)
    
    if not args.skip_memory:
        run_memory_profiling(profile_dir, args.symbols, args.duration, not args.skip_leak_test)
    
    # Generate summary report
    summary_file = generate_summary_report(profile_dir)
    
    # Done
    elapsed = time.time() - start_time
    print(f"\nProfiling completed in {elapsed:.2f} seconds.")
    print(f"Results saved to: {profile_dir}")
    print(f"Summary report: {summary_file}")

if __name__ == "__main__":
    main() 
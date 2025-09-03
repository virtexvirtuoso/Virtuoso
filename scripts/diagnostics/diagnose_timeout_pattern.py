#!/usr/bin/env python3
"""
Diagnose timeout patterns in Virtuoso logs
"""
import re
from datetime import datetime
import subprocess

def analyze_timeout_patterns():
    """Analyze timeout patterns from VPS logs"""
    
    # Get recent logs
    cmd = 'ssh linuxuser@VPS_HOST_REDACTED "sudo journalctl -u virtuoso.service --since \'1 hour ago\' | grep -E \'(timeout|Timeout|ERROR.*Request timeout|Empty DataFrame)\'"'
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        logs = result.stdout.strip().split('\n')
        
        # Patterns to analyze
        timeout_pattern = re.compile(r'(\d{2}:\d{2}:\d{2}).*Request timeout after (\d+)s: (.+)')
        empty_df_pattern = re.compile(r'(\d{2}:\d{2}:\d{2}).*Empty DataFrame for (.+)')
        
        timeout_endpoints = {}
        empty_df_symbols = {}
        timeline = []
        
        for log in logs:
            # Check for timeout
            timeout_match = timeout_pattern.search(log)
            if timeout_match:
                time, duration, endpoint = timeout_match.groups()
                if endpoint not in timeout_endpoints:
                    timeout_endpoints[endpoint] = []
                timeout_endpoints[endpoint].append({
                    'time': time,
                    'duration': int(duration)
                })
                timeline.append((time, 'timeout', endpoint))
            
            # Check for empty DataFrame
            empty_match = empty_df_pattern.search(log)
            if empty_match:
                time, symbol_or_tf = empty_match.groups()
                if symbol_or_tf not in empty_df_symbols:
                    empty_df_symbols[symbol_or_tf] = []
                empty_df_symbols[symbol_or_tf].append(time)
                timeline.append((time, 'empty_df', symbol_or_tf))
        
        # Analyze patterns
        print("="*60)
        print("TIMEOUT PATTERN ANALYSIS")
        print("="*60)
        
        print("\n1. Timeout Frequency by Endpoint:")
        for endpoint, timeouts in sorted(timeout_endpoints.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"   {endpoint}: {len(timeouts)} timeouts")
            # Check if timeouts cluster at specific times
            times = [t['time'] for t in timeouts]
            if len(set(times)) < len(times) / 2:
                print(f"      ⚠️  Clustered timeouts detected")
        
        print("\n2. Empty DataFrame Frequency:")
        for symbol, times in sorted(empty_df_symbols.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"   {symbol}: {len(times)} occurrences")
        
        print("\n3. Timeline Analysis (last 10 events):")
        for time, event_type, detail in timeline[-10:]:
            icon = "⏱️" if event_type == "timeout" else "📊"
            print(f"   {time} {icon} {event_type}: {detail}")
        
        # Check for patterns
        print("\n4. Pattern Detection:")
        
        # Check if timeouts happen in bursts
        if timeline:
            burst_threshold = 60  # seconds
            bursts = []
            current_burst = [timeline[0]]
            
            for i in range(1, len(timeline)):
                # Simple time comparison (assumes same day)
                prev_time = timeline[i-1][0]
                curr_time = timeline[i][0]
                
                # Convert to seconds for rough comparison
                prev_seconds = sum(int(x) * m for x, m in zip(prev_time.split(':'), [3600, 60, 1]))
                curr_seconds = sum(int(x) * m for x, m in zip(curr_time.split(':'), [3600, 60, 1]))
                
                if curr_seconds - prev_seconds < burst_threshold:
                    current_burst.append(timeline[i])
                else:
                    if len(current_burst) > 2:
                        bursts.append(current_burst)
                    current_burst = [timeline[i]]
            
            if len(current_burst) > 2:
                bursts.append(current_burst)
            
            if bursts:
                print(f"   ⚠️  Detected {len(bursts)} timeout bursts")
                for i, burst in enumerate(bursts[-3:]):  # Show last 3 bursts
                    print(f"      Burst {i+1}: {len(burst)} events from {burst[0][0]} to {burst[-1][0]}")
        
        # Recommendations
        print("\n5. Recommendations:")
        
        if timeout_endpoints:
            most_problematic = max(timeout_endpoints.items(), key=lambda x: len(x[1]))
            print(f"   • Most problematic endpoint: {most_problematic[0]}")
            print(f"     Consider caching or reducing call frequency")
        
        if bursts:
            print(f"   • Timeout bursts detected - likely indicates:")
            print(f"     - Network congestion")
            print(f"     - API rate limiting")
            print(f"     - Server-side issues")
            print(f"   • Implement exponential backoff and circuit breakers")
        
        if empty_df_symbols:
            print(f"   • Empty DataFrames often follow timeouts")
            print(f"     Implement retry logic with data validation")
            
    except Exception as e:
        print(f"Error analyzing logs: {e}")

if __name__ == "__main__":
    analyze_timeout_patterns()
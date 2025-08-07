#!/usr/bin/env python3
"""
Simple connection pool monitor that runs as a separate script
"""

import asyncio
import psutil
import time
import json
from datetime import datetime
import subprocess

async def get_connection_stats():
    """Get network connection statistics for the Virtuoso process"""
    try:
        # Find the main.py process
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['cmdline'] and 'main.py' in ' '.join(proc.info['cmdline']):
                pid = proc.info['pid']
                
                # Get connections
                connections = proc.connections(kind='inet')
                
                # Count by state
                stats = {
                    'pid': pid,
                    'timestamp': datetime.now().isoformat(),
                    'total_connections': len(connections),
                    'established': sum(1 for c in connections if c.status == 'ESTABLISHED'),
                    'time_wait': sum(1 for c in connections if c.status == 'TIME_WAIT'),
                    'close_wait': sum(1 for c in connections if c.status == 'CLOSE_WAIT'),
                    'listen': sum(1 for c in connections if c.status == 'LISTEN'),
                    'other': sum(1 for c in connections if c.status not in ['ESTABLISHED', 'TIME_WAIT', 'CLOSE_WAIT', 'LISTEN'])
                }
                
                # Count by remote address (Bybit IPs)
                bybit_connections = sum(1 for c in connections 
                                      if c.raddr and '18.161' in str(c.raddr[0]))
                stats['bybit_connections'] = bybit_connections
                
                # Get CPU and memory
                stats['cpu_percent'] = proc.cpu_percent(interval=1)
                stats['memory_mb'] = proc.memory_info().rss / 1024 / 1024
                
                return stats
                
    except Exception as e:
        return {'error': str(e)}
    
    return {'error': 'Process not found'}

async def monitor_loop():
    """Main monitoring loop"""
    while True:
        stats = await get_connection_stats()
        
        # Log to file
        with open('/tmp/pool_stats.json', 'w') as f:
            json.dump(stats, f)
            
        # Print summary
        if 'error' not in stats:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Connections: {stats['established']}/{stats['total_connections']} "
                  f"(Bybit: {stats['bybit_connections']}) | "
                  f"CPU: {stats['cpu_percent']:.1f}% | "
                  f"Mem: {stats['memory_mb']:.0f}MB")
            
            # Alert on high connection count
            if stats['established'] > 100:
                print(f"⚠️  HIGH CONNECTION COUNT: {stats['established']}")
        else:
            print(f"Error: {stats['error']}")
            
        await asyncio.sleep(60)  # Check every minute

if __name__ == "__main__":
    print("Starting connection pool monitor...")
    print("Press Ctrl+C to stop")
    
    try:
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        print("\nMonitor stopped")
#!/usr/bin/env python3
"""
Fix Bybit timeout issues by increasing timeout and optimizing data fetching
"""
import os
import sys

def fix_bybit_timeouts():
    """Apply timeout fixes to Bybit exchange module"""
    
    bybit_file = "src/core/exchanges/bybit.py"
    
    # Read the file
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Increase general timeout from 10s to 30s
    content = content.replace(
        "async with asyncio.timeout(10.0):",
        "async with asyncio.timeout(30.0):"
    )
    
    # Fix 2: Increase aiohttp timeout
    content = content.replace(
        "timeout = aiohttp.ClientTimeout(total=10)",
        "timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)"
    )
    
    # Fix 3: Update error message
    content = content.replace(
        'self.logger.error(f"Request timeout after 10s: {endpoint}")',
        'self.logger.error(f"Request timeout after 30s: {endpoint}")'
    )
    
    # Fix 4: Add connection pooling limits to reduce concurrent connections
    if "connector = aiohttp.TCPConnector(" in content:
        content = content.replace(
            "connector = aiohttp.TCPConnector(",
            "connector = aiohttp.TCPConnector(limit=30, limit_per_host=10, "
        )
    
    # Write back
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print("✅ Fixed Bybit timeout issues:")
    print("  - Increased timeout from 10s to 30s")
    print("  - Added separate connect and read timeouts")
    print("  - Limited connection pool to prevent overwhelming")
    
    # Also fix the top_symbols to fetch fewer symbols initially
    top_symbols_file = "src/core/market/top_symbols.py"
    
    if os.path.exists(top_symbols_file):
        with open(top_symbols_file, 'r') as f:
            content = f.read()
        
        # Reduce initial symbol count
        content = content.replace(
            "def get_symbols(self, limit: int = 15)",
            "def get_symbols(self, limit: int = 5)"
        )
        
        with open(top_symbols_file, 'w') as f:
            f.write(content)
        
        print("  - Reduced initial symbol fetch from 15 to 5")
    
    return True

if __name__ == "__main__":
    fix_bybit_timeouts()
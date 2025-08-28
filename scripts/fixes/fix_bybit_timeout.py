#!/usr/bin/env python3
"""
Fix for Bybit timeout issues - reduces aggressive timeout values to prevent API failures
"""

import os
import sys

# Add project root to path
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

def fix_bybit_timeouts():
    """Apply timeout fixes to the Bybit exchange module"""
    
    bybit_file = '/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/core/exchanges/bybit.py'
    
    # Read the file
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    print("🔧 Applying Bybit timeout fixes...")
    
    # Fix 1: Reduce aggressive timeout values
    # Change 90s timeout for tickers to 15s
    content = content.replace(
        "timeout_val = 90.0 if 'tickers' in endpoint else 60.0",
        "timeout_val = 15.0 if 'tickers' in endpoint else 10.0"
    )
    
    # Fix 2: Update timeout error message
    content = content.replace(
        "timeout_val = 90 if 'tickers' in endpoint else 60",
        "timeout_val = 15 if 'tickers' in endpoint else 10"
    )
    
    # Fix 3: Reduce POST timeout
    content = content.replace(
        "async with asyncio.timeout(60.0):",
        "async with asyncio.timeout(10.0):"
    )
    
    # Fix 4: Update session timeout configuration for consistency
    content = content.replace(
        """timeout=aiohttp.ClientTimeout(
                    total=30,
                    connect=5,
                    sock_read=25
                )""",
        """timeout=aiohttp.ClientTimeout(
                    total=15,
                    connect=3,
                    sock_read=10
                )"""
    )
    
    # Fix 5: Circuit breaker recovery timeout
    content = content.replace(
        "'recovery_timeout': 60,  # Try again after 60 seconds",
        "'recovery_timeout': 30,  # Try again after 30 seconds"
    )
    
    # Fix 6: Simple session timeout in test function
    content = content.replace(
        "timeout = aiohttp.ClientTimeout(total=60)",
        "timeout = aiohttp.ClientTimeout(total=15)"
    )
    
    # Write back the fixed content
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print("✅ Applied timeout fixes:")
    print("   - Reduced API request timeouts from 60-90s to 10-15s")
    print("   - Updated session timeout from 30s to 15s") 
    print("   - Reduced circuit breaker recovery from 60s to 30s")
    print("   - Made all timeout values consistent")

if __name__ == "__main__":
    fix_bybit_timeouts()
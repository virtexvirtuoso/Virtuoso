#!/usr/bin/env python3
"""Fix request timeout issues in Bybit exchange."""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def fix_session_timeouts():
    """Adjust session timeouts to be more reasonable."""
    
    file_path = PROJECT_ROOT / "src/core/exchanges/bybit.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Update session timeout configuration
    old_timeout_config = """            self.timeout = aiohttp.ClientTimeout(
                total=10,  # Further reduced total timeout
                connect=3,  # Aggressive connection timeout
                sock_read=7,  # Reduced socket read timeout
                sock_connect=3  # Aggressive socket connection timeout
            )"""
    
    new_timeout_config = """            self.timeout = aiohttp.ClientTimeout(
                total=30,  # Reasonable total timeout for API requests
                connect=10,  # Connection establishment timeout
                sock_read=20,  # Socket read timeout for large responses
                sock_connect=10  # Socket connection timeout
            )"""
    
    content = content.replace(old_timeout_config, new_timeout_config)
    
    # Fix 2: Update error message to reflect actual timeout
    old_error_msg = 'self.logger.error(f"Request timeout after 10s: {endpoint}")'
    new_error_msg = 'self.logger.error(f"Request timeout after {self.timeout.total}s: {endpoint}")'
    
    content = content.replace(old_error_msg, new_error_msg)
    
    # Fix 3: Add retry logic for timeout errors in _make_request
    # Find the timeout handling section
    old_timeout_handling = """            except asyncio.TimeoutError:
                self.logger.error(f"Request timeout after {self.timeout.total}s: {endpoint}")
                return {'retCode': -1, 'retMsg': 'Request timeout'}"""
    
    new_timeout_handling = """            except asyncio.TimeoutError:
                self.logger.error(f"Request timeout after {self.timeout.total}s: {endpoint}")
                # Return timeout error that will trigger retry in _make_request_with_retry
                return {'retCode': 10002, 'retMsg': 'Request timeout'}  # 10002 triggers retry"""
    
    content = content.replace(old_timeout_handling, new_timeout_handling)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✓ Fixed session timeout configuration")
    print("  - Increased total timeout: 10s → 30s")
    print("  - Increased connection timeout: 3s → 10s")
    print("  - Increased socket read timeout: 7s → 20s")
    print("  - Fixed error message to show actual timeout")
    print("  - Made timeout errors trigger retry logic")

def add_adaptive_timeouts():
    """Add adaptive timeout based on endpoint type."""
    
    file_path = PROJECT_ROOT / "src/core/exchanges/bybit.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add endpoint-specific timeout configuration
    timeout_config = '''    # Endpoint-specific timeout configuration
    ENDPOINT_TIMEOUTS = {
        'kline': 45,  # Historical data can be large
        'recent-trade': 30,  # Trade history
        'orderbook': 20,  # Order book data
        'tickers': 25,  # Multiple tickers
        'time': 10,  # Server time check
        'default': 30  # Default timeout
    }
'''
    
    # Insert after RATE_LIMITS definition
    insert_marker = "    # Class-level initialization tracking"
    content = content.replace(insert_marker, timeout_config + "\n" + insert_marker)
    
    # Update _make_request to use adaptive timeouts
    old_get_request = """                    async with asyncio.timeout(30.0):
                        async with self.session.get(url, params=params, headers=headers) as response:"""
    
    new_get_request = """                    # Get endpoint-specific timeout
                    endpoint_key = endpoint.split('/')[-1].replace('-', '_')
                    timeout_seconds = self.ENDPOINT_TIMEOUTS.get(endpoint_key, self.ENDPOINT_TIMEOUTS['default'])
                    
                    async with asyncio.timeout(timeout_seconds):
                        async with self.session.get(url, params=params, headers=headers) as response:"""
    
    content = content.replace(old_get_request, new_get_request)
    
    # Same for POST requests
    old_post_request = """                    async with asyncio.timeout(30.0):
                        async with self.session.post(url, json=params, headers=headers) as response:"""
    
    new_post_request = """                    # Get endpoint-specific timeout
                    endpoint_key = endpoint.split('/')[-1].replace('-', '_')
                    timeout_seconds = self.ENDPOINT_TIMEOUTS.get(endpoint_key, self.ENDPOINT_TIMEOUTS['default'])
                    
                    async with asyncio.timeout(timeout_seconds):
                        async with self.session.post(url, json=params, headers=headers) as response:"""
    
    content = content.replace(old_post_request, new_post_request)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✓ Added adaptive timeout configuration")
    print("  - kline: 45s (historical data)")
    print("  - recent-trade: 30s")
    print("  - orderbook: 20s")
    print("  - tickers: 25s")
    print("  - default: 30s")

def main():
    """Apply all timeout fixes."""
    print("Fixing request timeout issues...")
    
    # Create backup
    import shutil
    file_path = PROJECT_ROOT / "src/core/exchanges/bybit.py"
    backup_path = file_path.with_suffix('.py.backup_timeout')
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Apply fixes
    fix_session_timeouts()
    add_adaptive_timeouts()
    
    print("\n✅ All timeout fixes applied successfully!")
    print("\nThese changes will:")
    print("- Reduce timeout errors for data-heavy endpoints")
    print("- Trigger retry logic on timeouts")
    print("- Provide endpoint-specific timeout handling")

if __name__ == "__main__":
    main()
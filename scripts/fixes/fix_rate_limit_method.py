#!/usr/bin/env python3
"""Fix the _check_rate_limit method."""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def fix_check_rate_limit_method():
    """Replace the _check_rate_limit method with the updated version."""
    bybit_file = PROJECT_ROOT / "src/core/exchanges/bybit.py"
    
    with open(bybit_file, 'r') as f:
        lines = f.readlines()
    
    # Find the start of the method
    start_line = None
    for i, line in enumerate(lines):
        if "async def _check_rate_limit(self, endpoint: str, category: str = 'linear') -> None:" in line:
            start_line = i
            break
    
    if start_line is None:
        print("Could not find _check_rate_limit method")
        return False
    
    # Find the end of the method (next method or class end)
    end_line = None
    indent_level = len(lines[start_line]) - len(lines[start_line].lstrip())
    
    for i in range(start_line + 1, len(lines)):
        line = lines[i]
        # Skip empty lines
        if line.strip() == "":
            continue
        
        # Check if we've reached the next method or decreased indentation
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= indent_level and line.strip():
            end_line = i
            break
    
    if end_line is None:
        end_line = len(lines)
    
    # New method implementation
    new_method = '''    async def _check_rate_limit(self, endpoint: str, category: str = 'linear') -> None:
        """Check rate limit using sliding window approach matching Bybit's limits."""
        async with self._rate_limit_lock:
            now = time.time()
            
            # Use global rate limit bucket (600 requests per 5 seconds)
            global_bucket = self._rate_limit_buckets.setdefault('global', [])
            window_start = now - 5.0  # 5-second sliding window
            
            # Clean expired timestamps (older than 5 seconds)
            global_bucket[:] = [ts for ts in global_bucket if ts > window_start]
            
            # Check if we've hit the global limit
            if len(global_bucket) >= 600:
                # Calculate wait time until oldest request expires
                wait_time = global_bucket[0] + 5.0 - now
                if wait_time > 0:
                    self.logger.warning(f"Global rate limit reached (600/5s), waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    # Recursive check after waiting
                    await self._check_rate_limit(endpoint, category)
                    return
            
            # Also check endpoint-specific limits for internal throttling
            endpoint_bucket = self._rate_limit_buckets.setdefault(endpoint, [])
            endpoint_limit = self.RATE_LIMITS['endpoints'].get(endpoint, {'requests': 100, 'per_second': 1})
            
            # Clean expired timestamps for endpoint
            endpoint_window = now - endpoint_limit['per_second']
            endpoint_bucket[:] = [ts for ts in endpoint_bucket if ts > endpoint_window]
            
            # Check endpoint limit
            if len(endpoint_bucket) >= endpoint_limit['requests']:
                wait_time = endpoint_bucket[0] + endpoint_limit['per_second'] - now
                if wait_time > 0:
                    self.logger.debug(f"Endpoint {endpoint} rate limit, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    await self._check_rate_limit(endpoint, category)
                    return
            
            # Check dynamic rate limit from headers
            if hasattr(self, 'rate_limit_status') and self.rate_limit_status['remaining'] < 50:
                self.logger.warning(f"Low rate limit remaining: {self.rate_limit_status['remaining']}")
                # Add small delay to be conservative
                await asyncio.sleep(0.1)
            
            # Record the request timestamp
            global_bucket.append(now)
            endpoint_bucket.append(now)

'''
    
    # Replace the method
    new_lines = lines[:start_line] + [new_method] + lines[end_line:]
    
    with open(bybit_file, 'w') as f:
        f.writelines(new_lines)
    
    print(f"✓ Replaced _check_rate_limit method (lines {start_line+1} to {end_line})")
    return True

if __name__ == "__main__":
    if fix_check_rate_limit_method():
        print("Successfully updated _check_rate_limit method!")
    else:
        print("Failed to update _check_rate_limit method!")
        sys.exit(1)
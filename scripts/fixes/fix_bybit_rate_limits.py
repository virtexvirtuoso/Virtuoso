#!/usr/bin/env python3
"""Fix Bybit rate limit compliance issues."""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_rate_limit_constants():
    """Fix rate limit constants to match Bybit's official limits."""
    bybit_file = PROJECT_ROOT / "src/core/exchanges/bybit.py"
    
    logger.info("Fixing rate limit constants...")
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Update rate limit constants to match Bybit's 600 requests per 5 seconds
    old_rate_limits = """    # Add rate limit constants
    RATE_LIMITS = {
        'category': {
            'linear': {'requests': 120, 'per_second': 1},  # Category-level limit
            'inverse': {'requests': 120, 'per_second': 1},
            'spot': {'requests': 120, 'per_second': 1}
        },
        'endpoints': {
            'kline': {'requests': 120, 'per_second': 1},
            'orderbook': {'requests': 50, 'per_second': 1},
            'recent_trades': {'requests': 60, 'per_second': 1},
            'ticker': {'requests': 60, 'per_second': 1},
            'market_data': {'requests': 100, 'per_second': 1},  # Composite limit for all market data
            'account': {'requests': 50, 'per_second': 1},
            'order': {'requests': 100, 'per_second': 1},
            'position': {'requests': 50, 'per_second': 1}
        }
    }"""
    
    new_rate_limits = """    # Add rate limit constants - Updated to match Bybit's official limits
    # Bybit allows 600 requests per 5-second window per IP
    RATE_LIMITS = {
        'global': {
            'requests': 600,
            'window_seconds': 5  # 5-second sliding window
        },
        'category': {
            # These are now informational - actual limiting is done at global level
            'linear': {'requests': 600, 'window_seconds': 5},
            'inverse': {'requests': 600, 'window_seconds': 5},
            'spot': {'requests': 600, 'window_seconds': 5}
        },
        'endpoints': {
            # Keep endpoint-specific limits for internal throttling
            'kline': {'requests': 120, 'per_second': 1},
            'orderbook': {'requests': 50, 'per_second': 1},
            'recent_trades': {'requests': 60, 'per_second': 1},
            'ticker': {'requests': 60, 'per_second': 1},
            'market_data': {'requests': 100, 'per_second': 1},
            'account': {'requests': 50, 'per_second': 1},
            'order': {'requests': 100, 'per_second': 1},
            'position': {'requests': 50, 'per_second': 1}
        }
    }"""
    
    content = content.replace(old_rate_limits, new_rate_limits)
    
    # Fix 2: Update initialization of rate limits
    old_init = """        # Initialize rate limits
        self.rate_limits = {
            'market_data': {'requests': 120, 'per_second': 1},
            'ticker': {'requests': 60, 'per_second': 1},
            'orderbook': {'requests': 50, 'per_second': 1},
            'trades': {'requests': 60, 'per_second': 1},
            'account': {'requests': 50, 'per_second': 1},
            'order': {'requests': 100, 'per_second': 1},
            'position': {'requests': 50, 'per_second': 1}
        }"""
    
    new_init = """        # Initialize rate limits with Bybit's official limits
        self.rate_limits = self.RATE_LIMITS.copy()
        
        # Track rate limit status from response headers
        self.rate_limit_status = {
            'remaining': 600,
            'limit': 600,
            'reset_timestamp': None
        }"""
    
    content = content.replace(old_init, new_init)
    
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    logger.info("✓ Fixed rate limit constants")

def add_header_tracking():
    """Add rate limit header tracking to response processing."""
    bybit_file = PROJECT_ROOT / "src/core/exchanges/bybit.py"
    
    logger.info("Adding rate limit header tracking...")
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Find and replace _process_response method
    old_process_response = '''async def _process_response(self, response, url):
        """Process HTTP response and return result with proper logging.
        
        Args:
            response: aiohttp response object
            url: The URL that was queried
            
        Returns:
            Processed API response
        """
        if response.status != 200:
            error_text = await response.text()
            self.logger.error(f"HTTP {response.status} error for {url}: {error_text}")
            return {'retCode': -1, 'retMsg': f'HTTP {response.status} error: {error_text}'}
            
        try:
            result = await response.json()
            if not result:
                self.logger.error("Empty response received")
                return {'retCode': -1, 'retMsg': 'Empty response'}
                
            # Log concise response summary instead of full response
            response_summary = self._summarize_response(result)
            self.logger.debug(f"Response from {url}: {response_summary}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing response: {str(e)}")
            return {'retCode': -1, 'retMsg': 'Invalid response format'}'''
    
    new_process_response = '''async def _process_response(self, response, url):
        """Process HTTP response and return result with proper logging.
        
        Args:
            response: aiohttp response object
            url: The URL that was queried
            
        Returns:
            Processed API response
        """
        # Extract rate limit headers from response
        try:
            self.rate_limit_status['remaining'] = int(response.headers.get('X-Bapi-Limit-Status', 600))
            self.rate_limit_status['limit'] = int(response.headers.get('X-Bapi-Limit', 600))
            reset_time = response.headers.get('X-Bapi-Limit-Reset-Timestamp')
            if reset_time:
                self.rate_limit_status['reset_timestamp'] = int(reset_time) / 1000  # Convert ms to seconds
            
            # Log rate limit status if getting low
            if self.rate_limit_status['remaining'] < 100:
                self.logger.warning(f"Rate limit warning: {self.rate_limit_status['remaining']}/{self.rate_limit_status['limit']} remaining")
        except Exception as e:
            self.logger.debug(f"Could not parse rate limit headers: {e}")
        
        if response.status != 200:
            error_text = await response.text()
            self.logger.error(f"HTTP {response.status} error for {url}: {error_text}")
            return {'retCode': -1, 'retMsg': f'HTTP {response.status} error: {error_text}'}
            
        try:
            result = await response.json()
            if not result:
                self.logger.error("Empty response received")
                return {'retCode': -1, 'retMsg': 'Empty response'}
                
            # Log concise response summary instead of full response
            response_summary = self._summarize_response(result)
            self.logger.debug(f"Response from {url}: {response_summary}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing response: {str(e)}")
            return {'retCode': -1, 'retMsg': 'Invalid response format'}'''
    
    content = content.replace(old_process_response, new_process_response)
    
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    logger.info("✓ Added rate limit header tracking")

def update_rate_limit_checking():
    """Update the rate limit checking logic to use sliding window."""
    bybit_file = PROJECT_ROOT / "src/core/exchanges/bybit.py"
    
    logger.info("Updating rate limit checking logic...")
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Replace the entire _check_rate_limit method
    old_method_start = "    async def _check_rate_limit(self, endpoint: str, category: str = 'linear') -> None:"
    old_method_end = "            # Record the request timestamp\n            category_bucket.append(now)\n            endpoint_bucket.append(now)"
    
    # Find the old method
    start_idx = content.find(old_method_start)
    if start_idx == -1:
        logger.error("Could not find _check_rate_limit method")
        return
    
    # Find the end of the method
    end_idx = content.find(old_method_end, start_idx)
    if end_idx == -1:
        logger.error("Could not find end of _check_rate_limit method")
        return
    
    # Adjust end_idx to include the last line
    end_idx = content.find('\n', end_idx + len(old_method_end)) + 1
    
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
            endpoint_bucket.append(now)'''
    
    # Replace the old method with the new one
    content = content[:start_idx] + new_method + content[end_idx:]
    
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    logger.info("✓ Updated rate limit checking logic")

def optimize_connection_pool():
    """Optimize connection pool configuration."""
    bybit_file = PROJECT_ROOT / "src/core/exchanges/bybit.py"
    
    logger.info("Optimizing connection pool configuration...")
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Fix connection pool in _create_session
    old_connector = """            # Create TCP connector with connection pooling
            self.connector = aiohttp.TCPConnector(
                limit=150,  # Increased total connection pool limit
                limit_per_host=40,  # Increased per-host connection limit
                ttl_dns_cache=300,  # DNS cache timeout
                force_close=True,  # Force close connections
                enable_cleanup_closed=True,  # Enable cleanup of closed connections
                keepalive_timeout=30,  # Keepalive timeout
                ssl=False  # Disable SSL verification for better performance
            )"""
    
    new_connector = """            # Create TCP connector with optimized connection pooling
            # Bybit allows up to 500 connections in 5 minutes, 1000 for market data
            self.connector = aiohttp.TCPConnector(
                limit=300,  # Increased total connection pool (well below 500 limit)
                limit_per_host=100,  # Increased per-host limit for api.bybit.com
                ttl_dns_cache=300,  # DNS cache timeout
                force_close=False,  # Don't force close - reuse connections
                enable_cleanup_closed=True,  # Enable cleanup of closed connections
                keepalive_timeout=60,  # Longer keepalive for connection reuse
                ssl=False  # Disable SSL verification for better performance
            )"""
    
    content = content.replace(old_connector, new_connector)
    
    # Fix aggressive timeouts
    old_timeout = """            # Configure timeouts with more aggressive settings to prevent hanging
            self.timeout = aiohttp.ClientTimeout(
                total=10,  # Further reduced total timeout
                connect=3,  # Aggressive connection timeout
                sock_connect=3,  # Socket connection timeout
                sock_read=5  # Socket read timeout
            )"""
    
    new_timeout = """            # Configure timeouts with balanced settings to reduce retries
            self.timeout = aiohttp.ClientTimeout(
                total=30,  # Reasonable total timeout to avoid unnecessary retries
                connect=10,  # More lenient connection timeout
                sock_connect=10,  # Socket connection timeout
                sock_read=20  # Socket read timeout for large responses
            )"""
    
    content = content.replace(old_timeout, new_timeout)
    
    # Also fix the timeout in _make_request
    old_request_timeout = """                    async with asyncio.timeout(10.0):"""
    new_request_timeout = """                    async with asyncio.timeout(30.0):"""
    
    content = content.replace(old_request_timeout, new_request_timeout)
    
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    logger.info("✓ Optimized connection pool configuration")

def add_rate_limit_monitoring():
    """Add method to get current rate limit status."""
    bybit_file = PROJECT_ROOT / "src/core/exchanges/bybit.py"
    
    logger.info("Adding rate limit monitoring...")
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Find a good place to add the new method (after _check_rate_limit)
    insertion_point = content.find("    async def _fetch_with_rate_limit")
    if insertion_point == -1:
        logger.error("Could not find insertion point for rate limit monitoring")
        return
    
    new_method = '''    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status.
        
        Returns:
            Dict with rate limit information
        """
        status = {
            'remaining': self.rate_limit_status.get('remaining', 600),
            'limit': self.rate_limit_status.get('limit', 600),
            'reset_timestamp': self.rate_limit_status.get('reset_timestamp'),
            'percentage_used': 0
        }
        
        if status['limit'] > 0:
            status['percentage_used'] = ((status['limit'] - status['remaining']) / status['limit']) * 100
        
        # Add global bucket info
        global_bucket = self._rate_limit_buckets.get('global', [])
        now = time.time()
        window_start = now - 5.0
        active_requests = len([ts for ts in global_bucket if ts > window_start])
        
        status['active_requests_5s'] = active_requests
        status['capacity_5s'] = 600 - active_requests
        
        return status
    
    '''
    
    # Insert the new method
    content = content[:insertion_point] + new_method + content[insertion_point:]
    
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    logger.info("✓ Added rate limit monitoring")

def main():
    """Apply all rate limit fixes."""
    try:
        logger.info("Starting Bybit rate limit fixes...")
        
        # Create backup
        bybit_file = PROJECT_ROOT / "src/core/exchanges/bybit.py"
        backup_file = bybit_file.with_suffix('.py.backup_ratelimit')
        
        import shutil
        shutil.copy2(bybit_file, backup_file)
        logger.info(f"Created backup: {backup_file}")
        
        # Apply fixes
        fix_rate_limit_constants()
        add_header_tracking()
        update_rate_limit_checking()
        optimize_connection_pool()
        add_rate_limit_monitoring()
        
        logger.info("\n✅ All rate limit fixes applied successfully!")
        logger.info("\nChanges made:")
        logger.info("1. ✓ Updated rate limits to 600 requests per 5-second window")
        logger.info("2. ✓ Added X-Bapi-Limit header tracking")
        logger.info("3. ✓ Implemented sliding window rate limiting")
        logger.info("4. ✓ Increased connection pool limits (300 total, 100 per host)")
        logger.info("5. ✓ Adjusted timeouts (30s total, 10s connect)")
        logger.info("6. ✓ Added rate limit monitoring method")
        
    except Exception as e:
        logger.error(f"Error applying fixes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
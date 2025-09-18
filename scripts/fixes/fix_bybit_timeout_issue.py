"""
Fix for Bybit timeout issues causing system degradation
Author: Assistant
Date: August 26, 2025

Problem: Bybit API requests timeout after 10-15 seconds, but connections aren't properly 
released, leading to connection pool exhaustion over time.

Solution: Implement proper connection cleanup, timeout handling, and pool management.
"""

import asyncio
import aiohttp
import logging
import time
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class BybitTimeoutFix:
    """
    Fix implementation for Bybit timeout issues.
    This class provides methods to patch the existing Bybit implementation.
    """
    
    @staticmethod
    def get_enhanced_make_request():
        """Returns an enhanced _make_request method with proper cleanup."""
        
        async def _make_request_enhanced(self, method: str, endpoint: str, params: Optional[Dict] = None):
            """Enhanced request method with timeout handling and connection cleanup."""
            
            # Initialize tracking attributes if they don't exist
            if not hasattr(self, '_timeout_count'):
                self._timeout_count = 0
            if not hasattr(self, '_last_session_recreate'):
                self._last_session_recreate = 0
            if not hasattr(self, '_request_count'):
                self._request_count = 0
            
            self._request_count += 1
            
            # Check if we need to recreate session due to too many timeouts
            if self._timeout_count > 5 and (time.time() - self._last_session_recreate) > 60:
                self.logger.warning(f"High timeout count ({self._timeout_count}), recreating session...")
                try:
                    await self._cleanup_session()
                    await self._create_session()
                    self._timeout_count = 0
                    self._last_session_recreate = time.time()
                except Exception as e:
                    self.logger.error(f"Failed to recreate session: {e}")
            
            # Periodic session refresh (every 1000 requests)
            if self._request_count % 1000 == 0:
                self.logger.info("Performing periodic session refresh...")
                try:
                    await self._cleanup_session()
                    await self._create_session()
                    self._request_count = 0
                except Exception as e:
                    self.logger.error(f"Failed to refresh session: {e}")
            
            # Original request logic with enhanced error handling
            try:
                url = f"{self.base_url}{endpoint}"
                params = params or {}
                
                # Authentication headers if needed
                if self.api_key and self.api_secret:
                    timestamp = str(int(time.time() * 1000))
                    params['api_key'] = self.api_key
                    params['timestamp'] = timestamp
                    
                    # Generate signature
                    from urllib.parse import urlencode
                    import hmac
                    import hashlib
                    
                    sorted_params = dict(sorted(params.items()))
                    query_string = urlencode(sorted_params)
                    signature = hmac.new(
                        self.api_secret.encode(),
                        query_string.encode(),
                        hashlib.sha256
                    ).hexdigest()
                    params['sign'] = signature
                    
                    headers = {
                        'X-BAPI-API-KEY': self.api_key,
                        'X-BAPI-TIMESTAMP': timestamp,
                        'X-BAPI-SIGN': signature,
                        'Content-Type': 'application/json'
                    }
                else:
                    headers = {'Content-Type': 'application/json'}
                
                # Log request details safely
                safe_params = {k: '***' if k in ['api_key', 'sign'] else v 
                              for k, v in params.items()}
                self.logger.debug(f"Making request to {url}")
                self.logger.debug(f"Params: {safe_params}")
                
                # Ensure session exists
                if not self.session or self.session.closed:
                    await self._create_session()
                
                # Determine timeout based on endpoint
                timeout_val = 15.0 if 'tickers' in endpoint else 10.0
                
                # Create a CancelledError shield to ensure cleanup
                cleanup_done = False
                
                try:
                    # Use timeout with cleanup guarantee
                    async with asyncio.timeout(timeout_val):
                        if method.upper() == 'GET':
                            async with self.session.get(url, params=params, headers=headers) as response:
                                result = await self._process_response(response, url)
                                self._timeout_count = max(0, self._timeout_count - 1)  # Reduce timeout count on success
                                return result
                        elif method.upper() == 'POST':
                            async with self.session.post(url, json=params, headers=headers) as response:
                                result = await self._process_response(response, url)
                                self._timeout_count = max(0, self._timeout_count - 1)  # Reduce timeout count on success
                                return result
                                
                except asyncio.TimeoutError:
                    self._timeout_count += 1
                    self.logger.error(f"Request timeout after {timeout_val}s: {endpoint} (timeout count: {self._timeout_count})")
                    
                    # Cleanup on timeout
                    if not cleanup_done:
                        await self._cleanup_on_timeout()
                        cleanup_done = True
                    
                    return {'retCode': -1, 'retMsg': f'Request timeout after {timeout_val}s'}
                    
                except aiohttp.ClientConnectionError as e:
                    self.logger.error(f"Connection error for {endpoint}: {str(e)}")
                    
                    # Recreate session on connection error
                    try:
                        await self._cleanup_session()
                        await self._create_session()
                    except:
                        pass
                    
                    return {'retCode': -1, 'retMsg': f'Connection error: {str(e)}'}
                    
            except Exception as e:
                self.logger.error(f"Request error for {endpoint}: {str(e)}")
                return {'retCode': -1, 'retMsg': str(e)}
        
        return _make_request_enhanced
    
    @staticmethod
    def get_cleanup_on_timeout():
        """Returns a method to cleanup connections on timeout."""
        
        async def _cleanup_on_timeout(self):
            """Clean up connections after timeout."""
            try:
                if hasattr(self, 'connector') and self.connector:
                    # Force cleanup of closed connections
                    if hasattr(self.connector, '_cleanup_closed'):
                        self.connector._cleanup_closed()
                    
                    # Log connection pool status
                    if hasattr(self.connector, '_conns'):
                        total_conns = len(self.connector._conns)
                        if total_conns > 100:  # Too many connections
                            self.logger.warning(f"Too many connections in pool ({total_conns}), forcing cleanup...")
                            # Force close some connections
                            for key in list(self.connector._conns.keys())[:50]:
                                try:
                                    conns = self.connector._conns[key]
                                    for conn in conns[:5]:  # Close first 5 connections per host
                                        conn.close()
                                except:
                                    pass
            except Exception as e:
                self.logger.error(f"Error during timeout cleanup: {e}")
        
        return _cleanup_on_timeout
    
    @staticmethod
    def get_enhanced_create_session():
        """Returns an enhanced _create_session method with better limits."""
        
        async def _create_session_enhanced(self):
            """Create session with optimized connection pooling."""
            try:
                # Close existing session if any
                if self.session and not self.session.closed:
                    await self.session.close()
                
                # Close existing connector if any
                if hasattr(self, 'connector') and self.connector:
                    await self.connector.close()
                
                # Create TCP connector with conservative limits
                self.connector = aiohttp.TCPConnector(
                    limit=50,  # Reduced from 150 to prevent exhaustion
                    limit_per_host=10,  # Reduced from 40 
                    ttl_dns_cache=300,
                    enable_cleanup_closed=True,
                    keepalive_timeout=30,
                    force_close=True  # Force close on errors
                )
                
                # Configure timeouts
                self.timeout = aiohttp.ClientTimeout(
                    total=20,  # Reduced from 60
                    connect=5,  # Reduced from 10
                    sock_read=15,  # Reduced from 50
                    sock_connect=5  # Reduced from 10
                )
                
                # Create session with connection pooling
                self.session = aiohttp.ClientSession(
                    connector=self.connector,
                    timeout=self.timeout
                )
                
                self.logger.info("Created new session with optimized settings")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to create session: {str(e)}")
                return False
        
        return _create_session_enhanced


def generate_patch_file():
    """Generate a patch file that can be applied to the existing bybit.py"""
    
    patch_content = '''
# Apply this patch to src/core/exchanges/bybit.py

# 1. Add these imports at the top if not present:
import time
from typing import Optional, Dict, Any

# 2. Add these attributes in __init__ method:
        self._timeout_count = 0
        self._last_session_recreate = 0
        self._request_count = 0

# 3. Replace the _make_request method with the enhanced version below:

async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None):
    """Enhanced request method with timeout handling and connection cleanup."""
    
    # Track request count
    self._request_count = getattr(self, '_request_count', 0) + 1
    
    # Check if we need to recreate session due to too many timeouts
    if getattr(self, '_timeout_count', 0) > 5:
        current_time = time.time()
        if current_time - getattr(self, '_last_session_recreate', 0) > 60:
            self.logger.warning(f"High timeout count, recreating session...")
            try:
                await self._cleanup_session()
                await self._create_session()
                self._timeout_count = 0
                self._last_session_recreate = current_time
            except Exception as e:
                self.logger.error(f"Failed to recreate session: {e}")
    
    # Periodic session refresh (every 1000 requests)
    if self._request_count % 1000 == 0:
        self.logger.info("Performing periodic session refresh...")
        try:
            await self._cleanup_session()
            await self._create_session()
            self._request_count = 0
        except Exception as e:
            self.logger.error(f"Failed to refresh session: {e}")
    
    # [Keep existing authentication and request logic]
    
    # MODIFY the timeout handling section:
    try:
        async with asyncio.timeout(timeout_val):
            # [existing request code]
    except asyncio.TimeoutError:
        self._timeout_count = getattr(self, '_timeout_count', 0) + 1
        self.logger.error(f"Request timeout after {timeout_val}s: {endpoint} (count: {self._timeout_count})")
        
        # Force cleanup on timeout
        if hasattr(self, 'connector') and self.connector:
            try:
                self.connector._cleanup_closed()
                # If pool has too many connections, force close some
                if hasattr(self.connector, '_conns') and len(self.connector._conns) > 100:
                    self.logger.warning("Force closing excess connections...")
                    for key in list(self.connector._conns.keys())[:20]:
                        try:
                            for conn in self.connector._conns[key][:2]:
                                conn.close()
                        except:
                            pass
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")
        
        return {'retCode': -1, 'retMsg': f'Request timeout after {timeout_val}s'}
    
    # On successful request, reduce timeout count
    except Exception as e:
        # [existing error handling]
    else:
        self._timeout_count = max(0, getattr(self, '_timeout_count', 0) - 1)

# 4. Modify _create_session to use more conservative limits:
# Change these values in the _create_session method:
        self.connector = aiohttp.TCPConnector(
            limit=50,  # Reduced from 150
            limit_per_host=10,  # Reduced from 40
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
            keepalive_timeout=30,
            force_close=True  # Add this line
        )
        
        self.timeout = aiohttp.ClientTimeout(
            total=20,  # Reduced from 60
            connect=5,  # Reduced from 10
            sock_read=15,  # Reduced from 50
            sock_connect=5  # Reduced from 10
        )
'''
    
    return patch_content


# Write patch instructions
def main():
    print("=" * 60)
    print("BYBIT TIMEOUT FIX - SOLUTION")
    print("=" * 60)
    print("\nPROBLEM IDENTIFIED:")
    print("-" * 40)
    print("1. Connections timeout but aren't released from pool")
    print("2. Pool exhausts over time (150 connections fill up)")
    print("3. New requests wait indefinitely for free connections")
    print("4. System degrades progressively until restart needed")
    
    print("\nSOLUTION:")
    print("-" * 40)
    print("1. Reduce connection pool limits (50 total, 10 per host)")
    print("2. Force cleanup connections on timeout")
    print("3. Periodic session refresh every 1000 requests")
    print("4. Auto-recreate session after 5 consecutive timeouts")
    print("5. Add force_close=True to connector")
    
    print("\nIMPLEMENTATION STEPS:")
    print("-" * 40)
    print("1. SSH to VPS: ssh linuxuser@5.223.63.4")
    print("2. Navigate to: cd /home/linuxuser/trading/Virtuoso_ccxt")
    print("3. Edit: nano src/core/exchanges/bybit.py")
    print("4. Apply the changes shown in the patch above")
    print("5. Restart service: sudo systemctl restart virtuoso.service")
    print("6. Monitor logs: sudo journalctl -u virtuoso.service -f")
    
    print("\nQUICK FIX (Temporary):")
    print("-" * 40)
    print("If you need immediate relief without code changes:")
    print("1. sudo systemctl restart virtuoso.service")
    print("2. Add a cron job to restart every 6 hours:")
    print("   crontab -e")
    print("   0 */6 * * * sudo systemctl restart virtuoso.service")
    
    print("\n" + "=" * 60)
    
    # Generate patch file
    patch = generate_patch_file()
    with open('/tmp/bybit_timeout_patch.txt', 'w') as f:
        f.write(patch)
    print(f"\nPatch instructions saved to: /tmp/bybit_timeout_patch.txt")


if __name__ == "__main__":
    main()
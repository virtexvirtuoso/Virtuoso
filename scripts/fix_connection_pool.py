#!/usr/bin/env python3
"""
Fix connection pool issues in Bybit exchange
"""

import os
import sys

# Read the bybit.py file
bybit_path = "src/core/exchanges/bybit.py"

with open(bybit_path, 'r') as f:
    content = f.read()

# Fix 1: Ensure single session instance
fix1 = """
    async def initialize(self) -> bool:
        \"\"\"Initialize exchange connection and verify API credentials.
        
        Returns:
            bool: True if initialization successful, False otherwise
        \"\"\"
        try:
            self.logger.info(f"Initializing {self.exchange_id} exchange...")
            
            # Clean up any existing session first
            await self._cleanup_session()
            
            # Initialize session with proper connection pooling
            self.connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool
                limit_per_host=30,  # Per-host limit
                ttl_dns_cache=300,
                enable_cleanup_closed=True,  # Clean up closed connections
                force_close=True,  # Force close connections on cleanup
                keepalive_timeout=30
            )
            
            self.timeout = aiohttp.ClientTimeout(
                total=30,
                connect=5,
                sock_read=25
            )
            
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=self.timeout
            )
"""

# Fix 2: Add session cleanup method
cleanup_method = """
    async def _cleanup_session(self):
        \"\"\"Clean up existing session and connector\"\"\"
        try:
            if hasattr(self, 'session') and self.session:
                await self.session.close()
                self.session = None
            
            if hasattr(self, 'connector') and self.connector:
                await self.connector.close()
                self.connector = None
        except Exception as e:
            self.logger.warning(f"Error during session cleanup: {e}")
"""

# Fix 3: Reuse session in health check
health_check_fix = """
    async def health_check(self) -> bool:
        \"\"\"Check if the exchange is healthy and accessible.
        
        Returns:
            bool: True if exchange is healthy, False otherwise
        \"\"\"
        try:
            # Use existing session instead of creating new one
            if not self.session:
                self.logger.error("No session available for health check")
                return False
                
            url = f"{self.rest_endpoint}/v5/market/time"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        return True
            return False
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
"""

print("Connection Pool Fixes:")
print("=" * 50)
print("\n1. Single Session Management:")
print("   - Cleanup existing sessions before creating new ones")
print("   - Add connection pool limits and timeouts")
print("   - Enable automatic cleanup of closed connections")

print("\n2. Session Reuse:")
print("   - Health checks reuse existing session")
print("   - No temporary session creation")

print("\n3. Connection Limits:")
print("   - Total pool: 100 connections")
print("   - Per-host: 30 connections")
print("   - Keepalive timeout: 30 seconds")

print("\n4. Memory Management:")
print("   - Force close connections on cleanup")
print("   - TTL for DNS cache: 5 minutes")

print("\nTo apply these fixes:")
print("1. Review the changes above")
print("2. Manually update src/core/exchanges/bybit.py")
print("3. Test locally before deploying to VPS")
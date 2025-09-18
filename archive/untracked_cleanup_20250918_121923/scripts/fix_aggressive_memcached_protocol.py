#!/usr/bin/env python3
"""
Aggressive fix for memcached protocol confusion issues

This script implements a more aggressive approach to fix the persistent
"stats set failed: bytearray(b'END')" errors by:

1. Reducing connection pool size to 1 (eliminate pool conflicts)
2. Adding immediate connection reset on any protocol error
3. Adding connection reuse prevention after errors
4. Adding circuit breaker pattern for memcached
5. Enhanced error pattern detection
"""

import os
import re

def apply_aggressive_memcached_fixes():
    """Apply aggressive fixes to cache adapter for protocol confusion"""
    
    file_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/api/cache_adapter_direct.py"
    
    print("🔧 Applying aggressive memcached protocol fixes...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 1. Reduce connection pool to size 1 to eliminate concurrency issues
    content = re.sub(
        r'pool_size=5',
        'pool_size=1',
        content
    )
    
    # 2. Add connection reset tracking
    init_addition = '''        
        # Aggressive protocol confusion protection
        self._memcached_reset_count = 0
        self._memcached_last_reset = 0
        self._memcached_circuit_breaker_open = False
        self._memcached_consecutive_errors = 0'''
    
    # Add the tracking variables to __init__
    content = content.replace(
        'self.max_retry_delay = 2.0',
        'self.max_retry_delay = 2.0' + init_addition
    )
    
    # 3. Enhance the _get_memcached_client method with aggressive reset logic
    enhanced_client_method = '''    async def _get_memcached_client(self):
        """Get or create Memcached client with aggressive protocol safety"""
        import time
        
        # Check circuit breaker - if too many errors, disable memcached temporarily
        if self._memcached_circuit_breaker_open:
            if time.time() - self._memcached_last_reset > 60:  # Reset after 60 seconds
                self._memcached_circuit_breaker_open = False
                self._memcached_consecutive_errors = 0
                logger.info("Memcached circuit breaker reset - re-enabling memcached")
            else:
                logger.debug("Memcached circuit breaker is open - skipping memcached")
                raise Exception("Memcached circuit breaker is open")
        
        # Always create a fresh client if we had recent protocol errors
        if self._memcached_consecutive_errors > 2:
            logger.warning(f"Creating fresh memcached client due to {self._memcached_consecutive_errors} consecutive errors")
            self._memcached_client = None
            self._memcached_reset_count += 1
            self._memcached_last_reset = time.time()
        
        if self._memcached_client is None:
            try:
                # Aggressive approach: Use single connection to avoid pooling issues
                self._memcached_client = aiomcache.Client(
                    self.memcached_host, 
                    self.memcached_port, 
                    pool_size=1            # Single connection to eliminate pool conflicts
                )
                logger.debug("Created fresh memcached client with single connection")
            except Exception as e:
                logger.error(f"Failed to create memcached client: {e}")
                self._memcached_consecutive_errors += 1
                if self._memcached_consecutive_errors >= 5:
                    self._memcached_circuit_breaker_open = True
                    logger.error("Memcached circuit breaker opened due to client creation failures")
                raise
        
        return self._memcached_client'''
    
    # Replace the existing _get_memcached_client method
    content = re.sub(
        r'    async def _get_memcached_client\(self\):.*?return self\._memcached_client',
        enhanced_client_method,
        content,
        flags=re.DOTALL
    )
    
    # 4. Add protocol error detection and handling method
    protocol_error_handler = '''
    def _handle_protocol_error(self, error_msg: str, key: str):
        """Handle memcached protocol errors aggressively"""
        import time
        
        protocol_indicators = [
            "stats set failed",
            "bytearray(b'END')",
            "bytearray(b'VALUE",
            "protocol error",
            "connection lost",
            "broken pipe"
        ]
        
        is_protocol_error = any(indicator in error_msg for indicator in protocol_indicators)
        
        if is_protocol_error:
            logger.warning(f"Protocol confusion detected in: {error_msg}")
            
            # Immediately reset client connection
            if self._memcached_client:
                try:
                    self._memcached_client.close()
                except:
                    pass
                self._memcached_client = None
            
            self._memcached_consecutive_errors += 1
            self._memcached_last_reset = time.time()
            
            # Open circuit breaker if too many consecutive protocol errors
            if self._memcached_consecutive_errors >= 3:
                self._memcached_circuit_breaker_open = True
                logger.error(f"Memcached circuit breaker opened due to {self._memcached_consecutive_errors} consecutive protocol errors")
            
            return True
        
        return False'''
    
    # Add the protocol error handler before the _set method
    content = content.replace(
        'async def _set(self, key: str, value: Any, ttl: int = 3600) -> bool:',
        protocol_error_handler + '\n\n    async def _set(self, key: str, value: Any, ttl: int = 3600) -> bool:'
    )
    
    # 5. Update the _set method to use the protocol error handler
    enhanced_set_retry_logic = '''                error_msg = str(e)
                logger.error(f"Memcached write error for {key}: {error_msg} (attempt {attempt + 1})")
                
                # Use aggressive protocol error handling
                if self._handle_protocol_error(error_msg, key):
                    # Protocol error detected - skip remaining retries and force fallback
                    logger.warning(f"Protocol error for {key} - forcing fallback to Redis")
                    break
                else:
                    # Non-protocol error - continue with normal retry logic
                    if attempt == max_retries - 1:
                        break'''
    
    # Replace the error handling in _set method
    content = content.replace(
        '''                error_msg = str(e)
                logger.error(f"Memcached write error for {key}: {error_msg} (attempt {attempt + 1})")
                
                # Check for protocol confusion indicators
                if "stats set failed" in error_msg or "END" in error_msg or "VALUE" in error_msg:
                    logger.warning(f"Protocol confusion detected for {key}, resetting client")
                    self._memcached_client = None
                    
                    # If this is the last attempt, try Redis fallback immediately
                    if attempt == max_retries - 1:
                        break
                else:
                    # For other errors, break immediately
                    break''',
        enhanced_set_retry_logic
    )
    
    # 6. Add success tracking to reset consecutive errors
    success_tracking = '''                if result is True:
                    success = True
                    # Reset error counter on successful operation
                    self._memcached_consecutive_errors = 0
                    logger.debug(f"Set Memcached cache for {key} with TTL={ttl}s")
                    break'''
    
    content = content.replace(
        '''                if result is True:
                    success = True
                    logger.debug(f"Set Memcached cache for {key} with TTL={ttl}s")
                    break''',
        success_tracking
    )
    
    # Write the enhanced file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Applied aggressive memcached protocol fixes")
    return True

def create_test_protocol_errors():
    """Create a test script to verify the aggressive fixes"""
    
    test_script = '''#!/usr/bin/env python3
"""
Test aggressive memcached protocol error fixes
"""
import asyncio
import sys
import os
sys.path.append('/home/linuxuser/trading/Virtuoso_ccxt/src')

from src.api.cache_adapter_direct import DirectCacheAdapter

async def test_protocol_error_handling():
    """Test the aggressive protocol error handling"""
    
    print("🔬 Testing Aggressive Protocol Error Handling")
    print("=" * 60)
    
    cache = DirectCacheAdapter()
    
    # Test many concurrent operations to trigger protocol issues
    print("📝 Testing high-concurrency operations...")
    
    tasks = []
    for i in range(100):  # High number to stress test
        key = f"stress_test:{i}"
        value = {"test": i, "data": "x" * 100}  # Some data
        task = cache._set(key, value, ttl=30)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successes = sum(1 for r in results if r is True)
    errors = sum(1 for r in results if isinstance(r, Exception))
    failures = len(results) - successes - errors
    
    print(f"✅ Successful operations: {successes}")
    print(f"❌ Failed operations: {failures}")
    print(f"🚨 Exceptions: {errors}")
    
    # Check circuit breaker status
    print(f"\\n⚡ Circuit breaker status:")
    print(f"   Open: {cache._memcached_circuit_breaker_open}")
    print(f"   Consecutive errors: {cache._memcached_consecutive_errors}")
    print(f"   Reset count: {cache._memcached_reset_count}")
    
    # Test health check
    print(f"\\n🏥 Health check:")
    try:
        health = await cache._check_memcached_health()
        print(f"   Status: {'✅ Healthy' if health else '❌ Unhealthy'}")
    except Exception as e:
        print(f"   Status: ❌ Error - {e}")
    
    print(f"\\n🎯 Stress test completed")

if __name__ == "__main__":
    asyncio.run(test_protocol_error_handling())
'''
    
    with open("/Users/ffv_macmini/Desktop/Virtuoso_ccxt/test_aggressive_protocol_fixes.py", 'w') as f:
        f.write(test_script)
    
    print("✅ Created aggressive protocol test script")

def main():
    """Main function to apply all aggressive fixes"""
    
    print("🚀 Applying Aggressive Memcached Protocol Fixes")
    print("=" * 70)
    
    try:
        apply_aggressive_memcached_fixes()
        create_test_protocol_errors()
        
        print("\\n✅ All aggressive fixes applied successfully!")
        print("\\nNext steps:")
        print("1. Deploy to VPS")
        print("2. Restart service")
        print("3. Monitor for significant reduction in protocol errors")
        print("4. Test with: python3 test_aggressive_protocol_fixes.py")
        
    except Exception as e:
        print(f"❌ Error applying aggressive fixes: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
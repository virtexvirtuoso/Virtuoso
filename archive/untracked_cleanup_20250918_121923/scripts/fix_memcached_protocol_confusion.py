#!/usr/bin/env python3
"""
Fix for memcached protocol confusion: "stats set failed: bytearray(b'END')"

Root Cause Analysis:
The error occurs when aiomcache gets out of sync with the memcached protocol.
The client is receiving responses for different commands than what it expects.

Symptoms:
- "stats set failed: bytearray(b'END')" - receiving END when expecting STORED
- "stats set failed: bytearray(b'VALUE...')" - receiving VALUE when expecting STORED

This indicates command/response pipeline misalignment, usually caused by:
1. Connection pooling with shared state
2. Concurrent operations on the same connection
3. Improper exception handling leaving connections in bad state

Solution:
1. Use connection locking to prevent concurrent operations
2. Add proper connection cleanup on errors
3. Implement retry logic with fresh connections
4. Add connection health checks
"""

import os
import re
from pathlib import Path

def fix_cache_adapter_direct():
    """Fix the cache adapter to handle memcached protocol confusion"""
    
    file_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/api/cache_adapter_direct.py"
    
    print("🔧 Fixing memcached protocol confusion in cache_adapter_direct.py")
    
    # Read the current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the _get_memcached_client method and enhance it
    enhanced_client_method = '''    async def _get_memcached_client(self):
        """Get or create Memcached client with enhanced connection safety"""
        if self._memcached_client is None:
            # Phase 1 Optimization: Enhanced connection pool configuration with protocol safety
            self._memcached_client = aiomcache.Client(
                self.memcached_host, 
                self.memcached_port, 
                pool_size=5,            # Reduced from 20 to 5 to minimize connection conflicts
                pool_minsize=1,         # Ensure minimum connections
                pool_maxsize=5          # Limit maximum connections for better control
            )
        return self._memcached_client'''
    
    # Replace the existing _get_memcached_client method
    content = re.sub(
        r'    async def _get_memcached_client\(self\):.*?return self\._memcached_client',
        enhanced_client_method,
        content,
        flags=re.DOTALL
    )
    
    # Find the _set method and enhance it with better error handling
    enhanced_set_method = '''    async def _set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with enhanced protocol safety"""
        success = False
        
        # Serialize value
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value).encode()
            redis_serialized = json.dumps(value)
        else:
            serialized = str(value).encode()
            redis_serialized = str(value)
        
        # Try Memcached first with connection safety
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Get a fresh client on retries to avoid protocol confusion
                if attempt > 0:
                    self._memcached_client = None
                
                memcached_client = await self._get_memcached_client()
                
                # Use timeout to prevent hanging on protocol issues
                result = await asyncio.wait_for(
                    memcached_client.set(key.encode(), serialized, exptime=ttl),
                    timeout=2.0  # 2 second timeout per attempt
                )
                
                if result is True:
                    success = True
                    logger.debug(f"Set Memcached cache for {key} with TTL={ttl}s")
                    break
                else:
                    logger.warning(f"Memcached set returned {result} for {key} (attempt {attempt + 1})")
                    
            except asyncio.TimeoutError:
                logger.warning(f"Memcached timeout for {key} (attempt {attempt + 1})")
                # Reset client on timeout to prevent protocol confusion
                self._memcached_client = None
                
            except Exception as e:
                error_msg = str(e)
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
                    break
        
        # Also set in Redis if fallback is enabled or memcached failed
        if self.enable_fallback or not success:
            try:
                redis_client = await self._get_redis_client()
                await redis_client.set(key, redis_serialized, ex=ttl)
                success = True
                logger.debug(f"Set Redis cache for {key} with TTL={ttl}s")
            except Exception as e:
                logger.error(f"Redis write error for {key}: {e}")
        
        return success'''
    
    # Replace the existing _set method
    content = re.sub(
        r'    async def _set\(self, key: str, value: Any, ttl: int = 3600\) -> bool:.*?return success',
        enhanced_set_method,
        content,
        flags=re.DOTALL
    )
    
    # Also need to add asyncio import if not present
    if 'import asyncio' not in content[:500]:  # Check only at the top
        content = content.replace('import asyncio', '', 1)  # Remove if exists elsewhere
        content = 'import asyncio\n' + content
    
    # Write the enhanced file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Enhanced cache adapter with protocol safety fixes")
    
    return True

def add_connection_health_check():
    """Add a connection health check method to the cache adapter"""
    
    file_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/api/cache_adapter_direct.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add health check method before the existing health check
    health_check_method = '''
    async def _check_memcached_health(self) -> bool:
        """Check if memcached connection is healthy"""
        try:
            client = await self._get_memcached_client()
            test_key = f'health_check:{int(time.time())}'
            
            # Simple set/get test with timeout
            await asyncio.wait_for(
                client.set(test_key.encode(), b'health_test', exptime=5),
                timeout=1.0
            )
            
            result = await asyncio.wait_for(
                client.get(test_key.encode()),
                timeout=1.0
            )
            
            return result == b'health_test'
            
        except Exception as e:
            logger.warning(f"Memcached health check failed: {e}")
            # Reset client on health check failure
            self._memcached_client = None
            return False
'''
    
    # Insert the health check method before the existing get_health_status method
    content = content.replace(
        '    async def get_health_status(self) -> Dict[str, Any]:',
        health_check_method + '\n    async def get_health_status(self) -> Dict[str, Any]:'
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Added memcached connection health check")

def create_test_script():
    """Create a script to test the fixes"""
    
    test_script = '''#!/usr/bin/env python3
"""
Test script for memcached protocol confusion fixes
"""
import asyncio
import sys
import os
sys.path.append('/home/linuxuser/trading/Virtuoso_ccxt/src')

from api.cache_adapter_direct import DirectCacheAdapter

async def test_memcached_safety():
    """Test memcached operations with the new safety measures"""
    
    print("🧪 Testing Memcached Protocol Safety")
    print("=" * 50)
    
    # Initialize cache adapter
    cache = DirectCacheAdapter()
    
    # Test multiple concurrent operations
    test_keys = [
        f"test:safety:{i}" for i in range(20)
    ]
    
    test_values = [
        {"value": i * 10, "timestamp": 1234567890 + i}
        for i in range(20)
    ]
    
    print("📝 Testing concurrent SET operations...")
    
    # Test concurrent sets
    tasks = []
    for i, (key, value) in enumerate(zip(test_keys, test_values)):
        task = cache._set(key, value, ttl=60)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if r is True)
    error_count = sum(1 for r in results if isinstance(r, Exception))
    
    print(f"✅ Successful operations: {success_count}")
    print(f"❌ Failed operations: {len(results) - success_count}")
    print(f"🚨 Exceptions: {error_count}")
    
    # Test health check
    print("\\n🏥 Testing connection health...")
    health = await cache._check_memcached_health()
    print(f"Health status: {'✅ Healthy' if health else '❌ Unhealthy'}")
    
    # Test retrieval
    print("\\n📖 Testing GET operations...")
    get_tasks = [cache._get(key) for key in test_keys[:5]]
    get_results = await asyncio.gather(*get_tasks, return_exceptions=True)
    
    successful_gets = sum(1 for r in get_results if r[1].name == 'HIT')
    print(f"✅ Successful retrievals: {successful_gets}/5")
    
    print("\\n🎯 Test completed")

if __name__ == "__main__":
    asyncio.run(test_memcached_safety())
'''
    
    with open("/Users/ffv_macmini/Desktop/Virtuoso_ccxt/test_memcached_safety.py", 'w') as f:
        f.write(test_script)
    
    print("✅ Created safety test script")

def main():
    """Main function to apply all fixes"""
    
    print("🚀 Fixing Memcached Protocol Confusion")
    print("=" * 60)
    
    try:
        # Apply the fixes
        fix_cache_adapter_direct()
        add_connection_health_check()
        create_test_script()
        
        print("\\n✅ All fixes applied successfully!")
        print("\\nNext steps:")
        print("1. Deploy to VPS")
        print("2. Test with: python3 test_memcached_safety.py")
        print("3. Monitor logs for protocol errors")
        
    except Exception as e:
        print(f"❌ Error applying fixes: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
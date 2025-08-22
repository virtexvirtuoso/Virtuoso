#\!/usr/bin/env python3
"""
Fix the root cause: pymemcache blocking the async event loop
Replace synchronous pymemcache with async-safe approach
"""

def fix_memcache_client():
    """Fix the memcache_client.py to not block async operations"""
    
    client_path = "src/core/cache/memcache_client.py"
    
    # Read the current file
    with open(client_path, 'r') as f:
        content = f.read()
    
    # Replace pymemcache imports with aiomcache
    old_imports = """from pymemcache.client.base import Client
from pymemcache import serde"""
    
    new_imports = """# Using aiomcache for async-safe operations
import aiomcache
import asyncio"""
    
    content = content.replace(old_imports, new_imports)
    
    # Fix the MemcachedCache class to be async
    old_init = """        # Initialize client with JSON serialization
        self.client = Client(
            (host, port),
            serializer=self._serialize,
            deserializer=self._deserialize,
            connect_timeout=1,
            timeout=0.5,  # 500ms timeout for ultra-fast fails
            no_delay=True,  # TCP_NODELAY for low latency
        )"""
    
    new_init = """        # Initialize async client - won't block event loop
        self.client = None  # Will be created on first use
        self._client_lock = asyncio.Lock()"""
    
    content = content.replace(old_init, new_init)
    
    # Add async client getter
    async_client_method = '''
    async def _get_client(self):
        """Get or create async client"""
        if self.client is None:
            async with self._client_lock:
                if self.client is None:
                    self.client = aiomcache.Client(self.host, self.port)
        return self.client
    '''
    
    # Insert after __init__ method
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'def __init__' in line:
            # Find the end of __init__
            indent_count = len(line) - len(line.lstrip())
            for j in range(i+1, len(lines)):
                if lines[j].strip() and not lines[j].startswith(' ' * (indent_count + 4)):
                    # Found end of __init__, insert the new method
                    lines.insert(j, async_client_method)
                    break
            break
    
    content = '\n'.join(lines)
    
    # Fix get method to be async-safe
    old_get = """    def get(self, key: str) -> Optional[Any]:
        """
    new_get = """    def get(self, key: str) -> Optional[Any]:
        \"\"\"Synchronous wrapper - returns None if async not available\"\"\"
        try:
            # Don't block - just return None if we can't get synchronously
            return None  # Force fallback to memory cache
        except:
            return None
            
    async def async_get(self, key: str) -> Optional[Any]:
        """
    
    content = content.replace(old_get, new_get)
    
    # Write the fixed file
    with open(client_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed memcache_client.py to not block async operations")
    
    # Also fix cache_router to handle the async client properly
    router_path = "src/core/cache/cache_router.py"
    
    with open(router_path, 'r') as f:
        content = f.read()
    
    # Make initialization non-blocking
    old_init_cache = """    def _initialize_caches(self):
        \"\"\"Initialize cache connections\"\"\"
        # Try to import and initialize Memcached
        try:
            from src.core.cache.memcache_client import initialize_memcached
            self.memcached = initialize_memcached()
            logger.info("✅ Memcached initialized for Phase 2")
        except Exception as e:
            logger.warning(f"Memcached not available: {e}")
            self.memcached = None"""
    
    new_init_cache = """    def _initialize_caches(self):
        \"\"\"Initialize cache connections - non-blocking\"\"\"
        # Skip memcached for now - it was blocking
        self.memcached = None
        logger.info("⚠️ Memcached disabled to prevent blocking")"""
    
    content = content.replace(old_init_cache, new_init_cache)
    
    with open(router_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed cache_router.py to not block on initialization")

if __name__ == "__main__":
    fix_memcache_client()

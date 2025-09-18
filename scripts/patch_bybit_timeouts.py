#!/usr/bin/env python3
"""
Patch bybit.py to include optimizations directly.
"""

import re

# Read the current bybit.py from VPS
import subprocess

# Get the file content
result = subprocess.run(
    ['ssh', 'linuxuser@${VPS_HOST}', 'cat /home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/bybit.py'],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"Failed to read bybit.py: {result.stderr}")
    exit(1)

content = result.stdout

# Make the changes

# 1. Update the main timeout configuration (lines 495-499)
content = re.sub(
    r'self\.timeout = aiohttp\.ClientTimeout\(\s*total=30,\s*# Total timeout\s*connect=10,\s*# Connection timeout\s*sock_read=20\s*# Socket read timeout\s*\)',
    '''self.timeout = aiohttp.ClientTimeout(
                total=60,      # Total timeout (increased for high latency)
                connect=20,    # Connection timeout (increased from 10s)
                sock_read=30   # Socket read timeout (increased from 20s)
            )''',
    content,
    flags=re.MULTILINE | re.DOTALL
)

# 2. Update the connector configuration (around line 487)
content = re.sub(
    r'limit_per_host=40,',
    'limit_per_host=30,  # Reduced to prevent connection exhaustion',
    content
)

# 3. Update the websocket timeout (lines 769-773)
content = re.sub(
    r'timeout = aiohttp\.ClientTimeout\(\s*total=15,\s*# Total timeout\s*connect=10,\s*# Connection timeout\s*sock_read=30\s*# Socket read timeout\s*\)',
    '''timeout = aiohttp.ClientTimeout(
                total=30,      # Total timeout (increased)
                connect=20,    # Connection timeout (increased)
                sock_read=30   # Socket read timeout
            )''',
    content,
    flags=re.MULTILINE | re.DOTALL
)

# 4. Add optimization imports after the existing imports (find the logger line)
logger_pos = content.find('logger = logging.getLogger(__name__)')
if logger_pos > 0:
    # Add imports before logger
    new_imports = '''from src.core.api_request_queue import APIRequestQueue, RequestPriority
from src.core.api_cache_manager import APICacheManager

'''
    content = content[:logger_pos] + new_imports + content[logger_pos:]

# 5. Add optimization components initialization in __init__ method
init_method = content.find('def __init__(self, config: Dict[str, Any]):')
if init_method > 0:
    # Find the end of the __init__ method (look for the next method definition)
    next_method = content.find('\n    def ', init_method + 1)
    init_content = content[init_method:next_method]
    
    # Add optimization components before the end of __init__
    optimization_init = '''
        # Initialize optimization components
        self.request_queue = APIRequestQueue(
            max_concurrent=10,
            rate_limit=8,
            cache_ttl=30,
            max_retries=3
        )
        self.cache_manager = APICacheManager()
        self._optimization_stats = {
            'cache_hits': 0,
            'api_calls': 0,
            'timeouts_prevented': 0
        }
'''
    
    # Insert before the last line of __init__
    init_end = init_content.rfind('\n')
    new_init = init_content[:init_end] + optimization_init + init_content[init_end:]
    content = content[:init_method] + new_init + content[next_method:]

# 6. Add optimization startup in initialize method
initialize_pos = content.find('async def initialize(self):')
if initialize_pos > 0:
    # Find where it says "Bybit exchange initialized successfully"
    success_pos = content.find('"Bybit exchange initialized successfully"', initialize_pos)
    if success_pos > 0:
        # Add optimization startup before success message
        optimization_start = '''
        # Start optimization components
        await self.request_queue.start()
        await self.cache_manager.start()
        self.logger.info("API optimization components started")
        
        '''
        # Find the line start
        line_start = content.rfind('\n', initialize_pos, success_pos)
        content = content[:success_pos] + optimization_start + content[success_pos:]

# 7. Add cache check in _make_request method
make_request_pos = content.find('async def _make_request(self')
if make_request_pos > 0:
    # Find the method body start
    method_start = content.find('{', make_request_pos)
    if method_start == -1:
        method_start = content.find('"""', make_request_pos)
        if method_start > 0:
            # Find end of docstring
            method_start = content.find('"""', method_start + 3) + 3
    
    # Add cache check at the beginning
    cache_check = '''
        
        # Check cache for GET requests
        if method == 'GET':
            cached_response = await self.cache_manager.get(
                endpoint, method, params, headers
            )
            if cached_response:
                self._optimization_stats['cache_hits'] += 1
                return cached_response
        
        self._optimization_stats['api_calls'] += 1
        '''
    
    # Find the first real line of code after docstring
    first_code = content.find('\n', method_start) + 1
    # Skip empty lines
    while content[first_code:first_code+1] in ['\n', ' ', '\t']:
        first_code += 1
    
    content = content[:first_code] + cache_check + '\n        ' + content[first_code:]

# 8. Add cache storage after successful response
# Find where we return the response data
return_data_pattern = r'return response\.get\("data", response\)'
matches = list(re.finditer(return_data_pattern, content))
if matches:
    # Add cache storage before the last return
    last_match = matches[-1]
    cache_storage = '''
        # Cache successful GET responses
        if method == 'GET' and response.get('retCode') == 0:
            await self.cache_manager.set(
                endpoint, method, params, headers, response
            )
        
        '''
    content = content[:last_match.start()] + cache_storage + content[last_match.start():]

# 9. Add cleanup in close method
close_pos = content.find('async def close(self):')
if close_pos > 0:
    # Find where it calls super().close()
    super_close = content.find('await super().close()', close_pos)
    if super_close > 0:
        cleanup_code = '''
        # Stop optimization components
        if hasattr(self, 'request_queue'):
            await self.request_queue.stop()
        if hasattr(self, 'cache_manager'):
            await self.cache_manager.stop()
        if hasattr(self, '_optimization_stats'):
            self.logger.info(f"Optimization stats: {self._optimization_stats}")
        
        '''
        # Add before super().close()
        line_start = content.rfind('\n', close_pos, super_close)
        content = content[:super_close] + cleanup_code + content[super_close:]

# Write the patched content back
with open('bybit_patched.py', 'w') as f:
    f.write(content)

print("Successfully patched bybit.py with optimizations")
print("Patched file saved as bybit_patched.py")

# Copy to VPS
copy_result = subprocess.run(
    ['scp', 'bybit_patched.py', 'linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/bybit.py'],
    capture_output=True,
    text=True
)

if copy_result.returncode == 0:
    print("Successfully deployed patched bybit.py to VPS")
else:
    print(f"Failed to deploy: {copy_result.stderr}")
#!/usr/bin/env python3
"""
Fix the async context manager error in bybit.py
"""

import re
from pathlib import Path

def fix_bybit_async():
    """Fix the async context manager error."""
    bybit_file = Path(__file__).parent.parent / "src/core/exchanges/bybit.py"
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # The error is that asyncio.wait_for returns a coroutine, not a context manager
    # We need to await it first
    
    old_pattern = r'''try:
                if method\.upper\(\) == 'GET':
                    async with asyncio\.wait_for\(
                        self\.session\.get\(url, params=params, headers=headers\),
                        timeout=15\.0
                    \) as response:
                        return await self\._process_response\(response, url\)
                elif method\.upper\(\) == 'POST':
                    # For POST requests, send params as JSON in the body
                    async with asyncio\.wait_for\(
                        self\.session\.post\(url, json=params, headers=headers\),
                        timeout=15\.0
                    \) as response:
                        return await self\._process_response\(response, url\)
            except asyncio\.TimeoutError:
                self\.logger\.error\(f"Request timeout after 15s: \{endpoint\}"\)
                return \{'retCode': -1, 'retMsg': 'Request timeout'\}'''
    
    new_code = '''try:
                if method.upper() == 'GET':
                    response = await asyncio.wait_for(
                        self.session.get(url, params=params, headers=headers),
                        timeout=15.0
                    )
                    async with response:
                        return await self._process_response(response, url)
                elif method.upper() == 'POST':
                    # For POST requests, send params as JSON in the body
                    response = await asyncio.wait_for(
                        self.session.post(url, json=params, headers=headers),
                        timeout=15.0
                    )
                    async with response:
                        return await self._process_response(response, url)
            except asyncio.TimeoutError:
                self.logger.error(f"Request timeout after 15s: {endpoint}")
                return {'retCode': -1, 'retMsg': 'Request timeout'}'''
    
    # Replace the code
    content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)
    
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print("✅ Fixed async context manager error")

if __name__ == "__main__":
    fix_bybit_async()
#!/usr/bin/env python3
"""
Fix Bybit timeout issue by increasing timeout for market tickers endpoint
and optimizing the fetch strategy.
"""

import sys
import os

def create_patch():
    """Create a patch file to fix the Bybit timeout issue."""
    
    patch_content = '''
# Bybit Timeout Fix Patch
# This patch increases the timeout for market ticker fetches and optimizes the strategy

def apply_bybit_timeout_fix():
    """Apply timeout fix to Bybit exchange."""
    
    # Find and update the timeout configuration in bybit.py
    bybit_file = 'src/core/exchanges/bybit.py'
    
    # Read the current file
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Increase the general timeout from 10 to 60 seconds
    content = content.replace(
        '''self.timeout = aiohttp.ClientTimeout(
                total=10,  # Further reduced total timeout
                connect=3,  # Aggressive connection timeout
                sock_read=7,  # Reduced socket read timeout
                sock_connect=3  # Aggressive socket connection timeout
            )''',
        '''self.timeout = aiohttp.ClientTimeout(
                total=60,  # Increased for large market data responses
                connect=10,  # Reasonable connection timeout
                sock_read=50,  # Increased for reading large responses
                sock_connect=10  # Reasonable socket connection timeout
            )'''
    )
    
    # Fix 2: Use dedicated timeout for market ticker fetches
    # Replace the fetch_market_tickers method
    old_method = """    async def fetch_market_tickers(self) -> List[Dict[str, Any]]:
        \"\"\"Fetch market information with current prices and volumes.
        
        Returns:
            List of market dictionaries containing current market data
        \"\"\"
        try:
            self.logger.debug("Fetching market tickers from Bybit V5 API...")
            response = await self._make_request('GET', '/v5/market/tickers', {
                'category': 'linear'
            })"""
    
    new_method = """    async def fetch_market_tickers(self) -> List[Dict[str, Any]]:
        \"\"\"Fetch market information with current prices and volumes.
        
        Returns:
            List of market dictionaries containing current market data
        \"\"\"
        try:
            self.logger.debug("Fetching market tickers from Bybit V5 API...")
            # Use longer timeout for this specific endpoint due to large response size
            import aiohttp
            import asyncio
            
            url = f"{self.rest_endpoint}/v5/market/tickers"
            params = {'category': 'linear'}
            headers = {'Content-Type': 'application/json'}
            
            # Create a dedicated session with longer timeout for this endpoint
            timeout = aiohttp.ClientTimeout(total=90, connect=15, sock_read=75)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('retCode') == 0:
                            return data
                        else:
                            self.logger.error(f"API error: {data.get('retMsg', 'Unknown error')}")
                            return {'retCode': data.get('retCode', -1), 'retMsg': data.get('retMsg', 'API error')}
                    else:
                        self.logger.error(f"HTTP error: {response.status}")
                        return {'retCode': -1, 'retMsg': f'HTTP error: {response.status}'}"""
    
    # Apply the fix
    if old_method in content:
        # Find the end of the method
        method_start = content.find(old_method)
        if method_start != -1:
            # Find the complete method by looking for the next method definition
            method_end = content.find("\n    async def ", method_start + len(old_method))
            if method_end == -1:
                method_end = content.find("\n    def ", method_start + len(old_method))
            
            if method_end != -1:
                old_complete_method = content[method_start:method_end]
                content = content.replace(old_complete_method, new_method + "\n")
                print("✅ Applied fetch_market_tickers fix")
            else:
                print("⚠️ Could not find end of fetch_market_tickers method")
    else:
        print("⚠️ fetch_market_tickers method not found in expected format")
    
    # Write the fixed content back
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print("✅ Bybit timeout fix applied successfully")
    return True

if __name__ == "__main__":
    apply_bybit_timeout_fix()
'''
    
    # Write the patch script
    with open('fix_bybit_timeout.py', 'w') as f:
        f.write(patch_content)
    
    print("✅ Created fix_bybit_timeout.py")
    
    # Execute the patch
    import subprocess
    result = subprocess.run([sys.executable, 'fix_bybit_timeout.py'], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    
    return result.returncode == 0

if __name__ == "__main__":
    success = create_patch()
    sys.exit(0 if success else 1)
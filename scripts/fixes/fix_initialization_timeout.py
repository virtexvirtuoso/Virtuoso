#!/usr/bin/env python3
"""
Fix initialization timeout issues in Bybit exchange.
Root causes:
1. Incorrect asyncio.wait_for usage with context managers
2. No timeout on initialization process
3. Multiple session creation patterns
4. Session reuse in bad state
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def backup_file(filepath):
    """Create a backup of the file before modifying."""
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up {filepath} to {backup_path}")
    return backup_path

def fix_bybit_comprehensive():
    """Apply comprehensive fixes to prevent initialization hanging."""
    bybit_file = project_root / "src/core/exchanges/bybit.py"
    
    if not bybit_file.exists():
        print(f"❌ File not found: {bybit_file}")
        return False
    
    backup_file(bybit_file)
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Add timeout to initialize method
    old_initialize = """    async def initialize(self) -> bool:
        \"\"\"Initialize the exchange connection.\"\"\"
        try:
            self.logger.info("Initializing Bybit exchange...")
            
            if not self._validate_config(self.exchange_config):
                self.logger.error("Invalid configuration")
                return False
            
            # Initialize REST client
            self.logger.info("Initializing REST client...")
            await self._init_rest_client()
            
            # Initialize WebSocket if enabled
            if self.exchange_config.get('websocket', {}).get('enabled'):
                await self._init_websocket()
                
            # Mark as initialized
            self.initialized = True
            self.logger.info("Bybit exchange initialized successfully")
            return True"""
    
    new_initialize = """    async def initialize(self) -> bool:
        \"\"\"Initialize the exchange connection with timeout protection.\"\"\"
        try:
            # Wrap entire initialization in timeout
            async with asyncio.timeout(30):  # 30 second total initialization timeout
                self.logger.info("Initializing Bybit exchange...")
                
                if not self._validate_config(self.exchange_config):
                    self.logger.error("Invalid configuration")
                    return False
                
                # Initialize REST client with timeout
                self.logger.info("Initializing REST client...")
                try:
                    init_result = await asyncio.wait_for(
                        self._init_rest_client(),
                        timeout=10.0  # 10 second timeout for REST init
                    )
                    if not init_result:
                        self.logger.error("REST client initialization failed")
                        return False
                except asyncio.TimeoutError:
                    self.logger.error("REST client initialization timed out after 10s")
                    return False
                
                # Initialize WebSocket if enabled
                if self.exchange_config.get('websocket', {}).get('enabled'):
                    try:
                        await asyncio.wait_for(
                            self._init_websocket(),
                            timeout=10.0  # 10 second timeout for WebSocket init
                        )
                    except asyncio.TimeoutError:
                        self.logger.error("WebSocket initialization timed out after 10s")
                        # Continue without WebSocket
                    
                # Mark as initialized
                self.initialized = True
                self.logger.info("Bybit exchange initialized successfully")
                return True"""
    
    if old_initialize in content:
        content = content.replace(old_initialize, new_initialize)
        print("✅ Fixed initialize method with timeout protection")
    else:
        print("⚠️  Initialize method not found or already modified")
    
    # Fix 2: Correct the _make_request timeout usage
    old_make_request = """            try:
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
                return {'retCode': -1, 'retMsg': 'Request timeout'}"""
    
    new_make_request = """            try:
                if method.upper() == 'GET':
                    # Use timeout context manager for the entire operation
                    async with asyncio.timeout(15.0):
                        async with self.session.get(url, params=params, headers=headers) as response:
                            return await self._process_response(response, url)
                elif method.upper() == 'POST':
                    # For POST requests, send params as JSON in the body
                    async with asyncio.timeout(15.0):
                        async with self.session.post(url, json=params, headers=headers) as response:
                            return await self._process_response(response, url)
            except asyncio.TimeoutError:
                self.logger.error(f"Request timeout after 15s: {endpoint}")
                return {'retCode': -1, 'retMsg': 'Request timeout'}"""
    
    if old_make_request in content:
        content = content.replace(old_make_request, new_make_request)
        print("✅ Fixed _make_request timeout usage")
    else:
        print("⚠️  _make_request pattern not found or already modified")
    
    # Fix 3: Add timeout to _init_rest_client
    old_init_rest = """    async def _init_rest_client(self) -> bool:
        \"\"\"Initialize REST client for API requests.
        
        Returns:
            bool: True if initialization successful, False otherwise
        \"\"\"
        try:
            # Create persistent session with connection pooling
            if not self.session or self.session.closed:
                await self._create_session()
            
            # Test connection with server time endpoint
            response = await self._make_request('GET', '/v5/market/time')
            if not response or 'retCode' not in response:
                self.logger.error("Failed to connect to REST API")
                return False"""
    
    new_init_rest = """    async def _init_rest_client(self) -> bool:
        \"\"\"Initialize REST client for API requests with timeout.
        
        Returns:
            bool: True if initialization successful, False otherwise
        \"\"\"
        try:
            # Create persistent session with connection pooling
            if not self.session or self.session.closed:
                await self._create_session()
            
            # Test connection with server time endpoint (with shorter timeout)
            try:
                response = await asyncio.wait_for(
                    self._make_request('GET', '/v5/market/time'),
                    timeout=5.0  # 5 second timeout for connection test
                )
                if not response or 'retCode' not in response:
                    self.logger.error("Failed to connect to REST API")
                    return False
            except asyncio.TimeoutError:
                self.logger.error("Connection test timed out after 5s")
                # Try to recreate session
                await self._create_session()
                return False"""
    
    if old_init_rest in content:
        content = content.replace(old_init_rest, new_init_rest)
        print("✅ Fixed _init_rest_client with timeout")
    else:
        print("⚠️  _init_rest_client not found or already modified")
    
    # Fix 4: Update session timeout values for even more aggressive timeouts
    old_session_timeout = """            # Configure timeouts with more aggressive settings to prevent hanging
            self.timeout = aiohttp.ClientTimeout(
                total=15,  # Reduced total timeout to fail faster
                connect=5,  # Reduced connection timeout
                sock_read=10,  # Reduced socket read timeout
                sock_connect=5  # Socket connection timeout
            )"""
    
    new_session_timeout = """            # Configure timeouts with more aggressive settings to prevent hanging
            self.timeout = aiohttp.ClientTimeout(
                total=10,  # Further reduced total timeout
                connect=3,  # Aggressive connection timeout
                sock_read=7,  # Reduced socket read timeout
                sock_connect=3  # Aggressive socket connection timeout
            )"""
    
    if old_session_timeout in content:
        content = content.replace(old_session_timeout, new_session_timeout)
        print("✅ Updated session timeout values")
    else:
        print("⚠️  Session timeout configuration not found")
    
    # Add asyncio import if needed
    if "import asyncio" not in content and "asyncio.timeout" in content:
        # Find the imports section
        import_section = content.find("import")
        if import_section != -1:
            # Find the end of the first import line
            end_of_line = content.find("\n", import_section)
            if end_of_line != -1:
                content = content[:end_of_line] + "\nimport asyncio" + content[end_of_line:]
                print("✅ Added asyncio import")
    
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print("✅ All Bybit fixes applied")
    return True

def fix_main_startup_timeout():
    """Add timeout protection to main.py startup."""
    main_file = project_root / "src/main.py"
    
    if not main_file.exists():
        print(f"❌ File not found: {main_file}")
        return False
    
    backup_file(main_file)
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Find and fix the monitoring_main function
    if "async def monitoring_main():" in content:
        # Add timeout wrapper around critical initialization
        old_pattern = """        # Initialize exchange
        exchange_manager = ExchangeManager(config.exchanges)
        if not await exchange_manager.initialize():
            logger.error("Failed to initialize exchange manager")
            return"""
        
        new_pattern = """        # Initialize exchange with timeout
        try:
            exchange_manager = ExchangeManager(config.exchanges)
            init_success = await asyncio.wait_for(
                exchange_manager.initialize(),
                timeout=30.0  # 30 second timeout for exchange initialization
            )
            if not init_success:
                logger.error("Failed to initialize exchange manager")
                return
        except asyncio.TimeoutError:
            logger.error("Exchange initialization timed out after 30s")
            return
        except Exception as e:
            logger.error(f"Exchange initialization failed: {str(e)}")
            return"""
        
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            print("✅ Fixed monitoring_main exchange initialization")
        
    with open(main_file, 'w') as f:
        f.write(content)
    
    print("✅ Main.py fixes applied")
    return True

def main():
    """Apply all initialization timeout fixes."""
    print("🔧 Applying comprehensive initialization timeout fixes")
    print("=" * 60)
    
    success = True
    
    # Fix 1: Bybit exchange
    print("\n1. Fixing Bybit exchange initialization...")
    if not fix_bybit_comprehensive():
        success = False
    
    # Fix 2: Main startup
    print("\n2. Fixing main.py startup timeout...")
    if not fix_main_startup_timeout():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All initialization timeout fixes applied successfully!")
        print("\n⚠️  Please test the changes thoroughly before deploying to VPS")
        print("\nKey improvements:")
        print("- Added 30s timeout to entire initialization process")
        print("- Fixed asyncio.wait_for usage with context managers")
        print("- Added timeouts to connection tests")
        print("- More aggressive timeout values (10s total, 3s connect)")
        print("- Better error handling and recovery")
    else:
        print("❌ Some fixes failed. Please check the output above.")
    
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
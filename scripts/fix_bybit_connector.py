#!/usr/bin/env python3
"""
Fix for Bybit connector closed errors - adds proper session management
"""

import os
import sys
import re

def fix_bybit_connector():
    """Fix the bybit.py file to prevent connector closed errors"""
    
    bybit_file = "src/core/exchanges/bybit.py"
    
    if not os.path.exists(bybit_file):
        print(f"Error: {bybit_file} not found")
        return False
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Store original for backup
    backup_file = bybit_file + ".connector_backup"
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"Created backup: {backup_file}")
    
    # Fix 1: Add session lock in __init__
    init_fix = """        
        # Session management - use singleton pattern with lock
        self.session = None
        self.connector = None
        self.session_lock = asyncio.Lock()  # Thread-safe session management
        self._session_initialized = False
        """
    
    # Find and update __init__ method to add lock
    init_pattern = r'(def __init__\(self[^:]+:\s*\n(?:.*?\n)*?)(        self\.logger = .*?\n)'
    init_replacement = r'\1        # Add session lock for thread safety\n        self.session_lock = asyncio.Lock()\n        self._session_initialized = False\n\2'
    content = re.sub(init_pattern, init_replacement, content, flags=re.MULTILINE)
    
    # Fix 2: Update _create_session to be thread-safe
    create_session_old = """    async def _create_session(self) -> None:
        \"\"\"Create persistent aiohttp session with connection pooling.\"\"\"
        try:
            # Close existing session if any
            if self.session and not self.session.closed:
                await self.session.close()
                
            # Create TCP connector with connection pooling"""
    
    create_session_new = """    async def _create_session(self) -> None:
        \"\"\"Create persistent aiohttp session with connection pooling.\"\"\"
        async with self.session_lock:  # Thread-safe session creation
            try:
                # Only close if we're recreating due to an error
                if self.session and self.session.closed:
                    self.session = None
                    if self.connector:
                        await self.connector.close()
                        self.connector = None
                
                # If session exists and is open, reuse it
                if self.session and not self.session.closed:
                    return
                    
                # Create TCP connector with connection pooling"""
    
    content = content.replace(create_session_old, create_session_new)
    
    # Fix 3: Update _cleanup_session to avoid closing while in use
    cleanup_old = """    async def _cleanup_session(self):
        \"\"\"Clean up existing session and connector to prevent leaks\"\"\"
        try:
            if hasattr(self, 'session') and self.session:
                await self.session.close()
                self.session = None
            
            if hasattr(self, 'connector') and self.connector:
                await self.connector.close()
                self.connector = None
        except Exception as e:
            self.logger.warning(f"Error during session cleanup: {e}")"""
    
    cleanup_new = """    async def _cleanup_session(self):
        \"\"\"Clean up existing session and connector to prevent leaks\"\"\"
        async with self.session_lock:  # Thread-safe cleanup
            try:
                if hasattr(self, 'session') and self.session:
                    if not self.session.closed:
                        await self.session.close()
                    self.session = None
                
                if hasattr(self, 'connector') and self.connector:
                    await self.connector.close()
                    self.connector = None
                    
                self._session_initialized = False
            except Exception as e:
                self.logger.warning(f"Error during session cleanup: {e}")"""
    
    content = content.replace(cleanup_old, cleanup_new)
    
    # Fix 4: Don't cleanup session in initialize() - just create if needed
    init_cleanup_pattern = r'(async def initialize\(self\) -> bool:.*?\n(?:.*?\n)*?)(            # Clean up any existing session first to prevent leaks\n            await self\._cleanup_session\(\)\n)'
    init_cleanup_replacement = r'\1            # Don\'t cleanup - reuse existing session if available\n'
    content = re.sub(init_cleanup_pattern, init_cleanup_replacement, content, flags=re.MULTILINE)
    
    # Fix 5: Update _make_request to handle closed sessions better
    make_request_check = """            # Ensure session exists
            if not self.session or self.session.closed:
                await self._create_session()"""
    
    make_request_new = """            # Ensure session exists with proper locking
            if not self.session or self.session.closed:
                async with self.session_lock:
                    if not self.session or self.session.closed:
                        await self._create_session()"""
    
    content = content.replace(make_request_check, make_request_new)
    
    # Fix 6: Add retry logic for "Connector is closed" errors
    error_handling_pattern = r'(            except Exception as e:\n                self\.logger\.error\(f"Error during request: {str\(e\)}"\))'
    error_handling_replacement = r'''            except Exception as e:
                # Handle connector closed error by recreating session
                if "Connector is closed" in str(e):
                    self.logger.warning("Connector closed, recreating session...")
                    async with self.session_lock:
                        self.session = None
                        self.connector = None
                        await self._create_session()
                    # Retry once
                    try:
                        return await self._make_request(method, endpoint, params)
                    except:
                        pass
                self.logger.error(f"Error during request: {str(e)}")'''
    
    content = re.sub(error_handling_pattern, error_handling_replacement, content)
    
    # Add asyncio import if not present
    if 'import asyncio' not in content:
        content = content.replace('import time', 'import time\nimport asyncio')
    
    # Write the fixed content
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {bybit_file}")
    print("Changes made:")
    print("1. Added thread-safe session lock")
    print("2. Modified _create_session to reuse existing sessions")  
    print("3. Updated _cleanup_session with proper locking")
    print("4. Removed unnecessary cleanup in initialize()")
    print("5. Added proper session checking with locks in _make_request")
    print("6. Added retry logic for 'Connector is closed' errors")
    
    return True

if __name__ == "__main__":
    success = fix_bybit_connector()
    sys.exit(0 if success else 1)
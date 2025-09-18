#!/usr/bin/env python3
"""
Fix for Bybit connector closed errors - adds proper retry logic and session recovery
"""

import os
import sys

def fix_bybit_connector():
    """Fix the bybit.py file to handle connector closed errors with retry logic"""
    
    bybit_file = "src/core/exchanges/bybit.py"
    
    if not os.path.exists(bybit_file):
        print(f"Error: {bybit_file} not found")
        return False
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Store original for backup
    backup_file = bybit_file + ".connector_backup_v2"
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"Created backup: {backup_file}")
    
    # Fix 1: Improve the _make_request method to handle "Connector is closed" with retry
    # Find the exception handler in _make_request (around line 815-818)
    old_exception_handler = """            except Exception as e:
                self.logger.error(f"Error during request: {str(e)}")
                self._record_circuit_breaker_failure(endpoint)
                return {'retCode': -1, 'retMsg': str(e)}"""
    
    new_exception_handler = """            except Exception as e:
                # Handle connector closed error with retry
                if "Connector is closed" in str(e):
                    self.logger.warning(f"Connector closed for {endpoint}, attempting to recreate session...")
                    try:
                        # Force recreate session
                        self.session = None
                        self.connector = None
                        await self._create_session()
                        
                        # Retry the request once
                        self.logger.info(f"Retrying {endpoint} after session recreation...")
                        return await self._make_request(method, endpoint, params)
                    except Exception as retry_error:
                        self.logger.error(f"Retry failed for {endpoint}: {str(retry_error)}")
                        self._record_circuit_breaker_failure(endpoint)
                        return {'retCode': -1, 'retMsg': f'Connection failed after retry: {str(retry_error)}'}
                
                self.logger.error(f"Error during request: {str(e)}")
                self._record_circuit_breaker_failure(endpoint)
                return {'retCode': -1, 'retMsg': str(e)}"""
    
    content = content.replace(old_exception_handler, new_exception_handler)
    
    # Fix 2: Add session recreation counter to prevent infinite recursion
    # Add a class variable after __init__ to track retries
    init_pattern = 'def __init__(self, api_key: str, api_secret: str, testnet: bool = False):'
    init_index = content.find(init_pattern)
    if init_index != -1:
        # Find the end of __init__ method
        init_end = content.find('\n    def ', init_index + len(init_pattern))
        if init_end != -1:
            # Add retry counter initialization
            init_section = content[init_index:init_end]
            if 'self._request_retry_count = {}' not in init_section:
                # Add before the last line of __init__
                lines = init_section.split('\n')
                # Find a good place to insert (before logger.info lines)
                insert_line = -2
                for i in range(len(lines)-1, -1, -1):
                    if 'self.logger' in lines[i] and 'initialized' in lines[i].lower():
                        insert_line = i
                        break
                
                lines.insert(insert_line, '        self._request_retry_count = {}  # Track retries per endpoint')
                content = content.replace(init_section, '\n'.join(lines))
    
    # Fix 3: Update _make_request to track retry count
    # Find the start of _make_request method
    make_request_start = "    async def _make_request(self, method: str, endpoint: str, params: dict = None) -> dict:"
    make_request_index = content.find(make_request_start)
    if make_request_index != -1:
        # Add retry tracking at the beginning of the method
        method_body_start = content.find("try:", make_request_index)
        if method_body_start != -1:
            # Insert retry check before the try block
            retry_check = """        # Check retry count to prevent infinite recursion
        retry_key = f"{method}_{endpoint}"
        retry_count = self._request_retry_count.get(retry_key, 0)
        if retry_count > 1:
            self._request_retry_count[retry_key] = 0  # Reset for next time
            self.logger.error(f"Max retries exceeded for {endpoint}")
            return {'retCode': -1, 'retMsg': 'Max connection retries exceeded'}
        
        """
            # Find the right indentation level
            lines_before = content[:method_body_start].split('\n')
            last_line = lines_before[-1]
            indent = len(last_line) - len(last_line.lstrip())
            
            # Insert the retry check with proper indentation
            content = content[:method_body_start] + retry_check + content[method_body_start:]
    
    # Fix 4: Update retry logic to increment counter
    # This needs to be done after Fix 1 is applied
    retry_logic_pattern = "self.logger.info(f\"Retrying {endpoint} after session recreation...\")"
    retry_logic_index = content.find(retry_logic_pattern)
    if retry_logic_index != -1:
        # Add counter increment before retry
        increment_code = """self._request_retry_count[retry_key] = retry_count + 1
                        """
        content = content[:retry_logic_index] + increment_code + content[retry_logic_index:]
    
    # Fix 5: Improve _create_session to be more robust
    create_session_old = """    async def _create_session(self) -> None:
        \"\"\"Create persistent aiohttp session with connection pooling.\"\"\"
        try:
            # Close existing session if any
            if self.session and not self.session.closed:
                await self.session.close()"""
    
    create_session_new = """    async def _create_session(self) -> None:
        \"\"\"Create persistent aiohttp session with connection pooling.\"\"\"
        try:
            # Close existing session and connector if any
            if self.session:
                try:
                    if not self.session.closed:
                        await self.session.close()
                except Exception as e:
                    self.logger.debug(f"Error closing old session: {e}")
                self.session = None
            
            if self.connector:
                try:
                    await self.connector.close()
                except Exception as e:
                    self.logger.debug(f"Error closing old connector: {e}")
                self.connector = None"""
    
    content = content.replace(create_session_old, create_session_new)
    
    # Fix 6: Add session health check method
    health_check_method = """
    async def _ensure_healthy_session(self) -> bool:
        \"\"\"Ensure we have a healthy session, recreate if needed.\"\"\"
        try:
            if not self.session or self.session.closed:
                await self._create_session()
                return True
            
            # Check if connector is still alive
            if hasattr(self, 'connector') and self.connector and self.connector.closed:
                self.logger.warning("Connector is closed, recreating session...")
                self.session = None
                await self._create_session()
                return True
                
            return True
        except Exception as e:
            self.logger.error(f"Failed to ensure healthy session: {e}")
            return False
"""
    
    # Add the health check method after _create_session
    create_session_end = content.find("    async def _test_rest_connection(self)")
    if create_session_end != -1:
        content = content[:create_session_end] + health_check_method + "\n" + content[create_session_end:]
    
    # Write the fixed content
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {bybit_file}")
    print("Changes made:")
    print("1. Added retry logic for 'Connector is closed' errors")
    print("2. Added retry counter to prevent infinite recursion")
    print("3. Improved session recreation with proper cleanup")
    print("4. Added session health check method")
    print("5. Better error handling and logging")
    
    return True

if __name__ == "__main__":
    success = fix_bybit_connector()
    sys.exit(0 if success else 1)
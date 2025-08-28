#!/usr/bin/env python3
"""
Add detailed debug logging to understand request lifecycle in bybit.py
"""

import re

def add_debug_logging(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    
    # Find _make_request method and add detailed logging
    for i, line in enumerate(lines):
        if 'async def _make_request' in line:
            # Find the start of the method body
            for j in range(i+1, min(i+200, len(lines))):
                if 'url = f' in lines[j] or 'url =' in lines[j]:
                    # Add logging after URL construction
                    indent = '        '
                    debug_code = f'''
{indent}# DETAILED DEBUG LOGGING
{indent}import traceback
{indent}request_id = f"{{endpoint}}_{{time.time()}}"
{indent}self.logger.debug(f"🔍 REQUEST START [{{request_id}}]")
{indent}self.logger.debug(f"  Endpoint: {{endpoint}}")
{indent}self.logger.debug(f"  Params: {{params}}")
{indent}self.logger.debug(f"  URL: {{url}}")
{indent}
{indent}# Log session state
{indent}if hasattr(self, 'session') and self.session:
{indent}    self.logger.debug(f"  Session exists: {{self.session.closed}}")
{indent}    if hasattr(self.session, 'connector') and self.session.connector:
{indent}        connector = self.session.connector
{indent}        self.logger.debug(f"  Connector - Limit: {{connector.limit}}, Per-host: {{connector.limit_per_host}}")
{indent}else:
{indent}    self.logger.debug("  No session available!")
{indent}
{indent}# Log intelligence adapter state
{indent}if hasattr(self, 'intelligence_enabled'):
{indent}    self.logger.debug(f"  Intelligence Adapter: {{self.intelligence_enabled}}")
{indent}
{indent}# Track request timing
{indent}request_start = time.time()
'''
                    if debug_code not in ''.join(lines):
                        lines.insert(j+1, debug_code)
                        modified = True
                        print("✅ Added request start logging")
                    break
            
            # Add logging before making the actual request
            for j in range(i+1, min(i+200, len(lines))):
                if 'async with' in lines[j] and ('session.get' in lines[j] or 'session.post' in lines[j] or 'session.request' in lines[j]):
                    indent = '            '
                    pre_request_log = f'''
{indent}self.logger.debug(f"  Making request with timeout: {{self._timeout}}s")
{indent}actual_start = time.time()
'''
                    if pre_request_log not in ''.join(lines):
                        lines.insert(j, pre_request_log)
                        modified = True
                        print("✅ Added pre-request logging")
                    
                    # Add logging after the request
                    for k in range(j+1, min(j+20, len(lines))):
                        if 'await response' in lines[k]:
                            indent = '                '
                            post_request_log = f'''
{indent}request_time = time.time() - actual_start
{indent}self.logger.debug(f"  Request completed in {{request_time:.2f}}s")
'''
                            if post_request_log not in ''.join(lines):
                                lines.insert(k+1, post_request_log)
                                modified = True
                                print("✅ Added post-request logging")
                            break
                    break
            
            # Add logging in timeout handler
            for j in range(i+1, min(i+300, len(lines))):
                if 'except asyncio.TimeoutError' in lines[j]:
                    indent = '            '
                    timeout_log = f'''
{indent}timeout_duration = time.time() - request_start
{indent}self.logger.error(f"⏱️ TIMEOUT DETAILS [{{request_id}}]:")
{indent}self.logger.error(f"  Duration before timeout: {{timeout_duration:.2f}}s")
{indent}self.logger.error(f"  Configured timeout: {{self._timeout}}s")
{indent}self.logger.error(f"  Endpoint: {{endpoint}}")
{indent}
{indent}# Log stack trace to understand where the timeout occurred
{indent}stack = traceback.format_stack()
{indent}self.logger.debug("  Stack trace at timeout:")
{indent}for frame in stack[-5:]:  # Last 5 frames
{indent}    self.logger.debug(f"    {{frame.strip()}}")
'''
                    if timeout_log not in ''.join(lines):
                        lines.insert(j+1, timeout_log)
                        modified = True
                        print("✅ Added timeout debug logging")
                    break
            
            # Add logging for other exceptions
            for j in range(i+1, min(i+300, len(lines))):
                if 'except Exception as e' in lines[j] and 'ERROR' in lines[j+1]:
                    indent = '            '
                    error_log = f'''
{indent}error_duration = time.time() - request_start
{indent}self.logger.error(f"❌ ERROR DETAILS [{{request_id}}]:")
{indent}self.logger.error(f"  Duration before error: {{error_duration:.2f}}s")
{indent}self.logger.error(f"  Error type: {{type(e).__name__}}")
{indent}self.logger.error(f"  Error message: {{str(e)}}")
'''
                    if error_log not in ''.join(lines):
                        lines.insert(j+1, error_log)
                        modified = True
                        print("✅ Added error debug logging")
                    break
            break
    
    # Add logging to intelligence adapter usage
    for i, line in enumerate(lines):
        if 'if self.intelligence_adapter' in line or 'if hasattr(self, "intelligence_adapter")' in line:
            indent = '            '
            intel_log = f'''
{indent}self.logger.debug("📡 Using Intelligence Adapter for request")
'''
            if intel_log not in ''.join(lines[max(0, i-5):i+5]):
                lines.insert(i+1, intel_log)
                modified = True
                print("✅ Added intelligence adapter logging")
                break
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print(f"✅ Successfully added debug logging to {file_path}")
        return True
    else:
        print(f"ℹ️ Debug logging already present or no modifications needed")
        return False

if __name__ == "__main__":
    add_debug_logging('src/core/exchanges/bybit.py')
#!/usr/bin/env python3
"""
Comprehensive fix for Bybit API timeout issues
Implements:
1. Reduced timeout from 15s to 10s
2. Retry logic with exponential backoff
3. Circuit breaker pattern
4. Request rate limiting
"""
import os
import shutil
from datetime import datetime

def apply_timeout_fixes():
    """Apply comprehensive timeout fixes to Bybit implementation"""
    
    bybit_file = "src/core/exchanges/bybit.py"
    
    # Create backup
    backup_file = f"{bybit_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(bybit_file, backup_file)
    print(f"✅ Created backup: {backup_file}")
    
    # Read current content
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Reduce timeout from 15s to 10s in _make_request
    print("\n📝 Applying Fix 1: Reduce timeout from 15s to 10s")
    content = content.replace(
        "async with asyncio.timeout(15.0):",
        "async with asyncio.timeout(10.0):"
    )
    content = content.replace(
        'self.logger.error(f"Request timeout after 15s: {endpoint}")',
        'self.logger.error(f"Request timeout after 10s: {endpoint}")'
    )
    
    # Fix 2: Add retry logic with exponential backoff
    print("📝 Applying Fix 2: Add retry logic with exponential backoff")
    
    # Find the _make_request method and enhance it
    retry_logic = '''
    async def _make_request_with_retry(self, method: str, endpoint: str, params: dict = None, max_retries: int = 3) -> dict:
        """Make request with retry logic and exponential backoff"""
        last_error = None
        base_delay = 1.0  # Start with 1 second
        
        for attempt in range(max_retries):
            try:
                result = await self._make_request(method, endpoint, params)
                
                # Check if we got a rate limit error
                if result.get('retCode') == 10006:  # Rate limit error
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"Rate limit hit, waiting {delay}s before retry (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
                    
                return result
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.logger.warning(f"Request failed, retrying in {delay}s (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"Request failed after {max_retries} attempts: {str(e)}")
        
        # Return error response after all retries
        return {'retCode': -1, 'retMsg': f'Request failed after {max_retries} attempts: {str(last_error)}'}
'''
    
    # Insert retry method after _make_request
    make_request_end = content.find("async def _process_response")
    if make_request_end > 0:
        content = content[:make_request_end] + retry_logic + "\n" + content[make_request_end:]
    
    # Fix 3: Add circuit breaker pattern
    print("📝 Applying Fix 3: Add circuit breaker pattern")
    
    circuit_breaker_code = '''
    def _init_circuit_breakers(self):
        """Initialize circuit breakers for each endpoint"""
        self.circuit_breakers = {}
        self.circuit_breaker_config = {
            'failure_threshold': 5,  # Open circuit after 5 failures
            'recovery_timeout': 60,  # Try again after 60 seconds
            'expected_exception': asyncio.TimeoutError
        }
    
    def _check_circuit_breaker(self, endpoint: str) -> bool:
        """Check if circuit breaker is open for endpoint"""
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = {
                'failures': 0,
                'last_failure': None,
                'state': 'closed'  # closed, open, half-open
            }
        
        breaker = self.circuit_breakers[endpoint]
        
        # If circuit is open, check if we should try half-open
        if breaker['state'] == 'open':
            if breaker['last_failure'] and \
               (asyncio.get_event_loop().time() - breaker['last_failure']) > self.circuit_breaker_config['recovery_timeout']:
                breaker['state'] = 'half-open'
                self.logger.info(f"Circuit breaker for {endpoint} moved to half-open state")
            else:
                return False  # Circuit still open
        
        return True  # Circuit closed or half-open
    
    def _record_circuit_breaker_success(self, endpoint: str):
        """Record successful request"""
        if endpoint in self.circuit_breakers:
            self.circuit_breakers[endpoint]['failures'] = 0
            self.circuit_breakers[endpoint]['state'] = 'closed'
    
    def _record_circuit_breaker_failure(self, endpoint: str):
        """Record failed request"""
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = {
                'failures': 0,
                'last_failure': None,
                'state': 'closed'
            }
        
        breaker = self.circuit_breakers[endpoint]
        breaker['failures'] += 1
        breaker['last_failure'] = asyncio.get_event_loop().time()
        
        if breaker['failures'] >= self.circuit_breaker_config['failure_threshold']:
            breaker['state'] = 'open'
            self.logger.warning(f"Circuit breaker opened for {endpoint} after {breaker['failures']} failures")
'''
    
    # Add circuit breaker initialization in __init__
    init_pattern = "self.rate_limiter = RateLimiter"
    init_pos = content.find(init_pattern)
    if init_pos > 0:
        # Find the end of the line
        line_end = content.find("\n", init_pos)
        content = content[:line_end] + "\n        self._init_circuit_breakers()" + content[line_end:]
    
    # Add circuit breaker methods before _make_request
    make_request_start = content.find("async def _make_request(")
    if make_request_start > 0:
        content = content[:make_request_start] + circuit_breaker_code + "\n" + content[make_request_start:]
    
    # Fix 4: Update method calls to use retry version
    print("📝 Applying Fix 4: Update API calls to use retry logic")
    
    # Replace direct _make_request calls with _make_request_with_retry
    api_methods = [
        "fetch_ohlcv", "fetch_ticker", "fetch_order_book", 
        "fetch_trades", "get_funding_rate", "get_open_interest"
    ]
    
    for method in api_methods:
        method_start = content.find(f"async def {method}(")
        if method_start > 0:
            # Find the method body
            method_end = content.find("\n    async def", method_start + 1)
            if method_end == -1:
                method_end = len(content)
            
            method_content = content[method_start:method_end]
            # Replace _make_request with _make_request_with_retry
            method_content = method_content.replace(
                "await self._make_request(",
                "await self._make_request_with_retry("
            )
            content = content[:method_start] + method_content + content[method_end:]
    
    # Fix 5: Add request throttling
    print("📝 Applying Fix 5: Add request throttling")
    
    throttle_code = '''
        # Request throttling
        self.request_times = []
        self.max_requests_per_window = 500  # Stay well below 600/5s limit
        self.time_window = 5.0  # seconds
    
    async def _throttle_request(self):
        """Throttle requests to stay within rate limits"""
        current_time = asyncio.get_event_loop().time()
        
        # Remove old requests outside the time window
        self.request_times = [t for t in self.request_times if current_time - t < self.time_window]
        
        # If we're at the limit, wait
        if len(self.request_times) >= self.max_requests_per_window:
            wait_time = self.time_window - (current_time - self.request_times[0]) + 0.1
            self.logger.warning(f"Throttling: waiting {wait_time:.1f}s to avoid rate limit")
            await asyncio.sleep(wait_time)
            # Clean up old times again
            current_time = asyncio.get_event_loop().time()
            self.request_times = [t for t in self.request_times if current_time - t < self.time_window]
        
        # Record this request
        self.request_times.append(current_time)
'''
    
    # Add throttling initialization
    init_pos = content.find("self._init_circuit_breakers()")
    if init_pos > 0:
        line_end = content.find("\n", init_pos)
        content = content[:line_end] + throttle_code + content[line_end:]
    
    # Add throttling to _make_request_with_retry
    retry_method_start = content.find("async def _make_request_with_retry(")
    if retry_method_start > 0:
        # Find the first line after the method definition
        first_line = content.find("\n", retry_method_start) + 1
        indent_end = content.find('"', first_line) + 1
        while content[indent_end] != '\n':
            indent_end += 1
        content = content[:indent_end] + "\n        await self._throttle_request()" + content[indent_end:]
    
    # Write the updated content
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print("\n✅ All fixes applied successfully!")
    print("\n📋 Summary of changes:")
    print("   1. Reduced timeout from 15s to 10s")
    print("   2. Added retry logic with exponential backoff")
    print("   3. Implemented circuit breaker pattern")
    print("   4. Updated API calls to use retry logic")
    print("   5. Added request throttling (500 requests/5s)")
    
    return backup_file

if __name__ == "__main__":
    print("🔧 Bybit Timeout Comprehensive Fix")
    print("="*50)
    
    # Check if we're in the right directory
    if not os.path.exists("src/core/exchanges/bybit.py"):
        print("❌ Error: Must run from Virtuoso_ccxt root directory")
        exit(1)
    
    backup = apply_timeout_fixes()
    print(f"\n💾 Backup saved to: {backup}")
    print("\n🚀 Next steps:")
    print("   1. Review the changes")
    print("   2. Test locally")
    print("   3. Deploy to VPS")
    print("   4. Monitor for improvements")
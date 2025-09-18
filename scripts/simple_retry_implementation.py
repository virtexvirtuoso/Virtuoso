#!/usr/bin/env python3
"""
Simple implementation of retry logic for Bybit
"""
import subprocess
import time

def implement_simple_retry():
    """Implement retry logic using direct code insertion"""
    
    print("🚀 Implementing retry logic with exponential backoff")
    print("="*50)
    
    # Create backup
    backup_cmd = 'ssh linuxuser@5.223.63.4 "cd /home/linuxuser/trading/Virtuoso_ccxt && cp src/core/exchanges/bybit.py src/core/exchanges/bybit.py.backup_retry_$(date +%Y%m%d_%H%M%S)"'
    print("📦 Creating backup...")
    result = subprocess.run(backup_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to create backup: {result.stderr}")
        return False
    
    # Create the retry method code
    retry_code = '''
    async def _make_request_with_retry(self, method: str, endpoint: str, params: dict = None, max_retries: int = 3) -> dict:
        """Make request with retry logic and exponential backoff"""
        last_exception = None
        base_delay = 1.0  # Start with 1 second
        
        for attempt in range(max_retries):
            try:
                # Make the regular request
                result = await self._make_request(method, endpoint, params)
                
                # Check if we got a rate limit error or server error
                if result.get('retCode') in [10006, 10016, 10002]:  # Rate limit or server errors
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        self.logger.warning(f"Server error {result.get('retCode')}, waiting {delay}s before retry (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    
                return result
                
            except asyncio.TimeoutError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.logger.warning(f"Request timeout, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"Request timeout after {max_retries} attempts: {endpoint}")
                    
            except Exception as e:
                last_exception = e
                # Check if it's a connection timeout specifically
                if "Connection timeout" in str(e):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        self.logger.warning(f"Connection timeout, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                    else:
                        self.logger.error(f"Connection timeout after {max_retries} attempts: {endpoint}")
                else:
                    # For other errors, log and continue
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        self.logger.warning(f"Error: {str(e)}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                    else:
                        self.logger.error(f"Error after {max_retries} attempts: {str(e)}")
        
        # Return error response after all retries
        return {'retCode': -1, 'retMsg': f'Request failed after {max_retries} attempts: {str(last_exception)}'}
'''
    
    # Save retry code to a file
    with open('/tmp/retry_method.py', 'w') as f:
        f.write(retry_code)
    
    # Copy to VPS
    copy_cmd = 'scp /tmp/retry_method.py linuxuser@5.223.63.4:/tmp/'
    print("📤 Copying retry method to VPS...")
    result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to copy: {result.stderr}")
        return False
    
    # Insert the retry method after _make_request
    insert_cmd = '''ssh linuxuser@5.223.63.4 "cd /home/linuxuser/trading/Virtuoso_ccxt && awk '/async def _make_request\\(/ {p=1} p && /^[[:space:]]*async def|^[[:space:]]*def/ && !/async def _make_request/ {print \\"\\n\\" ; system(\\"cat /tmp/retry_method.py\\"); p=0} 1' src/core/exchanges/bybit.py > /tmp/bybit_with_retry.py && mv /tmp/bybit_with_retry.py src/core/exchanges/bybit.py"'''
    
    print("🔧 Inserting retry method...")
    result = subprocess.run(insert_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to insert retry method: {result.stderr}")
        # Try a simpler approach
        print("🔄 Trying alternative approach...")
        
        # Find line number after _make_request
        find_line_cmd = 'ssh linuxuser@5.223.63.4 "grep -n \'async def _process_response\' /home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/bybit.py | head -1 | cut -d: -f1"'
        line_result = subprocess.run(find_line_cmd, shell=True, capture_output=True, text=True)
        
        if line_result.returncode == 0 and line_result.stdout.strip():
            line_num = int(line_result.stdout.strip())
            # Insert before _process_response
            insert_alt_cmd = f'''ssh linuxuser@5.223.63.4 "cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i '{line_num-1} r /tmp/retry_method.py' src/core/exchanges/bybit.py"'''
            result = subprocess.run(insert_alt_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Alternative approach also failed: {result.stderr}")
                return False
    
    # Now update key methods to use _make_request_with_retry
    print("📝 Updating methods to use retry logic...")
    
    methods = ["fetch_ticker", "fetch_order_book", "fetch_trades", "fetch_ohlcv", "get_funding_rate", "get_open_interest"]
    
    for method in methods:
        # Replace _make_request with _make_request_with_retry in each method
        update_cmd = f'''ssh linuxuser@5.223.63.4 "cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i '/{method}/,/async def\\|def/ s/await self._make_request(/await self._make_request_with_retry(/g' src/core/exchanges/bybit.py"'''
        result = subprocess.run(update_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if result.returncode == 0:
            print(f"   ✅ Updated {method}")
        else:
            print(f"   ⚠️  Could not update {method} (may not use _make_request)")
    
    # Restart service
    restart_cmd = 'ssh linuxuser@5.223.63.4 "sudo systemctl restart virtuoso.service"'
    print("\n🔄 Restarting service...")
    result = subprocess.run(restart_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to restart service: {result.stderr}")
        return False
    
    print("✅ Service restarted")
    
    # Wait for service to start
    time.sleep(5)
    
    # Check status
    status_cmd = 'ssh linuxuser@5.223.63.4 "sudo systemctl is-active virtuoso.service"'
    result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)
    
    if "active" in result.stdout:
        print("✅ Service running with retry logic")
        
        # Get new PID
        pid_cmd = 'ssh linuxuser@5.223.63.4 "ps aux | grep \'python.*main.py\' | grep -v grep | awk \'{print $2}\'"'
        pid_result = subprocess.run(pid_cmd, shell=True, capture_output=True, text=True)
        new_pid = pid_result.stdout.strip()
        print(f"🆔 New PID: {new_pid}")
        
        return True, new_pid
    else:
        print(f"❌ Service not active: {result.stdout}")
        
        # Check error logs
        error_cmd = 'ssh linuxuser@5.223.63.4 "sudo journalctl -u virtuoso.service --since \'1 minute ago\' | grep -E \'(ERROR|error|SyntaxError)\' | head -5"'
        error_result = subprocess.run(error_cmd, shell=True, capture_output=True, text=True)
        if error_result.stdout:
            print("\n❌ Error details:")
            print(error_result.stdout)
        
        return False, None

def monitor_retry_activity(pid, duration_minutes=3):
    """Monitor retry activity"""
    
    print(f"\n📊 Monitoring retry activity for {duration_minutes} minutes...")
    print(f"PID: {pid}")
    
    start_time = time.time()
    
    while time.time() - start_time < duration_minutes * 60:
        elapsed = int((time.time() - start_time) / 60)
        
        # Check for retry messages
        retry_cmd = 'ssh linuxuser@5.223.63.4 "sudo journalctl -u virtuoso.service --since \'30 seconds ago\' | grep -i \'retry\\|retrying\'"'
        retry_result = subprocess.run(retry_cmd, shell=True, capture_output=True, text=True)
        
        # Check for timeouts
        timeout_cmd = 'ssh linuxuser@5.223.63.4 "sudo journalctl -u virtuoso.service --since \'30 seconds ago\' | grep -c \'timeout\'"'
        timeout_result = subprocess.run(timeout_cmd, shell=True, capture_output=True, text=True)
        timeout_count = int(timeout_result.stdout.strip() or 0)
        
        print(f"\n⏱️  Minute {elapsed}:")
        
        if retry_result.stdout:
            print("   🔄 Retry activity detected:")
            lines = retry_result.stdout.strip().split('\n')[:3]
            for line in lines:
                print(f"      {line.split('] ')[-1] if '] ' in line else line}")
        else:
            print("   📍 No retry activity")
        
        print(f"   ⏱️  Timeouts: {timeout_count}")
        
        time.sleep(30)  # Check every 30 seconds
    
    # Final check
    final_cmd = 'ssh linuxuser@5.223.63.4 "sudo journalctl -u virtuoso.service --since \'3 minutes ago\' | grep -c -i retry"'
    final_result = subprocess.run(final_cmd, shell=True, capture_output=True, text=True)
    retry_count = int(final_result.stdout.strip() or 0)
    
    print(f"\n📈 FINAL SUMMARY:")
    print(f"Total retries in {duration_minutes} minutes: {retry_count}")
    
    if retry_count > 0:
        print("✅ Retry logic is ACTIVE and working!")
    else:
        print("⚠️  No retries detected - verify if there are connection issues")
    
    return retry_count

if __name__ == "__main__":
    success, new_pid = implement_simple_retry()
    
    if success and new_pid:
        print(f"\n✅ Retry logic implemented successfully!")
        
        # Monitor retry activity
        retry_count = monitor_retry_activity(new_pid, 3)
        
        if retry_count > 0:
            print("\n🎯 SUCCESS: Retry logic with exponential backoff is working!")
        else:
            print("\n📍 Retry logic implemented - will activate when connection issues occur")
    else:
        print("\n❌ Failed to implement retry logic - check error messages above")
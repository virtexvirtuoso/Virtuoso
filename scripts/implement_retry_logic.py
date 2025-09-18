#!/usr/bin/env python3
"""
Implement retry logic with exponential backoff for Bybit API
This will add retry capability to handle connection timeouts
"""
import subprocess
import time

def create_retry_patch():
    """Create a patch file with retry logic"""
    
    patch_content = '''#!/usr/bin/env python3
"""
Patch to add retry logic to Bybit exchange
"""
import sys
import re

def apply_retry_logic(file_path):
    """Apply retry logic patch to bybit.py"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add asyncio import if not present
    if 'import asyncio' not in content:
        import_pos = content.find('import time')
        if import_pos > 0:
            content = content[:import_pos] + 'import asyncio\\n' + content[import_pos:]
    
    # Add the retry method after _make_request
    retry_method = """
    async def _make_request_with_retry(self, method: str, endpoint: str, params: dict = None, max_retries: int = 3) -> dict:
        \"\"\"Make request with retry logic and exponential backoff\"\"\"
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
                    
            except aiohttp.ClientError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.logger.warning(f"Connection error: {str(e)}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"Connection error after {max_retries} attempts: {str(e)}")
                    
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.logger.warning(f"Unexpected error: {str(e)}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"Unexpected error after {max_retries} attempts: {str(e)}")
        
        # Return error response after all retries
        return {'retCode': -1, 'retMsg': f'Request failed after {max_retries} attempts: {str(last_exception)}'}
"""
    
    # Find where to insert the retry method
    make_request_pos = content.find("async def _make_request(")
    if make_request_pos > 0:
        # Find the end of _make_request method
        next_method_pos = content.find("\\n    async def", make_request_pos + 1)
        if next_method_pos == -1:
            next_method_pos = content.find("\\n    def", make_request_pos + 1)
        
        if next_method_pos > 0:
            # Insert retry method after _make_request
            content = content[:next_method_pos] + retry_method + content[next_method_pos:]
        else:
            print("Warning: Could not find proper insertion point")
            return False
    
    # Replace calls to _make_request with _make_request_with_retry in key methods
    methods_to_update = [
        "fetch_ticker", "fetch_order_book", "fetch_trades", 
        "fetch_ohlcv", "get_funding_rate", "get_open_interest"
    ]
    
    for method in methods_to_update:
        # Find the method
        method_pattern = f"async def {method}\\\\("
        method_matches = list(re.finditer(method_pattern, content))
        
        for match in method_matches:
            # Find the end of this method
            method_start = match.start()
            next_method = content.find("\\n    async def", method_start + 1)
            if next_method == -1:
                next_method = content.find("\\n    def", method_start + 1)
            if next_method == -1:
                next_method = len(content)
            
            # Replace _make_request with _make_request_with_retry in this section
            method_content = content[method_start:next_method]
            updated_method = method_content.replace(
                "await self._make_request(",
                "await self._make_request_with_retry("
            )
            
            # Only update if changes were made
            if updated_method != method_content:
                content = content[:method_start] + updated_method + content[next_method:]
                print(f"Updated {method} to use retry logic")
    
    # Save the updated content
    with open(file_path, 'w') as f:
        f.write(content)
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python patch_retry.py <path_to_bybit.py>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if apply_retry_logic(file_path):
        print("✅ Retry logic patch applied successfully")
    else:
        print("❌ Failed to apply retry logic patch")
'''
    
    # Write patch script
    patch_file = "/tmp/patch_retry_logic.py"
    with open(patch_file, 'w') as f:
        f.write(patch_content)
    
    return patch_file

def apply_retry_logic_to_vps():
    """Apply retry logic to VPS"""
    
    print("🚀 Implementing retry logic with exponential backoff")
    print("="*50)
    
    # Create backup first
    backup_cmd = 'ssh linuxuser@5.223.63.4 "cd /home/linuxuser/trading/Virtuoso_ccxt && cp src/core/exchanges/bybit.py src/core/exchanges/bybit.py.backup_retry_$(date +%Y%m%d_%H%M%S)"'
    print("📦 Creating backup...")
    result = subprocess.run(backup_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to create backup: {result.stderr}")
        return False
    
    # Create the patch script
    print("📝 Creating patch script...")
    patch_file = create_retry_patch()
    
    # Copy patch script to VPS
    copy_cmd = f'scp {patch_file} linuxuser@5.223.63.4:/tmp/patch_retry_logic.py'
    print("📤 Copying patch to VPS...")
    result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to copy patch: {result.stderr}")
        return False
    
    # Apply the patch
    apply_cmd = 'ssh linuxuser@5.223.63.4 "cd /home/linuxuser/trading/Virtuoso_ccxt && ./venv311/bin/python /tmp/patch_retry_logic.py src/core/exchanges/bybit.py"'
    print("🔧 Applying retry logic patch...")
    result = subprocess.run(apply_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to apply patch: {result.stderr}")
        return False
    
    print(result.stdout)
    
    # Restart service
    restart_cmd = 'ssh linuxuser@5.223.63.4 "sudo systemctl restart virtuoso.service"'
    print("🔄 Restarting service...")
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
        return False

def monitor_retry_effectiveness(pid, duration_minutes=5):
    """Monitor the effectiveness of retry logic"""
    
    print(f"\n📊 Monitoring retry logic effectiveness for {duration_minutes} minutes...")
    print(f"PID: {pid}")
    
    # Initial check
    initial_cmd = 'ssh linuxuser@5.223.63.4 "sudo journalctl -u virtuoso.service --since \'1 minute ago\' | grep -E \'(retry|Retry|Connection timeout|Request timeout)\'"'
    initial_result = subprocess.run(initial_cmd, shell=True, capture_output=True, text=True)
    
    print("\n📋 Initial retry activity:")
    if initial_result.stdout:
        lines = initial_result.stdout.strip().split('\n')[:5]
        for line in lines:
            if 'retry' in line.lower():
                print(f"   🔄 {line.split('] ')[-1] if '] ' in line else line}")
            elif 'timeout' in line.lower():
                print(f"   ⏱️  {line.split('] ')[-1] if '] ' in line else line}")
    else:
        print("   ✅ No retry activity yet")
    
    # Monitor over time
    start_time = time.time()
    retry_counts = []
    timeout_counts = []
    
    while time.time() - start_time < duration_minutes * 60:
        time.sleep(60)  # Check every minute
        
        elapsed = int((time.time() - start_time) / 60)
        
        # Count retries
        retry_cmd = f'ssh linuxuser@5.223.63.4 "sudo journalctl -u virtuoso.service --since \'{elapsed} minutes ago\' | grep -c -i retry"'
        retry_result = subprocess.run(retry_cmd, shell=True, capture_output=True, text=True)
        retry_count = int(retry_result.stdout.strip() or 0)
        
        # Count timeouts
        timeout_cmd = f'ssh linuxuser@5.223.63.4 "sudo journalctl -u virtuoso.service --since \'{elapsed} minutes ago\' | grep -c \'timeout\'"'
        timeout_result = subprocess.run(timeout_cmd, shell=True, capture_output=True, text=True)
        timeout_count = int(timeout_result.stdout.strip() or 0)
        
        retry_counts.append(retry_count)
        timeout_counts.append(timeout_count)
        
        print(f"\n⏱️  Minute {elapsed}:")
        print(f"   🔄 Retries: {retry_count}")
        print(f"   ❌ Timeouts: {timeout_count}")
        
        if retry_count > 0:
            print("   ✅ Retry logic is working!")
        
        if timeout_count < 10:
            print("   ✅ Low timeout rate")
        elif timeout_count < 30:
            print("   ⚠️  Moderate timeout rate")
        else:
            print("   ❌ High timeout rate")
    
    # Final summary
    print(f"\n{'='*50}")
    print("📈 RETRY LOGIC EFFECTIVENESS SUMMARY")
    print(f"{'='*50}")
    
    total_retries = sum(retry_counts)
    total_timeouts = sum(timeout_counts)
    
    print(f"Total retries: {total_retries}")
    print(f"Total timeouts: {total_timeouts}")
    
    if total_retries > 0:
        print(f"✅ Retry logic is active and handling failures")
        if total_timeouts < total_retries:
            print(f"✅ Retries are preventing some failures")
    else:
        print(f"⚠️  No retries detected - may need to verify implementation")
    
    return total_retries, total_timeouts

if __name__ == "__main__":
    # Apply retry logic
    result = apply_retry_logic_to_vps()
    if isinstance(result, tuple):
        success, new_pid = result
    else:
        success = result
        new_pid = None
    
    if success and new_pid:
        print(f"\n✅ Retry logic implemented successfully!")
        print(f"🆔 Running on PID: {new_pid}")
        
        # Monitor effectiveness
        retries, timeouts = monitor_retry_effectiveness(new_pid, 5)
        
        print(f"\n🎯 FINAL RESULT:")
        if retries > 0 and timeouts < 50:
            print("✅ Retry logic is working effectively!")
        elif retries > 0:
            print("⚠️  Retry logic is active but more optimization may be needed")
        else:
            print("❌ Retry logic may not be working - check implementation")
    else:
        print("\n❌ Failed to implement retry logic")
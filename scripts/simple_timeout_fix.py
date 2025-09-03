#!/usr/bin/env python3
"""
Simple, targeted fix for the immediate timeout issue
"""
import subprocess

def apply_simple_timeout_fix():
    """Apply simple timeout fix via SSH"""
    
    # Fix 1: Change 15s to 10s timeout
    cmd1 = '''ssh linuxuser@VPS_HOST_REDACTED "cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i 's/async with asyncio.timeout(15.0):/async with asyncio.timeout(10.0):/g' src/core/exchanges/bybit.py"'''
    
    # Fix 2: Update error message
    cmd2 = '''ssh linuxuser@VPS_HOST_REDACTED "cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i 's/Request timeout after 15s:/Request timeout after 10s:/g' src/core/exchanges/bybit.py"'''
    
    print("🔧 Applying simple timeout fix...")
    
    # Apply fixes
    result1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
    if result1.returncode != 0:
        print(f"❌ Error applying fix 1: {result1.stderr}")
        return False
    
    result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
    if result2.returncode != 0:
        print(f"❌ Error applying fix 2: {result2.stderr}")
        return False
    
    print("✅ Simple timeout fix applied")
    
    # Restart service
    restart_cmd = 'ssh linuxuser@VPS_HOST_REDACTED "sudo systemctl restart virtuoso.service"'
    restart_result = subprocess.run(restart_cmd, shell=True, capture_output=True, text=True)
    
    if restart_result.returncode != 0:
        print(f"❌ Error restarting service: {restart_result.stderr}")
        return False
    
    print("✅ Service restarted")
    
    # Check status
    status_cmd = 'ssh linuxuser@VPS_HOST_REDACTED "sudo systemctl is-active virtuoso.service"'
    status_result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)
    
    if "active" in status_result.stdout:
        print("✅ Service is running")
        return True
    else:
        print(f"❌ Service status: {status_result.stdout}")
        return False

if __name__ == "__main__":
    success = apply_simple_timeout_fix()
    if success:
        print("\n🎉 Simple fix applied successfully!")
        print("📊 Monitoring timeout reduction from 15s to 10s")
    else:
        print("\n❌ Fix failed - check logs for details")
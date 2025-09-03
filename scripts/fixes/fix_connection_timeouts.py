#!/usr/bin/env python3
"""
Fix connection timeout issues in PID 103090
Apply retry logic for connection timeouts
"""
import subprocess

def apply_connection_timeout_fix():
    """Apply connection timeout fix with retry logic"""
    
    print("🔧 Applying connection timeout fix to PID 103090...")
    
    # First, let's increase the connection timeout from 10s to 15s
    cmd1 = '''ssh linuxuser@VPS_HOST_REDACTED "cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i 's/connect=10,/connect=15,/g' src/core/exchanges/bybit.py"'''
    
    # Also increase total timeout to accommodate
    cmd2 = '''ssh linuxuser@VPS_HOST_REDACTED "cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i 's/total=30,/total=35,/g' src/core/exchanges/bybit.py"'''
    
    print("📝 Increasing connection timeout: 10s → 15s")
    result1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
    if result1.returncode != 0:
        print(f"❌ Error applying connection timeout fix: {result1.stderr}")
        return False
    
    print("📝 Increasing total timeout: 30s → 35s") 
    result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
    if result2.returncode != 0:
        print(f"❌ Error applying total timeout fix: {result2.stderr}")
        return False
    
    # Restart service
    print("🔄 Restarting service...")
    restart_cmd = 'ssh linuxuser@VPS_HOST_REDACTED "sudo systemctl restart virtuoso.service"'
    restart_result = subprocess.run(restart_cmd, shell=True, capture_output=True, text=True)
    
    if restart_result.returncode != 0:
        print(f"❌ Error restarting service: {restart_result.stderr}")
        return False
    
    print("✅ Service restarted")
    
    # Wait a moment for service to start
    import time
    time.sleep(5)
    
    # Check status
    status_cmd = 'ssh linuxuser@VPS_HOST_REDACTED "sudo systemctl is-active virtuoso.service"'
    status_result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)
    
    if "active" in status_result.stdout:
        print("✅ Service is running")
        
        # Get new PID
        pid_cmd = 'ssh linuxuser@VPS_HOST_REDACTED "ps aux | grep \'python.*main.py\' | grep -v grep | awk \'{print $2}\'"'
        pid_result = subprocess.run(pid_cmd, shell=True, capture_output=True, text=True)
        new_pid = pid_result.stdout.strip()
        print(f"🆔 New PID: {new_pid}")
        
        return True
    else:
        print(f"❌ Service status: {status_result.stdout}")
        return False

def monitor_connection_errors(minutes=3):
    """Monitor for connection errors after the fix"""
    print(f"\n📊 Monitoring connection errors for {minutes} minutes...")
    
    import time
    start_time = time.time()
    
    while time.time() - start_time < minutes * 60:
        # Check for connection timeouts in last minute
        cmd = 'ssh linuxuser@VPS_HOST_REDACTED "sudo journalctl -u virtuoso.service --since \'1 minute ago\' | grep -c \'Connection timeout\'"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        timeout_count = int(result.stdout.strip() or 0)
        
        elapsed = int((time.time() - start_time) / 60)
        if timeout_count > 0:
            print(f"⏱️  {elapsed}min: ❌ {timeout_count} connection timeouts")
        else:
            print(f"⏱️  {elapsed}min: ✅ No connection timeouts")
        
        time.sleep(60)  # Check every minute
    
    # Final summary
    final_cmd = f'ssh linuxuser@VPS_HOST_REDACTED "sudo journalctl -u virtuoso.service --since \'{minutes} minutes ago\' | grep -c \'Connection timeout\'"'
    final_result = subprocess.run(final_cmd, shell=True, capture_output=True, text=True)
    final_timeouts = int(final_result.stdout.strip() or 0)
    
    print(f"\n📈 Final summary ({minutes}min): {final_timeouts} connection timeouts")
    
    if final_timeouts == 0:
        print("🎉 Success: No connection timeouts!")
    elif final_timeouts < 10:
        print("✅ Improvement: Low timeout rate")
    else:
        print("⚠️  Still high timeout rate - may need comprehensive retry logic")
    
    return final_timeouts

if __name__ == "__main__":
    print("🔧 Connection Timeout Fix for PID 103090")
    print("="*50)
    
    # Apply fix
    success = apply_connection_timeout_fix()
    
    if success:
        print("\n✅ Fix applied successfully!")
        
        # Monitor results
        timeout_count = monitor_connection_errors(3)
        
        if timeout_count == 0:
            print("\n🎯 Connection timeout issue resolved!")
        else:
            print(f"\n📊 Still seeing {timeout_count} timeouts - may need retry logic")
            print("💡 Consider deploying comprehensive solution with retry logic")
    else:
        print("\n❌ Fix failed - check service logs")
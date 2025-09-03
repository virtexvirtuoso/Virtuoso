#!/usr/bin/env python3
"""
Monitor timeout improvements after applying the fix
"""
import subprocess
import time
from datetime import datetime

def monitor_timeout_improvements(duration_minutes=5):
    """Monitor system for timeout improvements"""
    
    print(f"🔍 Monitoring timeout improvements for {duration_minutes} minutes...")
    print(f"Start time: {datetime.now()}")
    
    # Baseline - get current timeout count
    cmd_timeout = 'ssh linuxuser@VPS_HOST_REDACTED "sudo journalctl -u virtuoso.service --since \'5 minutes ago\' | grep -c \'Request timeout\'"'
    result = subprocess.run(cmd_timeout, shell=True, capture_output=True, text=True)
    baseline_timeouts = int(result.stdout.strip() or 0)
    
    cmd_empty = 'ssh linuxuser@VPS_HOST_REDACTED "sudo journalctl -u virtuoso.service --since \'5 minutes ago\' | grep -c \'Empty DataFrame\'"'
    result = subprocess.run(cmd_empty, shell=True, capture_output=True, text=True)
    baseline_empty = int(result.stdout.strip() or 0)
    
    print(f"📊 Baseline (last 5min): {baseline_timeouts} timeouts, {baseline_empty} empty DataFrames")
    
    # Monitor for specified duration
    start_time = time.time()
    check_interval = 60  # Check every minute
    
    while time.time() - start_time < duration_minutes * 60:
        time.sleep(check_interval)
        
        elapsed_minutes = int((time.time() - start_time) / 60)
        print(f"\n⏱️  Elapsed: {elapsed_minutes}min")
        
        # Check for new timeouts
        cmd_recent_timeout = f'ssh linuxuser@VPS_HOST_REDACTED "sudo journalctl -u virtuoso.service --since \'{elapsed_minutes + 1} minutes ago\' | grep \'Request timeout after 10s\'"'
        result = subprocess.run(cmd_recent_timeout, shell=True, capture_output=True, text=True)
        recent_timeouts = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        # Check for empty DataFrames
        cmd_recent_empty = f'ssh linuxuser@VPS_HOST_REDACTED "sudo journalctl -u virtuoso.service --since \'{elapsed_minutes + 1} minutes ago\' | grep \'Empty DataFrame\'"'
        result = subprocess.run(cmd_recent_empty, shell=True, capture_output=True, text=True)
        recent_empty = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        timeout_count = len([t for t in recent_timeouts if t.strip()])
        empty_count = len([e for e in recent_empty if e.strip()])
        
        if timeout_count > 0:
            print(f"   ❌ {timeout_count} new timeouts (now 10s instead of 15s)")
            # Show last timeout for debugging
            if recent_timeouts:
                print(f"      Latest: {recent_timeouts[-1].split(': ')[-1] if ': ' in recent_timeouts[-1] else 'N/A'}")
        else:
            print(f"   ✅ No new timeouts")
        
        if empty_count > 0:
            print(f"   ⚠️  {empty_count} empty DataFrames")
        else:
            print(f"   ✅ No empty DataFrames")
    
    # Final summary
    print(f"\n{'='*60}")
    print("MONITORING SUMMARY")
    print(f"{'='*60}")
    
    # Get final counts
    cmd_final_timeout = f'ssh linuxuser@VPS_HOST_REDACTED "sudo journalctl -u virtuoso.service --since \'{duration_minutes} minutes ago\' | grep -c \'Request timeout after 10s\'"'
    result = subprocess.run(cmd_final_timeout, shell=True, capture_output=True, text=True)
    final_timeouts = int(result.stdout.strip() or 0)
    
    cmd_final_empty = f'ssh linuxuser@VPS_HOST_REDACTED "sudo journalctl -u virtuoso.service --since \'{duration_minutes} minutes ago\' | grep -c \'Empty DataFrame\'"'
    result = subprocess.run(cmd_final_empty, shell=True, capture_output=True, text=True)
    final_empty = int(result.stdout.strip() or 0)
    
    print(f"📊 Monitoring period ({duration_minutes}min): {final_timeouts} timeouts, {final_empty} empty DataFrames")
    
    # Calculate improvement
    if baseline_timeouts > 0:
        timeout_change = ((final_timeouts - baseline_timeouts) / baseline_timeouts) * 100
        print(f"📈 Timeout change: {timeout_change:+.1f}%")
    
    if baseline_empty > 0:
        empty_change = ((final_empty - baseline_empty) / baseline_empty) * 100
        print(f"📈 Empty DataFrame change: {empty_change:+.1f}%")
    
    # Check if system is running normally
    cmd_status = 'ssh linuxuser@VPS_HOST_REDACTED "sudo systemctl is-active virtuoso.service"'
    result = subprocess.run(cmd_status, shell=True, capture_output=True, text=True)
    
    if "active" in result.stdout:
        print("✅ System running normally")
    else:
        print("❌ System not running normally")
    
    return final_timeouts, final_empty

if __name__ == "__main__":
    try:
        timeouts, empty_dfs = monitor_timeout_improvements(5)
        
        print(f"\n🎯 RESULTS:")
        print(f"   Timeouts: {timeouts} (faster failure detection with 10s timeout)")
        print(f"   Empty DataFrames: {empty_dfs}")
        
        if timeouts < 10:
            print("✅ Good: Low timeout rate")
        else:
            print("⚠️  High timeout rate - may need additional fixes")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Error during monitoring: {e}")
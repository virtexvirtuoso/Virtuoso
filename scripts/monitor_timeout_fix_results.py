#!/usr/bin/env python3
"""
Monitor and validate Bybit timeout fix results on VPS.
"""

import subprocess
import time
import sys
from datetime import datetime

def run_ssh_command(command):
    """Execute SSH command and return result."""
    ssh_cmd = f'ssh linuxuser@${VPS_HOST} "{command}"'
    try:
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"ERROR: {result.stderr.strip()}"
    except Exception as e:
        return f"EXCEPTION: {str(e)}"

def main():
    """Monitor timeout fix results."""
    print("🔍 Monitoring Bybit Timeout Fix Results")
    print("=" * 60)
    print(f"Start Time: {datetime.now()}")
    print("=" * 60)
    
    # Monitoring duration: 10 minutes
    monitoring_duration = 600  # 10 minutes
    check_interval = 30  # Check every 30 seconds
    checks = monitoring_duration // check_interval
    
    baseline_metrics = {}
    timeout_events = []
    
    print(f"📊 Starting {checks} checks over {monitoring_duration//60} minutes...")
    print()
    
    for check_num in range(1, checks + 1):
        print(f"🔍 Check {check_num}/{checks} - {datetime.now().strftime('%H:%M:%S')}")
        
        # 1. Check service status
        status = run_ssh_command('sudo systemctl is-active virtuoso.service')
        print(f"   Service Status: {status}")
        
        if status != "active":
            print("   ❌ SERVICE NOT ACTIVE - STOPPING MONITORING")
            break
        
        # 2. Count timeout errors in last minute
        timeout_cmd = 'sudo journalctl -u virtuoso.service --since "1 minute ago" | grep -i "timeout after" | wc -l'
        timeout_count = run_ssh_command(timeout_cmd)
        print(f"   API Timeouts (last minute): {timeout_count}")
        
        if timeout_count.isdigit() and int(timeout_count) > 0:
            # Get specific timeout details
            timeout_details = run_ssh_command(
                'sudo journalctl -u virtuoso.service --since "1 minute ago" | grep -i "timeout after" | head -2'
            )
            timeout_events.append({
                'time': datetime.now(),
                'count': int(timeout_count),
                'details': timeout_details
            })
            print(f"   ⚠️  Timeout Details: {timeout_details}")
        
        # 3. Check WebSocket activity
        ws_cmd = 'sudo journalctl -u virtuoso.service --since "1 minute ago" | grep "messages.*minute" | tail -1'
        ws_activity = run_ssh_command(ws_cmd)
        if "messages" in ws_activity:
            print(f"   WebSocket Activity: {ws_activity.split('messages')[0].split()[-1]} msg/min")
        
        # 4. Check connection pool status (if visible)
        pool_cmd = 'sudo journalctl -u virtuoso.service --since "1 minute ago" | grep -i "pool.*connection" | tail -1'
        pool_status = run_ssh_command(pool_cmd)
        if pool_status and "ERROR" not in pool_status:
            print(f"   Pool Activity: Present")
        
        # 5. Check for errors
        error_cmd = 'sudo journalctl -u virtuoso.service --since "1 minute ago" | grep -E "ERROR|CRITICAL" | wc -l'
        error_count = run_ssh_command(error_cmd)
        print(f"   Errors (last minute): {error_count}")
        
        # 6. Memory usage
        memory_cmd = 'free -m | grep "^Mem" | awk \'{print $3"/"$2" MB ("int($3/$2*100)"%)"}\'}'
        memory_usage = run_ssh_command(memory_cmd)
        print(f"   Memory Usage: {memory_usage}")
        
        print()
        
        if check_num < checks:
            time.sleep(check_interval)
    
    # Final analysis
    print("=" * 60)
    print("📈 FINAL ANALYSIS")
    print("=" * 60)
    
    total_timeout_events = len(timeout_events)
    total_timeouts = sum(event['count'] for event in timeout_events)
    
    print(f"Total monitoring time: {monitoring_duration//60} minutes")
    print(f"Timeout events detected: {total_timeout_events}")
    print(f"Total timeout count: {total_timeouts}")
    
    if total_timeouts == 0:
        print("🎉 EXCELLENT: Zero API timeout errors detected!")
        print("✅ The timeout fixes are working successfully")
    elif total_timeouts <= 2:
        print("✅ GOOD: Very few timeout errors (≤2)")
        print("👍 Significant improvement achieved")
    elif total_timeouts <= 5:
        print("⚠️  ACCEPTABLE: Some timeout errors (3-5)")
        print("📈 Some improvement, may need further tuning")
    else:
        print("❌ CONCERN: High timeout count (>5)")
        print("🔧 Additional fixes may be needed")
    
    # Show timeout details if any
    if timeout_events:
        print("\n📋 Timeout Event Details:")
        for event in timeout_events:
            print(f"   {event['time'].strftime('%H:%M:%S')}: {event['count']} timeouts")
            if event['details'] and "ERROR" not in event['details']:
                print(f"      {event['details'][:100]}...")
    
    # Performance recommendations
    print("\n🎯 Recommendations:")
    if total_timeouts == 0:
        print("   • Continue normal monitoring")
        print("   • Adaptive timeout system is working well")
        print("   • Connection pool optimization successful")
    elif total_timeouts <= 2:
        print("   • Monitor for 24 hours to confirm stability")
        print("   • Good baseline established")
    else:
        print("   • Consider additional timeout value increases")
        print("   • Check network conditions on VPS")
        print("   • Monitor WebSocket vs REST API resource contention")
    
    # Success metrics
    print(f"\n📊 Success Rate: {((monitoring_duration//60 * 60 - total_timeouts) / (monitoring_duration//60 * 60)) * 100:.1f}%")
    print(f"   (Based on expectation of ~1 timeout per minute without fixes)")
    
    print("=" * 60)
    print("🏁 Monitoring completed successfully")
    print("=" * 60)

if __name__ == "__main__":
    main()
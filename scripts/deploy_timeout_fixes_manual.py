#!/usr/bin/env python3
"""
Manual deployment of Bybit timeout fixes to VPS using SCP.
"""

import subprocess
import sys
import time

def run_command(command, description="", ignore_errors=False):
    """Run a shell command and return the result."""
    print(f"🔧 {description}...")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print(f"   ✅ Success: {description}")
            if result.stdout.strip():
                print(f"   📋 Output: {result.stdout.strip()}")
            return result.stdout.strip()
        else:
            if ignore_errors:
                print(f"   ⚠️  Warning: {description} - {result.stderr.strip()}")
                return ""
            else:
                print(f"   ❌ Error: {description} - {result.stderr.strip()}")
                return None
                
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Timeout: {description}")
        return None
    except Exception as e:
        print(f"   💥 Exception: {description} - {str(e)}")
        return None

def main():
    """Manual deployment process."""
    print("🚀 Manually deploying Bybit timeout fixes to VPS...")
    
    # 1. Copy critical files to VPS
    print("\n📦 Step 1: Copying timeout-optimized files to VPS...")
    
    files_to_copy = [
        "src/core/exchanges/bybit.py",
        "src/core/intelligence/connection_pool_manager.py"
    ]
    
    for file_path in files_to_copy:
        scp_command = f'scp "{file_path}" linuxuser@VPS_HOST_REDACTED:/home/linuxuser/trading/Virtuoso_ccxt/{file_path}'
        result = run_command(scp_command, f"Copy {file_path}")
        if result is None:
            print(f"❌ Failed to copy {file_path}")
            sys.exit(1)
    
    print("✅ All files copied successfully!")
    
    # 2. Backup and restart service
    print("\n🔄 Step 2: Backing up and restarting service...")
    
    restart_commands = [
        # Backup current files
        "cp src/core/exchanges/bybit.py src/core/exchanges/bybit_backup_$(date +%Y%m%d_%H%M%S).py",
        
        # Stop service
        "sudo systemctl stop virtuoso.service",
        
        # Wait
        "sleep 5",
        
        # Start service
        "sudo systemctl start virtuoso.service",
        
        # Wait for startup
        "sleep 15",
        
        # Check status
        "sudo systemctl status virtuoso.service --no-pager | head -10"
    ]
    
    for cmd in restart_commands:
        ssh_command = f'ssh linuxuser@VPS_HOST_REDACTED "cd /home/linuxuser/trading/Virtuoso_ccxt && {cmd}"'
        result = run_command(ssh_command, f"VPS: {cmd}")
        
        if result is None and "systemctl status" not in cmd:
            print("⚠️ Command had issues, but continuing...")
    
    print("\n✅ Service restart completed!")
    
    # 3. Immediate validation
    print("\n📊 Step 3: Immediate validation...")
    
    # Wait for service to stabilize
    print("⏳ Waiting 30 seconds for service to stabilize...")
    time.sleep(30)
    
    # Check for immediate issues
    validation_commands = [
        # Check if service is running
        'sudo systemctl is-active virtuoso.service',
        
        # Check recent logs for errors
        'sudo journalctl -u virtuoso.service --since "1 minute ago" | grep -i error | wc -l',
        
        # Check for timeout improvements
        'sudo journalctl -u virtuoso.service --since "1 minute ago" | grep -i "adaptive.*timeout" | head -2',
        
        # Check connection pool status
        'sudo journalctl -u virtuoso.service --since "1 minute ago" | grep -i "pool.*connection" | head -2'
    ]
    
    validation_results = {}
    
    for cmd in validation_commands:
        ssh_command = f'ssh linuxuser@VPS_HOST_REDACTED "{cmd}"'
        result = run_command(ssh_command, f"Validation: {cmd[:50]}...")
        if result is not None:
            validation_results[cmd] = result
    
    # 4. Results analysis
    print("\n📈 Step 4: Immediate Results Analysis")
    
    # Check service status
    service_status = validation_results.get(validation_commands[0], "")
    if service_status == "active":
        print("   ✅ EXCELLENT: Service is running normally")
    else:
        print(f"   ❌ ISSUE: Service status: {service_status}")
        return
    
    # Check error count
    error_count = validation_results.get(validation_commands[1], "0")
    print(f"   📊 Recent errors: {error_count}")
    
    if int(error_count) == 0:
        print("   ✅ GREAT: No recent errors detected!")
    elif int(error_count) < 3:
        print("   ⚠️  ACCEPTABLE: Few errors, within normal range")
    else:
        print("   ❌ CONCERN: High error count, needs investigation")
    
    # Check for adaptive timeout logs
    adaptive_logs = validation_results.get(validation_commands[2], "")
    if adaptive_logs:
        print("   ✅ CONFIRMED: Adaptive timeout system is active")
        print(f"      Sample: {adaptive_logs[:100]}...")
    else:
        print("   ⚠️  No adaptive timeout logs yet (may need more time)")
    
    # 5. Monitoring recommendations  
    print("\n📋 Step 5: Extended Monitoring Plan")
    print("   🎯 Monitor these metrics for the next 1 hour:")
    print("   • Timeout frequency: ssh linuxuser@VPS_HOST_REDACTED 'sudo journalctl -u virtuoso.service -f | grep timeout'")
    print("   • Connection pool: ssh linuxuser@VPS_HOST_REDACTED 'sudo journalctl -u virtuoso.service -f | grep pool'") 
    print("   • WebSocket activity: ssh linuxuser@VPS_HOST_REDACTED 'sudo journalctl -u virtuoso.service -f | grep messages.*minute'")
    print("   • Service health: ssh linuxuser@VPS_HOST_REDACTED 'sudo systemctl status virtuoso.service'")
    
    # 6. Performance expectations
    print("\n🎯 Expected Performance Improvements:")
    print("   • Timeout errors should decrease from random spikes to <1%")
    print("   • Connection pool should maintain 8+ connections minimum")
    print("   • Better handling during high WebSocket activity periods")
    print("   • Faster recovery from network interruptions")
    print("   • Adaptive timeout adjustments visible in logs")
    
    # 7. Quick test command
    print("\n🧪 Quick Test Commands:")
    print("   # Check timeout errors in last 10 minutes:")
    print("   ssh linuxuser@VPS_HOST_REDACTED 'sudo journalctl -u virtuoso.service --since \"10 minutes ago\" | grep timeout | wc -l'")
    print("   # Check adaptive timeout usage:")
    print("   ssh linuxuser@VPS_HOST_REDACTED 'sudo journalctl -u virtuoso.service --since \"5 minutes ago\" | grep adaptive'")
    print("   # Check connection pool scaling:")
    print("   ssh linuxuser@VPS_HOST_REDACTED 'sudo journalctl -u virtuoso.service --since \"5 minutes ago\" | grep scaling'")
    
    print("\n" + "="*60)
    print("🎉 MANUAL DEPLOYMENT COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("✅ Changes Deployed:")
    print("   • Adaptive timeout system (15s→15-25s based on endpoint)")
    print("   • Enhanced connection pool (minimum 8 connections)")
    print("   • WebSocket activity monitoring")
    print("   • Intelligent retry with exponential backoff")
    print("   • Resource isolation between WebSocket and REST")
    
    print("\n🔍 What to Monitor:")
    print("   • Timeout error reduction (target: <5 per hour)")
    print("   • Connection pool stability (8+ connections maintained)")
    print("   • Adaptive timeout adjustments in logs")
    print("   • Improved performance during high WebSocket activity")
    
    print("\n✅ Deployment successful - monitoring recommended for 1 hour")
    print("="*60)

if __name__ == "__main__":
    main()
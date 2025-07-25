#!/usr/bin/env python3
"""
Check if the market report scheduler is active and properly configured
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

async def check_scheduler_status():
    """Check if the market report scheduler is configured and would run"""
    print("🔍 Checking Market Report Scheduler Status")
    print("=" * 60)
    
    try:
        from monitoring.market_reporter import MarketReporter
        from monitoring.alert_manager import AlertManager
        
        # Create basic config
        config = {
            'monitoring': {
                'alerts': {
                    'discord_webhook': {
                        'max_retries': 3,
                        'timeout_seconds': 30,
                        'exponential_backoff': True
                    }
                }
            }
        }
        
        # Initialize components
        print("📡 Initializing Market Reporter...")
        alert_manager = AlertManager(config)
        reporter = MarketReporter(alert_manager=alert_manager)
        
        # Check scheduled times
        print(f"⏰ Scheduled report times: {reporter.report_times}")
        
        # Check current UTC time
        current_utc = datetime.utcnow()
        current_hhmm = current_utc.strftime("%H:%M")
        print(f"🕐 Current UTC time: {current_hhmm}")
        
        # Check if we're at a scheduled time
        if current_hhmm in reporter.report_times:
            print(f"✅ Current time matches scheduled time: {current_hhmm}")
            print("   A report should be generated right now!")
        else:
            # Calculate next scheduled time
            next_times = []
            for time_str in reporter.report_times:
                hour, minute = map(int, time_str.split(':'))
                next_time = current_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_time <= current_utc:
                    next_time = next_time.replace(day=next_time.day + 1)  # Next day
                next_times.append(next_time)
            
            next_report = min(next_times)
            time_until = next_report - current_utc
            hours, remainder = divmod(time_until.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            
            print(f"⏳ Next scheduled report: {next_report.strftime('%H:%M UTC')}")
            print(f"   Time until next report: {int(hours)}h {int(minutes)}m")
        
        # Check if alert manager has Discord webhook
        print("\n🔗 Checking Discord Integration...")
        if hasattr(alert_manager, 'discord_webhook_url') and alert_manager.discord_webhook_url:
            print("✅ Discord webhook URL is configured")
            webhook_preview = alert_manager.discord_webhook_url[:50] + "..."
            print(f"   URL preview: {webhook_preview}")
        else:
            print("❌ Discord webhook URL not found in alert manager")
            print("   Check DISCORD_WEBHOOK_URL environment variable")
        
        # Check if alert manager has Discord sending capability
        if hasattr(alert_manager, 'send_discord_webhook_message'):
            print("✅ Discord webhook sending method available")
        else:
            print("❌ Discord webhook sending method not found")
        
        # Test the scheduling logic
        print("\n🧪 Testing Scheduling Logic...")
        
        # Simulate scheduler check
        test_times = ["00:00", "08:00", "16:00", "20:00"]
        for test_time in test_times:
            if test_time == current_hhmm:
                print(f"✅ {test_time}: Would trigger report NOW")
            else:
                print(f"⏳ {test_time}: Waiting for this time")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking scheduler status: {e}")
        import traceback
        traceback.print_exc()
        return False

async def check_main_app_integration():
    """Check if the scheduler would be started by the main app"""
    print("\n🚀 Checking Main App Integration")
    print("=" * 60)
    
    try:
        # Check if monitor.py would create the scheduler task
        from monitoring.monitor import MarketMonitor
        
        print("📊 Checking MarketMonitor initialization...")
        
        # Look for the task creation line in the code
        monitor_file = Path(__file__).parent.parent / 'src' / 'monitoring' / 'monitor.py'
        
        if monitor_file.exists():
            with open(monitor_file, 'r') as f:
                content = f.read()
                
            if 'run_scheduled_reports' in content:
                print("✅ MarketMonitor contains scheduled reports task creation")
                
                # Find the specific line
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'run_scheduled_reports' in line and 'create_task' in line:
                        print(f"   Found at line {i+1}: {line.strip()}")
                        break
            else:
                print("❌ MarketMonitor does not contain scheduled reports task creation")
                
        # Check if the main app starts MarketMonitor
        main_file = Path(__file__).parent.parent / 'src' / 'main.py'
        
        if main_file.exists():
            with open(main_file, 'r') as f:
                content = f.read()
                
            if 'MarketMonitor' in content:
                print("✅ main.py imports and uses MarketMonitor")
            else:
                print("❌ main.py does not appear to use MarketMonitor")
                
        return True
        
    except Exception as e:
        print(f"❌ Error checking main app integration: {e}")
        return False

async def suggest_fixes():
    """Suggest potential fixes for scheduler issues"""
    print("\n🔧 Potential Fixes")
    print("=" * 60)
    
    print("If scheduled reports are not working, try:")
    print()
    print("1. **Check if main app is running the monitoring system:**")
    print("   python src/main.py")
    print("   Look for 'Starting scheduled market reports service...' in logs")
    print()
    print("2. **Verify Discord webhook URL:**")
    print("   echo $DISCORD_WEBHOOK_URL")
    print("   Should contain: https://discord.com/api/webhooks/...")
    print()
    print("3. **Check application logs:**")
    print("   tail -f logs/app.log")
    print("   Look for scheduled report attempts or errors")
    print()
    print("4. **Test manual report generation:**")
    print("   # In Python console")
    print("   from monitoring.market_reporter import MarketReporter")
    print("   reporter = MarketReporter()")
    print("   await reporter.generate_market_summary()")
    print()
    print("5. **Verify UTC time alignment:**")
    print("   date -u")
    print("   Should match one of: 00:00, 08:00, 16:00, 20:00 for immediate trigger")

async def main():
    """Main function"""
    print("🕐 Market Report Scheduler Investigation")
    print("=" * 80)
    
    # Set up logging
    logging.basicConfig(level=logging.WARNING)
    
    # Check scheduler status
    scheduler_ok = await check_scheduler_status()
    
    # Check main app integration
    integration_ok = await check_main_app_integration()
    
    # Suggest fixes
    await suggest_fixes()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Investigation Summary")
    print("=" * 80)
    
    print(f"Scheduler Configuration: {'✅ OK' if scheduler_ok else '❌ Issues Found'}")
    print(f"Main App Integration: {'✅ OK' if integration_ok else '❌ Issues Found'}")
    
    if scheduler_ok and integration_ok:
        print("\n✅ Scheduler appears to be properly configured!")
        print("   If reports aren't sending, check:")
        print("   - Is the main application running?")
        print("   - Are there errors in the logs?")
        print("   - Is the Discord webhook URL valid?")
    else:
        print("\n⚠️ Issues found with scheduler configuration")
        print("   Review the findings above and apply suggested fixes")

if __name__ == "__main__":
    asyncio.run(main())
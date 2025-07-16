#!/usr/bin/env python3
"""
Verify whale monitoring system configuration and readiness.
This test checks the system without actually starting it.
"""

import os
import sys
import json
import importlib.util

def test_whale_system_readiness():
    """Test whale monitoring system readiness without starting it."""
    
    print("🔍 WHALE MONITORING SYSTEM VERIFICATION")
    print("=" * 50)
    
    results = {
        "config_check": False,
        "monitor_file_check": False,
        "whale_method_check": False,
        "alert_manager_check": False,
        "discord_webhook_check": False,
        "main_entry_check": False
    }
    
    # 1. Check configuration
    print("\n📋 1. CONFIGURATION CHECK")
    try:
        import yaml
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        whale_config = config.get('monitoring', {}).get('whale_activity', {})
        
        if whale_config.get('enabled', False):
            print("✅ Whale monitoring is ENABLED in config")
            print(f"   - Accumulation threshold: ${whale_config.get('accumulation_threshold', 0):,}")
            print(f"   - Distribution threshold: ${whale_config.get('distribution_threshold', 0):,}")
            print(f"   - Imbalance threshold: {whale_config.get('imbalance_threshold', 0)*100:.1f}%")
            print(f"   - Min order count: {whale_config.get('min_order_count', 0)}")
            print(f"   - Cooldown: {whale_config.get('cooldown', 0)} seconds")
            results["config_check"] = True
        else:
            print("❌ Whale monitoring is DISABLED in config")
            
    except Exception as e:
        print(f"❌ Error reading config: {str(e)}")
    
    # 2. Check monitor file exists
    print("\n📁 2. MONITOR FILE CHECK")
    monitor_file = 'src/monitoring/monitor.py'
    if os.path.exists(monitor_file):
        print("✅ MarketMonitor file exists")
        results["monitor_file_check"] = True
        
        # Check for whale method
        try:
            with open(monitor_file, 'r') as f:
                content = f.read()
                if '_monitor_whale_activity' in content:
                    print("✅ Whale monitoring method found")
                    if 'imbalance' in content:
                        print("✅ Imbalance calculations present")
                        results["whale_method_check"] = True
                    else:
                        print("⚠️  Imbalance calculations may be missing")
                else:
                    print("❌ Whale monitoring method not found")
        except Exception as e:
            print(f"❌ Error reading monitor file: {str(e)}")
    else:
        print("❌ MarketMonitor file not found")
    
    # 3. Check alert manager
    print("\n🔔 3. ALERT MANAGER CHECK")
    alert_file = 'src/monitoring/alert_manager.py'
    if os.path.exists(alert_file):
        print("✅ AlertManager file exists")
        
        try:
            with open(alert_file, 'r') as f:
                content = f.read()
                if 'whale_activity' in content:
                    print("✅ Whale activity alert handling found")
                    results["alert_manager_check"] = True
                else:
                    print("⚠️  Whale activity alert handling may be missing")
        except Exception as e:
            print(f"❌ Error reading alert manager file: {str(e)}")
    else:
        print("❌ AlertManager file not found")
    
    # 4. Check Discord webhook
    print("\n🔗 4. DISCORD WEBHOOK CHECK")
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if webhook_url:
        print("✅ Discord webhook URL is configured")
        if webhook_url.startswith('https://discord.com/api/webhooks/'):
            print("✅ Discord webhook URL format is correct")
            results["discord_webhook_check"] = True
        else:
            print("⚠️  Discord webhook URL format may be incorrect")
    else:
        print("❌ DISCORD_WEBHOOK_URL environment variable not set")
    
    # 5. Check main entry point
    print("\n🚀 5. MAIN ENTRY POINT CHECK")
    main_file = 'src/main.py'
    if os.path.exists(main_file):
        print("✅ Main entry point exists")
        
        try:
            with open(main_file, 'r') as f:
                content = f.read()
                if 'MarketMonitor' in content and 'start' in content:
                    print("✅ MarketMonitor startup code found")
                    results["main_entry_check"] = True
                else:
                    print("⚠️  MarketMonitor startup code may be missing")
        except Exception as e:
            print(f"❌ Error reading main file: {str(e)}")
    else:
        print("❌ Main entry point not found")
    
    # 6. Summary
    print("\n📊 SYSTEM READINESS SUMMARY")
    print("=" * 30)
    
    passed_checks = sum(results.values())
    total_checks = len(results)
    
    print(f"✅ Passed: {passed_checks}/{total_checks} checks")
    
    if passed_checks == total_checks:
        print("\n🎉 EXCELLENT: Whale monitoring system is fully configured and ready!")
        print("\n💡 TO START WHALE MONITORING:")
        print("   Run: python src/main.py")
        print("   The system will automatically monitor for whale activity")
        print("   Look for logs: 'Monitoring whale activity for [SYMBOL]'")
        
    elif passed_checks >= 3:
        print("\n⚠️  GOOD: Most components are ready, but some issues detected")
        print("\n🔧 ISSUES TO FIX:")
        for check, status in results.items():
            if not status:
                print(f"   - {check.replace('_', ' ').title()}")
                
    else:
        print("\n❌ POOR: Multiple critical issues detected")
        print("\n🔧 CRITICAL ISSUES:")
        for check, status in results.items():
            if not status:
                print(f"   - {check.replace('_', ' ').title()}")
    
    # 7. Whale threshold analysis
    print("\n🐋 WHALE THRESHOLD ANALYSIS")
    print("-" * 30)
    
    try:
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        whale_config = config.get('monitoring', {}).get('whale_activity', {})
        
        acc_threshold = whale_config.get('accumulation_threshold', 0)
        dist_threshold = whale_config.get('distribution_threshold', 0)
        imb_threshold = whale_config.get('imbalance_threshold', 0)
        min_orders = whale_config.get('min_order_count', 0)
        
        print(f"Current thresholds:")
        print(f"  - Accumulation: ${acc_threshold:,}")
        print(f"  - Distribution: ${dist_threshold:,}")
        print(f"  - Imbalance: {imb_threshold*100:.1f}%")
        print(f"  - Min orders: {min_orders}")
        
        if acc_threshold >= 5000000:
            print("⚠️  High thresholds: May see few alerts (very restrictive)")
        elif acc_threshold >= 1000000:
            print("ℹ️  Moderate thresholds: Balanced detection")
        else:
            print("ℹ️  Low thresholds: More sensitive detection")
            
        print("\n🎯 EXPECTED BEHAVIOR:")
        print("   - The system uses statistical analysis to detect whale orders")
        print("   - Whale threshold = mean + (2 * std_dev) of order sizes")
        print("   - Only triggers alerts when all conditions are met:")
        print(f"     • USD value > ${acc_threshold:,}")
        print(f"     • Order count >= {min_orders}")
        print(f"     • Imbalance > {imb_threshold*100:.1f}%")
        print("   - If no alerts, it means no whale activity meets ALL criteria")
        
    except Exception as e:
        print(f"❌ Error analyzing thresholds: {str(e)}")
    
    return results

if __name__ == "__main__":
    try:
        results = test_whale_system_readiness()
        
        # Exit with status based on results
        passed = sum(results.values())
        total = len(results)
        
        if passed == total:
            print(f"\n✅ SUCCESS: All {total} checks passed!")
            sys.exit(0)
        elif passed >= 3:
            print(f"\n⚠️  PARTIAL: {passed}/{total} checks passed")
            sys.exit(1)
        else:
            print(f"\n❌ FAILURE: Only {passed}/{total} checks passed")
            sys.exit(2)
            
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {str(e)}")
        sys.exit(3) 
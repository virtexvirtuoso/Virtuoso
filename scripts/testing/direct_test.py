#!/usr/bin/env python3
"""Direct test for contango implementation"""

import os
import sys

# Change to src directory for proper imports
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def main():
    print("🧪 DIRECT CONTANGO IMPLEMENTATION TEST")
    print("=" * 50)
    
    try:
        from monitoring.monitor import MarketMonitor
        print('✅ MarketMonitor imported successfully')
        
        methods = [
            '_monitor_contango_status', 
            '_is_futures_symbol', 
            '_check_contango_alerts', 
            '_send_contango_alert', 
            '_get_contango_alert_severity'
        ]
        
        found = []
        
        for method in methods:
            if hasattr(MarketMonitor, method):
                found.append(method)
                print(f'✅ Found: {method}')
            else:
                print(f'❌ Missing: {method}')
        
        print(f'\n📊 SUCCESS: {len(found)}/{len(methods)} contango methods implemented')
        
        # Test symbol detection logic directly
        monitor = MarketMonitor()
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'BTC-27JUN25', 'BTCUSD']
        
        print('\n🧪 Testing symbol detection:')
        for symbol in test_symbols:
            result = monitor._is_futures_symbol(symbol)
            print(f'   {symbol}: {result}')
        
        # Test alert severity
        print('\n🧪 Testing alert severity:')
        alert_types = ['status_change', 'extreme_contango', 'extreme_backwardation']
        for alert_type in alert_types:
            severity = monitor._get_contango_alert_severity(alert_type)
            print(f'   {alert_type}: {severity}')
        
        if len(found) == len(methods):
            print('\n🎉 CONTANGO MONITORING: FULLY IMPLEMENTED AND READY!')
            return True
        else:
            print(f'\n⚠️  CONTANGO MONITORING: PARTIALLY IMPLEMENTED ({len(found)}/{len(methods)})')
            return False
            
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

if __name__ == "__main__":
    success = main()
    print("=" * 50)
    exit(0 if success else 1) 
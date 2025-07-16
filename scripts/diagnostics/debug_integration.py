#!/usr/bin/env python3

import sys
sys.path.append('src')

from dashboard_integration import get_dashboard_integration

def test_integration():
    integration = get_dashboard_integration()
    
    if not integration:
        print("❌ No dashboard integration found")
        return
        
    print("✅ Dashboard integration found")
    print(f"Monitor type: {type(integration.monitor) if integration.monitor else None}")
    
    if not integration.monitor:
        print("❌ Monitor is None")
        return
        
    print("✅ Monitor exists")
    print(f"Monitor has symbols: {hasattr(integration.monitor, 'symbols')}")
    print(f"Monitor has market_data_manager: {hasattr(integration.monitor, 'market_data_manager')}")
    
    if hasattr(integration.monitor, 'symbols'):
        symbols = getattr(integration.monitor, 'symbols', [])
        print(f"Symbols count: {len(symbols)}")
        if symbols:
            print(f"First 5 symbols: {symbols[:5]}")
    
    if hasattr(integration.monitor, 'market_data_manager'):
        mdm = getattr(integration.monitor, 'market_data_manager')
        print(f"Market data manager type: {type(mdm)}")

if __name__ == "__main__":
    test_integration() 
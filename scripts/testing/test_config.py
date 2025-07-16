#!/usr/bin/env python3

import os
import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

from src.config.manager import ConfigManager

def test_config():
    print("=== Environment Variables ===")
    print(f"ENABLE_BINANCE_DATA: {os.getenv('ENABLE_BINANCE_DATA')}")
    print(f"BINANCE_AS_PRIMARY: {os.getenv('BINANCE_AS_PRIMARY')}")
    
    print("\n=== Loading Configuration ===")
    config_manager = ConfigManager()
    
    print("\n=== Exchanges Configuration ===")
    exchanges = config_manager.get_value('exchanges', {})
    
    for exchange_id, config in exchanges.items():
        enabled = config.get('enabled', False)
        primary = config.get('primary', False)
        print(f"{exchange_id}:")
        print(f"  enabled: {enabled}")
        print(f"  primary: {primary}")
        print()

if __name__ == "__main__":
    test_config() 
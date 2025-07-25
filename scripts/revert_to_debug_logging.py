#!/usr/bin/env python3
"""
Revert Logging to DEBUG Mode
Reverts all logging configurations back to DEBUG level for detailed troubleshooting.
"""

import yaml
import os
import shutil
from datetime import datetime

def revert_logging_to_debug():
    """Revert all logging configurations to DEBUG mode"""
    
    config_path = "config/config.yaml"
    backup_path = f"config/config.yaml.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("🔄 Reverting logging configuration to DEBUG mode...")
    
    # Create backup
    if os.path.exists(config_path):
        shutil.copy2(config_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
    
    # Load current config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Revert logging levels to DEBUG
    changes_made = []
    
    # System log level
    if config.get('system', {}).get('log_level') != 'DEBUG':
        config['system']['log_level'] = 'DEBUG'
        changes_made.append("system.log_level: INFO → DEBUG")
    
    # WebSocket log level
    if config.get('websocket', {}).get('log_level') != 'DEBUG':
        config['websocket']['log_level'] = 'DEBUG'
        changes_made.append("websocket.log_level: INFO → DEBUG")
    
    # Market data websocket log level
    if config.get('market_data', {}).get('websocket_log_level') != 'DEBUG':
        if 'market_data' not in config:
            config['market_data'] = {}
        config['market_data']['websocket_log_level'] = 'DEBUG'
        changes_made.append("market_data.websocket_log_level: INFO → DEBUG")
    
    # Monitoring log level
    if config.get('monitoring', {}).get('log_level') != 'debug':
        if 'monitoring' not in config:
            config['monitoring'] = {}
        config['monitoring']['log_level'] = 'debug'
        changes_made.append("monitoring.log_level: info → debug")
    
    # Save updated config
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)
    
    print(f"✅ Configuration updated with DEBUG logging")
    
    if changes_made:
        print("\n📋 Changes made:")
        for change in changes_made:
            print(f"  • {change}")
    else:
        print("ℹ️  No changes needed - already in DEBUG mode")
    
    print(f"\n🔧 Configuration file: {config_path}")
    print(f"💾 Backup file: {backup_path}")
    
    print("\n⚠️  Note: Application restart required to apply logging changes")
    print("   Run: python scripts/restart_application.py")

if __name__ == "__main__":
    revert_logging_to_debug() 
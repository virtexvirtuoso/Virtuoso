#!/usr/bin/env python3
"""Optimize CPU usage by adjusting configuration settings."""

import yaml
import sys
from pathlib import Path

def optimize_config():
    """Optimize configuration settings to reduce CPU usage."""
    
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        print("❌ Config file not found")
        return False
    
    print("🔧 Optimizing configuration for lower CPU usage...")
    
    # Load current config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Original values for reference
    original_settings = {}
    
    # 1. Reduce monitoring frequency
    if 'monitoring' in config:
        original_settings['monitoring_interval'] = config['monitoring'].get('interval', 30)
        config['monitoring']['interval'] = 60  # Increase from 30 to 60 seconds
        print(f"✅ Monitoring interval: {original_settings['monitoring_interval']}s → 60s")
    
    # 2. Reduce market data update frequency
    if 'market_data' in config:
        original_settings['market_data_update_interval'] = config['market_data'].get('update_interval', 1.0)
        config['market_data']['update_interval'] = 5.0  # Increase from 1.0 to 5.0 seconds
        print(f"✅ Market data update interval: {original_settings['market_data_update_interval']}s → 5.0s")
        
        # Increase WebSocket update throttle
        original_settings['websocket_update_throttle'] = config['market_data'].get('websocket_update_throttle', 5)
        config['market_data']['websocket_update_throttle'] = 15  # Increase from 5 to 15 seconds
        print(f"✅ WebSocket update throttle: {original_settings['websocket_update_throttle']}s → 15s")
    
    # 3. Reduce data processing frequency
    if 'data_processing' in config:
        original_settings['data_processing_update_interval'] = config['data_processing'].get('update_interval', 1.0)
        config['data_processing']['update_interval'] = 5.0  # Increase from 1.0 to 5.0 seconds
        print(f"✅ Data processing update interval: {original_settings['data_processing_update_interval']}s → 5.0s")
    
    # 4. Change log level from DEBUG to INFO
    if 'system' in config:
        original_settings['log_level'] = config['system'].get('log_level', 'DEBUG')
        if config['system']['log_level'] == 'DEBUG':
            config['system']['log_level'] = 'INFO'
            print(f"✅ Log level: {original_settings['log_level']} → INFO")
    
    # 5. Reduce health check frequency
    if 'monitoring' in config:
        original_settings['health_check_interval'] = config['monitoring'].get('health_check_interval', 30)
        config['monitoring']['health_check_interval'] = 120  # Increase from 30 to 120 seconds
        print(f"✅ Health check interval: {original_settings['health_check_interval']}s → 120s")
    
    # 6. Optimize smart intervals
    if 'market_data' in config and 'smart_intervals' in config['market_data']:
        smart_intervals = config['market_data']['smart_intervals']
        original_settings['smart_intervals_min'] = smart_intervals.get('min_interval', 30)
        original_settings['smart_intervals_max'] = smart_intervals.get('max_interval', 60)
        smart_intervals['min_interval'] = 45  # Increase from 30 to 45 seconds
        smart_intervals['max_interval'] = 120  # Increase from 60 to 120 seconds
        print(f"✅ Smart intervals: {original_settings['smart_intervals_min']}-{original_settings['smart_intervals_max']}s → 45-120s")
    
    # 7. Reduce metrics collection frequency
    if 'monitoring' in config and 'metrics' in config['monitoring']:
        original_settings['metrics_collection_interval'] = config['monitoring']['metrics'].get('collection_interval', 60)
        config['monitoring']['metrics']['collection_interval'] = 300  # Increase from 60 to 300 seconds
        print(f"✅ Metrics collection interval: {original_settings['metrics_collection_interval']}s → 300s")
    
    # 8. Reduce memory tracking frequency
    if 'monitoring' in config and 'memory_tracking' in config['monitoring']:
        original_settings['memory_check_interval'] = config['monitoring']['memory_tracking'].get('check_interval_seconds', 300)
        config['monitoring']['memory_tracking']['check_interval_seconds'] = 600  # Increase from 300 to 600 seconds
        print(f"✅ Memory check interval: {original_settings['memory_check_interval']}s → 600s")
    
    # Create backup of original config
    backup_path = config_path.with_suffix('.yaml.backup')
    with open(backup_path, 'w') as f:
        # We need to load the original config again for backup
        with open(config_path, 'r') as orig_f:
            f.write(orig_f.read())
    print(f"✅ Original config backed up to: {backup_path}")
    
    # Write optimized config
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print("\n🎯 CPU Optimization Summary:")
    print("- Reduced monitoring frequency by 50%")
    print("- Increased market data update intervals by 400%")
    print("- Changed log level from DEBUG to INFO")
    print("- Reduced health check frequency by 300%")
    print("- Optimized smart intervals for better performance")
    print("- Reduced metrics collection frequency by 400%")
    
    print(f"\n📁 Configuration optimized and saved to: {config_path}")
    print(f"📁 Original configuration backed up to: {backup_path}")
    print("\n⚠️  Restart the application to apply these changes")
    
    return True

if __name__ == "__main__":
    success = optimize_config()
    sys.exit(0 if success else 1) 
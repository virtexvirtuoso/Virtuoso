#!/usr/bin/env python3
"""
Alpha Alerts Toggle Script
Allows real-time control of alpha alert system without restart
"""

import yaml
import argparse
import os
import sys
from pathlib import Path

def load_config(config_path: str) -> dict:
    """Load the current configuration."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ Error parsing config file: {e}")
        sys.exit(1)

def save_config(config: dict, config_path: str) -> None:
    """Save the updated configuration."""
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"✅ Configuration saved to {config_path}")
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        sys.exit(1)

def toggle_alerts(config_path: str, enable: bool) -> None:
    """Toggle alpha alerts on/off."""
    config = load_config(config_path)
    
    current_status = config['alpha_scanning_optimized'].get('alpha_alerts_enabled', True)
    config['alpha_scanning_optimized']['alpha_alerts_enabled'] = enable
    
    save_config(config, config_path)
    
    status = "ENABLED" if enable else "DISABLED"
    previous_status = "ENABLED" if current_status else "DISABLED"
    
    print(f"🔄 Alpha alerts: {previous_status} → {status}")

def toggle_extreme_mode(config_path: str, enable: bool) -> None:
    """Toggle extreme mode on/off."""
    config = load_config(config_path)
    
    if 'extreme_mode' not in config['alpha_scanning_optimized']:
        config['alpha_scanning_optimized']['extreme_mode'] = {}
    
    current_status = config['alpha_scanning_optimized']['extreme_mode'].get('enabled', False)
    config['alpha_scanning_optimized']['extreme_mode']['enabled'] = enable
    
    save_config(config, config_path)
    
    status = "ENABLED" if enable else "DISABLED"
    previous_status = "ENABLED" if current_status else "DISABLED"
    
    print(f"🎯 Extreme mode: {previous_status} → {status}")
    
    if enable:
        print("⚡ Extreme mode active:")
        print("   • Only 100%+ alpha alerts (Tier 1)")
        print("   • Only 50%+ alpha alerts (Tier 2)")
        print("   • Only Beta Expansion/Compression patterns")
        print("   • Cross Timeframe, Alpha Breakout, Correlation Breakdown DISABLED")
        print("   • Maximum 3 alerts per hour")
        print("   • Maximum 10 alerts per day")
    else:
        print("📊 Normal mode active:")
        print("   • All tier thresholds enabled")
        print("   • All pattern types enabled")
        print("   • Standard alert limits")

def show_status(config_path: str) -> None:
    """Show current alpha alert system status."""
    config = load_config(config_path)
    
    alerts_enabled = config['alpha_scanning_optimized'].get('alpha_alerts_enabled', True)
    extreme_mode = config['alpha_scanning_optimized'].get('extreme_mode', {}).get('enabled', False)
    
    print("📊 Alpha Alert System Status")
    print("=" * 40)
    print(f"Alpha Alerts: {'🟢 ENABLED' if alerts_enabled else '🔴 DISABLED'}")
    print(f"Extreme Mode: {'🎯 ENABLED' if extreme_mode else '📈 DISABLED'}")
    
    if alerts_enabled:
        if extreme_mode:
            print("\n⚡ EXTREME MODE SETTINGS:")
            print("   • Tier 1: 100%+ alpha, 98% confidence, 30s scan")
            print("   • Tier 2: 50%+ alpha, 95% confidence, 2m scan")
            print("   • Tier 3 & 4: DISABLED")
            print("   • Patterns ENABLED: Beta Expansion, Beta Compression")
            print("   • Patterns DISABLED: Cross Timeframe, Alpha Breakout, Correlation Breakdown")
            print("   • Max alerts: 3/hour, 10/day")
        else:
            print("\n📈 NORMAL MODE SETTINGS:")
            print("   • Tier 1: 50%+ alpha, 95% confidence, 1m scan")
            print("   • Tier 2: 15%+ alpha, 90% confidence, 3m scan")
            print("   • Tier 3: 8%+ alpha, 85% confidence, 10m scan")
            print("   • Tier 4: 5%+ alpha, 80% confidence, 30m scan")
            print("   • All patterns enabled")
    else:
        print("\n🔴 All alpha alerts are currently DISABLED")

def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description="Toggle Alpha Alert System Settings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python toggle_alpha_alerts.py --status                    # Show current status
  python toggle_alpha_alerts.py --enable                    # Enable alpha alerts
  python toggle_alpha_alerts.py --disable                   # Disable alpha alerts
  python toggle_alpha_alerts.py --extreme-on                # Enable extreme mode
  python toggle_alpha_alerts.py --extreme-off               # Disable extreme mode
  python toggle_alpha_alerts.py --disable --extreme-on      # Disable alerts but set extreme mode
        """
    )
    
    parser.add_argument('--config', 
                       default='config/alpha_optimization.yaml',
                       help='Path to alpha optimization config file')
    
    parser.add_argument('--enable', action='store_true',
                       help='Enable alpha alerts')
    
    parser.add_argument('--disable', action='store_true',
                       help='Disable alpha alerts')
    
    parser.add_argument('--extreme-on', action='store_true',
                       help='Enable extreme mode (only highest value alerts)')
    
    parser.add_argument('--extreme-off', action='store_true',
                       help='Disable extreme mode (normal thresholds)')
    
    parser.add_argument('--status', action='store_true',
                       help='Show current status')
    
    args = parser.parse_args()
    
    # Validate config file exists
    if not os.path.exists(args.config):
        print(f"❌ Config file not found: {args.config}")
        sys.exit(1)
    
    # If no arguments, show status
    if not any([args.enable, args.disable, args.extreme_on, args.extreme_off, args.status]):
        show_status(args.config)
        return
    
    # Process commands
    if args.enable and args.disable:
        print("❌ Cannot enable and disable at the same time")
        sys.exit(1)
    
    if args.extreme_on and args.extreme_off:
        print("❌ Cannot enable and disable extreme mode at the same time")
        sys.exit(1)
    
    # Apply changes
    if args.enable:
        toggle_alerts(args.config, True)
    elif args.disable:
        toggle_alerts(args.config, False)
    
    if args.extreme_on:
        toggle_extreme_mode(args.config, True)
    elif args.extreme_off:
        toggle_extreme_mode(args.config, False)
    
    if args.status:
        print()  # Add spacing
        show_status(args.config)

if __name__ == "__main__":
    main() 
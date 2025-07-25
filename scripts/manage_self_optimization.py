#!/usr/bin/env python3
"""
Self-Optimization Management Utility for Virtuoso Trading System

This script provides an easy way to enable/disable and configure 
the self-optimization features without manually editing config files.
"""

import sys
import yaml
import argparse
from pathlib import Path
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """Load the main configuration file."""
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def save_config(config: Dict[str, Any]) -> None:
    """Save the configuration file."""
    config_path = Path("config/config.yaml")
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"✅ Configuration saved to {config_path}")

def show_status(config: Dict[str, Any]) -> None:
    """Display current self-optimization status."""
    self_opt = config.get('self_optimization', {})
    
    print("🎯 Virtuoso Self-Optimization Status")
    print("=" * 45)
    
    # Master status
    enabled = self_opt.get('enabled', False)
    status_icon = "🟢" if enabled else "🔴"
    print(f"{status_icon} Self-Optimization: {'ENABLED' if enabled else 'DISABLED'}")
    
    if not enabled:
        print("\n💡 Optuna integration is disabled by default for safety.")
        print("   To enable self-optimization, run:")
        print("   python scripts/manage_self_optimization.py --enable basic")
        print("   python scripts/manage_self_optimization.py --enable advanced")
        print("   python scripts/manage_self_optimization.py --enable expert")
        return
    
    # Detailed status
    optimization = self_opt.get('optimization', {})
    adaptive = self_opt.get('adaptive_parameters', {})
    auto_deploy = self_opt.get('auto_deployment', {})
    safety = self_opt.get('safety', {})
    
    print(f"\n📊 Optimization Settings:")
    print(f"   Database: {optimization.get('database_url', 'Not configured')}")
    print(f"   Scheduled: {'Yes' if optimization.get('schedule', {}).get('enabled', False) else 'No'}")
    print(f"   Max Trials: {optimization.get('performance', {}).get('max_trials_per_study', 100)}")
    
    print(f"\n🔄 Active Targets:")
    targets = optimization.get('targets', {})
    for target, enabled in targets.items():
        icon = "✅" if enabled else "❌"
        print(f"   {icon} {target.replace('_', ' ').title()}")
    
    print(f"\n🤖 Adaptive Parameters: {'ENABLED' if adaptive.get('enabled', False) else 'DISABLED'}")
    print(f"🚀 Auto-Deployment: {'ENABLED' if auto_deploy.get('enabled', False) else 'DISABLED'}")
    print(f"🛡️  Safety Mode: {'ENABLED' if safety.get('conservative_mode', True) else 'DISABLED'}")
    
    # Dashboard info
    dashboard = self_opt.get('dashboard', {})
    if dashboard.get('enabled', True):
        host = dashboard.get('host', '127.0.0.1')
        port = dashboard.get('port', 8080)
        print(f"\n📊 Dashboard: http://{host}:{port}")
        print("   To launch: optuna-dashboard sqlite:///data/optuna_studies.db --port 8080")

def enable_self_optimization(config: Dict[str, Any], level: str = 'basic') -> None:
    """Enable self-optimization with specified safety level."""
    if 'self_optimization' not in config:
        print("❌ Self-optimization configuration not found in config file")
        return
    
    config['self_optimization']['enabled'] = True
    
    if level == 'basic':
        # Basic safe configuration
        config['self_optimization']['optimization']['targets'].update({
            'technical_indicators': True,
            'volume_indicators': True,
            'orderbook_indicators': False,  # Conservative start
            'orderflow_indicators': False,
            'sentiment_indicators': False,
            'price_structure_indicators': False,
            'confluence_weights': False,
            'risk_management': False,
            'signal_generation': False
        })
        
        config['self_optimization']['adaptive_parameters']['enabled'] = False
        config['self_optimization']['auto_deployment']['enabled'] = False
        config['self_optimization']['safety']['require_human_approval'] = True
        config['self_optimization']['safety']['conservative_mode'] = True
        
        print("🟢 Self-optimization ENABLED with BASIC safety settings")
        print("   • Only technical and volume indicators will be optimized")
        print("   • Human approval required for all parameter changes")
        print("   • No automatic deployment")
        
    elif level == 'advanced':
        # More aggressive configuration for experienced users
        config['self_optimization']['optimization']['targets'].update({
            'technical_indicators': True,
            'volume_indicators': True,
            'orderbook_indicators': True,
            'orderflow_indicators': True,
            'sentiment_indicators': True,
            'price_structure_indicators': True,
            'confluence_weights': False,  # Still conservative with weights
            'risk_management': False,
            'signal_generation': False
        })
        
        config['self_optimization']['adaptive_parameters']['enabled'] = True
        config['self_optimization']['auto_deployment']['enabled'] = False  # Still require manual approval
        config['self_optimization']['safety']['require_human_approval'] = True
        config['self_optimization']['safety']['conservative_mode'] = True
        
        print("🟢 Self-optimization ENABLED with ADVANCED settings")
        print("   • All indicator classes will be optimized")
        print("   • Adaptive parameters enabled")
        print("   • Human approval still required")
        
    elif level == 'expert':
        # Full automation for expert users (use with caution)
        config['self_optimization']['optimization']['targets'] = {k: True for k in config['self_optimization']['optimization']['targets']}
        config['self_optimization']['adaptive_parameters']['enabled'] = True
        config['self_optimization']['auto_deployment']['enabled'] = True
        config['self_optimization']['safety']['require_human_approval'] = False
        config['self_optimization']['safety']['conservative_mode'] = False
        
        print("🟢 Self-optimization ENABLED with EXPERT settings")
        print("   ⚠️  WARNING: Full automation enabled - use with extreme caution!")
        print("   • All parameters will be optimized")
        print("   • Automatic deployment enabled")
        print("   • Reduced safety controls")

def disable_self_optimization(config: Dict[str, Any]) -> None:
    """Disable self-optimization system."""
    if 'self_optimization' in config:
        config['self_optimization']['enabled'] = False
        print("🔴 Self-optimization DISABLED")
    else:
        print("❌ Self-optimization configuration not found")

def configure_targets(config: Dict[str, Any], targets: list, enable: bool) -> None:
    """Enable or disable specific optimization targets."""
    if 'self_optimization' not in config:
        print("❌ Self-optimization configuration not found")
        return
    
    optimization_targets = config['self_optimization']['optimization']['targets']
    
    for target in targets:
        if target in optimization_targets:
            optimization_targets[target] = enable
            action = "ENABLED" if enable else "DISABLED"
            print(f"✅ {target.replace('_', ' ').title()}: {action}")
        else:
            print(f"❌ Unknown target: {target}")
            available_targets = list(optimization_targets.keys())
            print(f"   Available targets: {', '.join(available_targets)}")

def launch_dashboard() -> None:
    """Launch the Optuna dashboard."""
    import subprocess
    import webbrowser
    import time
    
    print("🚀 Launching Optuna Dashboard...")
    
    try:
        # Launch dashboard in background
        process = subprocess.Popen([
            'optuna-dashboard', 
            'sqlite:///data/optuna_studies.db', 
            '--port', '8080',
            '--host', '127.0.0.1'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for server to start
        time.sleep(2)
        
        # Open browser
        webbrowser.open('http://127.0.0.1:8080')
        
        print("📊 Dashboard launched at http://127.0.0.1:8080")
        print("   Press Ctrl+C to stop the dashboard")
        
        # Wait for user to stop
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping dashboard...")
            process.terminate()
            
    except FileNotFoundError:
        print("❌ optuna-dashboard not found. Install with:")
        print("   pip install optuna-dashboard")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Manage Virtuoso Self-Optimization System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/manage_self_optimization.py --status
  python scripts/manage_self_optimization.py --enable basic
  python scripts/manage_self_optimization.py --enable advanced
  python scripts/manage_self_optimization.py --disable
  python scripts/manage_self_optimization.py --enable-targets technical_indicators volume_indicators
  python scripts/manage_self_optimization.py --disable-targets risk_management
  python scripts/manage_self_optimization.py --dashboard
        """
    )
    
    parser.add_argument('--status', action='store_true', 
                       help='Show current self-optimization status')
    parser.add_argument('--enable', choices=['basic', 'advanced', 'expert'],
                       help='Enable self-optimization with safety level')
    parser.add_argument('--disable', action='store_true',
                       help='Disable self-optimization system')
    parser.add_argument('--enable-targets', nargs='+',
                       help='Enable specific optimization targets')
    parser.add_argument('--disable-targets', nargs='+', 
                       help='Disable specific optimization targets')
    parser.add_argument('--dashboard', action='store_true',
                       help='Launch Optuna dashboard')
    
    args = parser.parse_args()
    
    # Default to showing status if no arguments
    if not any(vars(args).values()):
        args.status = True
    
    # Load configuration
    config = load_config()
    
    # Execute requested action
    if args.status:
        show_status(config)
        
    elif args.enable:
        enable_self_optimization(config, args.enable)
        save_config(config)
        
    elif args.disable:
        disable_self_optimization(config)
        save_config(config)
        
    elif args.enable_targets:
        configure_targets(config, args.enable_targets, True)
        save_config(config)
        
    elif args.disable_targets:
        configure_targets(config, args.disable_targets, False)  
        save_config(config)
        
    elif args.dashboard:
        launch_dashboard()

if __name__ == "__main__":
    main()
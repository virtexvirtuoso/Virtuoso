#!/usr/bin/env python3
"""
Alpha Integration Setup Script
Comprehensive setup to ensure seamless alpha generation integration with existing systems.
"""

import asyncio
import logging
import yaml
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.monitoring.alpha_integration import setup_alpha_integration


async def validate_dependencies():
    """Validate that all required dependencies are available."""
    print("🔍 Validating dependencies...")
    
    required_modules = [
        'src.reports.bitcoin_beta_alpha_detector',
        'src.monitoring.monitor',
        'src.monitoring.alert_manager'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {str(e)}")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n❌ Missing required modules: {', '.join(missing_modules)}")
        return False
    
    print("✅ All dependencies validated")
    return True


def load_configuration() -> Dict[str, Any]:
    """Load and validate configuration for alpha integration."""
    print("📄 Loading configuration...")
    
    # Load alpha integration config
    alpha_config_path = project_root / "config" / "alpha_integration.yaml"
    if not alpha_config_path.exists():
        print(f"❌ Alpha config file not found: {alpha_config_path}")
        return {}
    
    with open(alpha_config_path, 'r') as f:
        alpha_config = yaml.safe_load(f)
    
    # Load main system config (you may need to adjust this path)
    main_config_path = project_root / "config" / "config.yaml"
    if main_config_path.exists():
        with open(main_config_path, 'r') as f:
            main_config = yaml.safe_load(f)
    else:
        # Create default config structure
        main_config = {
            'monitoring': {
                'alerts': {
                    'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL'),
                    'thresholds': {
                        'buy': 60.0,
                        'sell': 40.0
                    }
                }
            },
            'exchange': {
                'name': 'bybit',
                'testnet': True
            }
        }
    
    # Merge configurations
    merged_config = {**main_config, **alpha_config}
    
    print(f"  ✅ Alpha integration config loaded")
    print(f"  📊 Monitoring {len(alpha_config.get('alpha_detection', {}).get('monitored_symbols', []))} symbols")
    print(f"  🎯 Alert threshold: {alpha_config.get('alpha_detection', {}).get('alert_threshold', 0.70):.1%}")
    
    return merged_config


def validate_configuration(config: Dict[str, Any]) -> bool:
    """Validate configuration for alpha integration."""
    print("🔧 Validating configuration...")
    
    issues = []
    
    # Check alpha detection config
    alpha_config = config.get('alpha_detection', {})
    if not alpha_config.get('enabled', True):
        print("  ⚠️  Alpha detection is disabled in config")
    
    # Check monitored symbols
    symbols = alpha_config.get('monitored_symbols', [])
    if not symbols:
        issues.append("No monitored symbols configured")
    else:
        print(f"  📈 {len(symbols)} symbols configured for monitoring")
    
    # Check alert threshold
    threshold = alpha_config.get('alert_threshold', 0.70)
    if threshold < 0.5 or threshold > 1.0:
        issues.append(f"Alert threshold {threshold} outside valid range [0.5, 1.0]")
    
    # Check Discord webhook
    webhook_url = config.get('monitoring', {}).get('alerts', {}).get('discord_webhook_url')
    if not webhook_url:
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        issues.append("Discord webhook URL not configured")
    else:
        print("  🔗 Discord webhook configured")
    
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("✅ Configuration validated")
    return True


class MockSystemComponents:
    """Mock system components for testing integration."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.MockSystem")
    
    def create_mock_monitor(self):
        """Create a mock monitor that mimics the real MarketMonitor interface."""
        
        class MockMonitor:
            def __init__(self, config):
                self.config = config
                self.logger = logging.getLogger(f"{__name__}.MockMonitor")
                self._original_process_symbol = self._process_symbol
                
                # Mock market data
                self.mock_data = {
                    'ETHUSDT': {'price': 1642.50, 'volume': 1000},
                    'SOLUSDT': {'price': 146.75, 'volume': 800},
                    'BTCUSDT': {'price': 65100.0, 'volume': 100}
                }
            
            async def _process_symbol(self, symbol: str):
                """Mock symbol processing."""
                symbol_str = symbol['symbol'] if isinstance(symbol, dict) else symbol
                self.logger.info(f"Processing {symbol_str}")
                await asyncio.sleep(0.1)  # Simulate processing time
            
            async def fetch_market_data(self, symbol: str):
                """Mock market data fetching."""
                if symbol in self.mock_data:
                    base_data = self.mock_data[symbol]
                    return {
                        'ticker': {
                            'last': base_data['price'],
                            'volume': base_data['volume']
                        },
                        'ohlcv': {
                            '1m': [base_data['price']*0.999, base_data['price']*1.001, 
                                   base_data['price']*0.998, base_data['price'], base_data['volume']],
                            '5m': [base_data['price']*0.995, base_data['price']*1.005, 
                                   base_data['price']*0.990, base_data['price'], base_data['volume']*5],
                        }
                    }
                return None
        
        return MockMonitor(self.config)
    
    def create_mock_alert_manager(self):
        """Create a mock alert manager."""
        
        class MockAlertManager:
            def __init__(self, config):
                self.config = config
                self.logger = logging.getLogger(f"{__name__}.MockAlertManager")
                self.sent_alerts = []
            
            async def send_alpha_opportunity_alert(self, **kwargs):
                """Mock alpha alert sending."""
                symbol = kwargs.get('symbol', 'UNKNOWN')
                alpha = kwargs.get('alpha_estimate', 0)
                confidence = kwargs.get('confidence_score', 0)
                
                alert_data = {
                    'timestamp': asyncio.get_event_loop().time(),
                    'symbol': symbol,
                    'alpha_estimate': alpha,
                    'confidence_score': confidence,
                    **kwargs
                }
                self.sent_alerts.append(alert_data)
                
                self.logger.info(f"📢 Alpha alert sent for {symbol}: "
                               f"{alpha:+.2%} alpha, {confidence:.1%} confidence")
            
            def get_alert_stats(self):
                """Get alert statistics."""
                return {
                    'total_alerts': len(self.sent_alerts),
                    'alerts_by_symbol': {}
                }
        
        return MockAlertManager(self.config)


async def test_integration(config: Dict[str, Any]) -> bool:
    """Test the alpha integration with mock components."""
    print("🧪 Testing alpha integration...")
    
    try:
        # Create mock components
        mock_system = MockSystemComponents(config)
        monitor = mock_system.create_mock_monitor()
        alert_manager = mock_system.create_mock_alert_manager()
        
        # Setup alpha integration
        alpha_integration = await setup_alpha_integration(
            monitor=monitor,
            alert_manager=alert_manager,
            config=config
        )
        
        print(f"  ✅ Alpha integration setup successful")
        print(f"  📊 Monitoring {len(alpha_integration.monitored_symbols)} symbols")
        print(f"  🎯 Alert threshold: {alpha_integration.alpha_alert_threshold:.1%}")
        
        # Test processing some symbols
        test_symbols = ['ETHUSDT', 'SOLUSDT', 'BTCUSDT']
        for symbol in test_symbols:
            await monitor._process_symbol(symbol)
        
        # Get statistics
        stats = alpha_integration.get_alpha_stats()
        print(f"  📈 Alpha checks performed: {len(stats['last_checks'])}")
        print(f"  🚨 Alerts sent: {stats['opportunities_sent']}")
        
        # Cleanup
        await alpha_integration.cleanup()
        print("  🧹 Integration cleaned up")
        
        print("✅ Integration test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False


async def setup_production_integration():
    """Setup alpha integration for production use."""
    print("🚀 Setting up production alpha integration...")
    
    try:
        # Import real components
        from src.monitoring.monitor import MarketMonitor
        from src.monitoring.alert_manager import AlertManager
        
        # Load configuration
        config = load_configuration()
        if not validate_configuration(config):
            return False
        
        # Note: In production, you would get these from your existing system initialization
        print("📝 Note: In production, pass your existing MarketMonitor and AlertManager instances")
        print("       Example integration code:")
        print("""
        # In your main system initialization:
        from src.monitoring.alpha_integration import setup_alpha_integration
        
        # After creating monitor and alert_manager
        alpha_integration = await setup_alpha_integration(
            monitor=your_monitor_instance,
            alert_manager=your_alert_manager_instance,
            config=alpha_config
        )
        
        # Alpha detection now runs automatically with your monitoring cycles
        """)
        
        return True
        
    except Exception as e:
        print(f"❌ Production setup failed: {str(e)}")
        return False


def print_integration_summary():
    """Print summary of integration capabilities."""
    print("\n" + "="*60)
    print("🎯 ALPHA INTEGRATION SUMMARY")
    print("="*60)
    print("✨ Features Enabled:")
    print("  📊 Cross-timeframe beta divergence detection")
    print("  🚀 Alpha breakout pattern recognition") 
    print("  📉 Correlation breakdown identification")
    print("  ⚖️  Risk-adjusted opportunity scoring")
    print("  🔔 Smart Discord alerting with throttling")
    print("  📈 Integration with existing confluence system")
    print()
    print("🔧 Configuration:")
    print("  📁 config/alpha_integration.yaml - Main configuration")
    print("  🎛️  Adjustable confidence thresholds")
    print("  ⏱️  Configurable check intervals")
    print("  📋 Customizable symbol monitoring lists")
    print()
    print("📊 Monitoring & Alerts:")
    print("  🎯 70%+ confidence threshold (default)")
    print("  ⏰ 5-minute check intervals (default)")
    print("  🚨 Discord webhook integration")
    print("  📝 Comprehensive logging and statistics")
    print()
    print("🔗 Integration Points:")
    print("  🔄 Seamless with MarketMonitor._process_symbol()")
    print("  📢 Enhanced AlertManager with alpha alerts")
    print("  🧹 Clean integration/removal capabilities")
    print("="*60)


async def main():
    """Main setup script."""
    print("🔧 ALPHA GENERATION INTEGRATION SETUP")
    print("="*50)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    success = True
    
    # Step 1: Validate dependencies
    if not await validate_dependencies():
        success = False
    
    # Step 2: Load and validate configuration
    if success:
        config = load_configuration()
        if not config or not validate_configuration(config):
            success = False
    
    # Step 3: Test integration
    if success:
        if not await test_integration(config):
            success = False
    
    # Step 4: Setup for production (informational)
    if success:
        await setup_production_integration()
    
    # Summary
    print("\n" + "="*50)
    if success:
        print("✅ ALPHA INTEGRATION SETUP COMPLETED SUCCESSFULLY")
        print_integration_summary()
        print("\n💡 Next Steps:")
        print("  1. Review config/alpha_integration.yaml settings")
        print("  2. Set DISCORD_WEBHOOK_URL environment variable")
        print("  3. Integrate with your existing monitor/alert system")
        print("  4. Monitor logs/alpha_detection.log for activity")
    else:
        print("❌ ALPHA INTEGRATION SETUP FAILED")
        print("\n🔧 Troubleshooting:")
        print("  1. Check all dependencies are installed")
        print("  2. Verify configuration files exist")
        print("  3. Ensure Discord webhook URL is set")
        print("  4. Review error messages above")
    
    return success


if __name__ == "__main__":
    # Set environment variable hint
    if not os.getenv('DISCORD_WEBHOOK_URL'):
        print("💡 Tip: Set DISCORD_WEBHOOK_URL environment variable for Discord alerts")
        print("   export DISCORD_WEBHOOK_URL='your_webhook_url_here'")
        print()
    
    # Run setup
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 
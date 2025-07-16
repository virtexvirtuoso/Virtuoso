#!/usr/bin/env python3
"""
Production Alpha Integration Example
Shows how to seamlessly integrate alpha generation with your existing Virtuoso system.
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


class VirtuosoAlphaIntegration:
    """Production-ready alpha integration for Virtuoso trading system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the alpha integration system."""
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or "config/alpha_integration.yaml"
        self.alpha_integration = None
        self.monitor = None
        self.alert_manager = None
        
    async def initialize(self, monitor, alert_manager) -> bool:
        """Initialize alpha integration with existing system components.
        
        Args:
            monitor: Your existing MarketMonitor instance
            alert_manager: Your existing AlertManager instance
            
        Returns:
            bool: True if initialization successful
        """
        try:
            self.logger.info("🔧 Initializing Alpha Generation Integration")
            
            # Store references to existing components
            self.monitor = monitor
            self.alert_manager = alert_manager
            
            # Load alpha configuration
            config = self._load_alpha_config()
            if not config:
                self.logger.error("Failed to load alpha configuration")
                return False
            
            # Validate configuration
            if not self._validate_config(config):
                self.logger.error("Alpha configuration validation failed")
                return False
            
            # Setup alpha integration
            from src.monitoring.alpha_integration import setup_alpha_integration
            
            self.alpha_integration = await setup_alpha_integration(
                monitor=self.monitor,
                alert_manager=self.alert_manager,
                config=config
            )
            
            self.logger.info("✅ Alpha integration initialized successfully")
            self._log_integration_status()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize alpha integration: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False
    
    def _load_alpha_config(self) -> Optional[Dict[str, Any]]:
        """Load alpha integration configuration."""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                self.logger.error(f"Alpha config file not found: {config_file}")
                return None
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            self.logger.info(f"📄 Loaded alpha config from {config_file}")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading alpha config: {str(e)}")
            return None
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate alpha configuration."""
        try:
            alpha_config = config.get('alpha_detection', {})
            
            # Check required fields
            required_fields = ['enabled', 'alert_threshold', 'monitored_symbols']
            for field in required_fields:
                if field not in alpha_config:
                    self.logger.error(f"Missing required config field: alpha_detection.{field}")
                    return False
            
            # Validate threshold
            threshold = alpha_config.get('alert_threshold', 0)
            if not 0.5 <= threshold <= 1.0:
                self.logger.error(f"Invalid alert threshold: {threshold} (must be 0.5-1.0)")
                return False
            
            # Validate symbols
            symbols = alpha_config.get('monitored_symbols', [])
            if not symbols:
                self.logger.warning("No symbols configured for alpha monitoring")
            
            self.logger.info("✅ Alpha configuration validated")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating alpha config: {str(e)}")
            return False
    
    def _log_integration_status(self):
        """Log current integration status."""
        if self.alpha_integration:
            stats = self.alpha_integration.get_alpha_stats()
            self.logger.info("📊 Alpha Integration Status:")
            self.logger.info(f"  - Enabled: {stats['enabled']}")
            self.logger.info(f"  - Alert Threshold: {stats['alert_threshold']:.1%}")
            self.logger.info(f"  - Check Interval: {stats['check_interval']}s")
            self.logger.info(f"  - Monitored Symbols: {len(stats['monitored_symbols'])}")
            self.logger.info(f"  - Opportunities Sent: {stats['opportunities_sent']}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get alpha integration statistics."""
        if self.alpha_integration:
            return self.alpha_integration.get_alpha_stats()
        return {}
    
    async def shutdown(self):
        """Gracefully shutdown alpha integration."""
        try:
            if self.alpha_integration:
                await self.alpha_integration.cleanup()
                self.logger.info("🧹 Alpha integration shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during alpha integration shutdown: {str(e)}")


async def integrate_with_existing_system():
    """Example of how to integrate alpha generation with your existing Virtuoso system."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🚀 Starting Production Alpha Integration Example")
        
        # Step 1: Initialize your existing system components
        # In your actual implementation, you already have these initialized
        logger.info("📊 Initializing system components...")
        
        # Example - replace with your actual initialization
        monitor, alert_manager = await initialize_virtuoso_system()
        
        if not monitor or not alert_manager:
            logger.error("❌ Failed to initialize core system components")
            return False
        
        logger.info("✅ Core system components ready")
        
        # Step 2: Initialize alpha integration
        alpha_system = VirtuosoAlphaIntegration()
        
        if not await alpha_system.initialize(monitor, alert_manager):
            logger.error("❌ Alpha integration initialization failed")
            return False
        
        # Step 3: Run monitoring with alpha integration
        logger.info("🔄 Starting monitoring with alpha integration...")
        
        # Your existing monitoring loop continues to work as normal
        # Alpha detection is now automatically integrated
        await run_monitoring_example(monitor, alpha_system)
        
        # Step 4: Show statistics
        stats = await alpha_system.get_statistics()
        logger.info("📈 Final Alpha Statistics:")
        for key, value in stats.items():
            if key != 'detector_stats':
                logger.info(f"  - {key}: {value}")
        
        # Step 5: Graceful shutdown
        await alpha_system.shutdown()
        
        logger.info("✅ Production integration example completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Production integration example failed: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


async def initialize_virtuoso_system():
    """Initialize your existing Virtuoso system components.
    
    This is a placeholder - replace with your actual system initialization.
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Load your system configuration
        config = load_system_config()
        
        # For this example, use simplified mock components
        # In production, replace this with your actual initialization
        logger.info("Using mock components for example (replace with your actual system)")
        
        # Mock monitor that mimics the interface
        class MockMonitor:
            def __init__(self, config):
                self.config = config
                self.logger = logging.getLogger("MockMonitor")
                self._original_process_symbol = self._process_symbol
                
                # Mock market data
                self.mock_data = {
                    'ETHUSDT': {'price': 3624.50, 'volume': 1500},
                    'SOLUSDT': {'price': 146.75, 'volume': 800},
                    'ADAUSDT': {'price': 0.485, 'volume': 1200},
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
                            '30m': [base_data['price']*0.985, base_data['price']*1.015, 
                                    base_data['price']*0.980, base_data['price'], base_data['volume']*30],
                            '4h': [base_data['price']*0.950, base_data['price']*1.050, 
                                   base_data['price']*0.940, base_data['price'], base_data['volume']*240],
                        }
                    }
                return None
        
        # Mock alert manager
        class MockAlertManager:
            def __init__(self, config):
                self.config = config
                self.logger = logging.getLogger("MockAlertManager")
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
        
        monitor = MockMonitor(config)
        alert_manager = MockAlertManager(config)
        
        logger.info("✅ Mock system components initialized")
        return monitor, alert_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {str(e)}")
        return None, None


def load_system_config() -> Dict[str, Any]:
    """Load your system configuration.
    
    Replace this with your actual configuration loading logic.
    """
    # Example configuration - adjust to match your system
    return {
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
            'name': 'bybit',  # or your exchange
            'testnet': True
        },
        # Add your other configuration sections
    }


async def run_monitoring_example(monitor, alpha_system):
    """Example monitoring loop with alpha integration.
    
    Your existing monitoring loop continues to work unchanged.
    Alpha detection is automatically integrated.
    """
    logger = logging.getLogger(__name__)
    
    # Example symbols - replace with your actual symbol list
    symbols = ['ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'BTCUSDT']
    
    logger.info("🔄 Running monitoring cycles with alpha integration...")
    
    # Run a few monitoring cycles as an example
    for cycle in range(3):
        logger.info(f"--- Monitoring Cycle {cycle + 1} ---")
        
        for symbol in symbols:
            try:
                # Your existing _process_symbol call
                # Alpha detection now runs automatically
                await monitor._process_symbol(symbol)
                
                # Small delay for demo purposes
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
        
        # Show progress
        stats = await alpha_system.get_statistics()
        logger.info(f"Alpha checks: {len(stats.get('last_checks', {}))}, "
                   f"Alerts sent: {stats.get('opportunities_sent', 0)}")
        
        # Wait before next cycle
        if cycle < 2:
            await asyncio.sleep(5)


def create_integration_template():
    """Create a template for easy integration into existing systems."""
    
    template = '''
# Add this to your existing Virtuoso system initialization

import asyncio
from src.monitoring.alpha_integration import setup_alpha_integration

class YourExistingVirtuosoSystem:
    def __init__(self):
        # Your existing initialization code
        self.monitor = None
        self.alert_manager = None
        self.alpha_integration = None
    
    async def initialize(self):
        """Initialize your system with alpha integration."""
        
        # Your existing initialization code
        self.monitor = MarketMonitor(...)
        self.alert_manager = AlertManager(...)
        
        # Add alpha integration (just 3 lines!)
        alpha_config = self.load_alpha_config()
        self.alpha_integration = await setup_alpha_integration(
            monitor=self.monitor,
            alert_manager=self.alert_manager,
            config=alpha_config
        )
        
        # That's it! Alpha detection now runs automatically
        # with your existing monitoring cycles
    
    def load_alpha_config(self):
        """Load alpha configuration."""
        import yaml
        with open('config/alpha_integration.yaml', 'r') as f:
            return yaml.safe_load(f)
    
    async def shutdown(self):
        """Graceful shutdown."""
        if self.alpha_integration:
            await self.alpha_integration.cleanup()
        
        # Your existing shutdown code
'''
    
    print("📝 Integration Template:")
    print("="*60)
    print(template)
    print("="*60)


async def main():
    """Main function for production integration example."""
    
    print("🔧 PRODUCTION ALPHA INTEGRATION EXAMPLE")
    print("="*50)
    
    # Show integration template
    create_integration_template()
    
    # Run integration example
    success = await integrate_with_existing_system()
    
    print("\n" + "="*50)
    if success:
        print("✅ PRODUCTION INTEGRATION EXAMPLE COMPLETED")
        print("\n💡 Integration Summary:")
        print("  🔧 Add 3 lines to your existing system initialization")
        print("  🔄 Your monitoring cycles continue unchanged")
        print("  🚨 Alpha alerts automatically sent to Discord")
        print("  📊 Statistics available via get_alpha_stats()")
        print("  🧹 Clean shutdown with cleanup()")
        
        print("\n📋 Next Steps:")
        print("  1. Copy alpha integration code to your system")
        print("  2. Configure config/alpha_integration.yaml")
        print("  3. Set Discord webhook URL")
        print("  4. Deploy and monitor alerts")
    else:
        print("❌ PRODUCTION INTEGRATION EXAMPLE FAILED")
        print("\n🔧 Check the error messages above for details")
    
    return success


if __name__ == "__main__":
    # Check environment
    if not os.getenv('DISCORD_WEBHOOK_URL'):
        print("💡 Tip: Set DISCORD_WEBHOOK_URL environment variable")
        print("   export DISCORD_WEBHOOK_URL='your_webhook_url'")
        print()
    
    # Run example
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 
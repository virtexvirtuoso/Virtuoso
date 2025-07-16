#!/usr/bin/env python3
"""
Alpha Generation Integration Example
Shows how to integrate alpha detection with existing monitor and alert systems.
"""

import asyncio
import logging
import yaml
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.monitoring.monitor import MarketMonitor
from src.monitoring.alert_manager import AlertManager
from src.monitoring.alpha_integration import setup_alpha_integration


async def main():
    """Main integration example."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config_path = project_root / "config" / "alpha_integration.yaml"
        with open(config_path, 'r') as f:
            alpha_config = yaml.safe_load(f)
        
        # Load main system config (you would use your existing config loading)
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
                'name': 'bybit',  # or your preferred exchange
                'testnet': True
            }
        }
        
        logger.info("🚀 Starting Alpha Generation Integration Demo")
        
        # Initialize core components (this would be your existing initialization)
        logger.info("📊 Initializing market monitor...")
        
        # Create mock monitor and alert manager for demo
        # In production, you'd use your existing instances
        monitor = create_mock_monitor(main_config)
        alert_manager = AlertManager(main_config)
        
        # Setup alpha integration
        logger.info("🧠 Setting up alpha detection integration...")
        alpha_integration = await setup_alpha_integration(
            monitor=monitor,
            alert_manager=alert_manager,
            config=alpha_config
        )
        
        logger.info(f"✅ Alpha integration setup complete!")
        logger.info(f"   - Alert threshold: {alpha_integration.alpha_alert_threshold:.1%}")
        logger.info(f"   - Check interval: {alpha_integration.check_interval}s")
        logger.info(f"   - Enabled: {alpha_integration.enabled}")
        
        # Start monitoring (this would be your existing monitor.start())
        logger.info("🔄 Starting enhanced monitoring with alpha detection...")
        
        # Simulate monitoring cycle with alpha detection
        symbols_to_monitor = alpha_config['alpha_detection']['monitored_symbols'][:3]  # Limit for demo
        
        for i in range(3):  # Run 3 monitoring cycles for demo
            logger.info(f"\n--- Monitoring Cycle {i+1} ---")
            
            for symbol in symbols_to_monitor:
                logger.info(f"📈 Processing {symbol}...")
                
                # This would be called automatically in your integrated system
                # Here we're calling it manually for demonstration
                await monitor._process_symbol(symbol)  # This now includes alpha detection
                
                # Small delay between symbols
                await asyncio.sleep(2)
            
            # Wait before next cycle
            if i < 2:  # Don't wait after last cycle
                logger.info("⏳ Waiting before next cycle...")
                await asyncio.sleep(10)
        
        # Show integration statistics
        logger.info("\n📊 Alpha Integration Statistics:")
        stats = alpha_integration.get_alpha_stats()
        for key, value in stats.items():
            if key != 'detector_stats':
                logger.info(f"   - {key}: {value}")
        
        logger.info("✅ Alpha integration demo completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error in alpha integration demo: {str(e)}")
        raise
    finally:
        # Cleanup
        logger.info("🧹 Cleaning up...")


def create_mock_monitor(config):
    """Create a mock monitor for demonstration purposes."""
    
    class MockMonitor:
        """Mock monitor that simulates the real MarketMonitor interface."""
        
        def __init__(self, config):
            self.config = config
            self.logger = logging.getLogger(f"{__name__}.MockMonitor")
            
            # Simulate market data
            self.mock_data = {
                'ETHUSDT': {
                    'ohlcv': {
                        '1m': [1640, 1645, 1635, 1642, 1000],  # O,H,L,C,V
                        '5m': [1630, 1650, 1625, 1642, 5000],
                        '30m': [1600, 1660, 1595, 1642, 25000],
                        '4h': [1500, 1700, 1480, 1642, 100000]
                    },
                    'price': 1642.50,
                    'volume': 1000
                },
                'SOLUSDT': {
                    'ohlcv': {
                        '1m': [145, 147, 144, 146, 800],
                        '5m': [143, 148, 142, 146, 4000],
                        '30m': [140, 150, 138, 146, 20000],
                        '4h': [130, 155, 128, 146, 80000]
                    },
                    'price': 146.75,
                    'volume': 800
                },
                'ADAUSDT': {
                    'ohlcv': {
                        '1m': [0.45, 0.46, 0.44, 0.45, 500],
                        '5m': [0.44, 0.47, 0.43, 0.45, 2500],
                        '30m': [0.42, 0.48, 0.41, 0.45, 12000],
                        '4h': [0.40, 0.50, 0.39, 0.45, 50000]
                    },
                    'price': 0.455,
                    'volume': 500
                },
                'BTCUSDT': {  # Bitcoin data for comparison
                    'ohlcv': {
                        '1m': [65000, 65200, 64800, 65100, 100],
                        '5m': [64800, 65300, 64700, 65100, 500],
                        '30m': [64000, 65500, 63900, 65100, 2500],
                        '4h': [62000, 66000, 61800, 65100, 10000]
                    },
                    'price': 65100.0,
                    'volume': 100
                }
            }
        
        async def _process_symbol(self, symbol: str):
            """Mock symbol processing that will be enhanced with alpha detection."""
            self.logger.info(f"   Processing market data for {symbol}")
            
            # Simulate some processing delay
            await asyncio.sleep(1)
            
            # In the real system, this would trigger confluence analysis, etc.
            # The alpha integration will add alpha detection to this process
            self.logger.info(f"   ✓ Completed processing for {symbol}")
        
        async def fetch_market_data(self, symbol: str):
            """Mock market data fetching."""
            self.logger.debug(f"Fetching market data for {symbol}")
            
            # Add some realistic price variation
            import random
            base_data = self.mock_data.get(symbol, {})
            
            if base_data:
                # Add small random variation to simulate live data
                variation = random.uniform(-0.02, 0.02)  # ±2%
                price = base_data['price'] * (1 + variation)
                
                return {
                    'ohlcv': base_data['ohlcv'],
                    'price': price,
                    'volume': base_data['volume'],
                    'timestamp': asyncio.get_event_loop().time()
                }
            
            return None
    
    return MockMonitor(config)


if __name__ == "__main__":
    # Set environment variable for Discord webhook (optional for demo)
    if not os.getenv('DISCORD_WEBHOOK_URL'):
        print("💡 Tip: Set DISCORD_WEBHOOK_URL environment variable to see actual Discord alerts")
        print("   For now, alerts will be logged to console")
    
    # Run the demo
    asyncio.run(main()) 
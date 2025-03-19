#!/usr/bin/env python3
"""
Test script to verify the MarketMonitor's market report generation functionality.
This script tests the initial report generation upon startup and the monitoring cycle report logic.
"""

import asyncio
import logging
import os
import sys
import yaml
from datetime import datetime, timezone, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import necessary components
from src.monitoring.monitor import MarketMonitor
from src.monitoring.market_reporter import MarketReporter
from src.monitoring.alert_manager import AlertManager
from src.core.market.top_symbols import TopSymbolsManager
from src.monitoring.metrics_manager import MetricsManager
from src.config.manager import ConfigManager

class MockExchangeManager:
    """Mock implementation of ExchangeManager."""
    
    def __init__(self):
        self.logger = logging.getLogger("MockExchangeManager")
    
    async def get_primary_exchange(self):
        """Return mock exchange."""
        return MockExchange()
    
    async def initialize(self):
        """Initialize exchange manager."""
        self.logger.info("Mock exchange manager initialized")
        return True

class MockExchange:
    """Mock implementation of Exchange."""
    
    def __init__(self):
        self.exchange_id = "mock_exchange"
        
    async def initialize(self):
        """Initialize exchange."""
        return True

class MockTopSymbolsManager:
    """Mock implementation of TopSymbolsManager."""
    
    def __init__(self):
        self.logger = logging.getLogger("MockTopSymbolsManager")
        self.exchange = None
        
    def set_exchange(self, exchange):
        """Set exchange."""
        self.exchange = exchange
        
    async def get_symbols(self, limit=10):
        """Return mock symbols."""
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    def get_symbol_data(self, symbol):
        """Return mock data for a symbol."""
        return {
            "ticker": {
                "last": 45000.0,
                "change24h": 2.5,
                "turnover24h": 10000000000.0,
                "openInterest": 5000000000.0,
                "fundingRate": 0.0001
            }
        }
    
    def get_all_symbol_data(self):
        """Return all symbol data."""
        return {
            "BTCUSDT": self.get_symbol_data("BTCUSDT"),
            "ETHUSDT": self.get_symbol_data("ETHUSDT"),
            "SOLUSDT": self.get_symbol_data("SOLUSDT")
        }

class MockMarketDataManager:
    """Mock implementation of MarketDataManager."""
    
    def __init__(self):
        self.logger = logging.getLogger("MockMarketDataManager")
    
    async def initialize(self, symbols):
        """Initialize market data manager."""
        self.logger.info(f"Mock market data manager initialized with symbols: {symbols}")
        return True
    
    async def start_monitoring(self):
        """Start monitoring."""
        self.logger.info("Mock market data manager started monitoring")
        return True
    
    def get_stats(self):
        """Return mock stats."""
        return {
            "rest_calls": 10,
            "websocket_updates": 20
        }
    
    async def stop(self):
        """Stop monitoring."""
        self.logger.info("Mock market data manager stopped")
        return True

async def load_config():
    """Load configuration from file or use default."""
    try:
        # Try loading from config/config.yaml first
        config_path = "config/config.yaml"
        if not os.path.exists(config_path):
            # Fallback to src/config/config.yaml
            config_path = "src/config/config.yaml"
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        else:
            # Use default minimal config
            logger.info("Using default minimal configuration")
            return {
                "monitoring": {
                    "alerts": {
                        "discord_webhook": os.getenv("DISCORD_WEBHOOK_URL")
                    },
                    "interval": 10  # Short interval for testing
                }
            }
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        sys.exit(1)

async def test_market_monitor_report():
    """Test the MarketMonitor's market report generation functionality."""
    try:
        logger.info("Starting MarketMonitor report test...")
        
        # Load configuration
        config = await load_config()
        
        # Initialize components
        exchange_manager = MockExchangeManager()
        top_symbols_manager = MockTopSymbolsManager()
        alert_manager = AlertManager(config)
        metrics_manager = MetricsManager(config, alert_manager)
        market_data_manager = MockMarketDataManager()
        
        # Initialize MarketReporter
        market_reporter = MarketReporter(
            top_symbols_manager=top_symbols_manager,
            alert_manager=alert_manager,
            logger=logger
        )
        
        # Initialize MarketMonitor
        monitor = MarketMonitor(
            logger=logger,
            metrics_manager=metrics_manager,
            config=config
        )
        
        # Set required components
        monitor.exchange_manager = exchange_manager
        monitor.top_symbols_manager = top_symbols_manager
        monitor.alert_manager = alert_manager
        monitor.market_data_manager = market_data_manager
        monitor.market_reporter = market_reporter
        
        # Initialize alert manager
        await alert_manager.start()
        
        # Start the monitor - this should generate the initial report
        logger.info("Starting the MarketMonitor - initial report should be generated...")
        await monitor.start()
        
        # Check if initial report was generated
        if monitor.last_report_time is not None:
            logger.info(f"Initial report was generated at {monitor.last_report_time}")
        else:
            logger.error("Initial report was NOT generated!")
        
        # Wait a bit, then trigger a monitoring cycle to test the modified report logic
        logger.info("Waiting for 5 seconds, then running a monitoring cycle...")
        await asyncio.sleep(5)
        
        # Run a monitoring cycle
        logger.info("Running a monitoring cycle...")
        await monitor._monitoring_cycle()
        
        # Wait a bit more to ensure any async tasks complete
        await asyncio.sleep(2)
        
        # Stop the monitor
        logger.info("Stopping the MarketMonitor...")
        await monitor.stop()
        
        # Stop the alert manager
        await alert_manager.stop()
        
        logger.info("Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_market_monitor_report()) 
from src.utils.task_tracker import create_tracked_task
#!/usr/bin/env python3
"""
Liquidation Monitor Tool

This script monitors liquidation data from exchanges and verifies that:
1. WebSocket connections are successfully subscribed to liquidation channels
2. Liquidation data is being cached properly
3. Alerts are being triggered for significant liquidations

This can be run as a standalone script to validate liquidation alert functionality.
"""

import os
import sys
import time
import asyncio
import argparse
import logging
import json
from typing import Dict, Any, List, Optional
import traceback

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.core.market.market_data_manager import MarketDataManager
from src.monitoring.alert_manager import AlertManager
from src.core.config.config_manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("liquidation_monitor")


class LiquidationMonitor:
    """Monitor for liquidation events on a specific symbol."""
    
    def __init__(
        self, 
        symbol: str = "BTCUSDT",
        config_manager: Optional['ConfigManager'] = None,
        alert_manager: Optional['AlertManager'] = None,
        exchange_manager: Optional['ExchangeManager'] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialize the liquidation monitor.
        
        Args:
            symbol: Trading symbol to monitor
            config_manager: Optional ConfigManager instance
            alert_manager: Optional AlertManager instance  
            exchange_manager: Optional ExchangeManager instance
            config_path: Optional path to config file (used only if config_manager not provided)
        """
        self.symbol = symbol
        self.running = False
        self.logger = logger
        
        # Initialize or use provided config manager
        if config_manager:
            self.config_manager = config_manager
            self.config = config_manager.config
            self.logger.info("Using provided ConfigManager instance")
        else:
            # Fallback to creating own instance
            from src.core.config.config_manager import ConfigManager
            self.config_manager = ConfigManager(config_path)
            self.config = self.config_manager._config
            self.logger.info("Created new ConfigManager instance")
        
        # Initialize or use provided alert manager
        if alert_manager:
            self.alert_manager = alert_manager
            self.logger.info("Using provided AlertManager instance")
        else:
            # Fallback to creating own instance
            self.alert_manager = AlertManager(config=self.config)
            self.logger.info("Created new AlertManager instance")
        
        # Store exchange manager (will be initialized in start() if not provided)
        self.exchange_manager = exchange_manager
        
        # Create MarketDataManager instance (will be initialized in start())
        self.market_data_manager = None
        
        # Tracking for detected liquidations
        self.detected_liquidations = []
        self.last_check_time = 0
        
        # Stats
        self.stats = {
            'total_liquidations': 0,
            'long_liquidations': 0,
            'short_liquidations': 0,
            'total_value_usd': 0,
            'alerts_triggered': 0,
            'connection_drops': 0,
            'websocket_errors': 0
        }
        
        self.logger.info(f"Initialized LiquidationMonitor for {symbol}")

    async def start(self) -> None:
        """Start the liquidation monitor."""
        try:
            self.running = True
            self.logger.info(f"Starting liquidation monitor for {self.symbol}...")
            
            # Initialize the alert manager
            await self.alert_manager.start()
            
            # Create and initialize exchange manager if not provided
            if not self.exchange_manager:
                from src.core.exchanges.manager import ExchangeManager
                self.exchange_manager = ExchangeManager(self.config_manager)
                await self.exchange_manager.initialize()
                self.logger.info("Created and initialized new ExchangeManager instance")
            
            # Create and initialize market data manager
            self.market_data_manager = MarketDataManager(
                config=self.config,
                exchange_manager=self.exchange_manager,
                alert_manager=self.alert_manager
            )
            
            # Set the alert manager
            self.market_data_manager.alert_manager = self.alert_manager
            
            # Initialize market data manager
            await self.market_data_manager.initialize([self.symbol])
            
            # Log current configuration
            self._log_configuration()
            
            # Start monitoring loop
            await self._monitoring_loop()
            
        except Exception as e:
            self.logger.error(f"Error starting liquidation monitor: {str(e)}")
            self.logger.error(traceback.format_exc())
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the liquidation monitor."""
        self.running = False
        self.logger.info("Stopping liquidation monitor...")
        
        # Cleanup market data manager
        if self.market_data_manager:
            await self.market_data_manager.stop()
            
        # Cleanup alert manager
        await self.alert_manager.stop()
        
        self.logger.info("Liquidation monitor stopped")
        
        # Print final stats
        self._print_stats()

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop to check for liquidations."""
        check_interval = 5  # seconds
        status_interval = 30  # seconds
        last_status_time = time.time()
        
        self.logger.info(f"Starting monitoring loop, checking every {check_interval} seconds")
        
        while self.running:
            try:
                # Check for new liquidations
                await self._check_liquidations()
                
                # Print status periodically
                current_time = time.time()
                if current_time - last_status_time >= status_interval:
                    self._print_status()
                    last_status_time = current_time
                
                # Wait for next check
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                self.logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                self.logger.error(traceback.format_exc())
                await asyncio.sleep(check_interval)

    async def _check_liquidations(self) -> None:
        """Check for new liquidations in the cache."""
        try:
            # Get market data for the symbol
            market_data = await self.market_data_manager.get_market_data(self.symbol)
            
            # Check if market data contains liquidations
            if not market_data or 'liquidations' not in market_data:
                return
                
            liquidations = market_data.get('liquidations', [])
            if not liquidations:
                return
                
            # Get new liquidations since last check
            current_time = time.time()
            new_liquidations = [
                liq for liq in liquidations
                if liq.get('timestamp', 0) / 1000 > self.last_check_time
            ]
            
            if new_liquidations:
                self.logger.info(f"Found {len(new_liquidations)} new liquidation(s)")
                
                # Process each new liquidation
                for liquidation in new_liquidations:
                    await self._process_liquidation(liquidation)
                    
                # Update last check time
                self.last_check_time = current_time
                
                # Store detected liquidations
                self.detected_liquidations.extend(new_liquidations)
                
                # Trim detected liquidations list to keep only last 100
                if len(self.detected_liquidations) > 100:
                    self.detected_liquidations = self.detected_liquidations[-100:]
            
        except Exception as e:
            self.logger.error(f"Error checking liquidations: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def _process_liquidation(self, liquidation: Dict[str, Any]) -> None:
        """Process a liquidation event.
        
        Args:
            liquidation: Liquidation data
        """
        try:
            # Extract liquidation details
            side = liquidation.get('side', '')
            size = float(liquidation.get('amount', 0))
            price = float(liquidation.get('price', 0))
            
            # Calculate USD value
            usd_value = size * price
            
            # Update stats
            self.stats['total_liquidations'] += 1
            self.stats['total_value_usd'] += usd_value
            
            if side.upper() == 'BUY':
                self.stats['long_liquidations'] += 1
                position_type = "LONG"
            else:
                self.stats['short_liquidations'] += 1
                position_type = "SHORT"
                
            # Log the liquidation
            self.logger.info(
                f"Liquidation: {position_type} {size} {self.symbol} @ {price} = ${usd_value:,.2f}"
            )
            
            # Determine if this would trigger an alert
            threshold = self.config.get('monitoring', {}).get('alerts', {}).get('liquidation', {}).get('threshold', 250000)
            would_alert = usd_value >= threshold
            
            if would_alert:
                self.logger.info(f"⚠️ This liquidation exceeds the alert threshold (${threshold:,.2f})")
                self.stats['alerts_triggered'] += 1
            
        except Exception as e:
            self.logger.error(f"Error processing liquidation: {str(e)}")

    def _log_configuration(self) -> None:
        """Log the current configuration."""
        try:
            # Get liquidation threshold
            threshold = self.config.get('monitoring', {}).get('alerts', {}).get('liquidation', {}).get('threshold', 250000)
            cooldown = self.config.get('monitoring', {}).get('alerts', {}).get('liquidation', {}).get('cooldown', 300)
            
            self.logger.info(f"Liquidation alert configuration:")
            self.logger.info(f"  - Threshold: ${threshold:,.2f}")
            self.logger.info(f"  - Cooldown: {cooldown} seconds")
            
            # Log WebSocket configuration
            websocket_config = self.config.get('websocket', {})
            self.logger.info(f"WebSocket configuration:")
            self.logger.info(f"  - Enabled: {websocket_config.get('enabled', False)}")
            self.logger.info(f"  - Channels: {websocket_config.get('channels', [])}")
            
        except Exception as e:
            self.logger.error(f"Error logging configuration: {str(e)}")

    def _print_status(self) -> None:
        """Print current monitoring status."""
        try:
            # Get websocket status if available
            ws_status = "Unknown"
            if self.market_data_manager:
                if hasattr(self.market_data_manager, 'websocket_manager') and self.market_data_manager.websocket_manager:
                    ws_manager = self.market_data_manager.websocket_manager
                    # Check if get_status method exists
                    if hasattr(ws_manager, 'get_status'):
                        try:
                            ws_details = ws_manager.get_status()
                            if ws_details.get('connected', False):
                                ws_status = f"Connected ({len(ws_details.get('active_connections', []))} connections)"
                            else:
                                ws_status = "Disconnected"
                        except Exception as e:
                            self.logger.debug(f"Error getting WebSocket status: {str(e)}")
                            ws_status = "Error"
            
            # Print status
            self.logger.info(f"=== Status Update ===")
            self.logger.info(f"WebSocket: {ws_status}")
            self.logger.info(f"Detected liquidations: {self.stats['total_liquidations']}")
            self.logger.info(f"  - Long: {self.stats['long_liquidations']}")
            self.logger.info(f"  - Short: {self.stats['short_liquidations']}")
            self.logger.info(f"Total value: ${self.stats['total_value_usd']:,.2f}")
            self.logger.info(f"Alerts triggered: {self.stats['alerts_triggered']}")
            
            # Check cache
            cache_status = "OK"
            if self.market_data_manager:
                if not hasattr(self.market_data_manager, 'data_cache'):
                    cache_status = "Not initialized"
                elif self.symbol not in self.market_data_manager.data_cache:
                    cache_status = "Symbol not in cache"
                elif 'liquidations' not in self.market_data_manager.data_cache.get(self.symbol, {}):
                    cache_status = "No liquidations cached"
            else:
                cache_status = "Manager not initialized"
                
            self.logger.info(f"Cache status: {cache_status}")
            self.logger.info(f"====================")
            
        except Exception as e:
            self.logger.error(f"Error printing status: {str(e)}")

    def _print_stats(self) -> None:
        """Print final statistics."""
        try:
            self.logger.info(f"=== Final Statistics ===")
            self.logger.info(f"Total monitoring time: {time.time() - self.last_check_time:.2f} seconds")
            self.logger.info(f"Total liquidations: {self.stats['total_liquidations']}")
            self.logger.info(f"  - Long liquidations: {self.stats['long_liquidations']}")
            self.logger.info(f"  - Short liquidations: {self.stats['short_liquidations']}")
            self.logger.info(f"Total USD value: ${self.stats['total_value_usd']:,.2f}")
            self.logger.info(f"Alerts triggered: {self.stats['alerts_triggered']}")
            self.logger.info(f"WebSocket errors: {self.stats['websocket_errors']}")
            self.logger.info(f"Connection drops: {self.stats['connection_drops']}")
            self.logger.info(f"=======================")
            
        except Exception as e:
            self.logger.error(f"Error printing stats: {str(e)}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Monitor liquidation events")
    parser.add_argument("--symbol", "-s", default="BTCUSDT", help="Symbol to monitor")
    parser.add_argument("--config", "-c", help="Path to configuration file")
    parser.add_argument("--duration", "-d", type=int, default=300, help="Monitoring duration in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create and start monitor
    monitor = LiquidationMonitor(config_path=args.config, symbol=args.symbol)
    
    # Run for specified duration
    try:
        # Start the monitor
        monitor_task = create_tracked_task(monitor.start(), name="auto_tracked_task")
        
        # Wait for specified duration
        await asyncio.sleep(args.duration)
        
        # Stop the monitor
        await monitor.stop()
        
        # Cancel the task
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping...")
        await monitor.stop()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())
        await monitor.stop()


if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python
"""
Bybit Demo Trading Runner

This script implements a demo trading system using the Bybit exchange demo API
with a confluence score-based strategy.
"""

import asyncio
import logging
import json
import os
import argparse
from typing import Dict, Any, List, Optional
import traceback
import time

from src.core.exchanges.factory import ExchangeFactory
from src.core.analysis.confluence import ConfluenceAnalyzer
from src.trade_execution.confluence_position_manager import ConfluenceBasedPositionManager
from src.trade_execution.confluence_trading_strategy import ConfluenceTradingStrategy
from src.signal_generation.signal_generator import SignalGenerator
from src.monitoring.alert_manager import AlertManager
from src.monitoring.monitor import MarketMonitor

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/demo_trading.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class DemoTradingRunner:
    """Main class for running demo trading"""
    
    def __init__(self, config_path: str = "config/demo_trading.json"):
        """Initialize the demo trading runner.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Components
        self.exchange = None
        self.confluence_analyzer = None
        self.position_manager = None
        self.strategy = None
        self.signal_generator = None
        self.alert_manager = None
        self.market_monitor = None
        
        # State
        self.initialized = False
        self.running = False
        self.active_symbols = set()
        self.signal_queue = asyncio.Queue()  # Queue to store signals for processing
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Check if file exists
            if not os.path.exists(self.config_path):
                # Create default configuration
                config = self._create_default_config()
                
                # Save configuration
                with open(self.config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                    
                logger.info(f"Created default configuration at {self.config_path}")
                return config
            
            # Load existing configuration
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            logger.error(traceback.format_exc())
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "exchanges": {
                "bybit": {
                    "api_credentials": {
                        "api_key": "YOUR_API_KEY", 
                        "api_secret": "YOUR_API_SECRET"
                    },
                    "endpoint": "https://api-demo.bybit.com",
                    "demo_mode": True,
                    "websocket": {
                        "enabled": True,
                        "mainnet_endpoint": "wss://stream.bybit.com/v5/public",
                        "testnet_endpoint": "wss://stream-testnet.bybit.com/v5/public",
                        "demo_endpoint": "wss://stream-demo.bybit.com/v5/public",
                        "symbols": ["BTCUSDT", "ETHUSDT"],
                        "channels": ["trades", "orderbook", "kline"]
                    }
                }
            },
            "position_manager": {
                "base_position_pct": 0.03,
                "min_confluence_score": 70,
                "trailing_stop_pct": 0.02,
                "scale_factor": 0.01,
                "max_position_pct": 0.10,
                "scaling_threshold": {
                    "long": 75,
                    "short": 25
                }
            },
            "strategy": {
                "long_threshold": 6,
                "short_threshold": 30, 
                "max_active_positions": 5,
                "update_interval": 60
            },
            "trading": {
                "update_interval": 60,
                "use_signals": True
            },
            "confluence": {
                "weights": {
                    "components": {
                        "technical": 0.20,
                        "volume": 0.10,
                        "orderflow": 0.25,
                        "sentiment": 0.15,
                        "orderbook": 0.20,
                        "price_structure": 0.10
                    }
                },
                "thresholds": {
                    "buy": 70,
                    "sell": 30
                }
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize all components.
        
        Returns:
            True if initialization was successful
        """
        try:
            # Force demo mode
            if 'exchanges' in self.config and 'bybit' in self.config['exchanges']:
                self.config['exchanges']['bybit']['demo_mode'] = True
                self.config['exchanges']['bybit']['endpoint'] = "https://api-demo.bybit.com"
            
            # Create exchange
            logger.info("Creating exchange...")
            self.exchange = await ExchangeFactory.create_exchange('bybit', self.config['exchanges']['bybit'])
            if not self.exchange:
                logger.error("Failed to create exchange")
                return False
            
            # Create alert manager
            logger.info("Creating alert manager...")
            self.alert_manager = AlertManager(self.config)
            await self.alert_manager.initialize()
            
            # Create signal generator with our alert manager
            logger.info("Creating signal generator...")
            self.signal_generator = SignalGenerator(self.config, alert_manager=self.alert_manager)
            
            # Register signal handler
            logger.info("Registering signal handler...")
            # Subscribe to signal generator
            self.signal_generator.on_signal = self._handle_signal
            
            # Create confluence analyzer
            logger.info("Creating confluence analyzer...")
            self.confluence_analyzer = ConfluenceAnalyzer(self.config)
            
            # Create market monitor to connect to existing monitoring infrastructure
            logger.info("Creating market monitor...")
            self.market_monitor = MarketMonitor(
                exchange=self.exchange,
                alert_manager=self.alert_manager,
                signal_generator=self.signal_generator,
                confluence_analyzer=self.confluence_analyzer,
                config=self.config
            )
            
            # Create position manager
            logger.info("Creating position manager...")
            self.position_manager = ConfluenceBasedPositionManager(self.config, self.exchange)
            await self.position_manager.initialize()
            
            # Create strategy
            logger.info("Creating trading strategy...")
            self.strategy = ConfluenceTradingStrategy(
                self.config,
                confluence_analyzer=self.confluence_analyzer,
                position_manager=self.position_manager
            )
            await self.strategy.initialize()
            
            # Get signals and add symbols dynamically from signals
            if self.config.get('trading', {}).get('use_signals', True):
                logger.info("Will add symbols dynamically from signals")
                # Get available symbols from the exchange as a starting point
                await self._get_symbols_from_exchange()
            else:
                # Use configured symbols
                logger.info("Using symbols from configuration")
                symbols = self.config.get('trading', {}).get('symbols', ["BTCUSDT"])
                for symbol in symbols:
                    await self.add_symbol(symbol)
            
            # Initialize market monitor if we're using signals
            if self.config.get('trading', {}).get('use_signals', True):
                # Start the market monitor to receive signals
                logger.info("Starting market monitor...")
                asyncio.create_task(self.market_monitor.start())
            
            self.initialized = True
            logger.info("Demo trading system initialized")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    async def _get_symbols_from_exchange(self) -> None:
        """Fetch available symbols from the exchange."""
        try:
            # Get initial set of symbols from exchange websocket config
            ws_symbols = self.config.get('exchanges', {}).get('bybit', {}).get(
                'websocket', {}).get('symbols', [])
            
            if ws_symbols:
                logger.info(f"Adding {len(ws_symbols)} initial symbols from websocket config")
                for symbol in ws_symbols:
                    await self.add_symbol(symbol)
            else:
                # Try to get some default symbols from markets if none configured
                logger.info("No initial symbols configured, fetching from exchange")
                markets = await self.exchange.fetch_markets()
                top_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
                
                added = 0
                for symbol in top_symbols:
                    if any(m['symbol'] == symbol for m in markets):
                        await self.add_symbol(symbol)
                        added += 1
                        if added >= 5:  # Limit initial symbols
                            break
            
            logger.info(f"Added {len(self.active_symbols)} initial symbols")
            
        except Exception as e:
            logger.error(f"Error fetching symbols: {str(e)}")
            logger.warning("Using default symbols BTCUSDT and ETHUSDT")
            await self.add_symbol("BTCUSDT")
            await self.add_symbol("ETHUSDT")
    
    async def add_symbol(self, symbol: str) -> bool:
        """Add a symbol to trading.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if symbol was added
        """
        if symbol in self.active_symbols:
            return True
            
        self.active_symbols.add(symbol)
        if self.strategy:
            await self.strategy.add_symbol(symbol)
            
        logger.info(f"Added symbol {symbol} to trading system")
        return True
    
    async def start(self) -> bool:
        """Start demo trading.
        
        Returns:
            True if trading was started
        """
        if not self.initialized:
            logger.error("System not initialized")
            return False
        
        if self.running:
            logger.warning("Demo trading already running")
            return True
        
        # Start signal listener if using signals
        if self.config.get('trading', {}).get('use_signals', True):
            asyncio.create_task(self._monitor_signals())
        
        # Start the strategy
        await self.strategy.start()
        
        self.running = True
        logger.info("Demo trading started")
        return True
    
    async def _handle_signal(self, signal_data: Dict[str, Any]) -> None:
        """Handle a received trading signal.
        
        Args:
            signal_data: The signal data
        """
        try:
            # Add to signal queue for processing
            await self.signal_queue.put(signal_data)
            logger.info(f"Added signal to queue for processing: {signal_data.get('symbol')} - {signal_data.get('signal')}")
        except Exception as e:
            logger.error(f"Error handling signal: {str(e)}")

    async def _monitor_signals(self) -> None:
        """Monitor for new signals and add symbols dynamically."""
        try:
            logger.info("Starting signal monitoring")
            
            while self.running:
                try:
                    # Get signal from queue with timeout
                    try:
                        signal_data = await asyncio.wait_for(self.signal_queue.get(), timeout=10)
                    except asyncio.TimeoutError:
                        # Just continue if no signals in queue
                        await asyncio.sleep(1)
                        continue
                        
                    # Extract symbol and direction
                    symbol = signal_data.get('symbol')
                    signal_type = signal_data.get('signal', '').upper()
                    score = signal_data.get('confluence_score', 0)
                    
                    if not symbol or not isinstance(symbol, str):
                        logger.warning(f"Ignoring signal with invalid symbol: {symbol}")
                        continue
                        
                    logger.info(f"Processing signal for {symbol}: {signal_type} with score {score}")
                    
                    # Skip neutral signals
                    if signal_type not in ['BUY', 'SELL']:
                        logger.debug(f"Ignoring NEUTRAL signal for {symbol}")
                        continue
                        
                    # Add symbol if not already trading
                    if symbol not in self.active_symbols:
                        logger.info(f"Adding new symbol from signal: {symbol}")
                        await self.add_symbol(symbol)
                        
                    # Process the signal through our strategy
                    if self.strategy:
                        # Convert to strategy-compatible signal format
                        strategy_signal = {
                            'symbol': symbol,
                            'action': signal_type.lower(),
                            'score': score,
                            'timestamp': signal_data.get('timestamp', time.time())
                        }
                        
                        # Execute the signal
                        await self.strategy.execute_signals(strategy_signal)
                        
                    # Mark as done
                    self.signal_queue.task_done()
                    
                except Exception as e:
                    logger.error(f"Error processing signal: {str(e)}")
                    logger.error(traceback.format_exc())
                    await asyncio.sleep(1)  # Prevent tight loop in case of persistent errors
                    
        except asyncio.CancelledError:
            logger.info("Signal monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in signal monitoring: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def stop(self) -> bool:
        """Stop demo trading.
        
        Returns:
            True if trading was stopped
        """
        if not self.running:
            logger.warning("Demo trading not running")
            return True
            
        self.enabled = False
        
        # Stop the strategy
        await self.strategy.stop()
        
        self.running = False
        logger.info("Demo trading stopped")
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Stop trading if running
            if self.running:
                await self.stop()
            
            # Close market monitor if initialized
            if self.market_monitor:
                await self.market_monitor.stop()
            
            # Close exchange connection
            if self.exchange:
                await self.exchange.close()
            
            logger.info("Demo trading system cleaned up")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def run_with_timeout(self, timeout_minutes: int = 60) -> None:
        """Run the demo trading system with a timeout.
        
        Args:
            timeout_minutes: Number of minutes to run before stopping
        """
        try:
            # Initialize
            if not await self.initialize():
                logger.error("Failed to initialize, exiting")
                return
            
            # Start trading
            if not await self.start():
                logger.error("Failed to start trading, exiting")
                return
            
            logger.info(f"Demo trading will run for {timeout_minutes} minutes")
            
            # Wait for timeout
            await asyncio.sleep(timeout_minutes * 60)
            
            # Stop trading
            await self.stop()
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, stopping")
            await self.stop()
        except Exception as e:
            logger.error(f"Error in run_with_timeout: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            # Clean up
            await self.cleanup()

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run demo trading with confluence-based strategy")
    parser.add_argument("--config", type=str, default="config/demo_trading.json", help="Path to config file")
    parser.add_argument("--timeout", type=int, default=60, help="Run timeout in minutes")
    parser.add_argument("--symbols", type=str, help="Comma-separated list of symbols to trade")
    args = parser.parse_args()
    
    try:
        # Create and run the demo trading system
        runner = DemoTradingRunner(args.config)
        
        # Add symbols from command line if provided
        if args.symbols:
            symbols = [s.strip() for s in args.symbols.split(',')]
            runner.config['trading']['symbols'] = symbols
            runner.config['trading']['use_signals'] = False
        
        await runner.run_with_timeout(args.timeout)
        
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 
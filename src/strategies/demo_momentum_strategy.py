#!/usr/bin/env python3
"""
Momentum Strategy Demo Script

This script demonstrates how to use the MomentumStrategy class with the Virtuoso
trading system. It shows:

1. How to configure the strategy
2. How to initialize and start the strategy
3. How to monitor performance and signals
4. How to handle graceful shutdown

Usage:
    python src/strategies/demo_momentum_strategy.py

Requirements:
    - Valid Bybit API credentials in .env file
    - Internet connection for real-time data
    - TA-Lib installed (pip install TA-Lib)

Author: Virtuoso Trading System
"""

import asyncio
import logging
import sys
import os
import signal
from datetime import datetime
from typing import Dict, Any

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.strategies.momentum_strategy import MomentumStrategy
from src.core.exchanges.bybit import BybitExchange
from src.data_acquisition.websocket_handler import WebSocketHandler
from src.signal_generation.signal_generator import SignalGenerator
from src.utils.logging_config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

class MomentumStrategyDemo:
    """Demo application for the MomentumStrategy"""
    
    def __init__(self):
        self.strategy = None
        self.is_running = False
        self.config = self._create_demo_config()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.is_running = False
    
    def _create_demo_config(self) -> Dict[str, Any]:
        """Create configuration for the momentum strategy demo"""
        return {
            'exchanges': {
                'bybit': {
                    'api_key': os.getenv('BYBIT_API_KEY'),
                    'api_secret': os.getenv('BYBIT_API_SECRET'),
                    'testnet': True,  # Use testnet for demo
                    'rest_endpoint': 'https://api-testnet.bybit.com',
                    'ws_endpoint': 'wss://stream-testnet.bybit.com/v5/public/spot'
                }
            },
            'momentum_strategy': {
                'symbols': ['BTCUSDT', 'ETHUSDT'],
                'timeframe': '5m',
                'lookback_periods': 100,  # Reduced for demo
                'risk_management': {
                    'risk_per_trade': 0.02,  # 2% risk per trade
                    'max_positions': 2,
                    'stop_loss_pct': 0.015,  # 1.5% stop loss
                    'take_profit_pct': 0.03  # 3% take profit
                },
                'indicators': {
                    'rsi_period': 14,
                    'rsi_oversold': 30,
                    'rsi_overbought': 70,
                    'macd_fast': 12,
                    'macd_slow': 26,
                    'macd_signal': 9
                }
            },
            'market_data': {
                'klines': {
                    'timeframes': ['1m', '5m', '15m', '1h'],
                    'symbols': ['BTCUSDT', 'ETHUSDT']
                }
            },
            'websocket': {
                'heartbeat_interval': 30,
                'heartbeat_timeout': 60,
                'reconnect_attempts': 5,
                'reconnect_delay': 5
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize the demo application"""
        try:
            logger.info("Initializing Momentum Strategy Demo...")
            
            # Validate API credentials
            if not self.config['exchanges']['bybit']['api_key']:
                logger.error("BYBIT_API_KEY environment variable not set")
                logger.info("Please set your Bybit API credentials in the .env file:")
                logger.info("BYBIT_API_KEY=your_api_key_here")
                logger.info("BYBIT_API_SECRET=your_api_secret_here")
                return False
            
            if not self.config['exchanges']['bybit']['api_secret']:
                logger.error("BYBIT_API_SECRET environment variable not set")
                return False
            
            # Create strategy instance
            self.strategy = MomentumStrategy(self.config)
            
            # Initialize strategy
            if not await self.strategy.initialize():
                logger.error("Failed to initialize momentum strategy")
                return False
            
            logger.info("Momentum Strategy Demo initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize demo: {str(e)}")
            return False
    
    async def run_demo(self):
        """Run the momentum strategy demo"""
        try:
            logger.info("Starting Momentum Strategy Demo...")
            logger.info("=" * 60)
            logger.info("This demo will:")
            logger.info("1. Connect to Bybit Testnet")
            logger.info("2. Subscribe to BTC/USDT and ETH/USDT real-time data")
            logger.info("3. Analyze momentum using RSI and MACD indicators")
            logger.info("4. Generate trading signals with 2% risk management")
            logger.info("5. Simulate trade execution (no real trades)")
            logger.info("6. Display performance metrics")
            logger.info("=" * 60)
            logger.info("Press Ctrl+C to stop the demo gracefully")
            logger.info("")
            
            # Start the strategy
            if not await self.strategy.start():
                logger.error("Failed to start momentum strategy")
                return
            
            self.is_running = True
            
            # Main monitoring loop
            performance_report_interval = 60  # Report every 60 seconds
            last_performance_report = 0
            
            while self.is_running:
                try:
                    current_time = datetime.now().timestamp()
                    
                    # Report performance periodically
                    if current_time - last_performance_report >= performance_report_interval:
                        await self._report_performance()
                        await self._report_latest_signals()
                        last_performance_report = current_time
                    
                    # Check for new signals
                    await self._check_recent_activity()
                    
                    # Sleep for a short interval
                    await asyncio.sleep(5)
                    
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(10)
            
            # Graceful shutdown
            await self._shutdown()
            
        except Exception as e:
            logger.error(f"Error running demo: {str(e)}")
        finally:
            if self.strategy:
                await self.strategy.stop()
    
    async def _report_performance(self):
        """Report current performance metrics"""
        try:
            if not self.strategy:
                return
            
            metrics = self.strategy.get_performance_metrics()
            
            logger.info("")
            logger.info("📊 PERFORMANCE REPORT")
            logger.info("-" * 40)
            logger.info(f"Total Trades: {metrics['total_trades']}")
            logger.info(f"Winning Trades: {metrics['winning_trades']}")
            logger.info(f"Losing Trades: {metrics['losing_trades']}")
            logger.info(f"Win Rate: {metrics.get('win_rate', 0):.1f}%")
            logger.info(f"Total PnL: {metrics['total_pnl']:.4f} USDT")
            logger.info(f"Average PnL: {metrics.get('average_pnl', 0):.4f} USDT")
            logger.info(f"Open Positions: {metrics['open_positions']}")
            
            # Show current positions if any
            if metrics.get('current_positions'):
                logger.info("")
                logger.info("💼 CURRENT POSITIONS:")
                for symbol, position in metrics['current_positions'].items():
                    side = position['side'].upper()
                    size = position['size']
                    entry = position['entry_price']
                    current = position.get('current_price', entry)
                    pnl = position.get('unrealized_pnl', 0)
                    
                    logger.info(f"  {symbol}: {side} {size:.4f} @ {entry:.4f} "
                              f"(Current: {current:.4f}, PnL: {pnl:.4f})")
            
            logger.info("")
            
        except Exception as e:
            logger.error(f"Error reporting performance: {str(e)}")
    
    async def _report_latest_signals(self):
        """Report latest trading signals"""
        try:
            if not self.strategy:
                return
            
            latest_signals = self.strategy.get_latest_signals()
            
            if latest_signals:
                logger.info("📈 LATEST SIGNALS")
                logger.info("-" * 40)
                
                for symbol, signal in latest_signals.items():
                    age_seconds = (datetime.now() - signal.timestamp).total_seconds()
                    age_str = f"{age_seconds/60:.1f}m ago" if age_seconds > 60 else f"{age_seconds:.0f}s ago"
                    
                    logger.info(f"{symbol}:")
                    logger.info(f"  Signal: {signal.signal.value}")
                    logger.info(f"  Confidence: {signal.confidence:.2f}")
                    logger.info(f"  RSI: {signal.indicators.rsi:.1f} ({signal.indicators.rsi_signal})")
                    logger.info(f"  MACD: {signal.indicators.macd:.4f} ({signal.indicators.macd_signal_line})")
                    logger.info(f"  Price: {signal.indicators.price:.4f}")
                    logger.info(f"  Age: {age_str}")
                    logger.info("")
            
        except Exception as e:
            logger.error(f"Error reporting signals: {str(e)}")
    
    async def _check_recent_activity(self):
        """Check for recent trading activity"""
        try:
            # This could be extended to show real-time updates
            # For now, we'll just maintain the connection
            pass
            
        except Exception as e:
            logger.error(f"Error checking activity: {str(e)}")
    
    async def _shutdown(self):
        """Graceful shutdown procedure"""
        try:
            logger.info("")
            logger.info("🛑 Shutting down Momentum Strategy Demo...")
            
            if self.strategy:
                # Get final performance report
                await self._report_performance()
                
                # Stop the strategy
                await self.strategy.stop()
                logger.info("Strategy stopped successfully")
            
            logger.info("Demo shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")

async def main():
    """Main entry point for the demo"""
    try:
        # Create and run demo
        demo = MomentumStrategyDemo()
        
        # Initialize
        if not await demo.initialize():
            logger.error("Failed to initialize demo")
            return 1
        
        # Run demo
        await demo.run_demo()
        
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error in demo: {str(e)}")
        return 1

if __name__ == "__main__":
    try:
        # Check for required dependencies
        try:
            import talib
        except ImportError:
            print("❌ TA-Lib is required but not installed.")
            print("Please install it with: pip install TA-Lib")
            print("Note: You may need to install TA-Lib C library first.")
            print("See: https://github.com/mrjbq7/ta-lib#installation")
            sys.exit(1)
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Run demo
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}")
        sys.exit(1)
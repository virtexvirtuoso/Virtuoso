import asyncio
import os
import logging
import json
import traceback
from dotenv import load_dotenv
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('liquidation_test')

# Add the root directory to the path
sys.path.append(os.path.abspath('.'))

# Load environment variables
load_dotenv()

from src.core.exchanges.bybit import BybitExchange
from src.monitoring.alert_manager import AlertManager

class LiquidationTester:
    def __init__(self):
        self.symbol = "BTCUSDT"
        self.price_at_liquidation = {}  # Store market price at liquidation time
        self.config = {
            'exchanges': {
                'bybit': {
                    'enabled': True,
                    'api_credentials': {
                        'api_key': os.getenv('BYBIT_API_KEY'),
                        'api_secret': os.getenv('BYBIT_API_SECRET')
                    },
                    'market_type': 'linear',
                    'rest_endpoint': 'https://api.bybit.com',
                    'websocket': {
                        'mainnet_endpoint': 'wss://stream.bybit.com/v5/public',
                        'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public',
                        'private_endpoint': 'wss://stream.bybit.com/v5/private'
                    }
                }
            },
            'alerts': {
                'discord': {
                    'webhook_url': os.getenv('DISCORD_WEBHOOK_URL')
                },
                'liquidation': {
                    'threshold': 100000,  # Lower threshold for testing
                    'cooldown': 30  # Short cooldown for testing
                }
            }
        }
        self.exchange = None
        self.alert_manager = None
        self.liquidations = []

    async def initialize(self):
        try:
            # Create alert manager
            self.alert_manager = AlertManager(self.config)
            await self.alert_manager.start()
            
            logger.info("Alert manager initialized successfully")
            
            # Create exchange client
            logger.info("Initializing Bybit exchange client...")
            self.exchange = await BybitExchange.get_instance(self.config)
            
            if not self.exchange:
                logger.error("Failed to create exchange instance")
                return False
                
            logger.info("Exchange client created successfully")

            # Initialize WebSocket (explicitly)
            logger.info("Initializing WebSocket connection...")
            if hasattr(self.exchange, '_init_websocket'):
                ws_success = await self.exchange._init_websocket()
                if not ws_success:
                    logger.error("Failed to initialize WebSocket connection")
                    return False
                logger.info("WebSocket initialized successfully")

            # Test the connection
            logger.info("Testing exchange REST connection...")
            if not await self.exchange.test_connection():
                logger.error("Failed to connect to Bybit")
                return False
            
            # Set up handler for liquidation messages
            if hasattr(self.exchange, 'ws') and self.exchange.ws:
                logger.info("Setting up liquidation message handler...")
                self.exchange.on_liquidation = self.on_liquidation
                logger.info("Liquidation handler set up successfully")
            else:
                logger.error("WebSocket not available - cannot set up liquidation handler")
                return False
            
            logger.info("Initialization complete - all connections established")
            return True
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def on_liquidation(self, liquidation_data):
        """Process liquidation message from the exchange."""
        logger.info(f"Raw liquidation data: {json.dumps(liquidation_data, indent=2)}")
        
        # Store for analysis
        self.liquidations.append(liquidation_data)
        
        # Analyze the side field and determine if it's actually a long or short liquidation
        side = liquidation_data.get('side', '').upper()
        
        # CORRECTED INTERPRETATION:
        # When side is "BUY", it means longs are being liquidated (forced to sell)
        # When side is "SELL", it means shorts are being liquidated (forced to buy)
        position_type = "LONG" if side == "BUY" else "SHORT"
        
        logger.info(f"Liquidation detected: {position_type} position at price ${liquidation_data.get('price', 0)}")
        logger.info(f"Side from exchange: {side}")
        logger.info(f"Our interpretation: {position_type} liquidation")
        
        # Record current market price for later analysis
        symbol = liquidation_data.get('symbol', self.symbol)
        asyncio.create_task(self.record_price_at_liquidation(symbol, liquidation_data))
        
        # Send to alert manager to test the actual signal generation
        asyncio.create_task(
            self.alert_manager.check_liquidation_threshold(symbol, liquidation_data)
        )

    async def record_price_at_liquidation(self, symbol, liquidation_data):
        """Record the market price at the time of liquidation for analysis."""
        try:
            # Get current market price
            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = ticker.get('last', 0)
            
            # Store for analysis
            liq_id = f"{symbol}_{liquidation_data.get('timestamp', int(time.time() * 1000))}"
            self.price_at_liquidation[liq_id] = {
                'liquidation_price': liquidation_data.get('price', 0),
                'market_price': current_price,
                'side': liquidation_data.get('side', ''),
                'position_type': "LONG" if liquidation_data.get('side', '').upper() == "BUY" else "SHORT",
                'timestamp': liquidation_data.get('timestamp', int(time.time() * 1000))
            }
            
            logger.info(f"Recorded market price at liquidation: ${current_price}")
            logger.info(f"Liquidation price: ${liquidation_data.get('price', 0)}")
            logger.info(f"Price difference: ${abs(current_price - liquidation_data.get('price', 0))}")
        except Exception as e:
            logger.error(f"Error recording price at liquidation: {str(e)}")

    async def start_monitoring(self):
        """Start monitoring liquidations."""
        try:
            # Ensure WebSocket is connected before subscribing
            if not hasattr(self.exchange, 'ws') or not self.exchange.ws or not getattr(self.exchange.ws, 'connected', False):
                logger.info("WebSocket not connected, attempting to initialize...")
                if hasattr(self.exchange, '_init_websocket'):
                    await self.exchange._init_websocket()
                else:
                    logger.error("WebSocket initialization method not available")
                    return
            
            # Subscribe to liquidation channel
            logger.info(f"Subscribing to liquidation events for {self.symbol}...")
            try:
                await self.exchange._subscribe_to_liquidations(self.symbol)
                logger.info(f"Successfully subscribed to liquidation feed for {self.symbol}")
            except Exception as e:
                logger.error(f"Error subscribing to liquidations: {str(e)}")
                logger.error(traceback.format_exc())
                return
            
            # Start processing messages
            logger.info(f"Started monitoring {self.symbol} for liquidations")
            logger.info("Waiting for liquidation events...")
            
            # Keep the process running
            while True:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("Monitoring canceled")
        except Exception as e:
            logger.error(f"Error in monitoring: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.exchange:
                logger.info("Closing exchange connection...")
                if hasattr(self.exchange, 'ws') and self.exchange.ws:
                    logger.info("Closing WebSocket connection...")
                    await self.exchange.ws.close()
                await self.exchange.close()
            if self.alert_manager:
                logger.info("Stopping alert manager...")
                await self.alert_manager.stop()
            logger.info("Cleanup complete - resources released")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    async def compare_with_price_action(self):
        """Compare liquidations with price action to verify interpretation."""
        if not self.liquidations:
            logger.info("No liquidations collected to analyze")
            return
            
        logger.info("\n=== Liquidation Analysis ===")
        logger.info(f"Total liquidations collected: {len(self.liquidations)}")
        
        # Group by corrected interpretation of position type
        long_liqs = [l for l in self.liquidations if l.get('side', '').upper() == 'BUY']
        short_liqs = [l for l in self.liquidations if l.get('side', '').upper() == 'SELL']
        
        logger.info(f"LONG liquidations (side=BUY): {len(long_liqs)}")
        logger.info(f"SHORT liquidations (side=SELL): {len(short_liqs)}")
        
        # Get current price
        ticker = await self.exchange.fetch_ticker(self.symbol)
        current_price = ticker.get('last', 0)
        
        logger.info(f"Current price: ${current_price}")
        
        # Check if liquidations match expected behavior
        for liq in self.liquidations[-5:]:  # Look at last 5 liquidations
            side = liq.get('side', '').upper()
            price = liq.get('price', 0)
            size = liq.get('size', 0)
            position_type = "LONG" if side == "BUY" else "SHORT"
            
            logger.info(f"Liquidation: {position_type} of {size} at ${price}")
            logger.info(f"  Exchange side: {side}")
            logger.info(f"  Our interpretation: {position_type} liquidation")
            
            # Check if interpretation matches typical price action
            # Typically:
            # - Long liquidations happen when price falls (forced selling)
            # - Short liquidations happen when price rises (forced buying)
            liq_id = f"{liq.get('symbol', self.symbol)}_{liq.get('timestamp', 0)}"
            if liq_id in self.price_at_liquidation:
                price_data = self.price_at_liquidation[liq_id]
                market_price = price_data.get('market_price', 0)
                logger.info(f"  Market price at liquidation: ${market_price}")
                
                if position_type == "LONG":
                    expected_movement = "downward"
                    consistent = market_price <= price
                else:
                    expected_movement = "upward"
                    consistent = market_price >= price
                
                logger.info(f"  Expected price movement: {expected_movement}")
                logger.info(f"  Consistent with expected behavior: {consistent}")
            else:
                logger.info("  No price data recorded for this liquidation")

async def main():
    logger.info("Initializing liquidation monitor test...")
    tester = LiquidationTester()
    
    if await tester.initialize():
        try:
            logger.info("Starting liquidation monitoring task...")
            # Create a task for monitoring
            monitor_task = asyncio.create_task(tester.start_monitoring())
            
            # Run for a shorter time (1 minute) for testing
            logger.info("Monitoring will run for 1 minute before analysis")
            await asyncio.sleep(60)
            await tester.compare_with_price_action()
            
            # Cancel monitoring
            monitor_task.cancel()
            await monitor_task
            
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        except Exception as e:
            logger.error(f"Error during test: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            await tester.cleanup()
    else:
        logger.error("Failed to initialize the liquidation tester")

if __name__ == "__main__":
    asyncio.run(main()) 
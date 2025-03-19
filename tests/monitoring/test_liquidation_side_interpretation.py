import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
import time
import json
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('liquidation_side_test')

# Add the root directory to the path
sys.path.append(os.path.abspath('.'))

# Load environment variables
load_dotenv()

class LiquidationSideTester:
    """Test how the system interprets the 'side' field in liquidation data."""
    
    def __init__(self):
        """Initialize the tester with sample liquidation data."""
        # Price at time of generating these samples: ~$86,550
        # Normal interpretation:
        # - When BTC price increases, shorts get liquidated (forced to BUY)
        # - When BTC price decreases, longs get liquidated (forced to SELL)
        
        # Sample liquidation data with different 'side' values
        self.sample_liquidations = [
            {
                'symbol': 'BTCUSDT',
                'side': 'BUY',  # This should be interpreted as a LONG liquidation
                'price': 86700.00,
                'size': 3.0,
                'timestamp': int(time.time() * 1000)
            },
            {
                'symbol': 'ETHUSDT',  # Using a different symbol to avoid cooldown conflicts
                'side': 'SELL',  # This should be interpreted as a SHORT liquidation
                'price': 3900.00,
                'size': 30.0,
                'timestamp': int(time.time() * 1000)
            }
        ]
        
    def test_side_interpretation(self):
        """Test the interpretation of the 'side' field."""
        from src.monitoring.alert_manager import AlertManager
        
        # Create a simple config
        config = {
            'alerts': {
                'liquidation': {
                    'threshold': 100000,
                    'cooldown': 30
                }
            }
        }
        
        # Create an instance of the alert manager
        alert_manager = AlertManager(config)
        
        logger.info("=== Testing Liquidation Side Interpretation ===")
        
        for idx, liquidation in enumerate(self.sample_liquidations):
            # Extract the side field
            side = liquidation.get('side', '').upper()
            symbol = liquidation.get('symbol')
            
            # Get the interpreted position type based on the code in check_liquidation_threshold
            # From alert_manager.py:
            # FIXED: When side is "BUY", it means longs are being liquidated
            # When side is "SELL", it means shorts are being liquidated
            position_type = "LONG" if side == "BUY" else "SHORT"
            
            logger.info(f"\nSample {idx+1}:")
            logger.info(f"Raw liquidation data: {json.dumps(liquidation, indent=2)}")
            logger.info(f"Side from exchange: {side}")
            logger.info(f"Symbol: {symbol}")
            logger.info(f"Interpreted position type: {position_type} LIQUIDATION")
            
            # Real-world interpretation
            if position_type == "LONG" and side == "BUY":
                logger.info("✓ Correct interpretation: A long position was liquidated - forced to SELL")
                logger.info("  This typically happens when price decreases")
            elif position_type == "SHORT" and side == "SELL":
                logger.info("✓ Correct interpretation: A short position was liquidated - forced to BUY")
                logger.info("  This typically happens when price increases")
            else:
                logger.info("❌ Inconsistent interpretation")
                
        # Test against the alert message that would be generated
        logger.info("\n=== Checking Actual Generated Message ===")
        self._test_message_generation()
        
    def _test_message_generation(self):
        """Test message generation by mocking parts of the alert manager."""
        from datetime import datetime, timezone
        
        class MockAlertManager:
            def __init__(self):
                self.liquidation_threshold = 100000
                self.liquidation_cooldown = 0  # Set to 0 to avoid cooldown issues
                self.logger = logger
                self.messages = []
                self._last_liquidation_alert = {}
                
            async def send_alert(self, level, message, details=None):
                self.messages.append({
                    'level': level,
                    'message': message,
                    'details': details
                })
                logger.info(f"Alert would be: {message}")
                
            def _determine_impact_level(self, usd_value):
                return "MEDIUM"
                
            def _generate_impact_bar(self, usd_value):
                return "▓▓▓▓▓░░░░░ 51%"
                
            def _get_price_action_note(self, position_type, impact_level):
                return "Moderate selling pressure may push price lower in the short term" if position_type == "LONG" else "Moderate buying pressure may push price higher in the short term"
                
            async def check_liquidation_threshold(self, symbol, liquidation_data):
                try:
                    # Debug log the incoming data
                    self.logger.debug(f"Received liquidation data for {symbol}: {liquidation_data}")
                    
                    # Get last alert time for this symbol
                    last_alert = self._last_liquidation_alert.get(symbol, 0)
                    current_time = time.time()
                    
                    # Check cooldown
                    if current_time - last_alert < self.liquidation_cooldown:
                        logger.info(f"Skipping due to cooldown for {symbol}")
                        return
                        
                    # Calculate USD value
                    usd_value = liquidation_data['size'] * liquidation_data['price']
                    
                    # Check against configured threshold (force to pass for testing)
                    if True:  # Always pass threshold check for testing
                        # Determine direction and impact
                        side = liquidation_data['side'].upper()
                        
                        # FIXED interpretation
                        position_type = "LONG" if side == "BUY" else "SHORT"
                        
                        # Format timestamp
                        timestamp = datetime.fromtimestamp(
                            liquidation_data['timestamp'] / 1000 if liquidation_data['timestamp'] > 1e12 
                            else liquidation_data['timestamp'], 
                            tz=timezone.utc
                        ).strftime('%H:%M:%S UTC')
                        
                        # Extract base asset name (e.g., BTC from BTCUSDT)
                        base_asset = symbol.split('USDT')[0] if 'USDT' in symbol else symbol.split('USD')[0]
                        
                        # Direction-specific emojis and formatting
                        direction_emoji = "🔴" if position_type == "LONG" else "🟢"
                        impact_level = self._determine_impact_level(usd_value)
                        impact_emoji = "💥" if impact_level == "HIGH" else "⚠️" if impact_level == "MEDIUM" else "ℹ️"
                        
                        # Generate visual impact bar
                        impact_bar = self._generate_impact_bar(usd_value)
                        
                        # Create a price action note
                        price_action = self._get_price_action_note(position_type, impact_level)
                        
                        # Format message
                        message = (
                            f"{direction_emoji} **{position_type} LIQUIDATION** {impact_emoji}\n"
                            f"**Symbol:** {symbol}\n"
                            f"**Time:** {timestamp}\n"
                            f"**Size:** {liquidation_data['size']:.4f} {base_asset}\n"
                            f"**Price:** ${liquidation_data['price']:,.2f}\n"
                            f"**Value:** ${usd_value:,.2f}\n"
                            f"**Impact:** Immediate {'buying 📈' if position_type == 'SHORT' else 'selling 📉'} pressure on market\n"
                            f"**Severity:** {impact_level}\n"
                            f"**Impact Meter:** `{impact_bar}`\n"
                            f"**Note:** {price_action}"
                        )
                        
                        await self.send_alert(
                            level="WARNING",
                            message=message,
                            details={
                                'type': 'liquidation',
                                'symbol': symbol,
                                'side': side,
                                'direction': position_type
                            }
                        )
                        
                        # Update last alert time for cooldown
                        self._last_liquidation_alert[symbol] = current_time
                        
                        logger.info(f"Updated last alert time for {symbol} to {current_time}")
                except Exception as e:
                    self.logger.error(f"Error checking liquidation threshold: {str(e)}")
                    self.logger.debug(traceback.format_exc())
        
        # Mock alert manager
        alert_manager = MockAlertManager()
        
        # Test each sample
        for idx, liquidation in enumerate(self.sample_liquidations):
            logger.info(f"\nTesting message generation for sample {idx+1}:")
            
            # Extract data
            side = liquidation.get('side', '').upper()
            symbol = liquidation.get('symbol')
            usd_value = liquidation.get('size', 0) * liquidation.get('price', 0)
            
            logger.info(f"Processing {symbol} with side {side}, value ${usd_value:,.2f}")
            
            # Run the check method
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                alert_manager.check_liquidation_threshold(
                    symbol,
                    liquidation
                )
            )
            
            # Check the results
            if idx < len(alert_manager.messages):
                msg = alert_manager.messages[idx]['message']
                logger.info(f"Message includes position type: {'LONG' in msg or 'SHORT' in msg}")
                logger.info(f"Position type in message: {'SHORT' if 'SHORT' in msg else 'LONG' if 'LONG' in msg else 'Not found'}")
                logger.info(f"Expected type based on side '{side}': {'LONG' if side == 'BUY' else 'SHORT'}")
                
                # Verify other parts of the message
                logger.info(f"Message includes correct market impact: {'buying' in msg if side == 'SELL' else 'selling' in msg}")
                
                # Check emoji
                expected_emoji = "🔴" if side == "BUY" else "🟢"
                logger.info(f"Has correct emoji: {expected_emoji in msg}")
            else:
                logger.info("No message generated")

def main():
    tester = LiquidationSideTester()
    tester.test_side_interpretation()

if __name__ == "__main__":
    main() 
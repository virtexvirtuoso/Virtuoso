#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
import json
import time
import websockets
from typing import Dict, List, Any

from config.manager import ConfigManager
from data_acquisition.binance.binance_exchange import BinanceExchange

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class WebSocketIntegrationTester:
    """Test WebSocket integration for real-time Binance data."""
    
    def __init__(self):
        self.test_results = {'passed': 0, 'failed': 0, 'warnings': 0}
        self.ws_base_url = "wss://fstream.binance.com/ws"
        self.received_messages = []
        
    def log_result(self, test_name: str, status: str, message: str):
        """Log test results."""
        if status == 'PASS':
            logger.info(f"✅ {test_name}: {message}")
            self.test_results['passed'] += 1
        elif status == 'FAIL':
            logger.error(f"❌ {test_name}: {message}")
            self.test_results['failed'] += 1
        else:
            logger.warning(f"⚠️ {test_name}: {message}")
            self.test_results['warnings'] += 1

    async def test_websocket_connection(self):
        """Test basic WebSocket connection to Binance."""
        try:
            logger.info("Testing WebSocket connection...")
            
            # Simple connection test
            stream_url = f"{self.ws_base_url}/btcusdt@ticker"
            
            async with websockets.connect(stream_url) as websocket:
                # Wait for first message
                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(message)
                
                if 's' in data and data['s'] == 'BTCUSDT':
                    self.log_result("WebSocket Connection", "PASS", 
                                   f"Connected successfully, received ticker for {data['s']}")
                else:
                    self.log_result("WebSocket Connection", "FAIL", 
                                   f"Invalid message format: {data}")
                    
        except asyncio.TimeoutError:
            self.log_result("WebSocket Connection", "FAIL", "Connection timeout")
        except Exception as e:
            self.log_result("WebSocket Connection", "FAIL", f"Connection error: {str(e)}")

    async def test_ticker_stream(self):
        """Test individual ticker stream."""
        try:
            logger.info("Testing individual ticker stream...")
            
            stream_url = f"{self.ws_base_url}/btcusdt@ticker"
            messages_received = 0
            price_updates = []
            
            async with websockets.connect(stream_url) as websocket:
                start_time = time.time()
                
                while messages_received < 5 and (time.time() - start_time) < 30:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10)
                        data = json.loads(message)
                        
                        if 'c' in data:  # 'c' is current price
                            price_updates.append(float(data['c']))
                            messages_received += 1
                            logger.debug(f"Received price update: ${data['c']}")
                        
                    except asyncio.TimeoutError:
                        break
            
            if messages_received >= 3:
                price_range = max(price_updates) - min(price_updates)
                self.log_result("Ticker Stream", "PASS", 
                               f"Received {messages_received} updates, price range: ${price_range:.2f}")
            else:
                self.log_result("Ticker Stream", "FAIL", 
                               f"Insufficient updates: {messages_received}")
                
        except Exception as e:
            self.log_result("Ticker Stream", "FAIL", f"Error: {str(e)}")

    async def test_multi_stream(self):
        """Test multiple symbol streams."""
        try:
            logger.info("Testing multi-symbol stream...")
            
            # Subscribe to multiple streams
            streams = ["btcusdt@ticker", "ethusdt@ticker", "solusdt@ticker"]
            stream_url = f"{self.ws_base_url}/{'/'.join(streams)}"
            
            symbols_received = set()
            messages_received = 0
            
            async with websockets.connect(stream_url) as websocket:
                start_time = time.time()
                
                while len(symbols_received) < 3 and (time.time() - start_time) < 30:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10)
                        data = json.loads(message)
                        
                        if 'stream' in data and 'data' in data:
                            symbol = data['data'].get('s', '').upper()
                            if symbol:
                                symbols_received.add(symbol)
                                messages_received += 1
                                logger.debug(f"Received update for {symbol}")
                        
                    except asyncio.TimeoutError:
                        break
            
            if len(symbols_received) >= 2:
                self.log_result("Multi-Stream", "PASS", 
                               f"Received data from {len(symbols_received)} symbols: {list(symbols_received)}")
            else:
                self.log_result("Multi-Stream", "FAIL", 
                               f"Insufficient symbol coverage: {list(symbols_received)}")
                
        except Exception as e:
            self.log_result("Multi-Stream", "FAIL", f"Error: {str(e)}")

    async def test_orderbook_stream(self):
        """Test order book depth stream."""
        try:
            logger.info("Testing order book stream...")
            
            stream_url = f"{self.ws_base_url}/btcusdt@depth5@100ms"
            orderbook_updates = 0
            
            async with websockets.connect(stream_url) as websocket:
                start_time = time.time()
                
                while orderbook_updates < 3 and (time.time() - start_time) < 20:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10)
                        data = json.loads(message)
                        
                        if 'bids' in data and 'asks' in data:
                            bids = len(data['bids'])
                            asks = len(data['asks'])
                            orderbook_updates += 1
                            logger.debug(f"Order book update: {bids} bids, {asks} asks")
                        
                    except asyncio.TimeoutError:
                        break
            
            if orderbook_updates >= 2:
                self.log_result("OrderBook Stream", "PASS", 
                               f"Received {orderbook_updates} order book updates")
            else:
                self.log_result("OrderBook Stream", "FAIL", 
                               f"Insufficient order book updates: {orderbook_updates}")
                
        except Exception as e:
            self.log_result("OrderBook Stream", "FAIL", f"Error: {str(e)}")

    async def test_stream_vs_rest_consistency(self, exchange):
        """Test consistency between WebSocket streams and REST API."""
        try:
            logger.info("Testing stream vs REST API consistency...")
            
            # Get REST API data
            rest_ticker = await exchange.get_ticker('BTCUSDT')
            rest_price = float(rest_ticker.get('last', 0)) if rest_ticker else 0
            
            if rest_price == 0:
                self.log_result("Stream vs REST", "FAIL", "Failed to get REST price")
                return
            
            # Get WebSocket data
            stream_url = f"{self.ws_base_url}/btcusdt@ticker"
            stream_price = 0
            
            async with websockets.connect(stream_url) as websocket:
                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(message)
                stream_price = float(data.get('c', 0))
            
            if stream_price > 0:
                price_diff_pct = abs(rest_price - stream_price) / rest_price * 100
                
                if price_diff_pct < 0.1:  # Less than 0.1% difference
                    self.log_result("Stream vs REST", "PASS", 
                                   f"Prices consistent: REST ${rest_price:.2f}, "
                                   f"Stream ${stream_price:.2f} ({price_diff_pct:.3f}% diff)")
                else:
                    self.log_result("Stream vs REST", "WARN", 
                                   f"Price difference: {price_diff_pct:.2f}%")
            else:
                self.log_result("Stream vs REST", "FAIL", "Failed to get stream price")
                
        except Exception as e:
            self.log_result("Stream vs REST", "FAIL", f"Error: {str(e)}")

    async def test_connection_stability(self):
        """Test WebSocket connection stability and reconnection."""
        try:
            logger.info("Testing connection stability...")
            
            stream_url = f"{self.ws_base_url}/btcusdt@ticker"
            connection_attempts = 0
            successful_connections = 0
            
            for attempt in range(3):
                connection_attempts += 1
                try:
                    async with websockets.connect(stream_url) as websocket:
                        # Test connection for 5 seconds
                        start_time = time.time()
                        messages_in_period = 0
                        
                        while (time.time() - start_time) < 5:
                            try:
                                await asyncio.wait_for(websocket.recv(), timeout=2)
                                messages_in_period += 1
                            except asyncio.TimeoutError:
                                break
                        
                        if messages_in_period >= 1:
                            successful_connections += 1
                        
                        logger.debug(f"Connection {attempt + 1}: {messages_in_period} messages")
                        
                except Exception as e:
                    logger.debug(f"Connection {attempt + 1} failed: {str(e)}")
                
                # Small delay between attempts
                await asyncio.sleep(1)
            
            success_rate = (successful_connections / connection_attempts) * 100
            
            if success_rate >= 80:
                self.log_result("Connection Stability", "PASS", 
                               f"{successful_connections}/{connection_attempts} connections successful")
            else:
                self.log_result("Connection Stability", "FAIL", 
                               f"Low success rate: {success_rate:.1f}%")
                
        except Exception as e:
            self.log_result("Connection Stability", "FAIL", f"Error: {str(e)}")

    async def test_rate_limiting_compliance(self):
        """Test WebSocket rate limiting compliance."""
        try:
            logger.info("Testing rate limiting compliance...")
            
            # Test multiple concurrent connections (Binance allows up to 5)
            stream_urls = [
                f"{self.ws_base_url}/btcusdt@ticker",
                f"{self.ws_base_url}/ethusdt@ticker",
                f"{self.ws_base_url}/solusdt@ticker"
            ]
            
            successful_connections = 0
            
            async def test_connection(url):
                try:
                    async with websockets.connect(url) as websocket:
                        # Receive one message to confirm connection
                        await asyncio.wait_for(websocket.recv(), timeout=5)
                        return True
                except:
                    return False
            
            # Test concurrent connections
            tasks = [test_connection(url) for url in stream_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_connections = sum(1 for r in results if r is True)
            
            if successful_connections >= 2:
                self.log_result("Rate Limiting", "PASS", 
                               f"{successful_connections}/{len(stream_urls)} concurrent connections successful")
            else:
                self.log_result("Rate Limiting", "WARN", 
                               f"Limited concurrent connections: {successful_connections}")
                
        except Exception as e:
            self.log_result("Rate Limiting", "FAIL", f"Error: {str(e)}")

    def generate_summary(self):
        """Generate test summary."""
        total = sum(self.test_results.values())
        passed = self.test_results['passed']
        
        logger.info("\n" + "="*60)
        logger.info("WEBSOCKET INTEGRATION TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"📊 Total Tests: {total}")
        logger.info(f"✅ Passed: {self.test_results['passed']}")
        logger.info(f"❌ Failed: {self.test_results['failed']}")
        logger.info(f"⚠️ Warnings: {self.test_results['warnings']}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 70:  # Lower threshold for WebSocket tests
            logger.info("🎉 WebSocket integration is functional!")
            return True
        else:
            logger.warning("⚠️ WebSocket integration needs attention")
            return False

async def main():
    """Run WebSocket integration tests."""
    logger.info("⚡ TEST 2: WebSocket Integration")
    logger.info("="*50)
    
    tester = WebSocketIntegrationTester()
    
    try:
        # Initialize exchange for comparison tests
        config_manager = ConfigManager()
        config = config_manager.config
        
        async with BinanceExchange(config=config) as exchange:
            logger.info("🔗 Exchange initialized for comparison tests")
            
            # Run WebSocket tests
            await tester.test_websocket_connection()
            await tester.test_ticker_stream()
            await tester.test_multi_stream()
            await tester.test_orderbook_stream()
            await tester.test_stream_vs_rest_consistency(exchange)
            await tester.test_connection_stability()
            await tester.test_rate_limiting_compliance()
            
        return tester.generate_summary()
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 
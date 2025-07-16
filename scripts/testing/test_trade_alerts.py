#!/usr/bin/env python
# test_trade_alerts.py
# Test script for trade execution alerts

import asyncio
import argparse
import yaml
import logging
import os
import sys
import time
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("trade_alerts_test")

# Add src to Python path
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

try:
    from src.monitoring.alert_manager import AlertManager
    from src.trade_execution.trade_executor import TradeExecutor
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure you are running this script from the project root directory")
    sys.exit(1)

class MockExchangeClient:
    """Mock CCXT exchange client for testing without API credentials."""
    
    def __init__(self):
        self.markets = {
            'BTC/USDT': {
                'id': 'BTCUSDT',
                'symbol': 'BTC/USDT',
                'base': 'BTC',
                'quote': 'USDT',
                'active': True,
                'precision': {
                    'price': 2,
                    'amount': 6
                },
                'limits': {
                    'amount': {
                        'min': 0.0001,
                        'max': 100
                    },
                    'price': {
                        'min': 0.01,
                        'max': 1000000
                    }
                }
            },
            'ETH/USDT': {
                'id': 'ETHUSDT',
                'symbol': 'ETH/USDT',
                'base': 'ETH',
                'quote': 'USDT',
                'active': True,
                'precision': {
                    'price': 2,
                    'amount': 6
                },
                'limits': {
                    'amount': {
                        'min': 0.001,
                        'max': 1000
                    },
                    'price': {
                        'min': 0.01,
                        'max': 100000
                    }
                }
            }
        }
        
        self._prices = {
            'BTC/USDT': 50000.0,
            'ETH/USDT': 3500.0
        }
        self.orders = {}
        self.positions = {}
    
    async def load_markets(self):
        """Mock market loading."""
        return self.markets
    
    async def fetch_ticker(self, symbol):
        """Return mock ticker data."""
        price = self._prices.get(symbol, 1000.0)
        return {
            'symbol': symbol,
            'last': price,
            'bid': price * 0.999,
            'ask': price * 1.001,
            'timestamp': int(time.time() * 1000)
        }
    
    async def create_market_order(self, symbol, side, amount, params=None):
        """Mock order creation."""
        order_id = str(uuid.uuid4())
        price = self._prices.get(symbol, 1000.0)
        
        order = {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'cost': price * amount,
            'timestamp': int(time.time() * 1000),
            'status': 'closed',
            'filled': amount
        }
        
        self.orders[order_id] = order
        return order
    
    async def fetch_balance(self):
        """Mock balance."""
        return {
            'info': {},
            'BTC': {'free': 1.0, 'used': 0.0, 'total': 1.0},
            'ETH': {'free': 10.0, 'used': 0.0, 'total': 10.0},
            'USDT': {'free': 100000.0, 'used': 0.0, 'total': 100000.0},
            'total': {'BTC': 1.0, 'ETH': 10.0, 'USDT': 100000.0}
        }
    
    async def close(self):
        """Mock close method."""
        pass

async def test_alert_manager_directly(live_mode=False):
    """Test trade execution alerts directly using the AlertManager."""
    logger.info("Testing trade execution alerts directly via AlertManager")
    
    # Load config
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Configure mock mode based on live_mode flag
    config["monitoring"] = config.get("monitoring", {})
    config["monitoring"]["alerts"] = config["monitoring"].get("alerts", {})
    config["monitoring"]["alerts"]["mock_mode"] = not live_mode  # Disable mock mode if live_mode is True
    config["monitoring"]["alerts"]["capture_alerts"] = True
    
    # Initialize alert manager
    alert_manager = AlertManager(config)
    
    # Test entry alerts
    logger.info("Testing long entry alert...")
    await alert_manager.send_trade_execution_alert(
        symbol="BTC/USDT",
        side="BUY",
        quantity=0.01,
        price=50000.0,
        trade_type="entry",
        order_id="test-order-001",
        transaction_id="test-txn-001",
        confluence_score=75.5,
        stop_loss_pct=0.03,
        take_profit_pct=0.05,
        position_size_usd=500.0,
        exchange="Bybit"
    )
    
    logger.info("Testing short entry alert...")
    await alert_manager.send_trade_execution_alert(
        symbol="ETH/USDT",
        side="SELL",
        quantity=0.1,
        price=3500.0,
        trade_type="entry",
        order_id="test-order-002",
        transaction_id="test-txn-002",
        confluence_score=85.0,
        stop_loss_pct=0.03,
        position_size_usd=350.0,
        exchange="Bybit"
    )
    
    # Test exit alerts
    logger.info("Testing long exit alert...")
    await alert_manager.send_trade_execution_alert(
        symbol="BTC/USDT",
        side="SELL",
        quantity=0.01,
        price=52000.0,
        trade_type="exit",
        order_id="test-order-003",
        transaction_id="test-txn-003",
        position_size_usd=520.0,
        exchange="Bybit"
    )
    
    logger.info("Testing short exit alert...")
    await alert_manager.send_trade_execution_alert(
        symbol="ETH/USDT",
        side="BUY",
        quantity=0.1,
        price=3400.0,
        trade_type="exit",
        order_id="test-order-004",
        transaction_id="test-txn-004",
        position_size_usd=340.0,
        exchange="Bybit"
    )
    
    # Print captured alerts
    if hasattr(alert_manager, "captured_alerts") and alert_manager.captured_alerts:
        logger.info(f"Successfully captured {len(alert_manager.captured_alerts)} alerts:")
        for i, alert in enumerate(alert_manager.captured_alerts):
            logger.info(f"Alert {i+1}: {alert['message'].get('content', '')[:50]}...")
    else:
        logger.warning("No alerts were captured")

async def test_trade_executor(live_mode=False):
    """Test trade execution alerts through the TradeExecutor."""
    logger.info("Testing trade execution alerts via TradeExecutor")
    
    # Load config
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Configure mock mode based on live_mode flag 
    config["monitoring"] = config.get("monitoring", {})
    config["monitoring"]["alerts"] = config["monitoring"].get("alerts", {})
    config["monitoring"]["alerts"]["mock_mode"] = not live_mode  # Disable mock mode if live_mode is True
    config["monitoring"]["alerts"]["capture_alerts"] = True
    
    # Enable test/demo mode in trade executor
    config["trade_execution"] = config.get("trade_execution", {})
    config["trade_execution"]["test_mode"] = True
    
    # Initialize trade executor
    trade_executor = TradeExecutor(config)
    
    # Use mock exchange client to bypass authentication
    mock_exchange = MockExchangeClient()
    trade_executor.exchange = mock_exchange
    
    # Mock the initialize method to bypass authentication
    original_initialize = trade_executor.initialize
    
    async def mock_initialize():
        trade_executor.markets = mock_exchange.markets
        trade_executor.initialized = True
        trade_executor.test_mode = True
        trade_executor.active_positions = {}
        return {'success': True, 'message': 'Initialized with mock exchange'}
    
    # Replace initialize method with our mock
    trade_executor.initialize = mock_initialize
    
    # Mock the _signed_request method
    async def mock_signed_request(endpoint, params=None, method="GET"):
        if endpoint == "/v5/market/tickers":
            symbol = params.get('symbol', 'BTCUSDT')
            price = 50000.0 if 'BTC' in symbol else 3500.0
            return {
                'retCode': 0,
                'result': {
                    'list': [{
                        'symbol': symbol,
                        'lastPrice': str(price),
                        'bidPrice': str(price * 0.999),
                        'askPrice': str(price * 1.001)
                    }]
                }
            }
        elif endpoint == "/v5/order/create":
            order_id = f"test-{str(uuid.uuid4())[:8]}"
            return {
                'retCode': 0,
                'result': {
                    'orderId': order_id,
                    'orderLinkId': ''
                }
            }
        return {'retCode': 0, 'result': {}}
    
    trade_executor._signed_request = mock_signed_request
    
    # Initialize trade executor with mock methods
    await trade_executor.initialize()
    
    try:
        # Test simulated trades
        logger.info("Testing simulated long trade...")
        long_result = await trade_executor.simulate_trade(
            symbol="BTC/USDT",
            side="buy",
            quantity=0.01,
            confluence_score=75.5
        )
        logger.info(f"Long trade simulation result: {long_result}")
        
        logger.info("Testing simulated short trade...")
        short_result = await trade_executor.simulate_trade(
            symbol="ETH/USDT",
            side="sell",
            quantity=0.1,
            confluence_score=25.5
        )
        logger.info(f"Short trade simulation result: {short_result}")
        
        # Test position closing
        if long_result.get('success', False) and 'order_id' in long_result:
            logger.info("Testing position close...")
            # Mock an active position
            trade_executor.active_positions[long_result['order_id']] = {
                'symbol': "BTC/USDT",
                'side': "buy",
                'quantity': 0.01,
                'entry_price': long_result.get('price', 50000.0),
                'entry_time': long_result.get('timestamp', time.time())
            }
            close_result = await trade_executor.close_position(long_result['order_id'])
            logger.info(f"Position close result: {close_result}")
    finally:
        # Clean up
        await trade_executor.close()
        
    # Print captured alerts
    if hasattr(trade_executor.alert_manager, "captured_alerts") and trade_executor.alert_manager.captured_alerts:
        logger.info(f"Successfully captured {len(trade_executor.alert_manager.captured_alerts)} alerts from TradeExecutor:")
        for i, alert in enumerate(trade_executor.alert_manager.captured_alerts):
            logger.info(f"Alert {i+1}: {alert['message'].get('content', '')[:50]}...")
    else:
        logger.warning("No alerts were captured from TradeExecutor")

async def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description="Test trade execution alerts")
    parser.add_argument("--mode", choices=["direct", "executor", "both"], default="both",
                        help="Test mode: direct (AlertManager only), executor (TradeExecutor), or both")
    parser.add_argument("--live", action="store_true", help="Send actual alerts instead of using mock mode")
    
    args = parser.parse_args()
    
    if args.live:
        logger.warning("Running in LIVE mode - actual alerts will be sent!")
    else:
        logger.info("Running in MOCK mode - no actual alerts will be sent")
    
    if args.mode in ["direct", "both"]:
        await test_alert_manager_directly(live_mode=args.live)
    
    if args.mode in ["executor", "both"]:
        await test_trade_executor(live_mode=args.live)
    
    logger.info("All tests completed")

if __name__ == "__main__":
    asyncio.run(main()) 
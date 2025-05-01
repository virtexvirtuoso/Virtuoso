#!/usr/bin/env python3
"""
Test script to verify the fixes with real Bybit API data:
1. numpy.float64 handling in PDF component charts
2. Timestamp formatting in enhanced confluence alerts
3. Actual webhook message sending to Discord with comprehensive data
"""

import os
import sys
import json
import asyncio
import logging
import numpy as np
import time
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)

logger = logging.getLogger("test_bybit_api")

# Import necessary modules
try:
    from src.monitoring.alert_manager import AlertManager
    from src.core.reporting.pdf_generator import ReportGenerator
except ImportError:
    logger.error("Failed to import required modules. Make sure you're running from the project root.")
    sys.exit(1)

def create_test_config() -> Dict[str, Any]:
    """Create a test configuration for the alert manager using environment variables."""
    # Try to get Discord webhook URL from environment
    discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/example')
    
    # Print the webhook URL (masked for security)
    if discord_webhook_url and len(discord_webhook_url) > 20:
        logger.info(f"Using Discord webhook URL from environment: {discord_webhook_url[:15]}...{discord_webhook_url[-10:]}")
    else:
        logger.warning("No Discord webhook URL found in environment, using placeholder")
    
    # Set BYBIT_API_KEY environment variable if present
    bybit_api_key = os.getenv('BYBIT_API_KEY', '')
    bybit_api_secret = os.getenv('BYBIT_API_SECRET', '')
    
    # Use enhanced configuration structure based on buy_signal_generation.py
    return {
        "monitoring": {
            "alerts": {
                "discord": {
                    "webhook_url": discord_webhook_url
                },
                "thresholds": {
                    "buy": 60,
                    "sell": 40
                }
            }
        },
        "exchanges": {
            "bybit": {
                "enabled": True,
                "testnet": False,
                "api_credentials": {
                    "api_key": bybit_api_key,
                    "api_secret": bybit_api_secret
                }
            }
        }
    }

async def fetch_bybit_market_data(symbol: str = "BTCUSDT") -> Optional[Dict[str, Any]]:
    """Fetch comprehensive market data from Bybit API."""
    logger.info(f"Fetching Bybit market data for {symbol}")
    
    tickers_url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
    trades_url = f"https://api.bybit.com/v5/market/recent-trade?category=linear&symbol={symbol}&limit=50"
    kline_url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=5m&limit=100"
    orderbook_url = f"https://api.bybit.com/v5/market/orderbook?category=linear&symbol={symbol}&limit=20"
    
    market_data = {
        "symbol": symbol,
        "metadata": {
            "exchange": "bybit",
            "market_type": "linear",
            "timeframe": "5m"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Fetch ticker data
            logger.info(f"Fetching ticker data from {tickers_url}")
            async with session.get(tickers_url) as response:
                if response.status == 200:
                    resp_data = await response.json()
                    if resp_data.get("retCode") == 0 and "result" in resp_data:
                        ticker_list = resp_data["result"].get("list", [])
                        if ticker_list:
                            ticker = ticker_list[0]
                            market_data["price"] = float(ticker.get("lastPrice", 0))
                            market_data["24h_high"] = float(ticker.get("highPrice24h", 0))
                            market_data["24h_low"] = float(ticker.get("lowPrice24h", 0))
                            market_data["24h_volume"] = float(ticker.get("volume24h", 0))
                            market_data["timestamp"] = int(time.time() * 1000)
                            market_data["funding_rate"] = float(ticker.get("fundingRate", 0))
                            market_data["open_interest"] = float(ticker.get("openInterest", 0))
                            logger.info(f"Current price for {symbol}: {market_data['price']}")
                else:
                    logger.error(f"Error fetching ticker data: HTTP {response.status}")
                    return None
            
            # Fetch recent trades
            logger.info(f"Fetching trades data from {trades_url}")
            async with session.get(trades_url) as response:
                if response.status == 200:
                    resp_data = await response.json()
                    if resp_data.get("retCode") == 0 and "result" in resp_data:
                        trades = resp_data["result"].get("list", [])
                        market_data["trades"] = trades
                        
                        # Calculate order flow metrics
                        buy_trades = [t for t in trades if t.get("side") == "Buy"]
                        sell_trades = [t for t in trades if t.get("side") == "Sell"]
                        
                        buy_volume = sum([float(t.get("size", 0)) for t in buy_trades])
                        sell_volume = sum([float(t.get("size", 0)) for t in sell_trades])
                        
                        # Store as numpy types to test our fixes
                        market_data["buy_volume"] = np.float64(buy_volume)
                        market_data["sell_volume"] = np.float64(sell_volume)
                        market_data["volume_ratio"] = np.float64(buy_volume / max(sell_volume, 0.0001))
                        
                        logger.info(f"Calculated buy volume: {buy_volume}, sell volume: {sell_volume}, ratio: {market_data['volume_ratio']}")
                else:
                    logger.error(f"Error fetching trade data: HTTP {response.status}")
            
            # Fetch orderbook data
            logger.info(f"Fetching orderbook data from {orderbook_url}")
            async with session.get(orderbook_url) as response:
                if response.status == 200:
                    resp_data = await response.json()
                    if resp_data.get("retCode") == 0 and "result" in resp_data:
                        orderbook = resp_data["result"]
                        market_data["orderbook"] = {
                            "bids": [[float(price), float(qty)] for price, qty in orderbook.get("b", [])],
                            "asks": [[float(price), float(qty)] for price, qty in orderbook.get("a", [])]
                        }
                        logger.info(f"Loaded orderbook with {len(market_data['orderbook']['bids'])} bids and {len(market_data['orderbook']['asks'])} asks")
                else:
                    logger.error(f"Error fetching orderbook data: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error during API request: {str(e)}")
            return None
    
    if not market_data.get("price"):
        logger.error("Failed to get market data from Bybit API")
        return None
    
    # Add additional fields for testing
    market_data["current_price"] = market_data["price"]
    
    return market_data

async def test_with_real_data():
    """Test both fixes with real data from Bybit API."""
    logger.info("=== Testing fixes with real Bybit market data ===")
    
    # Fetch market data
    market_data = await fetch_bybit_market_data("BTCUSDT")
    if not market_data:
        logger.error("Cannot proceed with testing without market data")
        return False, False, False
    
    # 1. Test numpy.float64 handling
    logger.info("\n=== Testing numpy.float64 handling with real data ===")
    
    # Create components with numpy values from real data
    components = {
        'technical': np.float64(65.5),
        'volume': np.float64(71.2),
        'orderbook': np.float64(68.7),
        'orderflow': market_data["volume_ratio"] * 50,  # Using real data as input
        'sentiment': np.float64(66.1),
        'price_structure': np.float64(62.1)
    }
    
    logger.info(f"Components with numpy.float64 values (including real API data): {components}")
    
    # Create PDF generator and test component chart generation
    pdf_test_result = False
    try:
        output_dir = "exports"
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_generator = ReportGenerator()
        chart_path = pdf_generator._create_component_chart(components, output_dir)
        
        if chart_path and os.path.exists(chart_path):
            logger.info(f"✅ Successfully created component chart with real data: {chart_path}")
            pdf_test_result = True
        else:
            logger.error("❌ Failed to create component chart with real data")
    except Exception as e:
        logger.error(f"❌ Error creating component chart with real data: {str(e)}")
    
    # 2. Test timestamp formatting with real timestamp from API
    logger.info("\n=== Testing timestamp formatting with real data ===")
    
    timestamp_test_result = False
    webhook_test_result = False
    
    try:
        # Create config for AlertManager using environment variables
        config = create_test_config()
        
        # Create AlertManager instance
        alert_manager = AlertManager(config)
        
        # Get timestamp from API response and manipulate it to make it problematic
        timestamp = market_data["timestamp"]
        problematic_timestamp = timestamp * 1000  # Convert to microseconds to test fix
        
        # Create test signal data with real market data
        signal_data = {
            'symbol': 'BTCUSDT',
            'score': 75.5,
            'signal': 'BUY',
            'strength': 'Strong',
            'emoji': '🚀',
            'timestamp': problematic_timestamp,
            'price': market_data["price"],
            'components': components,
            'buy_threshold': 65.0,
            'sell_threshold': 35.0,
            'reliability': 85.0,
            'results': {
                "price": market_data["price"],
                "volume_24h": market_data.get("24h_volume", 0),
                "funding_rate": market_data.get("funding_rate", 0),
            },
            'interpretations': [
                "Strong bullish momentum detected",
                f"Order flow ratio at {market_data['volume_ratio']:.2f}",
                f"Current price: ${market_data['price']:.2f}"
            ]
        }
        
        logger.info(f"Testing with real API timestamp multiplied to create a problematic value: {problematic_timestamp}")
        
        # Test the _format_enhanced_confluence_alert method
        webhook_msg = alert_manager._format_enhanced_confluence_alert(signal_data)
        if webhook_msg and isinstance(webhook_msg, dict):
            logger.info(f"✅ Successfully formatted alert with real timestamp: {webhook_msg.get('title', '')}")
            timestamp_test_result = True
            
            # Create a more detailed webhook message like in buy_signal_generation.py
            signal_type = "BUY"
            enhanced_webhook_message = {
                "username": "Virtuoso Trading Bot",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/2534/2534310.png",
                "content": f"**{signal_type} SIGNAL DETECTED**",
                "embeds": [
                    {
                        "title": f"{signal_type} Signal for {signal_data.get('symbol')}",
                        "description": f"Signal strength: {signal_data.get('strength')} {signal_data.get('emoji')}",
                        "color": 3066993,  # Green for buy
                        "fields": [
                            {
                                "name": "Confluence Score",
                                "value": f"{signal_data.get('score'):.2f}",
                                "inline": True
                            },
                            {
                                "name": "Current Price",
                                "value": f"${signal_data.get('price'):,.2f}",
                                "inline": True
                            },
                            {
                                "name": "Signal Type",
                                "value": signal_type,
                                "inline": True
                            },
                            {
                                "name": "Component Scores",
                                "value": "\n".join([f"{k}: {v:.2f}" for k, v in components.items()]),
                                "inline": False
                            }
                        ],
                        "footer": {
                            "text": f"Virtuoso Test Alert • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    }
                ]
            }
            
            # 3. Test sending the actual webhook message if env variable is set
            if os.getenv('DISCORD_WEBHOOK_URL') and os.getenv('DISCORD_WEBHOOK_URL') != 'https://discord.com/api/webhooks/example':
                logger.info("\n=== Testing sending actual webhook message ===")
                enhanced_webhook_message['content'] = "[TEST] Real market data alert from API test script"
                
                try:
                    success, response = await alert_manager.send_discord_webhook_message(enhanced_webhook_message)
                    if success:
                        logger.info("✅ Successfully sent actual webhook message to Discord")
                        webhook_test_result = True
                    else:
                        logger.error(f"❌ Failed to send Discord webhook: {response}")
                except Exception as e:
                    logger.error(f"❌ Error sending Discord webhook: {str(e)}")
            else:
                logger.warning("Skipping actual webhook test - no valid webhook URL in environment")
                webhook_test_result = None  # Skip this test
        else:
            logger.error("❌ Failed to format alert with real timestamp")
    except Exception as e:
        logger.error(f"❌ Error in alert testing: {str(e)}")
    
    return pdf_test_result, timestamp_test_result, webhook_test_result

async def main():
    """Run the test script."""
    logger.info("Starting test with real Bybit API data")
    
    # Test with real market data
    pdf_test_result, timestamp_test_result, webhook_test_result = await test_with_real_data()
    
    # Print summary
    logger.info("\n=== Test Results with Real Data ===")
    logger.info(f"numpy.float64 handling: {'✅ PASSED' if pdf_test_result else '❌ FAILED'}")
    logger.info(f"Timestamp formatting: {'✅ PASSED' if timestamp_test_result else '❌ FAILED'}")
    
    if webhook_test_result is not None:
        logger.info(f"Discord webhook sending: {'✅ PASSED' if webhook_test_result else '❌ FAILED'}")
    else:
        logger.info("Discord webhook sending: ⚠️ SKIPPED (no webhook URL)")
    
    all_passed = pdf_test_result and timestamp_test_result
    if webhook_test_result is not None:
        all_passed = all_passed and webhook_test_result
        
    if all_passed:
        logger.info("✅ All fixes are working correctly with real market data!")
        return 0
    else:
        logger.error("❌ Some fixes didn't work properly with real market data. See log for details.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 
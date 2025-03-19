#!/usr/bin/env python3
"""
Test script to troubleshoot Discord embed formatting issues.
This script tests various Discord webhook payload formats to identify which one works correctly.
"""

import os
import sys
import json
import time
import logging
import asyncio
import aiohttp
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("discord_embed_test")

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

async def test_discord_webhook():
    """Test different Discord webhook payload formats."""
    # Get Discord webhook URL from environment variable
    discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    
    if not discord_webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable not set. Cannot test.")
        return
    
    logger.info("Found Discord webhook URL in environment variables")
    
    # Test 1: Basic text message (baseline test)
    basic_message = {
        "content": "🧪 TEST 1: Basic text message test"
    }
    
    # Test 2: Standard discord embed format - This is the official Discord format 
    standard_embed = {
        "embeds": [
            {
                "title": "🧪 TEST 2: Standard Discord Embed",
                "description": "This is a test of the standard Discord embed format",
                "color": 3066993,  # Green
                "fields": [
                    {
                        "name": "Field 1",
                        "value": "This is a test field",
                        "inline": True
                    },
                    {
                        "name": "Field 2",
                        "value": "This is another test field",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Virtuoso Trading Bot"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }
    
    # Test 3: Discord embed with NULL content
    null_content_embed = {
        "content": None,
        "embeds": [
            {
                "title": "🧪 TEST 3: Embed with NULL content",
                "description": "This tests an embed with content explicitly set to null",
                "color": 15158332,  # Red
                "fields": [
                    {
                        "name": "Note",
                        "value": "Discord's API specifies that content can be null when using embeds"
                    }
                ]
            }
        ]
    }
    
    # Test 4: Discord embed with empty string content
    empty_content_embed = {
        "content": "",
        "embeds": [
            {
                "title": "🧪 TEST 4: Embed with empty string content",
                "description": "This tests an embed with content set to empty string",
                "color": 16776960,  # Yellow
                "fields": [
                    {
                        "name": "Note",
                        "value": "Some libraries convert empty string to null automatically"
                    }
                ]
            }
        ]
    }
    
    # Test 5: Discord embed with no content field at all
    no_content_field_embed = {
        "embeds": [
            {
                "title": "🧪 TEST 5: Embed with no content field",
                "description": "This tests an embed without a content field at all",
                "color": 3447003,  # Blue
                "fields": [
                    {
                        "name": "Note",
                        "value": "This completely omits the content field from the JSON"
                    }
                ]
            }
        ]
    }

    # Test 6: Complex trade alert embed (similar to our real alerts)
    trade_alert_embed = {
        "embeds": [
            {
                "title": "🟢 TRADE ALERT: BTCUSDT 🟢",
                "description": "**BUY SIGNAL | CONFLUENCE SCORE: 71.0/100**\n\nCurrent Price: $60123.45\n\nTimestamp: 2023-08-30 12:34:56 UTC",
                "color": 3066993,  # Green
                "fields": [
                    {
                        "name": "📊 ENTRY & EXITS",
                        "value": "**Stop Loss:** $58320.75 (3.00%)\n**Targets:**\nT1: $61325.92 (2.00%) - 25%\nT2: $62829.00 (4.50%) - 50%\nT3: $64332.09 (7.00%) - 25%",
                        "inline": True
                    },
                    {
                        "name": "⚖️ RISK MANAGEMENT",
                        "value": "**Risk/Reward Ratio:** 2.33\n**Recommended Leverage:** 1.0x\n**Position Size:** 5.0%",
                        "inline": True
                    },
                    {
                        "name": "🔍 DETAILED ANALYSIS",
                        "value": "**VOLUME (72.0)**: Volume indicates strong buying pressure\n**ORDERBOOK (68.0)**: Bid support stronger than asks\n**ORDERFLOW (76.0)**: Recent large buys detected\n**TECHNICAL (65.0)**: Multiple indicators showing bullish reversal\n**PRICE_STRUCTURE (69.0)**: Higher lows forming on 1h timeframe"
                    }
                ],
                "footer": {
                    "text": "Virtuoso Trading Bot"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }
    
    # List of all test payloads
    test_payloads = [
        basic_message,
        standard_embed,
        null_content_embed,
        empty_content_embed,
        no_content_field_embed,
        trade_alert_embed
    ]
    
    # Add proper headers
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'VirtuosoTradingBot/1.0'
    }
    
    # Send each test payload
    async with aiohttp.ClientSession() as session:
        for i, payload in enumerate(test_payloads, 1):
            try:
                logger.info(f"Sending test {i} payload to Discord webhook...")
                logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
                
                start_time = time.time()
                async with session.post(
                    discord_webhook_url,
                    json=payload,
                    headers=headers
                ) as response:
                    response_time = time.time() - start_time
                    response_text = await response.text()
                    
                    if response.status not in (200, 204):
                        logger.error(f"Test {i} failed: Discord API error: {response.status} - {response_text}")
                    else:
                        logger.info(f"Test {i} succeeded: Response: {response.status} ({response_time:.2f}s)")
                        if response_text:
                            logger.debug(f"Discord response: {response_text}")
                    
                    # Wait a bit between requests to avoid rate limiting
                    await asyncio.sleep(1.5)
                    
            except Exception as e:
                logger.error(f"Error in test {i}: {str(e)}")
    
    logger.info("All Discord webhook format tests completed")
    
    # Send a final message to indicate test completion
    completion_message = {
        "content": "✅ Discord embed format testing completed. Check console output for results."
    }
    
    async with session.post(
        discord_webhook_url,
        json=completion_message,
        headers=headers
    ) as response:
        if response.status in (200, 204):
            logger.info("Sent test completion message")

async def main():
    """Main entry point for the script."""
    logger.info("Starting Discord embed format tests")
    await test_discord_webhook()
    logger.info("Discord embed format tests complete")

if __name__ == "__main__":
    asyncio.run(main()) 
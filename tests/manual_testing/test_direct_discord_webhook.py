#!/usr/bin/env python3
"""Test script to directly send messages to Discord webhook without deduplication."""

import os
import sys
import asyncio
import logging
import time
import json
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import aiohttp

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("DirectDiscordTest")

async def test_discord_webhook():
    """Test direct Discord webhook functionality."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get Discord webhook URL
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            logger.error("No Discord webhook URL found in environment variables")
            print("\n⚠️ ERROR: Discord webhook URL not found in environment variables")
            print("Please set the DISCORD_WEBHOOK_URL environment variable and try again.")
            sys.exit(1)
        
        logger.info(f"Found Discord webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
        
        # Create test messages
        test_messages = [
            {
                "username": "Virtuoso Test 1",
                "avatar_url": "https://i.imgur.com/4M34hi2.png",
                "content": "🔍 Test message 1: Simple text message"
            },
            {
                "username": "Virtuoso Test 2",
                "avatar_url": "https://i.imgur.com/4M34hi2.png",
                "content": f"""🚨 **TRADE ALERT - LONG BTCUSDT** 🚨

**Confluence Score: 71.0** 🟢
**Current Price: $60000.00**

**Risk Management:**
• Stop Loss: $58200.00 (-3.0%)
• Target 1: $62700.00 (4.5%)
• Target 2: $64800.00 (8.0%)
• Target 3: $67800.00 (13.0%)

**Risk Reward: 1:2.7**

**Component Analysis:**
• Volume: 83.7 🟢
• Orderbook: 77.2 🟢
• Orderflow: 68.1 🟡
• Technical: 72.5 🟢
• Price Structure: 65.8 🟡
• Sentiment: 62.4 🟡

**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

*This is an automated alert. Always perform your own analysis.*"""
            }
        ]
        
        # Function to send message directly to Discord
        async def send_discord_message(message):
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'VirtuosoTradingBot/1.0'
            }
            
            logger.info(f"Sending message to Discord webhook: {message.get('content', '')[:50]}...")
            
            async with aiohttp.ClientSession() as session:
                try:
                    start_time = time.time()
                    async with session.post(
                        webhook_url,
                        json=message,
                        headers=headers
                    ) as response:
                        response_time = time.time() - start_time
                        response_text = await response.text()
                        
                        if response.status not in (200, 204):
                            logger.error(f"Discord API error: {response.status} - {response_text}")
                            logger.error(f"Request headers: {headers}")
                            logger.error(f"Response headers: {dict(response.headers)}")
                            return False
                        else:
                            logger.info(f"Successfully sent Discord message - Response: {response.status} ({response_time:.2f}s)")
                            if response_text:
                                logger.info(f"Response text: {response_text}")
                            return True
                except Exception as e:
                    logger.error(f"Error connecting to Discord: {str(e)}")
                    return False
        
        # Send test messages
        logger.info("Sending test messages to Discord webhook...")
        
        success_count = 0
        for i, message in enumerate(test_messages):
            logger.info(f"\nSending test message {i+1}/{len(test_messages)}...")
            success = await send_discord_message(message)
            if success:
                success_count += 1
                logger.info(f"Message {i+1} sent successfully")
            else:
                logger.error(f"Failed to send message {i+1}")
            
            # Wait a bit between messages to avoid rate limiting
            await asyncio.sleep(1)
        
        # Send final message
        final_message = {
            "username": "Virtuoso Test Summary",
            "avatar_url": "https://i.imgur.com/4M34hi2.png",
            "content": f"✅ Test completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nSuccessfully sent {success_count}/{len(test_messages)} test messages."
        }
        
        await send_discord_message(final_message)
        logger.info("\nTest completed!")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_discord_webhook()) 
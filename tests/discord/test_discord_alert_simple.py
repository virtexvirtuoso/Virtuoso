#!/usr/bin/env python3
"""
Test Discord Alert Functionality with Confluence Scores (Simplified)

This script tests the Discord alerting functionality when a confluence score
meets the buy or sell threshold using a simplified message format.
"""

import asyncio
import logging
import os
import yaml
import time
import aiohttp
from typing import Dict, Any
import dotenv
import traceback

# Load environment variables from .env file
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def send_discord_alert(webhook_url, message):
    """Send a simple message to Discord webhook."""
    try:
        async with aiohttp.ClientSession() as session:
            webhook_data = {"content": message}
            async with session.post(
                webhook_url,
                json=webhook_data
            ) as response:
                if response.status not in (200, 204):
                    response_text = await response.text()
                    logger.error(f"Discord API error: {response.status} - {response_text}")
                    return False
                else:
                    logger.info(f"Successfully sent Discord alert")
                    return True
    
    except Exception as e:
        logger.error(f"Error sending Discord alert: {str(e)}")
        return False

async def test_bullish_alert():
    """Test sending a bullish confluence alert."""
    # Get webhook URL from environment
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable is not set!")
        logger.info("Please set it in your .env file or environment variables")
        return False
    
    # Symbol and score
    symbol = "BTC/USDT"
    confluence_score = 75.0
    
    # Component scores
    components = {
        'volume': 80.0,
        'technical': 70.0,
        'orderflow': 65.0,
        'orderbook': 75.0,
        'sentiment': 80.0,
        'price_structure': 75.0
    }
    
    # Create a compact message
    message = f"🚨 **BULLISH SIGNAL - {symbol}** 🚨\n\n"
    message += f"**Confluence Score: {confluence_score:.2f}**\n\n"
    
    # Add component scores
    message += "**Component Scores:**\n"
    for component, component_score in components.items():
        message += f"• {component.replace('_', ' ').title()}: {component_score:.2f}\n"
    
    # Add signal interpretation
    message += "\n**Interpretation:** Strong bullish signal detected with significant volume and positive market sentiment"
    
    # Send the alert
    logger.info(f"Sending bullish alert for {symbol} with score {confluence_score}")
    success = await send_discord_alert(webhook_url, message)
    
    if success:
        logger.info("Bullish alert sent successfully. Please check your Discord channel.")
    else:
        logger.error("Failed to send bullish alert.")
        
    return success

async def test_bearish_alert():
    """Test sending a bearish confluence alert."""
    # Get webhook URL from environment
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable is not set!")
        return False
    
    # Symbol and score
    symbol = "BTC/USDT"
    confluence_score = 25.0
    
    # Component scores
    components = {
        'volume': 30.0,
        'technical': 20.0,
        'orderflow': 35.0,
        'orderbook': 25.0,
        'sentiment': 20.0,
        'price_structure': 30.0
    }
    
    # Create a compact message
    message = f"🔻 **BEARISH SIGNAL - {symbol}** 🔻\n\n"
    message += f"**Confluence Score: {confluence_score:.2f}**\n\n"
    
    # Add component scores
    message += "**Component Scores:**\n"
    for component, component_score in components.items():
        message += f"• {component.replace('_', ' ').title()}: {component_score:.2f}\n"
    
    # Add signal interpretation
    message += "\n**Interpretation:** Strong bearish signal detected with weak technical indicators and negative sentiment"
    
    # Send the alert
    logger.info(f"Sending bearish alert for {symbol} with score {confluence_score}")
    success = await send_discord_alert(webhook_url, message)
    
    if success:
        logger.info("Bearish alert sent successfully. Please check your Discord channel.")
    else:
        logger.error("Failed to send bearish alert.")
        
    return success

async def main():
    """Run all tests."""
    try:
        # Check if the webhook URL is set
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            logger.error("DISCORD_WEBHOOK_URL environment variable is not set!")
            logger.info("Please set it in your .env file or environment variables")
            logger.info("Example: DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-url")
            return
            
        logger.info(f"Using Discord webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
            
        # Test initial connection message
        logger.info("\n=== Testing Discord Connection ===")
        test_message = "🔄 **Discord Alert Test** 🔄\n\nThis is a test message to verify the Discord webhook connection."
        connection_success = await send_discord_alert(webhook_url, test_message)
        
        if not connection_success:
            logger.error("Failed to connect to Discord webhook. Please check your webhook URL and try again.")
            return
            
        # Short pause between messages
        await asyncio.sleep(2)
            
        # Test bullish alert
        logger.info("\n=== Testing Bullish Alert ===")
        await test_bullish_alert()
        
        # Short pause between tests
        await asyncio.sleep(2)
        
        # Test bearish alert
        logger.info("\n=== Testing Bearish Alert ===")
        await test_bearish_alert()
        
        logger.info("\n=== All tests completed ===")
        logger.info("Please check your Discord channel for the test alerts.")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 
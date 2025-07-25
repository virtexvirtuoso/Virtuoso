#!/usr/bin/env python3
"""Test the fixed webhook implementation."""

import os
import sys
import asyncio
import aiohttp
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_fixed_webhook():
    """Test webhook with Discord-compatible format."""
    webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL', '')
    
    if not webhook_url:
        print("ERROR: No webhook URL found")
        return
    
    message = "Test system alert from Virtuoso Trading"
    details = {
        "alert_type": "system_test",
        "symbol": "BTCUSDT",
        "price": "100000",
        "volume": "12345.67",
        "timestamp": str(datetime.now(timezone.utc))
    }
    
    # Discord webhook format
    payload = {
        "content": message[:2000],
        "username": "Virtuoso System Alerts"
    }
    
    # Add embed with details
    if details:
        embed = {
            "title": "Alert Details",
            "fields": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "color": 16776960  # Yellow
        }
        
        for key, value in list(details.items())[:25]:
            if key not in ['timestamp', 'source']:
                embed["fields"].append({
                    "name": str(key).replace('_', ' ').title()[:256],
                    "value": str(value)[:1024],
                    "inline": True
                })
        
        payload["embeds"] = [embed]
    
    print("Sending test webhook with fixed format...")
    print(f"Payload: {payload}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                print(f"Response status: {response.status}")
                if response.status in [200, 204]:
                    print("✅ Success! Webhook delivered")
                else:
                    text = await response.text()
                    print(f"❌ Failed: {text}")
                    
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_fixed_webhook())
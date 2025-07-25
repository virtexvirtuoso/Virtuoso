#!/usr/bin/env python3
"""Debug the system webhook error."""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_webhook_direct():
    """Test webhook directly with detailed error handling."""
    webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL', '')
    
    print("=== Direct Webhook Test ===")
    print(f"URL exists: {bool(webhook_url)}")
    if webhook_url:
        print(f"URL length: {len(webhook_url)}")
        print(f"URL starts with: {webhook_url[:30]}")
        print(f"URL ends with: {webhook_url[-20:]}")
    
    if not webhook_url:
        print("ERROR: No webhook URL found")
        return
    
    payload = {
        "text": "Test system webhook message",
        "details": {"type": "test"},
        "timestamp": asyncio.get_event_loop().time(),
        "source": "virtuoso_trading"
    }
    
    print("\nAttempting to send webhook...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                print(f"Response status: {response.status}")
                if response.status != 200:
                    text = await response.text()
                    print(f"Response text: {text[:200]}")
                    
    except aiohttp.ClientConnectorError as e:
        print(f"ClientConnectorError - Type: {type(e).__name__}")
        print(f"Error string: '{str(e)}'")
        print(f"Error repr: {repr(e)}")
        if hasattr(e, 'os_error'):
            print(f"OS Error: {e.os_error}")
        if hasattr(e, 'errno'):
            print(f"Errno: {e.errno}")
            
    except aiohttp.ClientTimeout as e:
        print(f"ClientTimeout - Type: {type(e).__name__}")
        print(f"Error string: '{str(e)}'")
        print(f"Error repr: {repr(e)}")
        
    except Exception as e:
        print(f"Unexpected error - Type: {type(e).__name__}")
        print(f"Error string: '{str(e)}'")
        print(f"Error repr: {repr(e)}")
        print(f"Has __cause__: {e.__cause__ is not None}")
        if e.__cause__:
            print(f"Cause type: {type(e.__cause__).__name__}")
            print(f"Cause string: {str(e.__cause__)}")
        
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_webhook_direct())
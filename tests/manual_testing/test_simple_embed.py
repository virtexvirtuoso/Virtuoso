import os
import json
import aiohttp
import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("simple_embed_test")

async def send_test_embed():
    """Send a simple embed test to Discord webhook"""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable not set!")
        return
    
    logger.info(f"Using webhook URL: {webhook_url[:20]}...")
    
    # Create a simple embed test
    payload = {
        "embeds": [
            {
                "title": "🟢 SIMPLE EMBED TEST 🟢",
                "description": "This is a test to verify Discord embeds are working properly",
                "color": 3066993,  # Green
                "fields": [
                    {
                        "name": "Test Field 1",
                        "value": "This field should display properly",
                        "inline": True
                    },
                    {
                        "name": "Test Field 2",
                        "value": "This field should also display properly",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Testing Discord Embed Format"
                }
            }
        ]
    }
    
    logger.info(f"Sending payload:\n{json.dumps(payload, indent=2)}")
    
    # Send the webhook
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(webhook_url, json=payload) as response:
                status = response.status
                logger.info(f"Discord API response: {status}")
                
                if status == 204:
                    logger.info("✅ Success! The embed was sent correctly.")
                else:
                    error_text = await response.text()
                    logger.error(f"Discord error: {error_text}")
        except Exception as e:
            logger.error(f"Error sending webhook: {str(e)}")

async def main():
    await send_test_embed()
    logger.info("Test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 
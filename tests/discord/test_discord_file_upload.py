#!/usr/bin/env python3
"""
Simple test script to verify Discord file uploads work correctly.
This script focuses only on sending a file to Discord via webhook.

Usage:
  export DISCORD_WEBHOOK_URL="your_webhook_url_here"
  python test_discord_file_upload.py
"""

import os
import sys
import json
import logging
import asyncio
import aiohttp
import aiofiles
import tempfile
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_test_file():
    """Create a simple test file to upload."""
    # Ensure exports directory exists
    exports_dir = Path("exports")
    exports_dir.mkdir(exist_ok=True)
    
    # Create a simple plot
    plt.figure(figsize=(8, 6))
    plt.plot(range(10), [random.random() * 10 for _ in range(10)], 'bo-')
    plt.title('Test Chart for Discord Upload')
    plt.xlabel('X Values')
    plt.ylabel('Y Values')
    plt.grid(True)
    
    # Save the file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_chart_{timestamp}.png"
    filepath = exports_dir / filename
    plt.savefig(filepath)
    plt.close()
    
    logger.info(f"Created test file: {filepath}")
    return str(filepath)

async def send_file_to_discord(webhook_url, filepath):
    """Send a file to Discord webhook."""
    logger.info(f"Preparing to send file: {filepath}")
    
    # Verify file exists
    if not os.path.exists(filepath):
        logger.error(f"File doesn't exist: {filepath}")
        return False
    
    file_size = os.path.getsize(filepath)
    logger.info(f"File size: {file_size} bytes")
    
    # Create a simple message
    message = {
        "content": "This is a test file upload to Discord",
        "embeds": [{
            "title": "Test File Upload",
            "description": "Testing file attachments to Discord webhooks",
            "color": 3447003  # Blue color
        }]
    }
    
    try:
        # Prepare form data with file
        form = aiohttp.FormData()
        
        # Add the payload_json field
        form.add_field(
            name='payload_json',
            value=json.dumps(message),
            content_type='application/json'
        )
        
        # Open and add the file
        async with aiofiles.open(filepath, 'rb') as f:
            file_content = await f.read()
            
            form.add_field(
                name='file',
                value=file_content,
                filename=os.path.basename(filepath),
                content_type='application/octet-stream'
            )
        
        logger.info("File added to form data")
        
        # Send request to Discord
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Discord-File-Upload-Test/1.0'
            }
            
            logger.info(f"Sending POST request to Discord webhook...")
            async with session.post(webhook_url, data=form, headers=headers) as response:
                status = response.status
                logger.info(f"Response status: {status}")
                
                if response.content_type == 'application/json':
                    response_data = await response.json()
                    logger.info(f"Response data: {response_data}")
                else:
                    response_text = await response.text()
                    logger.info(f"Response text: {response_text}")
                
                return status in (200, 204)
    
    except Exception as e:
        logger.error(f"Error sending file to Discord: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_file_upload_basic():
    """Basic test of file upload capabilities."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable not set")
        logger.error("Please set the webhook URL: export DISCORD_WEBHOOK_URL='your_webhook_url'")
        return False
    
    logger.info(f"Using webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
    
    # Create test file
    filepath = await create_test_file()
    
    # Send file to Discord
    success = await send_file_to_discord(webhook_url, filepath)
    
    if success:
        logger.info("✅ Successfully sent file to Discord")
    else:
        logger.error("❌ Failed to send file to Discord")
    
    return success

async def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("Discord File Upload Test")
    logger.info("=" * 60)
    
    success = await test_file_upload_basic()
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ TEST PASSED - File was uploaded to Discord")
    else:
        logger.info("❌ TEST FAILED - Could not upload file")
    logger.info("=" * 60)
    
    return success

if __name__ == "__main__":
    # Run the main function
    result = asyncio.run(main())
    sys.exit(0 if result else 1) 
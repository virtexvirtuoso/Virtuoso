import os
import yaml
from dotenv import load_dotenv
import asyncio
import logging
import sys

# Ensure src directory is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

try:
    from monitoring.alert_manager import AlertManager
except ImportError:
    # Fallback if running from root and src is not directly in path via sys.path yet
    # This can happen if the script is in root and imports src.monitoring
    from src.monitoring.alert_manager import AlertManager


# Configure basic logging to see output from AlertManager and discord_webhook library
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger("WebhookTestScript")

async def run_test():
    logger.info("Starting AlertManager webhook test...")
    load_dotenv()
    
    config = {}
    config_file_path = "config/config.yaml"
    try:
        with open(config_file_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Successfully loaded {config_file_path}")
    except Exception as e:
        logger.error(f"Error loading {config_file_path}: {e}")
        return

    logger.info("Initializing AlertManager...")
    # AlertManager's __init__ prints CRITICAL DEBUG lines showing URL loading logic
    alert_manager = AlertManager(config=config)
    
    webhook_url_in_manager = getattr(alert_manager, 'discord_webhook_url', 'NOT_FOUND')
    logger.info(f"AlertManager instance is configured with webhook URL: {webhook_url_in_manager}")

    if not webhook_url_in_manager or webhook_url_in_manager == 'NOT_FOUND':
        logger.error("CRITICAL_ERROR: AlertManager does not have a webhook URL configured after initialization.")
        return

    # Verify against the .env file's value directly for sanity check
    env_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if webhook_url_in_manager != env_webhook_url:
        logger.warning(f"POTENTIAL_MISCONFIGURATION: AlertManager URL ({webhook_url_in_manager}) does not match .env URL ({env_webhook_url}). Check AlertManager init logic and config.yaml overrides.")
    else:
        logger.info(".env URL and AlertManager URL match. Good.")

    test_message_payload = {
        "content": "✅ AlertManager Webhook Test (config.yaml updated)",
        "username": "Virtuoso Test Bot",
        "embeds": [{
            "title": "Configuration Test Successful!",
            "description": "This message confirms `AlertManager` is correctly initialized and using the webhook URL from your `.env` file after `config.yaml` changes.",
            "color": 0x2ECC71, # Green
            "fields": [
                {"name": "Source", "value": "Automated Test Script", "inline": True},
                {"name": "Status", "value": "Operational", "inline": True}
            ],
            "timestamp": asyncio.get_event_loop().time() # approx timestamp
        }]
    }
    
    logger.info(f"Attempting to send test message via AlertManager to: {webhook_url_in_manager[:40]}...")
    
    try:
        # The send_discord_webhook_message is an async method
        await alert_manager.send_discord_webhook_message(test_message_payload)
        # The discord_webhook library used by AlertManager should log the HTTP status code.
        # A successful send usually results in a 204 No Content from Discord.
        logger.info("Test message dispatch attempted via alert_manager.send_discord_webhook_message. Please check your Discord channel and script logs for confirmation from the 'discord_webhook.webhook' logger.")
        logger.info("If no 'discord_webhook.webhook' error (like 404) appears and the message is in Discord, the test is successful.")

    except Exception as e:
        logger.error(f"Error sending test message via AlertManager: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Ensure client session is properly closed if AlertManager creates one
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_test())
    finally:
        # Basic cleanup for any pending tasks, though AlertManager should handle its own session.
        tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
        if tasks:
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        # loop.close() # Closing the loop can cause issues if other async ops are pending or if run in some environments like Jupyter.
        logger.info("Test script finished.") 
import requests
import os
from dotenv import load_dotenv

load_dotenv()

webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
print(f"Webhook URL: {webhook_url}")

try:
    response = requests.post(
        webhook_url,
        json={"content": "This is a test message to verify the Discord webhook connection"}
    )
    print(f"Status code: {response.status_code}")
    print(f"Response content: {response.text}")
    if response.status_code in (200, 204):
        print("SUCCESS: Webhook is working!")
    else:
        print(f"ERROR: Webhook returned status code {response.status_code}")
except Exception as e:
    print(f"ERROR: {str(e)}") 
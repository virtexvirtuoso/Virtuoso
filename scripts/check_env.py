import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print(f"DISCORD_WEBHOOK_URL from script: {os.getenv('DISCORD_WEBHOOK_URL')}")
print(f"SYSTEM_ALERTS_WEBHOOK_URL from script: {os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')}")

# Print .env file contents for debugging
print("\nContents of .env file:")
try:
    with open('.env', 'r') as f:
        for line in f:
            if 'WEBHOOK' in line:
                # Mask webhooks for security
                parts = line.strip().split('=', 1)
                if len(parts) == 2:
                    key, value = parts
                    if value:
                        value = value[:20] + '...' + value[-10:] if len(value) > 30 else value
                    print(f"{key}={value}")
except Exception as e:
    print(f"Error reading .env file: {str(e)}")

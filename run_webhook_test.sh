#!/bin/bash
# Script to run the webhook URL configuration test

echo "Setting up test environment..."

# Set a test webhook URL
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/test_webhook_url"

echo "Running webhook configuration test..."
python test_webhook_config.py

# Store the exit code
EXIT_CODE=$?

# Unset the test webhook URL
unset DISCORD_WEBHOOK_URL

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test completed successfully!"
else
    echo "❌ Test failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE 
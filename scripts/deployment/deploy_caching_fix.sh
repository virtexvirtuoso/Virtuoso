#!/bin/bash

# Manual deployment steps for background caching fix

echo "=== Background Caching Deployment Instructions ==="
echo
echo "The SSH key authentication seems to be not set up. Please deploy manually:"
echo
echo "1. Copy the updated dashboard_integration.py file to VPS:"
echo "   scp src/dashboard/dashboard_integration.py root@45.77.40.77:/root/Virtuoso/src/dashboard/"
echo
echo "2. SSH into the VPS:"
echo "   ssh root@45.77.40.77"
echo
echo "3. Restart the service:"
echo "   sudo systemctl restart virtuoso"
echo
echo "4. Check service status:"
echo "   vt status"
echo
echo "5. Monitor the logs for cache updates:"
echo "   sudo journalctl -u virtuoso -f | grep -E '(confluence|cache)'"
echo
echo "6. Test the mobile dashboard:"
echo "   http://45.77.40.77:8003/dashboard/mobile"
echo
echo "The background caching will:"
echo "- Update confluence scores every 30 seconds"
echo "- Make API respond instantly"
echo "- Show real scores instead of 50"
echo
echo "Look for log messages like:"
echo "- 'Updated confluence cache for BTCUSDT: 54.16'"
echo "- 'Using cached confluence score 54.16 for BTCUSDT (age: 15.2s)'"
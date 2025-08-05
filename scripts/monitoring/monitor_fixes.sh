#!/bin/bash

# Monitor the critical fixes deployed on 2025-08-04
VPS_HOST="linuxuser@45.77.40.77"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

echo "🔍 Monitoring Critical Fixes on VPS"
echo "==================================="
echo "Time: $(date)"
echo ""

# Check if process is running
echo "1. Process Status:"
echo "-----------------"
ssh $VPS_HOST "ps aux | grep -E 'python.*main.py' | grep -v grep" | awk '{print "PID:", $2, "CPU:", $3"%", "MEM:", $4"%", "Uptime:", $10}'

# Check log file is being written
echo -e "\n2. Log File Activity:"
echo "--------------------"
ssh $VPS_HOST "cd $VPS_DIR && ls -la logs/app.log | awk '{print \"Size:\", \$5, \"bytes\", \"Last modified:\", \$6, \$7, \$8}'"

# Check for timeout errors (new fix)
echo -e "\n3. Timeout Errors (Last hour):"
echo "------------------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep -c 'Request timeout' logs/app.log || echo '0 timeout errors found'"

# Check for entry_pos errors (PDF fix)
echo -e "\n4. PDF Generation Errors (Last hour):"
echo "------------------------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep -c 'entry_pos' logs/pdf_generator.log 2>/dev/null || echo '0 entry_pos errors'"

# Check PENGUUSDT monitoring
echo -e "\n5. PENGUUSDT Activity:"
echo "----------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep -c 'PENGUUSDT' logs/app.log || echo 'Not found in current log'"

# Check recent errors
echo -e "\n6. Recent Errors (Last 10):"
echo "---------------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep -i 'error' logs/app.log | tail -10 || echo 'No recent errors'"

# Check API response times
echo -e "\n7. Recent API Calls:"
echo "--------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep 'Making request to' logs/app.log | tail -5 || echo 'No recent API calls logged'"

# Monitor memory usage
echo -e "\n8. Memory Usage:"
echo "---------------"
ssh $VPS_HOST "free -h | grep -E 'Mem:|Swap:'"

# Check if new symbols are getting price data
echo -e "\n9. Price Data Fetches:"
echo "---------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep -E 'Fetching immediate data|Immediate data fetched' logs/app.log | tail -5 || echo 'No immediate fetches logged (might not have new symbols yet)'"

echo -e "\n✅ Monitoring complete at $(date)"
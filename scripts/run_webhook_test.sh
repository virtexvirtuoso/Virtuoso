#!/bin/bash

# Run webhook test script for testing CPU alert routing
echo "===== Testing CPU Alert Routing ====="
python test_cpu_alert_routing.py
echo

# Pause to let Discord rate limits reset
echo "Waiting for 5 seconds..."
sleep 5

# Test the direct webhook simulation with exact formatting
echo "===== Testing Formatted CPU Alert ====="
python trigger_cpu_alert_test.py
echo

# Pause to let Discord rate limits reset
echo "Waiting for 5 seconds..."
sleep 5

# Test market report routing
echo "===== Testing Market Report Routing ====="
python test_market_report_webhook.py
echo

echo "===== All Tests Completed ====="
echo "Please check the Discord channels to verify:"
echo "1. CPU alerts are routed to the SYSTEM channel only"
echo "2. Market reports are routed to the SYSTEM channel only"
echo "3. No duplicate alerts appear in the MAIN channel" 
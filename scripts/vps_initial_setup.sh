#!/bin/bash

echo "🚀 Virtuoso Trading Bot VPS Initial Setup"
echo "========================================"
echo ""

# System info
echo "📊 System Information:"
echo "----------------------"
uname -a
echo ""
echo "Memory: $(free -h | grep Mem | awk '{print $2 " total, " $3 " used"}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $2 " total, " $3 " used (" $5 ")"}')"
echo "CPU: $(nproc) cores"
echo ""

# Check Python
echo "🐍 Python Status:"
echo "-----------------"
if command -v python3.11 &> /dev/null; then
    echo "✅ Python 3.11 installed: $(python3.11 --version)"
else
    echo "❌ Python 3.11 not found - will install"
fi
echo ""

# Check TA-Lib
echo "📈 TA-Lib Status:"
echo "-----------------"
if ldconfig -p | grep -q ta_lib; then
    echo "✅ TA-Lib is installed"
else
    echo "❌ TA-Lib not found - will install"
fi
echo ""

# Check essential services
echo "🔧 Essential Services:"
echo "---------------------"
for service in nginx redis-server; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        echo "✅ $service is running"
    else
        echo "❌ $service not found/running"
    fi
done
echo ""

# Network test
echo "🌐 Network Test to Bybit:"
echo "------------------------"
ping -c 3 api.bybit.com | tail -1
curl -s -w "HTTP Response Time: %{time_total}s\n" -o /dev/null https://api.bybit.com/v5/market/time
echo ""

# Setup SSH key
echo "🔐 Setting up SSH key access:"
echo "----------------------------"
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add your SSH key
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIK461ZlSmcPy+CjG1+qbcJiZmWk8I1yIfB7cvgpGVbYw vultr-trading-bot" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
echo "✅ SSH key added for passwordless access"
echo ""

echo "📋 Next Steps:"
echo "-------------"
echo "1. Install missing components"
echo "2. Clone your repository" 
echo "3. Set up Python environment"
echo "4. Configure API keys"
echo "5. Start the bot"
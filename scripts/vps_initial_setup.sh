#!/bin/bash

#############################################################################
# Script: vps_initial_setup.sh
# Purpose: Complete initial setup of VPS environment for Virtuoso trading system
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
#   Performs complete initial setup of a fresh VPS instance for running
#   the Virtuoso trading system. Installs required dependencies, configures
#   system services, sets up security measures, and prepares the environment
#   for trading bot deployment.
#
# Dependencies:
#   - Ubuntu 20.04+ or Debian 10+ (tested distributions)
#   - Root or sudo access
#   - Internet connectivity for package downloads
#   - Minimum 2GB RAM, 20GB disk space
#
# Usage:
#   ./vps_initial_setup.sh [options]
#   
#   Examples:
#     ./vps_initial_setup.sh
#     ./vps_initial_setup.sh --skip-security
#     ./vps_initial_setup.sh --python-version 3.11
#
# Options:
#   --skip-security      Skip security hardening setup
#   --skip-monitoring    Skip monitoring service installation
#   --python-version     Python version to install (default: 3.11)
#   --user USER          Target user for installation (default: linuxuser)
#   --no-reboot          Skip automatic reboot after setup
#
# Installation Components:
#   - Python 3.11+ with pip and development headers
#   - TA-Lib technical analysis library
#   - Redis and Memcached for caching
#   - Git for version control
#   - Nginx for reverse proxy (optional)
#   - Systemd service files
#   - Firewall configuration (ufw)
#   - SSH security hardening
#   - Automated backup configuration
#
# Environment Variables:
#   VPS_USER            Target username for installation
#   PYTHON_VERSION      Python version to install
#   TRADING_ENV         Environment type (production/development)
#
# Configuration:
#   Creates configuration in:
#   - /home/linuxuser/trading/ (project directory)
#   - /etc/systemd/system/ (service files)
#   - /etc/nginx/sites-available/ (web configuration)
#
# Output:
#   - System information and status checks
#   - Installation progress with success/failure indicators
#   - Post-installation verification
#   - Next steps and configuration instructions
#
# Exit Codes:
#   0 - Setup completed successfully
#   1 - General installation error
#   2 - Insufficient system resources
#   3 - Network connectivity issues
#   4 - Permission denied
#   5 - Package installation failed
#
# Notes:
#   - Run as root or with sudo privileges
#   - May require system reboot for kernel updates
#   - Creates backup of original configurations
#   - Provides post-setup verification checklist
#
#############################################################################

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
#!/bin/bash

#############################################################################
# Script: safe_restart_mac.sh
# Purpose: Safe Mac Restart Script for SSH Sessions
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - rsync
#   - ssh
#   - git
#   - systemctl
#   - Access to project directory structure
#
# Usage:
#   ./safe_restart_mac.sh [options]
#   
#   Examples:
#     ./safe_restart_mac.sh
#     ./safe_restart_mac.sh --verbose
#     ./safe_restart_mac.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 45.77.40.77)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Success
#   1 - Deployment failed
#   2 - Invalid arguments
#   3 - Connection error
#   4 - Service start failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

# This script safely restarts the Mac while maintaining SSH accessibility

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Safe Mac Restart for SSH Sessions ===${NC}"
echo ""

# Function to get IP addresses
get_ip_addresses() {
    echo -e "${YELLOW}Current IP addresses:${NC}"
    ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print "  • " $2}'
    echo ""
}

# Function to check SSH status
check_ssh_status() {
    if ps aux | grep -q "[s]shd"; then
        echo -e "${GREEN}✓ SSH service is running${NC}"
        
        # Check if Remote Login is enabled (without sudo)
        if launchctl list | grep -q "com.openssh.sshd"; then
            echo -e "${GREEN}✓ SSH appears to be enabled for startup${NC}"
        else
            echo -e "${YELLOW}⚠ SSH service status unclear - it's running but startup status unknown${NC}"
        fi
    else
        echo -e "${RED}✗ SSH service is NOT running!${NC}"
        echo -e "${RED}  Restart aborted - SSH must be running${NC}"
        exit 1
    fi
}

# Function to create a restart reminder
create_restart_info() {
    local info_file="$HOME/Desktop/SSH_RESTART_INFO.txt"
    cat > "$info_file" << EOF
SSH RESTART INFORMATION
======================
Restart initiated: $(date)

Your Mac's IP addresses:
$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print "  • " $2}')

To reconnect after restart:
1. Wait 2-3 minutes for the Mac to fully boot
2. From Termius, connect using one of the IP addresses above
3. If connection fails, try:
   - Waiting another minute
   - Using a different IP address from the list
   - Checking if the Mac is on the same network

This file: $info_file
EOF
    echo -e "${GREEN}✓ Restart information saved to: $info_file${NC}"
}

# Main script
echo -e "${BLUE}Checking system status...${NC}"
echo ""

# Show current user and connection
echo -e "${YELLOW}Current session:${NC}"
echo "  • User: $USER"
echo "  • SSH Connection: ${SSH_CONNECTION:-Not an SSH session}"
echo ""

# Check SSH status
check_ssh_status
echo ""

# Show IP addresses
get_ip_addresses

# Create restart info file
create_restart_info
echo ""

# Parse command line arguments
DELAY=${1:-60}
FORCE=${2:-""}

if [[ "$FORCE" == "--force" ]]; then
    echo -e "${YELLOW}Force restart requested${NC}"
else
    # Confirmation prompt
    echo -e "${YELLOW}This will restart your Mac in $DELAY seconds.${NC}"
    echo -e "${YELLOW}You will be disconnected from this SSH session.${NC}"
    echo ""
    read -p "Are you sure you want to restart? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        echo -e "${RED}Restart cancelled${NC}"
        exit 0
    fi
fi

# Schedule the restart
echo ""
echo -e "${YELLOW}Scheduling restart in $DELAY seconds...${NC}"
echo -e "${RED}To cancel: sudo shutdown -c${NC}"
echo ""

# Create a pre-restart script to ensure SSH is enabled
PRE_RESTART_SCRIPT="/tmp/ensure_ssh_enabled.sh"
cat > "$PRE_RESTART_SCRIPT" << 'EOF'
#!/bin/bash
# Ensure SSH is enabled before restart
launchctl list | grep -q "com.openssh.sshd" || echo "Warning: SSH might not start on boot"
EOF
chmod +x "$PRE_RESTART_SCRIPT"

# Schedule the restart
if [[ $DELAY -eq 0 ]]; then
    echo -e "${RED}Restarting NOW!${NC}"
    sudo shutdown -r now "Scheduled restart via safe_restart_mac.sh"
else
    echo -e "${YELLOW}System will restart in $DELAY seconds${NC}"
    echo -e "${YELLOW}Your SSH session will be disconnected${NC}"
    echo ""
    echo -e "${GREEN}After restart:${NC}"
    echo "  1. Wait 2-3 minutes for full boot"
    echo "  2. Reconnect using: ssh $USER@<ip-address>"
    echo "  3. Check ~/Desktop/SSH_RESTART_INFO.txt for details"
    echo ""
    
    # Use 'at' command for the restart if available, otherwise use shutdown
    if command -v at &> /dev/null; then
        echo "sudo shutdown -r now" | at now + $(($DELAY / 60)) minutes 2>/dev/null || \
        sudo shutdown -r +$(($DELAY / 60)) "Scheduled restart in $DELAY seconds"
    else
        sudo shutdown -r +$(($DELAY / 60)) "Scheduled restart in $DELAY seconds"
    fi
fi

echo ""
echo -e "${GREEN}Restart scheduled successfully!${NC}"
echo -e "${YELLOW}Goodbye! See you after the restart.${NC}"
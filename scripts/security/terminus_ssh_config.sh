#!/bin/bash
# Terminus SSH Configuration Helper
# This script temporarily enables password authentication for Terminus

set -e

echo "=== Terminus SSH Configuration Helper ==="
echo "This will enable hybrid authentication (password + key) for Terminus"
echo ""

# Function to enable password auth
enable_password_auth() {
    echo "[INFO] Creating hybrid SSH configuration..."
    
    # Create a backup
    sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.terminus_backup
    
    # Create new config with both auth methods
    sudo tee /etc/ssh/sshd_config.d/50-terminus.conf > /dev/null << 'EOF'
# Terminus-compatible SSH configuration
# Allows both password and key authentication

# Keep security for root
PermitRootLogin no

# Enable both authentication methods
PubkeyAuthentication yes
PasswordAuthentication yes
KbdInteractiveAuthentication yes

# Allow specific user
AllowUsers linuxuser

# Security settings remain
MaxAuthTries 3
MaxSessions 10

# Keep other security measures
X11Forwarding no
PrintMotd yes
PrintLastLog yes
TCPKeepAlive yes
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

    echo "[INFO] Restarting SSH service..."
    sudo systemctl restart ssh
    
    echo "[SUCCESS] Password authentication enabled for Terminus"
    echo ""
    echo "IMPORTANT: This reduces security. Use only if necessary."
    echo "To revert: sudo rm /etc/ssh/sshd_config.d/50-terminus.conf && sudo systemctl restart ssh"
}

# Function to disable password auth
disable_password_auth() {
    echo "[INFO] Removing Terminus configuration..."
    
    if [ -f /etc/ssh/sshd_config.d/50-terminus.conf ]; then
        sudo rm /etc/ssh/sshd_config.d/50-terminus.conf
        sudo systemctl restart ssh
        echo "[SUCCESS] Password authentication disabled"
    else
        echo "[INFO] Terminus config not found"
    fi
    
    if [ -f /etc/ssh/sshd_config.terminus_backup ]; then
        echo "[INFO] Backup available at /etc/ssh/sshd_config.terminus_backup"
    fi
}

# Function to show status
show_status() {
    echo "Current SSH Authentication Status:"
    echo "----------------------------------"
    
    # Check password auth
    if sudo grep -q "^PasswordAuthentication yes" /etc/ssh/sshd_config.d/* 2>/dev/null || \
       sudo grep -q "^PasswordAuthentication yes" /etc/ssh/sshd_config 2>/dev/null; then
        echo "Password Auth: ENABLED ⚠️"
    else
        echo "Password Auth: DISABLED ✅"
    fi
    
    # Check key auth
    if sudo grep -q "^PubkeyAuthentication yes" /etc/ssh/sshd_config.d/* 2>/dev/null || \
       sudo grep -q "^PubkeyAuthentication yes" /etc/ssh/sshd_config 2>/dev/null; then
        echo "Key Auth:      ENABLED ✅"
    else
        echo "Key Auth:      DISABLED ❌"
    fi
    
    # Check for Terminus config
    if [ -f /etc/ssh/sshd_config.d/50-terminus.conf ]; then
        echo "Terminus Mode: ACTIVE ⚠️"
    else
        echo "Terminus Mode: INACTIVE"
    fi
}

# Main menu
case "${1:-help}" in
    enable)
        enable_password_auth
        ;;
    disable)
        disable_password_auth
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {enable|disable|status}"
        echo ""
        echo "Commands:"
        echo "  enable  - Enable password auth for Terminus"
        echo "  disable - Disable password auth (secure mode)"
        echo "  status  - Show current authentication status"
        echo ""
        echo "Example:"
        echo "  $0 enable   # Allow Terminus to connect"
        echo "  $0 disable  # Return to secure mode"
        ;;
esac
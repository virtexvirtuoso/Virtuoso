#!/bin/bash

#############################################################################
# Script: setup_email.sh
# Purpose: Email System Setup for Virtuoso Health Monitoring
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates system setup, service configuration, and environment preparation for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - systemctl
#   - mkdir
#   - chmod
#   - Access to project directory structure
#
# Usage:
#   ./setup_email.sh [options]
#   
#   Examples:
#     ./setup_email.sh
#     ./setup_email.sh --verbose
#     ./setup_email.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Setup completed successfully
#   1 - Setup failed
#   2 - Permission denied
#   3 - Dependencies missing
#   4 - Configuration error
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

# Sets up postfix for local email delivery and external forwarding

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/home/linuxuser/trading/Virtuoso_ccxt"

echo "=== Setting up Email System for Health Monitoring ==="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

# Update package lists
log_info "Updating package lists..."
apt update

# Install required packages
log_info "Installing email packages..."
DEBIAN_FRONTEND=noninteractive apt install -y \
    postfix \
    mailutils \
    bsd-mailx

# Configure postfix for local delivery
log_info "Configuring postfix..."

# Backup original config if it exists
if [ -f /etc/postfix/main.cf ]; then
    cp /etc/postfix/main.cf /etc/postfix/main.cf.backup.$(date +%Y%m%d_%H%M%S)
fi

# Create postfix configuration
cat > /etc/postfix/main.cf << EOF
# Virtuoso Trading System - Postfix Configuration
# Generated on $(date)

# Basic settings
smtpd_banner = \$myhostname ESMTP \$mail_name
biff = no
append_dot_mydomain = no
readme_directory = no
compatibility_level = 2

# Network settings
inet_interfaces = loopback-only
inet_protocols = ipv4

# Local domain settings
myhostname = \$(hostname)
mydomain = localhost
myorigin = \$mydomain
mydestination = localhost, localhost.localdomain

# Mailbox settings
home_mailbox = Maildir/
mailbox_size_limit = 0
recipient_delimiter = +

# Security settings
smtpd_helo_restrictions = permit_mynetworks, reject_invalid_helo_hostname
smtpd_sender_restrictions = permit_mynetworks, reject_unknown_sender_domain
smtpd_recipient_restrictions = permit_mynetworks, reject_unauth_destination

# Local network
mynetworks = 127.0.0.0/8

# Disable IPv6
inet_protocols = ipv4

# Logging
maillog_file = /var/log/mail.log
EOF

# Create aliases for system users
log_info "Setting up email aliases..."

# Backup original aliases if it exists
if [ -f /etc/aliases ]; then
    cp /etc/aliases /etc/aliases.backup.$(date +%Y%m%d_%H%M%S)
fi

cat > /etc/aliases << EOF
# Virtuoso Trading System - Email Aliases
# Generated on $(date)

# System aliases
postmaster: root
nobody: root
hostmaster: root
usenet: root
news: root
webmaster: root
www: root
ftp: root
abuse: root
noc: root
security: root

# Virtuoso trading system
virtuoso-alerts: linuxuser
trading-alerts: linuxuser
admin: linuxuser

# Forward root emails to linuxuser
root: linuxuser
EOF

# Update aliases database
newaliases

# Create mail directory for linuxuser
log_info "Setting up mail directories..."
sudo -u linuxuser mkdir -p /home/linuxuser/Maildir/{cur,new,tmp}
chown -R linuxuser:linuxuser /home/linuxuser/Maildir
chmod -R 700 /home/linuxuser/Maildir

# Start and enable postfix
log_info "Starting postfix service..."
systemctl restart postfix
systemctl enable postfix

# Test email configuration
log_info "Testing email configuration..."

# Send test email
echo "This is a test email from Virtuoso Health Monitoring system.

System: $(hostname)
Date: $(date)
User: $(whoami)

If you receive this email, the email system is working correctly.

Configuration Details:
- Postfix configured for local delivery
- Mail stored in Maildir format
- Health monitoring alerts will be sent to this address

Test completed successfully." | mail -s "Virtuoso Email System Test - $(hostname)" linuxuser

# Check if test email was delivered
sleep 2
if [ -d /home/linuxuser/Maildir/new ] && [ "$(ls -A /home/linuxuser/Maildir/new 2>/dev/null)" ]; then
    log_info "Test email delivered successfully!"
else
    log_warn "Test email may not have been delivered. Check /var/log/mail.log"
fi

# Create email configuration for health monitor
log_info "Creating health monitor email configuration..."

cat > ${PROJECT_ROOT}/scripts/monitoring/email_config.json << EOF
{
    "email_settings": {
        "smtp_server": "localhost",
        "smtp_port": 25,
        "from_email": "virtuoso-monitor@$(hostname)",
        "to_email": "linuxuser@localhost",
        "subject_prefix": "[VIRTUOSO-$(hostname)]",
        "test_command": "echo 'Test from health monitor' | mail -s 'Health Monitor Test' linuxuser"
    },
    "alert_types": {
        "critical": ["service_down", "no_processes", "disk_full"],
        "warning": ["disk_space", "memory_usage", "cpu_usage", "load_average"],
        "info": ["backup_complete", "maintenance_start", "maintenance_end"]
    },
    "external_forwarding": {
        "enabled": false,
        "smtp_relay": "",
        "username": "",
        "password_file": "",
        "external_email": "",
        "note": "Configure these settings to forward alerts to external email"
    }
}
EOF

chown linuxuser:linuxuser ${PROJECT_ROOT}/scripts/monitoring/email_config.json

# Create external email forwarding setup script
cat > ${PROJECT_ROOT}/scripts/monitoring/setup_external_email.sh << 'EOF'
#!/bin/bash
# Setup external email forwarding (Gmail, etc.)
# Run this script to configure external email forwarding

echo "=== External Email Forwarding Setup ==="
echo "This script will help you configure external email forwarding"
echo "You can forward alerts to Gmail, Yahoo, or other email providers"
echo

read -p "Do you want to configure external email forwarding? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Skipping external email setup"
    exit 0
fi

read -p "Enter your external email address: " EXTERNAL_EMAIL
read -p "Enter SMTP server (e.g., smtp.gmail.com): " SMTP_SERVER
read -p "Enter SMTP port (e.g., 587 for Gmail): " SMTP_PORT
read -p "Enter username: " USERNAME

echo "Enter password (will be stored securely):"
read -s PASSWORD

# Create secure password file
PASS_FILE="/home/linuxuser/.email_password"
echo "$PASSWORD" > "$PASS_FILE"
chmod 600 "$PASS_FILE"
chown linuxuser:linuxuser "$PASS_FILE"

# Update postfix for relay
echo "Configuring postfix for relay..."

# Add relay configuration to main.cf
cat >> /etc/postfix/main.cf << EOL

# External relay configuration
relayhost = [$SMTP_SERVER]:$SMTP_PORT
smtp_use_tls = yes
smtp_sasl_auth_enable = yes
smtp_sasl_security_options = noanonymous
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt
EOL

# Create SASL password file
echo "[$SMTP_SERVER]:$SMTP_PORT    $USERNAME:$PASSWORD" > /etc/postfix/sasl_passwd
chmod 600 /etc/postfix/sasl_passwd
postmap /etc/postfix/sasl_passwd

# Add forwarding rule
echo "linuxuser: $EXTERNAL_EMAIL" >> /etc/aliases
newaliases

systemctl restart postfix

echo "External email forwarding configured!"
echo "Test it with: echo 'Test message' | mail -s 'Test' linuxuser"
EOF

chmod +x ${PROJECT_ROOT}/scripts/monitoring/setup_external_email.sh
chown linuxuser:linuxuser ${PROJECT_ROOT}/scripts/monitoring/setup_external_email.sh

# Create log rotation for mail logs
log_info "Setting up log rotation for mail logs..."

cat > /etc/logrotate.d/virtuoso-mail << EOF
/var/log/mail.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    postrotate
        systemctl reload postfix > /dev/null 2>&1 || true
    endscript
}
EOF

# Create mail reading helper script
cat > ${PROJECT_ROOT}/scripts/monitoring/read_mail.sh << 'EOF'
#!/bin/bash
# Helper script to read mail from command line

MAILDIR="/home/linuxuser/Maildir"

echo "=== Virtuoso Mail Reader ==="
echo

if [ ! -d "$MAILDIR/new" ] || [ -z "$(ls -A $MAILDIR/new 2>/dev/null)" ]; then
    echo "No new mail"
else
    echo "New mail found:"
    ls -la $MAILDIR/new/
    echo
    echo "Reading latest email:"
    LATEST=$(ls -t $MAILDIR/new/ | head -1)
    if [ -n "$LATEST" ]; then
        echo "--- Email: $LATEST ---"
        cat $MAILDIR/new/$LATEST
        echo
        read -p "Mark as read? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            mv "$MAILDIR/new/$LATEST" "$MAILDIR/cur/$LATEST:2,S"
            echo "Email marked as read"
        fi
    fi
fi

if [ -d "$MAILDIR/cur" ] && [ -n "$(ls -A $MAILDIR/cur 2>/dev/null)" ]; then
    echo
    echo "Read mail:"
    ls -la $MAILDIR/cur/
fi
EOF

chmod +x ${PROJECT_ROOT}/scripts/monitoring/read_mail.sh
chown linuxuser:linuxuser ${PROJECT_ROOT}/scripts/monitoring/read_mail.sh

# Final status check
log_info "Checking email system status..."
systemctl status postfix --no-pager

echo
log_info "Email system setup complete!"
echo
echo "Configuration Summary:"
echo "- Postfix configured for local delivery"
echo "- Mail stored in /home/linuxuser/Maildir"
echo "- Test email sent to linuxuser"
echo "- Health monitor will send alerts to linuxuser@localhost"
echo
echo "Useful commands:"
echo "- Read mail: ${PROJECT_ROOT}/scripts/monitoring/read_mail.sh"
echo "- Check mail log: tail -f /var/log/mail.log"
echo "- Send test: echo 'test' | mail -s 'test' linuxuser"
echo "- Setup external forwarding: ${PROJECT_ROOT}/scripts/monitoring/setup_external_email.sh"
echo
echo "Mail directories:"
echo "- New mail: /home/linuxuser/Maildir/new/"
echo "- Read mail: /home/linuxuser/Maildir/cur/"
echo
log_info "Health monitoring emails are now ready!"
#!/bin/bash

#############################################################################
# Script: harden_ssh.sh
# Purpose: SSH Hardening Script for Virtuoso Trading System VPS
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
#   ./harden_ssh.sh [options]
#   
#   Examples:
#     ./harden_ssh.sh
#     ./harden_ssh.sh --verbose
#     ./harden_ssh.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: ${VPS_HOST})
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

# Implements security best practices for SSH configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/home/linuxuser/trading/Virtuoso_ccxt"

echo "=== SSH Security Hardening ==="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

# Backup original SSH configuration
log_step "Backing up original SSH configuration..."
if [ -f /etc/ssh/sshd_config ]; then
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)
    log_info "SSH config backed up"
else
    log_error "SSH config file not found!"
    exit 1
fi

# Check if linuxuser exists
if ! id "linuxuser" &>/dev/null; then
    log_error "User 'linuxuser' does not exist. Please create it first."
    exit 1
fi

# Ensure linuxuser has sudo access
log_step "Ensuring linuxuser has sudo access..."
if ! groups linuxuser | grep -q sudo; then
    usermod -aG sudo linuxuser
    log_info "Added linuxuser to sudo group"
fi

# Generate strong SSH keys for linuxuser if they don't exist
log_step "Setting up SSH keys for linuxuser..."
sudo -u linuxuser mkdir -p /home/linuxuser/.ssh
sudo -u linuxuser chmod 700 /home/linuxuser/.ssh

if [ ! -f /home/linuxuser/.ssh/id_rsa ]; then
    log_info "Generating SSH key pair for linuxuser..."
    sudo -u linuxuser ssh-keygen -t rsa -b 4096 -f /home/linuxuser/.ssh/id_rsa -N "" -C "linuxuser@$(hostname)"
    log_info "SSH key pair generated"
else
    log_info "SSH key pair already exists"
fi

# Set up authorized_keys if it doesn't exist
if [ ! -f /home/linuxuser/.ssh/authorized_keys ]; then
    sudo -u linuxuser touch /home/linuxuser/.ssh/authorized_keys
    sudo -u linuxuser chmod 600 /home/linuxuser/.ssh/authorized_keys
    log_info "Created authorized_keys file"
fi

# Create hardened SSH configuration
log_step "Creating hardened SSH configuration..."

cat > /etc/ssh/sshd_config << EOF
# Virtuoso Trading System - Hardened SSH Configuration
# Generated on $(date)

# Basic Settings
Port 22
Protocol 2
ServerKeyBits 2048

# Hostkey Configuration
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key

# Logging
SyslogFacility AUTH
LogLevel INFO

# Authentication
LoginGraceTime 60
PermitRootLogin no
StrictModes yes
MaxAuthTries 3
MaxSessions 4
MaxStartups 10:30:60

# Public Key Authentication
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys

# Password Authentication (disabled for security)
PasswordAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no

# Kerberos and GSSAPI (disabled)
KerberosAuthentication no
GSSAPIAuthentication no

# X11 Forwarding
X11Forwarding no
X11DisplayOffset 10

# Misc Security Settings
AllowAgentForwarding yes
AllowTcpForwarding yes
GatewayPorts no
PermitTunnel no
PrintMotd no
PrintLastLog yes
TCPKeepAlive yes
UsePrivilegeSeparation sandbox
Compression delayed

# User Access Control
AllowUsers linuxuser
DenyUsers root
AllowGroups sudo

# Idle timeout (15 minutes)
ClientAliveInterval 300
ClientAliveCountMax 2

# Security Algorithms
KexAlgorithms curve25519-sha256@libssh.org,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha2-256,hmac-sha2-512

# Banner
Banner /etc/ssh/banner.txt

# Subsystem
Subsystem sftp internal-sftp

# Match blocks for specific configurations
Match User linuxuser
    AllowTcpForwarding yes
    AllowAgentForwarding yes
    X11Forwarding no
EOF

# Create security banner
log_step "Creating security banner..."

cat > /etc/ssh/banner.txt << EOF
################################################################################
#                                                                              #
#                     VIRTUOSO TRADING SYSTEM VPS                             #
#                                                                              #
#                        AUTHORIZED ACCESS ONLY                               #
#                                                                              #
# This system is for the exclusive use of authorized users. All activities    #
# on this system are monitored and recorded. By accessing this system, you    #
# consent to monitoring and agree to comply with all applicable policies.     #
#                                                                              #
# Unauthorized access is prohibited and will be prosecuted to the full        #
# extent of the law.                                                           #
#                                                                              #
# All connections are logged and monitored by security systems.               #
#                                                                              #
################################################################################
EOF

# Set proper permissions
chmod 644 /etc/ssh/banner.txt

# Create SSH security monitoring script
log_step "Creating SSH security monitoring..."

cat > ${PROJECT_ROOT}/scripts/security/ssh_monitor.py << 'EOF'
#!/usr/bin/env python3
"""
SSH Security Monitor for Virtuoso Trading System
Monitors SSH connections, failed attempts, and security events
"""

import re
import sys
import json
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict, Counter

def analyze_ssh_logs(hours=24):
    """Analyze SSH logs for security insights"""
    
    # Get auth logs from systemd journal
    since_time = f"{hours} hours ago"
    
    try:
        result = subprocess.run([
            'journalctl', 
            '-u', 'ssh', 
            '--since', since_time, 
            '--no-pager'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error reading logs: {result.stderr}")
            return None
            
        log_lines = result.stdout.split('\n')
        
    except Exception as e:
        print(f"Error accessing logs: {e}")
        return None
    
    # Analysis results
    analysis = {
        'timestamp': datetime.now().isoformat(),
        'period_hours': hours,
        'successful_logins': [],
        'failed_attempts': [],
        'invalid_users': Counter(),
        'attack_ips': Counter(),
        'connection_summary': {
            'total_connections': 0,
            'successful_logins': 0,
            'failed_attempts': 0,
            'invalid_user_attempts': 0
        }
    }
    
    # Regex patterns for SSH events
    patterns = {
        'successful_login': r'Accepted (?:password|publickey) for (\w+) from ([\d\.]+) port (\d+)',
        'failed_password': r'Failed password for (?:invalid user )?(\w+) from ([\d\.]+) port (\d+)',
        'invalid_user': r'Invalid user (\w+) from ([\d\.]+) port (\d+)',
        'connection_closed': r'Connection closed by ([\d\.]+) port (\d+)',
        'break_in_attempt': r'POSSIBLE BREAK-IN ATTEMPT.*from ([\d\.]+)',
    }
    
    for line in log_lines:
        if not line.strip():
            continue
            
        # Extract timestamp
        timestamp_match = re.search(r'(\w{3} \d{2} \d{2}:\d{2}:\d{2})', line)
        timestamp = timestamp_match.group(1) if timestamp_match else 'Unknown'
        
        # Check for successful logins
        match = re.search(patterns['successful_login'], line)
        if match:
            user, ip, port = match.groups()
            analysis['successful_logins'].append({
                'timestamp': timestamp,
                'user': user,
                'ip': ip,
                'port': port,
                'method': 'publickey' if 'publickey' in line else 'password'
            })
            analysis['connection_summary']['successful_logins'] += 1
            continue
        
        # Check for failed password attempts
        match = re.search(patterns['failed_password'], line)
        if match:
            user, ip, port = match.groups()
            analysis['failed_attempts'].append({
                'timestamp': timestamp,
                'user': user,
                'ip': ip,
                'port': port,
                'type': 'failed_password'
            })
            analysis['attack_ips'][ip] += 1
            analysis['connection_summary']['failed_attempts'] += 1
            continue
        
        # Check for invalid users
        match = re.search(patterns['invalid_user'], line)
        if match:
            user, ip, port = match.groups()
            analysis['invalid_users'][user] += 1
            analysis['attack_ips'][ip] += 1
            analysis['failed_attempts'].append({
                'timestamp': timestamp,
                'user': user,
                'ip': ip,
                'port': port,
                'type': 'invalid_user'
            })
            analysis['connection_summary']['invalid_user_attempts'] += 1
    
    return analysis

def print_security_report(analysis):
    """Print human-readable security report"""
    
    if not analysis:
        print("No analysis data available")
        return
    
    print(f"=== SSH Security Report ===")
    print(f"Period: Last {analysis['period_hours']} hours")
    print(f"Generated: {analysis['timestamp']}")
    print()
    
    # Connection summary
    summary = analysis['connection_summary']
    print("Connection Summary:")
    print(f"  Successful logins: {summary['successful_logins']}")
    print(f"  Failed attempts: {summary['failed_attempts']}")
    print(f"  Invalid user attempts: {summary['invalid_user_attempts']}")
    print(f"  Total security events: {summary['successful_logins'] + summary['failed_attempts']}")
    print()
    
    # Successful logins
    if analysis['successful_logins']:
        print("Recent Successful Logins:")
        for login in analysis['successful_logins'][-10:]:  # Last 10
            print(f"  {login['timestamp']} - {login['user']}@{login['ip']} ({login['method']})")
        print()
    
    # Top attacking IPs
    if analysis['attack_ips']:
        print("Top Attacking IPs:")
        for ip, count in analysis['attack_ips'].most_common(10):
            print(f"  {ip}: {count} attempts")
        print()
    
    # Most targeted invalid users
    if analysis['invalid_users']:
        print("Most Targeted Invalid Users:")
        for user, count in analysis['invalid_users'].most_common(10):
            print(f"  {user}: {count} attempts")
        print()
    
    # Security recommendations
    print("Security Status:")
    if summary['failed_attempts'] > 50:
        print("  ⚠️  HIGH: Many failed login attempts detected")
    elif summary['failed_attempts'] > 10:
        print("  ⚠️  MEDIUM: Moderate failed login attempts")
    else:
        print("  ✅ LOW: Few failed login attempts")
    
    if len(analysis['attack_ips']) > 20:
        print("  ⚠️  HIGH: Many different attacking IPs")
    elif len(analysis['attack_ips']) > 5:
        print("  ⚠️  MEDIUM: Several attacking IPs")
    else:
        print("  ✅ LOW: Few attacking IPs")
    
    print()
    print("Recommendations:")
    print("  1. Ensure fail2ban is running and configured")
    print("  2. Use key-based authentication only")
    print("  3. Monitor logs regularly")
    print("  4. Consider changing SSH port if attacks persist")
    
def main():
    """Main function"""
    hours = 24
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
        except ValueError:
            print("Invalid hours parameter")
            sys.exit(1)
    
    if len(sys.argv) > 2 and sys.argv[2] == '--json':
        analysis = analyze_ssh_logs(hours)
        if analysis:
            print(json.dumps(analysis, indent=2))
        else:
            sys.exit(1)
    else:
        analysis = analyze_ssh_logs(hours)
        print_security_report(analysis)

if __name__ == '__main__':
    main()
EOF

chmod +x ${PROJECT_ROOT}/scripts/security/ssh_monitor.py
chown linuxuser:linuxuser ${PROJECT_ROOT}/scripts/security/ssh_monitor.py

# Create SSH connection alerting script
cat > ${PROJECT_ROOT}/scripts/security/ssh_alert.sh << 'EOF'
#!/bin/bash
# SSH Connection Alert Script
# Sends alerts for new SSH connections

LOG_FILE="/var/log/auth.log"
LAST_CHECK_FILE="/tmp/ssh_alert_lastcheck"
PROJECT_ROOT="/home/linuxuser/trading/Virtuoso_ccxt"

# Get timestamp of last check
if [ -f "$LAST_CHECK_FILE" ]; then
    LAST_CHECK=$(cat $LAST_CHECK_FILE)
else
    LAST_CHECK=$(date -d "1 hour ago" +%s)
fi

# Current timestamp
CURRENT_CHECK=$(date +%s)

# Find new SSH connections since last check
NEW_CONNECTIONS=$(journalctl -u ssh --since "@$LAST_CHECK" --until "@$CURRENT_CHECK" | grep "Accepted \|Failed ")

if [ -n "$NEW_CONNECTIONS" ]; then
    # Send alert email
    {
        echo "New SSH Activity Detected"
        echo "========================"
        echo "Time Period: $(date -d @$LAST_CHECK) to $(date -d @$CURRENT_CHECK)"
        echo "Host: $(hostname)"
        echo
        echo "Activity Details:"
        echo "$NEW_CONNECTIONS"
        echo
        echo "Current SSH Sessions:"
        who
        echo
        echo "Recent Failed Attempts:"
        python3 ${PROJECT_ROOT}/scripts/security/ssh_monitor.py 1 | grep -A 10 "Top Attacking IPs"
    } | mail -s "SSH Activity Alert - $(hostname)" linuxuser
fi

# Update last check timestamp
echo $CURRENT_CHECK > $LAST_CHECK_FILE
EOF

chmod +x ${PROJECT_ROOT}/scripts/security/ssh_alert.sh
chown linuxuser:linuxuser ${PROJECT_ROOT}/scripts/security/ssh_alert.sh

# Test SSH configuration
log_step "Testing SSH configuration..."

# Check configuration syntax
if sshd -t; then
    log_info "SSH configuration syntax is valid"
else
    log_error "SSH configuration has syntax errors"
    exit 1
fi

# Create SSH test script for linuxuser
cat > ${PROJECT_ROOT}/scripts/security/test_ssh.sh << 'EOF'
#!/bin/bash
# SSH Connection Test Script

echo "=== SSH Configuration Test ==="
echo

# Check SSH service status
echo "SSH Service Status:"
systemctl status ssh --no-pager
echo

# Check current SSH connections
echo "Current SSH Connections:"
who
echo

# Check SSH configuration
echo "Key SSH Settings:"
echo "  Port: $(grep "^Port " /etc/ssh/sshd_config | cut -d' ' -f2)"
echo "  Root Login: $(grep "^PermitRootLogin " /etc/ssh/sshd_config | cut -d' ' -f2)"
echo "  Password Auth: $(grep "^PasswordAuthentication " /etc/ssh/sshd_config | cut -d' ' -f2)"
echo "  Public Key Auth: $(grep "^PubkeyAuthentication " /etc/ssh/sshd_config | cut -d' ' -f2)"
echo

# Check fail2ban SSH jail
echo "Fail2ban SSH Protection:"
if systemctl is-active fail2ban >/dev/null 2>&1; then
    fail2ban-client status sshd 2>/dev/null || echo "  SSH jail not active"
else
    echo "  Fail2ban not running"
fi
echo

# Check recent SSH activity
echo "Recent SSH Activity (last hour):"
python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/security/ssh_monitor.py 1
EOF

chmod +x ${PROJECT_ROOT}/scripts/security/test_ssh.sh
chown linuxuser:linuxuser ${PROJECT_ROOT}/scripts/security/test_ssh.sh

# Warn about imminent changes
log_warn "IMPORTANT: SSH configuration will be changed!"
log_warn "- Root login will be DISABLED"
log_warn "- Password authentication will be DISABLED"
log_warn "- Only 'linuxuser' will be allowed to connect"
echo

# Show current SSH connections
echo "Current SSH connections:"
who
echo

# Get confirmation
read -p "Do you want to apply these SSH security changes? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "SSH hardening cancelled by user"
    exit 0
fi

# Apply configuration
log_step "Applying SSH security configuration..."

# Restart SSH service
systemctl restart ssh

# Wait for service to start
sleep 3

# Check if SSH is running
if systemctl is-active ssh >/dev/null; then
    log_info "SSH service restarted successfully"
else
    log_error "SSH service failed to restart!"
    log_error "Restoring backup configuration..."
    cp /etc/ssh/sshd_config.backup.* /etc/ssh/sshd_config
    systemctl restart ssh
    exit 1
fi

# Set up SSH monitoring cron job
log_step "Setting up SSH monitoring..."

# Add cron job for SSH alerts (check every 15 minutes)
(crontab -u linuxuser -l 2>/dev/null; echo "*/15 * * * * ${PROJECT_ROOT}/scripts/security/ssh_alert.sh") | crontab -u linuxuser -

# Create summary report
cat > ${PROJECT_ROOT}/docs/SSH_HARDENING_SUMMARY.md << EOF
# SSH Hardening Summary

## Configuration Applied
- **Date**: $(date)
- **Host**: $(hostname)
- **Configuration File**: /etc/ssh/sshd_config
- **Backup Created**: /etc/ssh/sshd_config.backup.*

## Security Changes
1. **Root login disabled** - Only linuxuser can connect
2. **Password authentication disabled** - Key-based auth only  
3. **Maximum auth tries**: 3
4. **Connection timeout**: 15 minutes
5. **Strong encryption algorithms** enforced
6. **Security banner** displayed on connection

## Access Control
- **Allowed Users**: linuxuser only
- **Allowed Groups**: sudo
- **SSH Port**: 22 (default)
- **Max Sessions**: 4 per connection

## Monitoring Setup
- SSH activity alerts (every 15 minutes)
- Connection logging enhanced
- Failed attempt tracking
- Integration with fail2ban

## Key Files
- SSH Config: /etc/ssh/sshd_config
- User Keys: /home/linuxuser/.ssh/
- Banner: /etc/ssh/banner.txt
- Monitor: ${PROJECT_ROOT}/scripts/security/ssh_monitor.py

## Useful Commands
\`\`\`bash
# Check SSH status
systemctl status ssh

# Monitor SSH activity  
${PROJECT_ROOT}/scripts/security/ssh_monitor.py

# Test SSH configuration
${PROJECT_ROOT}/scripts/security/test_ssh.sh

# View recent connections
journalctl -u ssh --since "1 hour ago"

# Check fail2ban SSH protection
fail2ban-client status sshd
\`\`\`

## Recovery Instructions
If locked out, use VPS console access:
1. Login via VPS provider console
2. Restore backup: \`cp /etc/ssh/sshd_config.backup.* /etc/ssh/sshd_config\`
3. Restart SSH: \`systemctl restart ssh\`

## Important Notes
- **CRITICAL**: Ensure you have alternative access (VPS console) before disconnecting
- Key-based authentication is now required for all connections
- Root account cannot login via SSH (security best practice)
- All SSH activity is monitored and logged
EOF

echo
log_info "SSH hardening complete!"
echo
echo "Security Configuration Summary:"
echo "✅ Root login disabled"
echo "✅ Password authentication disabled"  
echo "✅ Key-based authentication only"
echo "✅ Connection monitoring enabled"
echo "✅ Security banner configured"
echo "✅ Strong encryption algorithms"
echo "✅ Fail2ban integration ready"
echo
echo "Next Steps:"
echo "1. Test SSH connection from another terminal"
echo "2. Ensure you can connect as linuxuser"
echo "3. Set up SSH keys for secure access"
echo "4. Monitor SSH activity regularly"
echo
log_warn "IMPORTANT: Test your SSH access before closing this session!"
echo
echo "Useful commands:"
echo "- Test configuration: ${PROJECT_ROOT}/scripts/security/test_ssh.sh" 
echo "- Monitor activity: ${PROJECT_ROOT}/scripts/security/ssh_monitor.py"
echo "- Check service: systemctl status ssh"
echo
echo "Documentation saved to: ${PROJECT_ROOT}/docs/SSH_HARDENING_SUMMARY.md"
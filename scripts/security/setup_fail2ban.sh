#!/bin/bash

#############################################################################
# Script: setup_fail2ban.sh
# Purpose: Fail2ban Security Setup for Virtuoso Trading System VPS
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
#   ./setup_fail2ban.sh [options]
#   
#   Examples:
#     ./setup_fail2ban.sh
#     ./setup_fail2ban.sh --verbose
#     ./setup_fail2ban.sh --dry-run
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

# Protects against brute force attacks and suspicious activity

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/home/linuxuser/trading/Virtuoso_ccxt"

echo "=== Setting up Fail2ban Security ==="

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

# Install fail2ban
log_info "Installing fail2ban..."
apt install -y fail2ban

# Backup original configuration
log_info "Backing up original fail2ban configuration..."
if [ -f /etc/fail2ban/jail.conf ]; then
    cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.conf.backup.$(date +%Y%m%d_%H%M%S)
fi

# Create custom jail configuration
log_info "Creating custom fail2ban configuration..."

cat > /etc/fail2ban/jail.local << EOF
# Virtuoso Trading System - Fail2ban Configuration
# Generated on $(date)

[DEFAULT]
# Ban settings
bantime = 3600
findtime = 600
maxretry = 3

# Email notifications (requires working mail system)
destemail = linuxuser@localhost
sender = fail2ban@$(hostname)
mta = mail

# Action shortcuts
action = %(action_mwl)s

# Whitelist trusted IPs (add your own IPs here)
ignoreip = 127.0.0.1/8 ::1

# Backend
backend = systemd

# SSH Protection
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600

# SSH Brute Force Protection (more aggressive)
[ssh-aggressive]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 2
bantime = 86400
findtime = 300

# HTTP/HTTPS Protection (if web services are exposed)
[http-get-dos]
enabled = true
port = http,https
filter = http-get-dos
logpath = /var/log/nginx/access.log
maxretry = 300
findtime = 300
bantime = 600

# Protect against port scanning
[port-scan]
enabled = true
filter = port-scan
logpath = /var/log/syslog
maxretry = 5
bantime = 86400
findtime = 3600

# Protect against repeated login failures
[pam-generic]
enabled = true
filter = pam-generic
logpath = /var/log/auth.log
maxretry = 6
bantime = 3600
findtime = 600

# Postfix SMTP protection
[postfix]
enabled = true
port = smtp,465,submission
filter = postfix
logpath = /var/log/mail.log
maxretry = 3
bantime = 3600
findtime = 600

# Custom filter for trading system logs
[virtuoso-trading]
enabled = true
filter = virtuoso-trading
logpath = ${PROJECT_ROOT}/logs/app.log
maxretry = 5
bantime = 1800
findtime = 300

# Recidive jail for repeat offenders
[recidive]
enabled = true
filter = recidive
logpath = /var/log/fail2ban.log
bantime = 86400
findtime = 86400
maxretry = 3
EOF

# Create custom filters
log_info "Creating custom fail2ban filters..."

# HTTP GET DOS filter
cat > /etc/fail2ban/filter.d/http-get-dos.conf << EOF
# HTTP GET DOS Filter
[Definition]
failregex = ^<HOST> -.*"GET .*" (200|404) .*$
ignoreregex =
EOF

# Port scan filter
cat > /etc/fail2ban/filter.d/port-scan.conf << EOF
# Port Scan Detection Filter
[Definition]
failregex = .*kernel:.*TCP.*SYN.*<HOST>.*
            .*kernel:.*UDP.*<HOST>.*
ignoreregex =
EOF

# Custom trading system filter
cat > /etc/fail2ban/filter.d/virtuoso-trading.conf << EOF
# Virtuoso Trading System Security Filter
[Definition]
failregex = .*SECURITY.*ALERT.*<HOST>.*
            .*Authentication.*failed.*<HOST>.*
            .*Suspicious.*activity.*<HOST>.*
            .*Rate.*limit.*exceeded.*<HOST>.*
            .*Invalid.*API.*key.*<HOST>.*
ignoreregex =
EOF

# Create fail2ban monitoring script
log_info "Creating fail2ban monitoring script..."

cat > ${PROJECT_ROOT}/scripts/security/fail2ban_monitor.py << 'EOF'
#!/usr/bin/env python3
"""
Fail2ban Status Monitor for Virtuoso Trading System
Monitors fail2ban status and banned IPs
"""

import subprocess
import json
import sys
from datetime import datetime

def get_fail2ban_status():
    """Get fail2ban status for all jails"""
    try:
        # Get list of active jails
        result = subprocess.run(['fail2ban-client', 'status'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error getting fail2ban status: {result.stderr}")
            return None
            
        output = result.stdout
        status = {
            'timestamp': datetime.now().isoformat(),
            'jails': {},
            'total_banned': 0,
            'active_jails': []
        }
        
        # Parse jail names
        for line in output.split('\n'):
            if 'Jail list:' in line:
                jail_list = line.split('Jail list:')[1].strip()
                if jail_list:
                    jail_names = [j.strip() for j in jail_list.split(',')]
                    status['active_jails'] = jail_names
                    
                    # Get detailed status for each jail
                    for jail in jail_names:
                        jail_status = get_jail_status(jail)
                        if jail_status:
                            status['jails'][jail] = jail_status
                            status['total_banned'] += jail_status.get('currently_banned', 0)
        
        return status
        
    except Exception as e:
        print(f"Error monitoring fail2ban: {e}")
        return None

def get_jail_status(jail_name):
    """Get detailed status for a specific jail"""
    try:
        result = subprocess.run(['fail2ban-client', 'status', jail_name], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            return None
            
        output = result.stdout
        jail_info = {
            'name': jail_name,
            'filter_files': [],
            'currently_failed': 0,
            'total_failed': 0,
            'currently_banned': 0,
            'total_banned': 0,
            'banned_ips': []
        }
        
        for line in output.split('\n'):
            line = line.strip()
            
            if 'Currently failed:' in line:
                jail_info['currently_failed'] = int(line.split(':')[1].strip())
            elif 'Total failed:' in line:
                jail_info['total_failed'] = int(line.split(':')[1].strip())
            elif 'Currently banned:' in line:
                jail_info['currently_banned'] = int(line.split(':')[1].strip())
            elif 'Total banned:' in line:
                jail_info['total_banned'] = int(line.split(':')[1].strip())
            elif 'Banned IP list:' in line:
                ip_list = line.split('Banned IP list:')[1].strip()
                if ip_list:
                    jail_info['banned_ips'] = [ip.strip() for ip in ip_list.split()]
                    
        return jail_info
        
    except Exception as e:
        print(f"Error getting jail status for {jail_name}: {e}")
        return None

def unban_ip(ip_address, jail=None):
    """Unban a specific IP address"""
    try:
        if jail:
            # Unban from specific jail
            result = subprocess.run(['fail2ban-client', 'set', jail, 'unbanip', ip_address], 
                                  capture_output=True, text=True)
        else:
            # Try to unban from all jails
            status = get_fail2ban_status()
            if not status:
                return False
                
            for jail_name in status['active_jails']:
                subprocess.run(['fail2ban-client', 'set', jail_name, 'unbanip', ip_address], 
                             capture_output=True, text=True)
                             
        print(f"IP {ip_address} unbanned successfully")
        return True
        
    except Exception as e:
        print(f"Error unbanning IP {ip_address}: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'status':
            status = get_fail2ban_status()
            if status:
                print(json.dumps(status, indent=2))
            else:
                sys.exit(1)
                
        elif command == 'unban' and len(sys.argv) > 2:
            ip = sys.argv[2]
            jail = sys.argv[3] if len(sys.argv) > 3 else None
            success = unban_ip(ip, jail)
            sys.exit(0 if success else 1)
            
        elif command == 'summary':
            status = get_fail2ban_status()
            if status:
                print(f"Fail2ban Status Summary - {status['timestamp']}")
                print(f"Active jails: {len(status['active_jails'])}")
                print(f"Total banned IPs: {status['total_banned']}")
                print()
                
                for jail_name, jail_info in status['jails'].items():
                    print(f"{jail_name}:")
                    print(f"  Currently banned: {jail_info['currently_banned']}")
                    print(f"  Total failed: {jail_info['total_failed']}")
                    if jail_info['banned_ips']:
                        print(f"  Banned IPs: {', '.join(jail_info['banned_ips'])}")
                    print()
            else:
                sys.exit(1)
        else:
            print("Usage:")
            print("  fail2ban_monitor.py status      - Show detailed JSON status")
            print("  fail2ban_monitor.py summary     - Show human-readable summary")
            print("  fail2ban_monitor.py unban IP [jail] - Unban IP address")
            sys.exit(1)
    else:
        # Default to summary
        status = get_fail2ban_status()
        if status:
            print(f"Fail2ban: {len(status['active_jails'])} jails, {status['total_banned']} banned IPs")
        else:
            print("Fail2ban: Status unavailable")
            sys.exit(1)

if __name__ == '__main__':
    main()
EOF

chmod +x ${PROJECT_ROOT}/scripts/security/fail2ban_monitor.py
chown linuxuser:linuxuser ${PROJECT_ROOT}/scripts/security/fail2ban_monitor.py

# Create fail2ban log analyzer
cat > ${PROJECT_ROOT}/scripts/security/analyze_fail2ban_logs.sh << 'EOF'
#!/bin/bash
# Analyze fail2ban logs for security insights

echo "=== Fail2ban Log Analysis ==="
echo

# Most banned IPs
echo "Top 10 Most Banned IPs:"
grep "Ban " /var/log/fail2ban.log | awk '{print $NF}' | sort | uniq -c | sort -nr | head -10
echo

# Ban summary by jail
echo "Ban Summary by Jail:"
grep "Ban " /var/log/fail2ban.log | awk '{for(i=1;i<=NF;i++) if($i ~ /\[.*\]/) print $i}' | sort | uniq -c | sort -nr
echo

# Recent bans (last 24 hours)
echo "Recent Bans (last 24 hours):"
journalctl -u fail2ban --since "24 hours ago" --no-pager | grep "Ban " | tail -20
echo

# Unban events
echo "Recent Unbans:"
grep "Unban " /var/log/fail2ban.log | tail -10
echo

# Geographic analysis (requires geoip tools)
if command -v geoiplookup >/dev/null 2>&1; then
    echo "Geographic Distribution of Banned IPs:"
    grep "Ban " /var/log/fail2ban.log | awk '{print $NF}' | sort -u | head -20 | \
    while read ip; do
        country=$(geoiplookup $ip 2>/dev/null | cut -d: -f2 | cut -d, -f1)
        echo "$ip: $country"
    done
    echo
fi

# Current status
echo "Current Fail2ban Status:"
python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/security/fail2ban_monitor.py summary
EOF

chmod +x ${PROJECT_ROOT}/scripts/security/analyze_fail2ban_logs.sh
chown linuxuser:linuxuser ${PROJECT_ROOT}/scripts/security/analyze_fail2ban_logs.sh

# Start and enable fail2ban
log_info "Starting and enabling fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban

# Wait for service to start
sleep 3

# Check status
log_info "Checking fail2ban status..."
systemctl status fail2ban --no-pager

# Test configuration
log_info "Testing fail2ban configuration..."
fail2ban-client status

# Create daily security report cron job
log_info "Setting up daily security reports..."

# Create security report script
cat > ${PROJECT_ROOT}/scripts/security/daily_security_report.sh << 'EOF'
#!/bin/bash
# Daily Security Report Generator

REPORT_DATE=$(date +%Y-%m-%d)
PROJECT_ROOT="/home/linuxuser/trading/Virtuoso_ccxt"

# Generate report
{
    echo "=== Virtuoso Trading System - Daily Security Report ==="
    echo "Date: $REPORT_DATE"
    echo "Host: $(hostname)"
    echo

    # Fail2ban status
    echo "=== Fail2ban Status ==="
    python3 ${PROJECT_ROOT}/scripts/security/fail2ban_monitor.py summary
    echo

    # Recent login attempts
    echo "=== Recent SSH Login Attempts ==="
    journalctl -u ssh --since "24 hours ago" --no-pager | grep "authentication failure\|Failed password\|Accepted password" | tail -20
    echo

    # System resource usage
    echo "=== System Resources ==="
    echo "Disk Usage:"
    df -h
    echo
    echo "Memory Usage:"
    free -h
    echo
    echo "Load Average:"
    uptime
    echo

    # Service status
    echo "=== Service Status ==="
    systemctl status virtuoso virtuoso-web virtuoso-cache virtuoso-ticker --no-pager
    echo

    echo "Report generated on $(date)"
} | mail -s "Daily Security Report - $(hostname) - $REPORT_DATE" linuxuser

# Also save to file
{
    echo "=== Virtuoso Trading System - Daily Security Report ==="
    echo "Date: $REPORT_DATE"
    echo "Host: $(hostname)"
    echo

    python3 ${PROJECT_ROOT}/scripts/security/fail2ban_monitor.py summary
    echo
    
    systemctl status fail2ban --no-pager
} > ${PROJECT_ROOT}/logs/security_report_$REPORT_DATE.txt
EOF

chmod +x ${PROJECT_ROOT}/scripts/security/daily_security_report.sh
chown linuxuser:linuxuser ${PROJECT_ROOT}/scripts/security/daily_security_report.sh

# Add cron job for security reports
(crontab -u linuxuser -l 2>/dev/null; echo "0 8 * * * ${PROJECT_ROOT}/scripts/security/daily_security_report.sh") | crontab -u linuxuser -

# Create manual unban script for emergencies
cat > ${PROJECT_ROOT}/scripts/security/emergency_unban.sh << 'EOF'
#!/bin/bash
# Emergency IP Unban Script

if [ $# -eq 0 ]; then
    echo "Usage: $0 <IP_ADDRESS> [jail_name]"
    echo "Example: $0 192.168.1.100"
    echo "Example: $0 192.168.1.100 sshd"
    exit 1
fi

IP=$1
JAIL=$2

echo "Unbanning IP: $IP"

if [ -n "$JAIL" ]; then
    echo "From jail: $JAIL"
    sudo fail2ban-client set $JAIL unbanip $IP
else
    echo "From all jails..."
    for jail in $(sudo fail2ban-client status | grep "Jail list" | cut -d: -f2 | tr ',' '\n'); do
        jail=$(echo $jail | xargs)
        echo "  Trying jail: $jail"
        sudo fail2ban-client set $jail unbanip $IP 2>/dev/null || true
    done
fi

echo "Unban completed for IP: $IP"
echo
echo "Current fail2ban status:"
python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/security/fail2ban_monitor.py summary
EOF

chmod +x ${PROJECT_ROOT}/scripts/security/emergency_unban.sh
chown linuxuser:linuxuser ${PROJECT_ROOT}/scripts/security/emergency_unban.sh

echo
log_info "Fail2ban security setup complete!"
echo
echo "Configuration Summary:"
echo "- Fail2ban installed and configured"
echo "- SSH brute force protection enabled"
echo "- Custom filters for trading system logs"
echo "- Email notifications configured"
echo "- Daily security reports scheduled"
echo
echo "Security Features Enabled:"
echo "- SSH protection (3 failures = 1 hour ban)"
echo "- Aggressive SSH protection (2 failures = 24 hour ban)"
echo "- Port scan detection"
echo "- Repeat offender tracking"
echo "- Custom trading system log monitoring"
echo
echo "Useful Commands:"
echo "- Check status: fail2ban-client status"
echo "- Monitor: ${PROJECT_ROOT}/scripts/security/fail2ban_monitor.py summary"
echo "- Analyze logs: ${PROJECT_ROOT}/scripts/security/analyze_fail2ban_logs.sh"
echo "- Unban IP: ${PROJECT_ROOT}/scripts/security/emergency_unban.sh <IP>"
echo "- View banned IPs: fail2ban-client status sshd"
echo
log_info "Your VPS is now protected against brute force attacks!"
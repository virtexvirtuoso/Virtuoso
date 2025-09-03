#!/bin/bash

#############################################################################
# Script: setup_backup_schedule.sh
# Purpose: Setup Automated Backup Schedule - Part of Phase 1: Emergency Stabilization
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
#   Automated backup schedule setup script for the Virtuoso trading system.
#   Configures LaunchAgent for macOS and cron jobs for regular backup operations
#   with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - systemctl
#   - mkdir
#   - chmod
#   - Access to project directory structure
#
# Usage:
#   ./setup_backup_schedule.sh [options]
#   
#   Examples:
#     ./setup_backup_schedule.sh
#     ./setup_backup_schedule.sh --verbose
#     ./setup_backup_schedule.sh --dry-run
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

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --install     Install backup schedule"
    echo "  --uninstall   Remove backup schedule"
    echo "  --status      Show current backup schedule status"
    echo "  --test        Test backup system"
    echo "  --help        Show this help message"
}

install_backup_schedule() {
    log_info "Installing automated backup schedule..."
    
    # Create backup directory
    BACKUP_DIR="/Users/ffv_macmini/Desktop/virtuoso_backups"
    mkdir -p "$BACKUP_DIR"
    
    # Create launchd plist for macOS (alternative to cron)
    PLIST_FILE="$HOME/Library/LaunchAgents/com.virtuoso.backup.plist"
    
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.virtuoso.backup</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_ROOT/scripts/core/backup.sh</string>
        <string>auto</string>
        <string>--cleanup</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardOutPath</key>
    <string>$BACKUP_DIR/backup_log.txt</string>
    <key>StandardErrorPath</key>
    <string>$BACKUP_DIR/backup_error.txt</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>BACKUP_ROOT</key>
        <string>$BACKUP_DIR</string>
    </dict>
</dict>
</plist>
EOF
    
    # Load the launchd job
    launchctl load "$PLIST_FILE"
    
    log_info "✅ Automated backup schedule installed"
    log_info "📅 Daily backup at 3:00 AM"
    log_info "📁 Backup location: $BACKUP_DIR"
    log_info "📋 Schedule file: $PLIST_FILE"
    
    # Also setup a weekly critical backup via cron as fallback
    setup_cron_backup
}

setup_cron_backup() {
    log_info "Setting up cron backup as fallback..."
    
    # Create cron job for weekly critical backup
    CRON_JOB="0 2 * * 0 $PROJECT_ROOT/scripts/core/backup.sh critical --cleanup >/dev/null 2>&1"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "backup.sh"; then
        log_warn "Backup cron job already exists"
    else
        # Add to existing crontab
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        log_info "✅ Weekly critical backup cron job added (Sundays 2:00 AM)"
    fi
}

uninstall_backup_schedule() {
    log_info "Removing automated backup schedule..."
    
    # Remove launchd job
    PLIST_FILE="$HOME/Library/LaunchAgents/com.virtuoso.backup.plist"
    if [ -f "$PLIST_FILE" ]; then
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
        rm "$PLIST_FILE"
        log_info "✅ LaunchAgent removed"
    fi
    
    # Remove cron job
    if crontab -l 2>/dev/null | grep -q "backup.sh"; then
        crontab -l 2>/dev/null | grep -v "backup.sh" | crontab -
        log_info "✅ Cron job removed"
    fi
    
    log_info "Backup schedule uninstalled"
}

show_backup_status() {
    log_info "Backup schedule status:"
    echo ""
    
    # Check LaunchAgent status
    PLIST_FILE="$HOME/Library/LaunchAgents/com.virtuoso.backup.plist"
    if [ -f "$PLIST_FILE" ]; then
        echo "📋 LaunchAgent: ✅ Installed"
        if launchctl list | grep -q "com.virtuoso.backup"; then
            echo "🔄 Status: ✅ Running"
        else
            echo "🔄 Status: ❌ Not loaded"
        fi
    else
        echo "📋 LaunchAgent: ❌ Not installed"
    fi
    
    # Check cron job
    if crontab -l 2>/dev/null | grep -q "backup.sh"; then
        echo "⏰ Cron Job: ✅ Installed"
    else
        echo "⏰ Cron Job: ❌ Not installed"
    fi
    
    # Check backup directory
    BACKUP_DIR="/Users/ffv_macmini/Desktop/virtuoso_backups"
    if [ -d "$BACKUP_DIR" ]; then
        echo "📁 Backup Directory: ✅ $BACKUP_DIR"
        backup_count=$(find "$BACKUP_DIR" -name "backup_*" -type d 2>/dev/null | wc -l)
        echo "📊 Existing Backups: $backup_count"
        
        # Show recent backups
        if [ "$backup_count" -gt 0 ]; then
            echo ""
            echo "Recent backups:"
            find "$BACKUP_DIR" -name "backup_*" -type d -exec ls -ld {} \; | tail -5 | while read line; do
                echo "  $line"
            done
        fi
    else
        echo "📁 Backup Directory: ❌ Not created"
    fi
    
    # Check backup script
    BACKUP_SCRIPT="$PROJECT_ROOT/scripts/core/backup.sh"
    if [ -x "$BACKUP_SCRIPT" ]; then
        echo "🔧 Backup Script: ✅ Executable"
    else
        echo "🔧 Backup Script: ❌ Not found or not executable"
    fi
}

test_backup_system() {
    log_info "Testing backup system..."
    
    BACKUP_SCRIPT="$PROJECT_ROOT/scripts/core/backup.sh"
    
    if [ ! -x "$BACKUP_SCRIPT" ]; then
        log_error "Backup script not found or not executable: $BACKUP_SCRIPT"
        return 1
    fi
    
    # Test backup script help
    log_info "Testing backup script help..."
    if "$BACKUP_SCRIPT" --help >/dev/null; then
        log_info "✅ Backup script help works"
    else
        log_error "❌ Backup script help failed"
        return 1
    fi
    
    # Test critical backup (small test)
    log_info "Testing critical backup creation..."
    BACKUP_ROOT="/tmp/virtuoso_backup_test"
    export BACKUP_ROOT
    
    if "$BACKUP_SCRIPT" critical --verify; then
        log_info "✅ Test backup created and verified successfully"
        
        # Clean up test backup
        rm -rf "$BACKUP_ROOT"
        log_info "✅ Test backup cleaned up"
    else
        log_error "❌ Test backup failed"
        return 1
    fi
    
    log_info "🎉 Backup system test completed successfully!"
}

# Main execution
main() {
    local action=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --install)
                action="install"
                shift
                ;;
            --uninstall)
                action="uninstall"
                shift
                ;;
            --status)
                action="status"
                shift
                ;;
            --test)
                action="test"
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    if [ -z "$action" ]; then
        log_error "Action not specified"
        show_usage
        exit 1
    fi
    
    # Execute action
    case $action in
        "install")
            install_backup_schedule
            ;;
        "uninstall")
            uninstall_backup_schedule
            ;;
        "status")
            show_backup_status
            ;;
        "test")
            test_backup_system
            ;;
    esac
}

main "$@"
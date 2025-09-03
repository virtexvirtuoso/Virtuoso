#!/bin/bash

#############################################################################
# Script: backup.sh
# Purpose: Emergency Backup Strategy - Part of Phase 1: Emergency Stabilization
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
#   ./backup.sh [options]
#   
#   Examples:
#     ./backup.sh
#     ./backup.sh --verbose
#     ./backup.sh --dry-run
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

# Comprehensive backup system for critical system components

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Backup configuration
BACKUP_ROOT="${BACKUP_ROOT:-/Users/ffv_macmini/Desktop/virtuoso_backups}"
REMOTE_BACKUP_HOST="${REMOTE_BACKUP_HOST:-linuxuser@VPS_HOST_REDACTED}"
REMOTE_BACKUP_PATH="${REMOTE_BACKUP_PATH:-/home/linuxuser/backups}"

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

log_stat() {
    echo -e "${BLUE}[STAT]${NC} $1"
}

show_usage() {
    echo "Usage: $0 [BACKUP_TYPE] [OPTIONS]"
    echo ""
    echo "Backup Types:"
    echo "  critical    Backup critical system files only (quick)"
    echo "  full        Complete system backup (comprehensive)"
    echo "  config      Backup configuration files only"
    echo "  data        Backup databases and data files"
    echo "  remote      Backup to remote VPS"
    echo "  auto        Automatic backup based on system state"
    echo ""
    echo "Options:"
    echo "  --encrypt   Encrypt backup files (requires gpg)"
    echo "  --compress  Compress backup files (default)"  
    echo "  --verify    Verify backup integrity after creation"
    echo "  --cleanup   Clean old backups (keep last 7 days)"
    echo "  --help      Show this help message"
}

create_backup_structure() {
    local backup_dir=$1
    mkdir -p "$backup_dir"/{source,config,data,logs,docs}
    echo "$backup_dir"
}

backup_critical() {
    local backup_dir=$1
    log_info "Creating critical system backup..."
    
    # Source code (excluding virtual environments and cache)
    log_info "Backing up source code..."
    tar --exclude='venv*' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.DS_Store' \
        -czf "$backup_dir/source/source_code_$(date +%Y%m%d_%H%M%S).tar.gz" \
        -C "$PROJECT_ROOT" src/
    
    # Critical configuration files
    log_info "Backing up configurations..."
    tar -czf "$backup_dir/config/configurations_$(date +%Y%m%d_%H%M%S).tar.gz" \
        -C "$PROJECT_ROOT" \
        config/ \
        .env 2>/dev/null || \
        tar -czf "$backup_dir/config/configurations_$(date +%Y%m%d_%H%M%S).tar.gz" \
        -C "$PROJECT_ROOT" config/
    
    # Essential scripts
    log_info "Backing up core scripts..."
    tar -czf "$backup_dir/source/scripts_core_$(date +%Y%m%d_%H%M%S).tar.gz" \
        -C "$PROJECT_ROOT" scripts/core/
    
    # Docker and deployment files
    if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        cp "$PROJECT_ROOT/docker-compose.yml" "$backup_dir/config/"
    fi
    
    if [ -f "$PROJECT_ROOT/Dockerfile" ]; then
        cp "$PROJECT_ROOT/Dockerfile" "$backup_dir/config/"
    fi
    
    # Requirements and setup files
    for file in requirements.txt setup.py pyproject.toml; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            cp "$PROJECT_ROOT/$file" "$backup_dir/config/"
        fi
    done
    
    log_stat "Critical backup completed successfully"
}

backup_full() {
    local backup_dir=$1
    log_info "Creating full system backup..."
    
    # First do critical backup
    backup_critical "$backup_dir"
    
    # Additional source directories
    log_info "Backing up additional source files..."
    for dir in alpha_system tests docs scripts; do
        if [ -d "$PROJECT_ROOT/$dir" ]; then
            tar --exclude='__pycache__' \
                --exclude='*.pyc' \
                --exclude='.DS_Store' \
                -czf "$backup_dir/source/${dir}_$(date +%Y%m%d_%H%M%S).tar.gz" \
                -C "$PROJECT_ROOT" "$dir/"
        fi
    done
    
    # Logs (last 7 days only)
    if [ -d "$PROJECT_ROOT/logs" ]; then
        log_info "Backing up recent logs..."
        find "$PROJECT_ROOT/logs" -name "*.log" -mtime -7 -exec tar -czf "$backup_dir/logs/recent_logs_$(date +%Y%m%d_%H%M%S).tar.gz" {} +
    fi
    
    # Documentation
    if [ -d "$PROJECT_ROOT/docs" ]; then
        log_info "Backing up documentation..."
        tar -czf "$backup_dir/docs/documentation_$(date +%Y%m%d_%H%M%S).tar.gz" \
            -C "$PROJECT_ROOT" docs/ 2>/dev/null || true
    fi
    
    log_stat "Full backup completed successfully"
}

backup_config() {
    local backup_dir=$1
    log_info "Creating configuration backup..."
    
    # All configuration files
    tar -czf "$backup_dir/config/all_config_$(date +%Y%m%d_%H%M%S).tar.gz" \
        -C "$PROJECT_ROOT" \
        config/ \
        .env* \
        docker-compose.yml \
        Dockerfile \
        requirements.txt \
        setup.py \
        pyproject.toml \
        .gitignore \
        .pre-commit-config.yaml \
        2>/dev/null || true
    
    # Environment-specific configs
    if [ -d "$PROJECT_ROOT/.github" ]; then
        tar -czf "$backup_dir/config/github_config_$(date +%Y%m%d_%H%M%S).tar.gz" \
            -C "$PROJECT_ROOT" .github/
    fi
    
    log_stat "Configuration backup completed successfully"
}

backup_data() {
    local backup_dir=$1
    log_info "Creating data backup..."
    
    # Database files
    for db_file in "$PROJECT_ROOT"/data/*.db "$PROJECT_ROOT"/*.db; do
        if [ -f "$db_file" ]; then
            cp "$db_file" "$backup_dir/data/"
            log_stat "Backed up database: $(basename "$db_file")"
        fi
    done
    
    # JSON data files  
    for json_file in "$PROJECT_ROOT"/data/*.json "$PROJECT_ROOT"/*.json; do
        if [ -f "$json_file" ] && [[ $(basename "$json_file") != *"test"* ]]; then
            cp "$json_file" "$backup_dir/data/"
            log_stat "Backed up data file: $(basename "$json_file")"
        fi
    done
    
    # Export directories
    if [ -d "$PROJECT_ROOT/exports" ]; then
        tar -czf "$backup_dir/data/exports_$(date +%Y%m%d_%H%M%S).tar.gz" \
            -C "$PROJECT_ROOT" exports/
        log_stat "Backed up exports directory"
    fi
    
    log_stat "Data backup completed successfully"
}

backup_remote() {
    local backup_dir=$1
    log_info "Creating remote backup to VPS..."
    
    # Test SSH connectivity
    if ! ssh -o ConnectTimeout=10 "$REMOTE_BACKUP_HOST" "echo 'SSH connection test'" >/dev/null 2>&1; then
        log_error "Cannot connect to remote host: $REMOTE_BACKUP_HOST"
        return 1
    fi
    
    # Create remote backup directory
    ssh "$REMOTE_BACKUP_HOST" "mkdir -p $REMOTE_BACKUP_PATH/$(date +%Y%m%d)"
    
    # Create local backup first
    backup_critical "$backup_dir"
    
    # Sync to remote
    log_info "Syncing backup to remote host..."
    rsync -av --progress "$backup_dir/" "$REMOTE_BACKUP_HOST:$REMOTE_BACKUP_PATH/$(date +%Y%m%d)/"
    
    log_stat "Remote backup completed successfully"
}

backup_auto() {
    local backup_dir=$1
    log_info "Creating automatic backup based on system state..."
    
    # Determine backup type based on system state
    local backup_type="critical"
    
    # Check if we have enough disk space for full backup
    if [ -d "$PROJECT_ROOT" ]; then
        project_size=$(du -s "$PROJECT_ROOT" | cut -f1)
        available_space=$(df "$BACKUP_ROOT" | awk 'NR==2 {print $4}')
        
        if [ "$available_space" -gt $((project_size * 3)) ]; then
            backup_type="full"
            log_info "Sufficient space available, performing full backup"
        else
            log_warn "Limited space available, performing critical backup only"
        fi
    fi
    
    # Check if it's been more than a day since last backup
    last_backup=$(find "$BACKUP_ROOT" -name "backup_*" -type d -mtime -1 | wc -l)
    if [ "$last_backup" -eq 0 ]; then
        log_info "No recent backups found, ensuring comprehensive backup"
        backup_type="full"
    fi
    
    # Perform the determined backup type
    case $backup_type in
        "full")
            backup_full "$backup_dir"
            ;;
        "critical")
            backup_critical "$backup_dir"
            ;;
    esac
    
    log_stat "Automatic backup ($backup_type) completed successfully"
}

verify_backup() {
    local backup_dir=$1
    log_info "Verifying backup integrity..."
    
    local verification_failed=0
    
    # Verify compressed files
    for tar_file in "$backup_dir"/*/*.tar.gz; do
        if [ -f "$tar_file" ]; then
            if tar -tzf "$tar_file" >/dev/null 2>&1; then
                log_stat "✓ $(basename "$tar_file") - integrity verified"
            else
                log_error "✗ $(basename "$tar_file") - corrupted"
                verification_failed=1
            fi
        fi
    done
    
    # Verify data files
    for data_file in "$backup_dir"/data/*; do
        if [ -f "$data_file" ] && [ ! "${data_file##*.}" = "gz" ]; then
            if [ -r "$data_file" ]; then
                log_stat "✓ $(basename "$data_file") - readable"
            else
                log_error "✗ $(basename "$data_file") - not readable"
                verification_failed=1
            fi
        fi
    done
    
    if [ $verification_failed -eq 0 ]; then
        log_stat "All backup files verified successfully"
        return 0
    else
        log_error "Backup verification failed"
        return 1
    fi
}

encrypt_backup() {
    local backup_dir=$1
    log_info "Encrypting backup files..."
    
    if ! command -v gpg >/dev/null 2>&1; then
        log_error "GPG not found. Cannot encrypt backups."
        return 1
    fi
    
    # Encrypt all tar.gz files
    for file in "$backup_dir"/*/*.tar.gz; do
        if [ -f "$file" ]; then
            gpg --batch --yes --trust-model always --cipher-algo AES256 --compress-algo 2 --symmetric --output "${file}.gpg" "$file"
            if [ $? -eq 0 ]; then
                rm "$file"
                log_stat "Encrypted: $(basename "$file")"
            else
                log_error "Failed to encrypt: $(basename "$file")"
            fi
        fi
    done
    
    log_stat "Backup encryption completed"
}

cleanup_old_backups() {
    local keep_days=${1:-7}
    log_info "Cleaning up backups older than $keep_days days..."
    
    if [ ! -d "$BACKUP_ROOT" ]; then
        log_warn "Backup root directory doesn't exist: $BACKUP_ROOT"
        return 0
    fi
    
    local deleted_count=0
    
    # Find and remove old backup directories
    while IFS= read -r -d '' backup_dir; do
        rm -rf "$backup_dir"
        deleted_count=$((deleted_count + 1))
        log_stat "Removed old backup: $(basename "$backup_dir")"
    done < <(find "$BACKUP_ROOT" -name "backup_*" -type d -mtime +$keep_days -print0 2>/dev/null)
    
    log_stat "Cleanup completed: $deleted_count old backups removed"
}

create_backup_manifest() {
    local backup_dir=$1
    local manifest_file="$backup_dir/BACKUP_MANIFEST.txt"
    
    log_info "Creating backup manifest..."
    
    {
        echo "Virtuoso CCXT Backup Manifest"
        echo "============================="
        echo "Created: $(date)"
        echo "Backup Directory: $backup_dir"
        echo "System: $(uname -a)"
        echo ""
        echo "Contents:"
        echo "--------"
        find "$backup_dir" -type f -exec ls -lh {} \; | awk '{print $9 " (" $5 ")"}'
        echo ""
        echo "Total Size: $(du -sh "$backup_dir" | cut -f1)"
        echo "File Count: $(find "$backup_dir" -type f | wc -l)"
    } > "$manifest_file"
    
    log_stat "Manifest created: $manifest_file"
}

# Main execution
main() {
    local backup_type=""
    local encrypt=false
    local verify=false
    local cleanup=false
    local compress=true
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            critical|full|config|data|remote|auto)
                backup_type=$1
                shift
                ;;
            --encrypt)
                encrypt=true
                shift
                ;;
            --verify)
                verify=true
                shift
                ;;
            --cleanup)
                cleanup=true
                shift
                ;;
            --no-compress)
                compress=false
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
    
    if [ -z "$backup_type" ]; then
        log_error "Backup type not specified"
        show_usage
        exit 1
    fi
    
    # Create timestamped backup directory
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="$BACKUP_ROOT/backup_${backup_type}_$TIMESTAMP"
    
    log_info "Starting $backup_type backup..."
    log_info "Backup location: $BACKUP_DIR"
    
    # Create backup structure
    create_backup_structure "$BACKUP_DIR"
    
    # Perform backup based on type
    case $backup_type in
        "critical")
            backup_critical "$BACKUP_DIR"
            ;;
        "full")
            backup_full "$BACKUP_DIR"
            ;;
        "config")
            backup_config "$BACKUP_DIR"
            ;;
        "data")
            backup_data "$BACKUP_DIR"
            ;;
        "remote")
            backup_remote "$BACKUP_DIR"
            ;;
        "auto")
            backup_auto "$BACKUP_DIR"
            ;;
    esac
    
    # Create manifest
    create_backup_manifest "$BACKUP_DIR"
    
    # Post-processing options
    if [ "$encrypt" = true ]; then
        encrypt_backup "$BACKUP_DIR"
    fi
    
    if [ "$verify" = true ]; then
        verify_backup "$BACKUP_DIR"
    fi
    
    if [ "$cleanup" = true ]; then
        cleanup_old_backups
    fi
    
    # Final summary
    BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
    FILE_COUNT=$(find "$BACKUP_DIR" -type f | wc -l)
    
    echo ""
    log_stat "🎉 Backup completed successfully!"
    log_stat "📁 Location: $BACKUP_DIR"
    log_stat "📊 Size: $BACKUP_SIZE ($FILE_COUNT files)"
    log_stat "🕐 Duration: Started at $TIMESTAMP"
    
    # Show how to restore
    echo ""
    log_info "To restore from this backup:"
    log_info "  Source Code: tar -xzf $BACKUP_DIR/source/source_code_*.tar.gz"
    log_info "  Config:      tar -xzf $BACKUP_DIR/config/configurations_*.tar.gz"
    log_info "  Full Guide:  cat $BACKUP_DIR/BACKUP_MANIFEST.txt"
}

main "$@"
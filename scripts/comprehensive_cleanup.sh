#!/bin/bash
#############################################################################
# Comprehensive Cleanup Script for Virtuoso CCXT Trading System
# Handles both local and VPS cleanup operations with safety measures
#############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/cleanup_$(date +%Y%m%d_%H%M%S).log"

# Configuration
LOCAL_CLEANUP=${LOCAL_CLEANUP:-true}
VPS_CLEANUP=${VPS_CLEANUP:-false}
DRY_RUN=${DRY_RUN:-false}
VPS_HOST=${VPS_HOST:-"linuxuser@5.223.63.4"}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}
LOG_RETENTION_DAYS=${LOG_RETENTION_DAYS:-30}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

OPTIONS:
    -l, --local-only     Run local cleanup only (default: true)
    -v, --vps-only       Run VPS cleanup only
    -b, --both           Run both local and VPS cleanup
    -d, --dry-run        Show what would be done without executing
    -h, --help           Show this help message

ENVIRONMENT VARIABLES:
    VPS_HOST                 VPS connection string (default: linuxuser@5.223.63.4)
    BACKUP_RETENTION_DAYS    Days to keep backups (default: 7)
    LOG_RETENTION_DAYS       Days to keep logs (default: 30)
    DRY_RUN                  Set to true for dry run (default: false)

EXAMPLES:
    $0 --local-only          # Clean local files only
    $0 --vps-only            # Clean VPS files only
    $0 --both                # Clean both local and VPS
    $0 --dry-run --both      # Show what would be cleaned
EOF
}

check_disk_usage() {
    local path="$1"
    local threshold=${2:-90}

    if [[ "$path" == *":"* ]]; then
        # Remote path
        local usage=$(ssh "$VPS_HOST" "df -P '$path' | awk 'NR==2 {print \$5}' | tr -d '%'" 2>/dev/null || echo "0")
    else
        # Local path
        local usage=$(df -P "$path" | awk 'NR==2 {print $5}' | tr -d '%')
    fi

    echo "$usage"
}

cleanup_local_logs() {
    log "Starting local log cleanup..."

    local logs_dir="$PROJECT_ROOT/logs"
    cd "$logs_dir"

    # Handle the massive ccxt_run.log file
    if [[ -f "ccxt_run.log" ]]; then
        local size=$(du -sh ccxt_run.log | cut -f1)
        warn "Found large ccxt_run.log file: $size"

        if [[ "$DRY_RUN" == "false" ]]; then
            # Archive the current log with timestamp
            local archive_name="ccxt_run_$(date +%Y%m%d_%H%M%S).log.gz"
            log "Archiving ccxt_run.log to $archive_name"
            gzip -c ccxt_run.log > "archived_logs/$archive_name" || mkdir -p archived_logs && gzip -c ccxt_run.log > "archived_logs/$archive_name"

            # Truncate the active log
            truncate -s 0 ccxt_run.log
            success "Archived and truncated ccxt_run.log"
        else
            log "[DRY RUN] Would archive and truncate ccxt_run.log ($size)"
        fi
    fi

    # Clean old log files
    log "Cleaning logs older than $LOG_RETENTION_DAYS days..."
    if [[ "$DRY_RUN" == "false" ]]; then
        find . -name "*.log.*" -type f -mtime +$LOG_RETENTION_DAYS -delete 2>/dev/null || true
        find . -name "*.gz" -type f -mtime +$LOG_RETENTION_DAYS -delete 2>/dev/null || true
        find . -name "*test*.log" -size +50M -mtime +7 -delete 2>/dev/null || true
    else
        find . -name "*.log.*" -type f -mtime +$LOG_RETENTION_DAYS -exec echo "[DRY RUN] Would delete: {}" \; 2>/dev/null || true
        find . -name "*.gz" -type f -mtime +$LOG_RETENTION_DAYS -exec echo "[DRY RUN] Would delete: {}" \; 2>/dev/null || true
    fi

    success "Local log cleanup completed"
}

cleanup_local_archives() {
    log "Starting local archive cleanup..."

    local archive_dir="$PROJECT_ROOT/archive"
    if [[ -d "$archive_dir" ]]; then
        # Remove deeply nested archive structures older than 30 days
        if [[ "$DRY_RUN" == "false" ]]; then
            find "$archive_dir" -name "*cleanup*" -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true
            find "$archive_dir" -name "*archived*" -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true
        else
            find "$archive_dir" -name "*cleanup*" -type d -mtime +30 -exec echo "[DRY RUN] Would remove archive: {}" \; 2>/dev/null || true
        fi
    fi

    success "Local archive cleanup completed"
}

cleanup_local_reports() {
    log "Starting local reports cleanup..."

    local reports_dir="$PROJECT_ROOT/reports"
    if [[ -d "$reports_dir" ]]; then
        # Clean reports older than 14 days
        if [[ "$DRY_RUN" == "false" ]]; then
            find "$reports_dir" -type f -mtime +14 -delete 2>/dev/null || true
            find "$reports_dir" -type d -empty -delete 2>/dev/null || true
        else
            find "$reports_dir" -type f -mtime +14 -exec echo "[DRY RUN] Would delete: {}" \; 2>/dev/null || true
        fi
    fi

    success "Local reports cleanup completed"
}

cleanup_vps() {
    log "Starting VPS cleanup..."

    # Check VPS connectivity
    if ! ssh "$VPS_HOST" "echo 'VPS connection test'" >/dev/null 2>&1; then
        error "Cannot connect to VPS: $VPS_HOST"
        return 1
    fi

    # Get VPS disk usage
    local vps_usage=$(check_disk_usage "/home/linuxuser/trading" 90)
    log "VPS disk usage: ${vps_usage}%"

    # Clean VPS backups
    log "Cleaning VPS backups older than $BACKUP_RETENTION_DAYS days..."
    if [[ "$DRY_RUN" == "false" ]]; then
        ssh "$VPS_HOST" "
            cd /home/linuxuser/trading
            # Remove uncompressed backup directories
            find . -name '*backup*' -type d -mtime +1 -exec rm -rf {} + 2>/dev/null || true
            # Remove old compressed backups
            find . -name '*backup*.tar.gz' -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null || true
            # Keep only last 3 backups
            ls -t *backup*.tar.gz 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
        "
    else
        ssh "$VPS_HOST" "
            cd /home/linuxuser/trading
            find . -name '*backup*' -type d -mtime +1 -exec echo '[DRY RUN] Would remove backup dir: {}' \; 2>/dev/null || true
            find . -name '*backup*.tar.gz' -mtime +$BACKUP_RETENTION_DAYS -exec echo '[DRY RUN] Would delete: {}' \; 2>/dev/null || true
        "
    fi

    # Clean VPS logs
    log "Cleaning VPS logs..."
    if [[ "$DRY_RUN" == "false" ]]; then
        ssh "$VPS_HOST" "
            cd /home/linuxuser/trading/Virtuoso_ccxt
            # Rotate large main.log files
            if [[ -f logs/main.log && \$(du -m logs/main.log | cut -f1) -gt 100 ]]; then
                gzip logs/main.log && mv logs/main.log.gz logs/main_\$(date +%Y%m%d_%H%M%S).log.gz
                touch logs/main.log
            fi
            # Remove old service logs
            find logs/ -name '*.log.gz' -mtime +$LOG_RETENTION_DAYS -delete 2>/dev/null || true
        "
    else
        ssh "$VPS_HOST" "
            cd /home/linuxuser/trading/Virtuoso_ccxt
            find logs/ -name '*.log.gz' -mtime +$LOG_RETENTION_DAYS -exec echo '[DRY RUN] Would delete: {}' \; 2>/dev/null || true
        "
    fi

    success "VPS cleanup completed"
}

show_cleanup_summary() {
    log "=== CLEANUP SUMMARY ==="

    # Local summary
    if [[ "$LOCAL_CLEANUP" == "true" ]]; then
        local logs_size=$(du -sh "$PROJECT_ROOT/logs" 2>/dev/null | cut -f1 || echo "N/A")
        local archive_size=$(du -sh "$PROJECT_ROOT/archive" 2>/dev/null | cut -f1 || echo "N/A")
        local reports_size=$(du -sh "$PROJECT_ROOT/reports" 2>/dev/null | cut -f1 || echo "N/A")

        log "Local directories after cleanup:"
        log "  Logs: $logs_size"
        log "  Archive: $archive_size"
        log "  Reports: $reports_size"
    fi

    # VPS summary
    if [[ "$VPS_CLEANUP" == "true" ]]; then
        local vps_usage_after=$(check_disk_usage "/home/linuxuser/trading" 90)
        log "VPS disk usage after cleanup: ${vps_usage_after}%"
    fi

    success "Cleanup operations completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--local-only)
            LOCAL_CLEANUP=true
            VPS_CLEANUP=false
            shift
            ;;
        -v|--vps-only)
            LOCAL_CLEANUP=false
            VPS_CLEANUP=true
            shift
            ;;
        -b|--both)
            LOCAL_CLEANUP=true
            VPS_CLEANUP=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log "Starting comprehensive cleanup..."
    log "Configuration:"
    log "  Local cleanup: $LOCAL_CLEANUP"
    log "  VPS cleanup: $VPS_CLEANUP"
    log "  Dry run: $DRY_RUN"
    log "  Backup retention: $BACKUP_RETENTION_DAYS days"
    log "  Log retention: $LOG_RETENTION_DAYS days"

    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"

    if [[ "$LOCAL_CLEANUP" == "true" ]]; then
        cleanup_local_logs
        cleanup_local_archives
        cleanup_local_reports
    fi

    if [[ "$VPS_CLEANUP" == "true" ]]; then
        cleanup_vps
    fi

    show_cleanup_summary
}

# Execute main function
main "$@"
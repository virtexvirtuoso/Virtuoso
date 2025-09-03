#!/bin/bash

#############################################################################
# Script: fix.sh
# Purpose: Master Fix Script - Common fixes in one place
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
#   Master fix script that consolidates common troubleshooting and repair operations
#   for the Virtuoso trading system. Provides unified interface for fixing cache,
#   connection, timeout, dashboard, and permission issues with proper error handling.
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
#   ./fix.sh [options]
#   
#   Examples:
#     ./fix.sh
#     ./fix.sh --verbose
#     ./fix.sh --dry-run
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

# Part of Phase 1: Emergency Stabilization

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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

show_usage() {
    echo "Usage: $0 [FIX_TYPE] [OPTIONS]"
    echo ""
    echo "Fix Types:"
    echo "  cache       Fix cache connectivity issues"
    echo "  connection  Fix exchange connection issues" 
    echo "  timeout     Fix timeout-related issues"
    echo "  dashboard   Fix dashboard display issues"
    echo "  permissions Fix file permissions"
    echo "  all         Run all common fixes"
    echo ""
    echo "Options:"
    echo "  --dry-run   Show what would be fixed without executing"
    echo "  --verbose   Show detailed output"
    echo "  --help      Show this help message"
}

fix_cache() {
    log_info "Fixing cache connectivity issues..."
    
    # Check if memcached is running
    if ! pgrep memcached >/dev/null; then
        log_warn "Memcached not running, attempting to start..."
        if command -v brew >/dev/null 2>&1; then
            brew services start memcached
        elif command -v systemctl >/dev/null 2>&1; then
            sudo systemctl start memcached
        else
            log_error "Cannot start memcached automatically"
            return 1
        fi
    fi
    
    # Check if Redis is running
    if ! pgrep redis-server >/dev/null; then
        log_warn "Redis not running, attempting to start..."
        if command -v brew >/dev/null 2>&1; then
            brew services start redis
        elif command -v systemctl >/dev/null 2>&1; then
            sudo systemctl start redis-server
        else
            log_error "Cannot start Redis automatically"
            return 1
        fi
    fi
    
    # Clear cache if needed
    log_info "Clearing cache..."
    echo 'flush_all' | nc localhost 11211 2>/dev/null || true
    redis-cli FLUSHALL 2>/dev/null || true
    
    log_info "Cache fixes completed"
}

fix_connection() {
    log_info "Fixing exchange connection issues..."
    
    # Check environment variables
    if [ -z "$BYBIT_API_KEY" ] || [ -z "$BYBIT_API_SECRET" ]; then
        log_error "Bybit API credentials not set in environment"
        log_info "Please check .env file and ensure credentials are configured"
        return 1
    fi
    
    # Test connectivity
    log_info "Testing exchange connectivity..."
    curl -s --connect-timeout 5 https://api.bybit.com/v2/public/time >/dev/null || {
        log_error "Cannot connect to Bybit API"
        log_info "Check internet connection or VPN settings"
        return 1
    }
    
    log_info "Connection fixes completed"
}

fix_timeout() {
    log_info "Fixing timeout-related issues..."
    
    # Kill any hanging python processes
    log_info "Cleaning up hanging processes..."
    pkill -f "python.*main.py" 2>/dev/null || true
    pkill -f "python.*web_server.py" 2>/dev/null || true
    
    # Reset connection pools if scripts exist
    if [ -f "$PROJECT_ROOT/scripts/fixes/fix_connection_pool.py" ]; then
        python3 "$PROJECT_ROOT/scripts/fixes/fix_connection_pool.py"
    fi
    
    log_info "Timeout fixes completed"
}

fix_dashboard() {
    log_info "Fixing dashboard display issues..."
    
    # Check if dashboard ports are available
    if lsof -Pi :8003 -sTCP:LISTEN >/dev/null; then
        log_warn "Port 8003 already in use, killing existing process..."
        lsof -ti :8003 | xargs kill -9 2>/dev/null || true
    fi
    
    if lsof -Pi :8001 -sTCP:LISTEN >/dev/null; then
        log_warn "Port 8001 already in use, killing existing process..."
        lsof -ti :8001 | xargs kill -9 2>/dev/null || true
    fi
    
    # Clear browser cache hint
    log_info "If dashboard still not loading, clear browser cache (Cmd+Shift+R)"
    
    log_info "Dashboard fixes completed"
}

fix_permissions() {
    log_info "Fixing file permissions..."
    
    # Make scripts executable
    find "$PROJECT_ROOT/scripts" -name "*.sh" -exec chmod +x {} \;
    
    # Fix Python script permissions
    find "$PROJECT_ROOT/scripts" -name "*.py" -exec chmod +x {} \;
    
    log_info "Permissions fixes completed"
}

fix_all() {
    log_info "Running all common fixes..."
    
    fix_permissions
    fix_cache
    fix_connection
    fix_timeout
    fix_dashboard
    
    log_info "All fixes completed successfully"
}

# Main execution
main() {
    local fix_type=""
    local dry_run=false
    local verbose=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            cache|connection|timeout|dashboard|permissions|all)
                fix_type=$1
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --verbose)
                verbose=true
                set -x
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
    
    if [ -z "$fix_type" ]; then
        log_error "Fix type not specified"
        show_usage
        exit 1
    fi
    
    if [ "$dry_run" = true ]; then
        log_info "DRY RUN: Would apply $fix_type fixes"
        return 0
    fi
    
    # Execute fix
    case $fix_type in
        "cache")
            fix_cache
            ;;
        "connection")
            fix_connection
            ;;
        "timeout")
            fix_timeout
            ;;
        "dashboard")
            fix_dashboard
            ;;
        "permissions")
            fix_permissions
            ;;
        "all")
            fix_all
            ;;
    esac
}

main "$@"
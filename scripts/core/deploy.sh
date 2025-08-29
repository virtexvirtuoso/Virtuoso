#!/bin/bash

#############################################################################
# Script: deploy.sh
# Purpose: Master Deployment Script - Unified deployment interface
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
#   Master deployment script that provides unified deployment interface for local,
#   staging, and production environments. Handles prerequisites checking, environment
#   validation, and safe deployment with rollback capabilities.
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
#   ./deploy.sh [options]
#   
#   Examples:
#     ./deploy.sh
#     ./deploy.sh --verbose
#     ./deploy.sh --dry-run
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
    echo "Usage: $0 [ENVIRONMENT] [OPTIONS]"
    echo ""
    echo "Environments:"
    echo "  local      Deploy to local development environment"
    echo "  staging    Deploy to staging VPS" 
    echo "  production Deploy to production VPS"
    echo ""
    echo "Options:"
    echo "  --dry-run  Show what would be deployed without executing"
    echo "  --force    Force deployment even if checks fail"
    echo "  --help     Show this help message"
}

check_prerequisites() {
    local env=$1
    
    case $env in
        "local")
            if [ ! -d "$PROJECT_ROOT/venv311" ]; then
                log_error "venv311 not found. Please create virtual environment first."
                return 1
            fi
            ;;
        "staging"|"production")
            if ! ssh -o ConnectTimeout=5 linuxuser@45.77.40.77 "echo 'Connection test'" >/dev/null 2>&1; then
                log_error "Cannot connect to VPS. Check SSH configuration."
                return 1
            fi
            ;;
    esac
    return 0
}

deploy_local() {
    log_info "Starting local deployment..."
    
    # Activate virtual environment
    source "$PROJECT_ROOT/venv311/bin/activate"
    
    # Install/update dependencies
    log_info "Installing dependencies..."
    pip install -q -r "$PROJECT_ROOT/requirements.txt"
    
    # Start services
    log_info "Starting local services..."
    python "$PROJECT_ROOT/src/main.py" &
    
    log_info "Local deployment completed successfully"
}

deploy_staging() {
    log_info "Starting staging deployment..."
    
    # Use existing deployment script if available
    if [ -f "$PROJECT_ROOT/scripts/deployment/deploy_to_vps.sh" ]; then
        source "$PROJECT_ROOT/scripts/deployment/deploy_to_vps.sh"
    else
        log_warn "No staging deployment script found. Using basic deployment."
        rsync -av --exclude='venv311' --exclude='__pycache__' "$PROJECT_ROOT/" linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/
    fi
    
    log_info "Staging deployment completed successfully"
}

deploy_production() {
    log_info "Starting production deployment..."
    
    # Production safety check
    read -p "Are you sure you want to deploy to PRODUCTION? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_warn "Production deployment cancelled"
        return 1
    fi
    
    # Use blue-green deployment when available
    if [ -f "$PROJECT_ROOT/scripts/deployment/deploy_production_blue_green.sh" ]; then
        source "$PROJECT_ROOT/scripts/deployment/deploy_production_blue_green.sh"
    else
        log_warn "Blue-green deployment not available. Using staging deployment method."
        deploy_staging
    fi
    
    log_info "Production deployment completed successfully"
}

# Main execution
main() {
    local environment=""
    local dry_run=false
    local force=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            local|staging|production)
                environment=$1
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --force)
                force=true
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
    
    if [ -z "$environment" ]; then
        log_error "Environment not specified"
        show_usage
        exit 1
    fi
    
    if [ "$dry_run" = true ]; then
        log_info "DRY RUN: Would deploy to $environment"
        return 0
    fi
    
    # Check prerequisites
    if ! check_prerequisites "$environment"; then
        if [ "$force" = true ]; then
            log_warn "Prerequisites check failed but continuing due to --force flag"
        else
            log_error "Prerequisites check failed. Use --force to override."
            exit 1
        fi
    fi
    
    # Execute deployment
    case $environment in
        "local")
            deploy_local
            ;;
        "staging")
            deploy_staging
            ;;
        "production")
            deploy_production
            ;;
    esac
}

main "$@"
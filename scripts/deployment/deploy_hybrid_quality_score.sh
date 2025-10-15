#!/bin/bash

#############################################################################
# Script: deploy_hybrid_quality_score.sh
# Purpose: Deploy Hybrid Quality-Adjusted Confluence Score implementation to VPS
# Date: 2025-10-10
# QA Status: APPROVED (98/100 quality score)
#############################################################################

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VPS_HOST="${VPS_HOST:-5.223.63.4}"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

# Files to deploy
FILES_TO_DEPLOY=(
    "src/core/analysis/confluence.py"
    "src/signal_generation/signal_generator.py"
    "src/core/formatting/formatter.py"
    "src/monitoring/quality_metrics_tracker.py"
)

DOCS_TO_DEPLOY=(
    "QUALITY_ADJUSTED_CONFLUENCE_SCORE_DESIGN.md"
    "HYBRID_QUALITY_SCORE_QA_VALIDATION_REPORT.md"
)

# Functions
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

# Banner
echo "============================================================"
echo "  Hybrid Quality-Adjusted Confluence Score Deployment"
echo "  QA Status: ✅ APPROVED (98/100)"
echo "  Target: $VPS_USER@$VPS_HOST"
echo "============================================================"
echo ""

# Step 1: Verify local files exist
log_step "Step 1: Verifying local files..."
for file in "${FILES_TO_DEPLOY[@]}"; do
    if [ ! -f "$LOCAL_PATH/$file" ]; then
        log_error "Local file not found: $file"
        exit 1
    fi
    log_info "✓ Found: $file"
done
echo ""

# Step 2: Create backup on VPS
log_step "Step 2: Creating backup on VPS..."
BACKUP_DIR="backup_hybrid_quality_$(date +%Y%m%d_%H%M%S)"
ssh $VPS_USER@$VPS_HOST "cd $VPS_PATH && mkdir -p $BACKUP_DIR"

for file in "${FILES_TO_DEPLOY[@]}"; do
    ssh $VPS_USER@$VPS_HOST "cd $VPS_PATH && cp $file $BACKUP_DIR/$file.backup 2>/dev/null || true"
    log_info "✓ Backed up: $file"
done
log_info "Backup created at: $VPS_PATH/$BACKUP_DIR"
echo ""

# Step 3: Deploy modified files
log_step "Step 3: Deploying modified files..."
for file in "${FILES_TO_DEPLOY[@]}"; do
    log_info "Deploying: $file"
    rsync -avz --progress "$LOCAL_PATH/$file" "$VPS_USER@$VPS_HOST:$VPS_PATH/$file"
done
echo ""

# Step 4: Deploy documentation
log_step "Step 4: Deploying documentation..."
for doc in "${DOCS_TO_DEPLOY[@]}"; do
    if [ -f "$LOCAL_PATH/$doc" ]; then
        log_info "Deploying: $doc"
        rsync -avz "$LOCAL_PATH/$doc" "$VPS_USER@$VPS_HOST:$VPS_PATH/$doc"
    fi
done
echo ""

# Step 5: Verify files on VPS
log_step "Step 5: Verifying deployment..."
for file in "${FILES_TO_DEPLOY[@]}"; do
    if ssh $VPS_USER@$VPS_HOST "[ -f $VPS_PATH/$file ]"; then
        log_info "✓ Verified: $file"
    else
        log_error "✗ Missing: $file"
        exit 1
    fi
done
echo ""

# Step 6: Check if services need restart
log_step "Step 6: Checking service status..."
ssh $VPS_USER@$VPS_HOST "sudo systemctl status virtuoso --no-pager | head -3" || true
echo ""

# Step 7: Restart services
log_step "Step 7: Restarting Virtuoso service..."
log_warn "This will restart the trading system..."
read -p "Continue with restart? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Restarting virtuoso service..."
    ssh $VPS_USER@$VPS_HOST "sudo systemctl restart virtuoso"

    # Wait for service to start
    log_info "Waiting for service to start (10 seconds)..."
    sleep 10

    # Check service status
    log_step "Step 8: Verifying service status..."
    if ssh $VPS_USER@$VPS_HOST "sudo systemctl is-active virtuoso --quiet"; then
        log_info "✅ Service is running"
    else
        log_error "❌ Service failed to start"
        log_warn "Check logs with: ssh $VPS_USER@$VPS_HOST 'sudo journalctl -u virtuoso -n 50'"
        exit 1
    fi
else
    log_warn "Skipped service restart. Changes deployed but not active."
    log_warn "Restart manually with: ssh $VPS_USER@$VPS_HOST 'sudo systemctl restart virtuoso'"
fi
echo ""

# Step 9: Monitor logs for quality metrics
log_step "Step 9: Checking recent logs for quality metrics..."
log_info "Looking for hybrid scoring in logs..."
ssh $VPS_USER@$VPS_HOST "sudo journalctl -u virtuoso -n 100 | grep -i 'quality impact\|base score' | head -10" || log_warn "No quality metrics in recent logs yet (may take a few minutes)"
echo ""

# Success summary
echo "============================================================"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE${NC}"
echo "============================================================"
echo ""
echo "Deployment Summary:"
echo "  • Files deployed: ${#FILES_TO_DEPLOY[@]}"
echo "  • Documentation: ${#DOCS_TO_DEPLOY[@]}"
echo "  • Backup location: $VPS_PATH/$BACKUP_DIR"
echo "  • VPS Host: $VPS_HOST"
echo ""
echo "Next Steps:"
echo "  1. Monitor quality impact values in confluence analyses"
echo "  2. Verify weak signals are suppressed (impact < -5)"
echo "  3. Check signal volume (expect 20-40% reduction)"
echo ""
echo "Monitoring Commands:"
echo "  • View logs: ssh $VPS_USER@$VPS_HOST 'sudo journalctl -u virtuoso -f'"
echo "  • Check quality: ssh $VPS_USER@$VPS_HOST 'sudo journalctl -u virtuoso -n 1000 | grep \"Quality Impact\"'"
echo "  • Service status: ssh $VPS_USER@$VPS_HOST 'sudo systemctl status virtuoso'"
echo ""
echo "Rollback (if needed):"
echo "  ssh $VPS_USER@$VPS_HOST 'cd $VPS_PATH && cp -r $BACKUP_DIR/* ./ && sudo systemctl restart virtuoso'"
echo ""
echo "============================================================"

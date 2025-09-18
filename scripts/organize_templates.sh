#!/bin/bash

# Dashboard Templates Organization Script
# Based on DASHBOARD_TEMPLATES_AUDIT.md
# Created: 2025-09-15

set -e

echo "======================================"
echo "Dashboard Templates Organization Script"
echo "======================================"
echo ""

# Configuration
TEMPLATES_DIR="/home/linuxuser/trading/Virtuoso_ccxt/src/dashboard/templates"
BACKUP_DIR="/home/linuxuser/trading/Virtuoso_ccxt/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="templates_backup_${TIMESTAMP}.tar.gz"

echo "Step 1: Creating backup of all templates..."
ssh vps "mkdir -p ${BACKUP_DIR}"
ssh vps "cd ${TEMPLATES_DIR} && tar -czf ${BACKUP_DIR}/${BACKUP_FILE} *.html"
echo "✅ Backup created: ${BACKUP_DIR}/${BACKUP_FILE}"
echo ""

echo "Step 2: Creating archive folder structure..."
ssh vps "cd ${TEMPLATES_DIR} && mkdir -p archive/{admin,dashboard_variants,mobile_variants,specialized}"
echo "✅ Archive folders created"
echo ""

echo "Step 3: Moving unused templates to archive..."
echo ""

# Admin Templates
echo "Moving admin templates..."
ssh vps "cd ${TEMPLATES_DIR} && mv -v admin_config_editor.html archive/admin/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v admin_config_editor_optimized.html archive/admin/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v admin_dashboard.html archive/admin/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v admin_dashboard_v2.html archive/admin/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v admin_login.html archive/admin/ 2>/dev/null || true"

# Dashboard Variants
echo "Moving dashboard variants..."
ssh vps "cd ${TEMPLATES_DIR} && mv -v dashboard.html archive/dashboard_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v dashboard_beta_analysis.html archive/dashboard_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v dashboard_market_analysis.html archive/dashboard_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v dashboard_phase1.html archive/dashboard_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v dashboard_phase2_cache.html archive/dashboard_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v dashboard_selector.html archive/dashboard_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v dashboard_v10.html archive/dashboard_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v confluence_analysis.html archive/dashboard_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v market_breadth_improved.html archive/dashboard_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v educational_guide.html archive/dashboard_variants/ 2>/dev/null || true"

# Mobile Variants
echo "Moving mobile variants..."
ssh vps "cd ${TEMPLATES_DIR} && mv -v dashboard_mobile_v1_enhanced_backup.html archive/mobile_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v dashboard_mobile_v1_improved.html archive/mobile_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v dashboard_mobile_v1_improved_with_lucide_backup.html archive/mobile_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v dashboard_mobile_v1_updated.html archive/mobile_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v mobile_beta_integration.html archive/mobile_variants/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v login_mobile.html archive/mobile_variants/ 2>/dev/null || true"

# Specialized Pages
echo "Moving specialized pages..."
ssh vps "cd ${TEMPLATES_DIR} && mv -v enhanced_liquidation_variant1.html archive/specialized/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v resilience_monitor.html archive/specialized/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v service_health.html archive/specialized/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v smart_money_liquidation_card_demo.html archive/specialized/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v smart_money_liquidation_gallery.html archive/specialized/ 2>/dev/null || true"
ssh vps "cd ${TEMPLATES_DIR} && mv -v system_monitoring.html archive/specialized/ 2>/dev/null || true"

echo ""
echo "✅ Templates moved to archive"
echo ""

echo "Step 4: Verifying active templates remain..."
echo ""
echo "Active templates in main folder:"
ssh vps "cd ${TEMPLATES_DIR} && ls -1 *.html 2>/dev/null | grep -v archive || echo 'No HTML files found'"
echo ""

echo "Step 5: Counting archived templates..."
ssh vps "cd ${TEMPLATES_DIR}/archive && find . -name '*.html' | wc -l" | read count
echo "Total archived: ${count} templates"
echo ""

echo "Step 6: Testing active routes..."
echo ""

# Test each active route
test_route() {
    local route=$1
    local name=$2
    echo -n "Testing $name ($route): "
    if curl -s -o /dev/null -w "%{http_code}" "http://${VPS_HOST}:8002$route" | grep -q "200"; then
        echo "✅ OK"
    else
        echo "❌ Failed"
    fi
}

test_route "/" "Main Dashboard"
test_route "/mobile" "Mobile Dashboard"
test_route "/links" "Links Page"
test_route "/paper" "Paper Trading"
test_route "/education" "Education"
test_route "/api/docs" "API Docs"

echo ""
echo "======================================"
echo "✅ Template Organization Complete!"
echo "======================================"
echo ""
echo "Summary:"
echo "• Backup saved to: ${BACKUP_DIR}/${BACKUP_FILE}"
echo "• Unused templates moved to: ${TEMPLATES_DIR}/archive/"
echo "• Active templates remain in: ${TEMPLATES_DIR}/"
echo ""
echo "To restore if needed:"
echo "  ssh vps 'cd ${TEMPLATES_DIR} && tar -xzf ${BACKUP_DIR}/${BACKUP_FILE}'"
echo ""
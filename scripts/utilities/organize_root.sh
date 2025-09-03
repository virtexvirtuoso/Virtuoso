#!/bin/bash
# Virtuoso CCXT Root Directory Organization Script
# Simple shell script version for quick organization

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=============================="
echo "ROOT DIRECTORY ORGANIZATION"
echo "=============================="
echo "Project: $PROJECT_ROOT"
echo "=============================="

# Check if we're in dry-run mode
DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 DRY RUN MODE - No changes will be made"
fi

# Function to move file with git
move_with_git() {
    local src="$1"
    local dst="$2"
    local dst_dir=$(dirname "$dst")
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] git mv $src $dst"
        return
    fi
    
    # Create destination directory if it doesn't exist
    mkdir -p "$dst_dir"
    
    # Use git mv if possible, otherwise regular mv
    if git mv "$src" "$dst" 2>/dev/null; then
        echo "✅ git mv $src $dst"
    elif mv "$src" "$dst" 2>/dev/null; then
        echo "✅ mv $src $dst"
    else
        echo "❌ Failed to move $src"
    fi
}

# Function to delete file/directory
delete_item() {
    local item="$1"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] rm -rf $item"
        return
    fi
    
    if rm -rf "$item" 2>/dev/null; then
        echo "🗑️  Deleted $item"
    else
        echo "❌ Failed to delete $item"
    fi
}

echo ""
echo "PHASE 1: Moving Python scripts to scripts/"
echo "----------------------------------------"

# Python utility scripts
[[ -f "analyze_scripts.py" ]] && move_with_git "analyze_scripts.py" "scripts/analyze_scripts.py"
[[ -f "batch_document_scripts.py" ]] && move_with_git "batch_document_scripts.py" "scripts/batch_document_scripts.py"
[[ -f "test_cache_debug.py" ]] && move_with_git "test_cache_debug.py" "scripts/test_cache_debug.py"
[[ -f "test_cache_performance.py" ]] && move_with_git "test_cache_performance.py" "scripts/test_cache_performance.py"
[[ -f "test_cache_rationalization.py" ]] && move_with_git "test_cache_rationalization.py" "scripts/test_cache_rationalization.py"
[[ -f "test_di_refactored_components.py" ]] && move_with_git "test_di_refactored_components.py" "scripts/test_di_refactored_components.py"
[[ -f "test_startup.py" ]] && move_with_git "test_startup.py" "scripts/test_startup.py"

# Deployment and fix scripts
[[ -f "deploy_confluence_cache_fix.sh" ]] && move_with_git "deploy_confluence_cache_fix.sh" "scripts/deploy_confluence_cache_fix.sh"
[[ -f "deploy_di_fixes.py" ]] && move_with_git "deploy_di_fixes.py" "scripts/deploy_di_fixes.py"
[[ -f "emergency_bridge_fix.py" ]] && move_with_git "emergency_bridge_fix.py" "scripts/emergency_bridge_fix.py"
[[ -f "fix_cache_bridge_dashboard_data.py" ]] && move_with_git "fix_cache_bridge_dashboard_data.py" "scripts/fix_cache_bridge_dashboard_data.py"
[[ -f "fix_confluence_caching.py" ]] && move_with_git "fix_confluence_caching.py" "scripts/fix_confluence_caching.py"
[[ -f "fix_confluence_caching_integration.py" ]] && move_with_git "fix_confluence_caching_integration.py" "scripts/fix_confluence_caching_integration.py"

echo ""
echo "PHASE 2: Moving documentation to docs/"
echo "-------------------------------------"

# Documentation files
[[ -f "CACHE_ARCHITECTURE_CHANGES.md" ]] && move_with_git "CACHE_ARCHITECTURE_CHANGES.md" "docs/CACHE_ARCHITECTURE_CHANGES.md"
[[ -f "CACHE_BRIDGE_FIX_IMPLEMENTATION.md" ]] && move_with_git "CACHE_BRIDGE_FIX_IMPLEMENTATION.md" "docs/CACHE_BRIDGE_FIX_IMPLEMENTATION.md"
[[ -f "CACHE_ENHANCEMENT_COMPLETE.md" ]] && move_with_git "CACHE_ENHANCEMENT_COMPLETE.md" "docs/CACHE_ENHANCEMENT_COMPLETE.md"
[[ -f "CACHE_OPTIMIZATION_DEPLOYMENT_SUMMARY.md" ]] && move_with_git "CACHE_OPTIMIZATION_DEPLOYMENT_SUMMARY.md" "docs/CACHE_OPTIMIZATION_DEPLOYMENT_SUMMARY.md"
[[ -f "CACHE_RATIONALIZATION_SUMMARY_REPORT.md" ]] && move_with_git "CACHE_RATIONALIZATION_SUMMARY_REPORT.md" "docs/CACHE_RATIONALIZATION_SUMMARY_REPORT.md"
[[ -f "DEPLOYMENT_MONITORING_REPORT.md" ]] && move_with_git "DEPLOYMENT_MONITORING_REPORT.md" "docs/DEPLOYMENT_MONITORING_REPORT.md"
[[ -f "DOCUMENTATION_AUDIT_COMPREHENSIVE_2025_08_30.md" ]] && move_with_git "DOCUMENTATION_AUDIT_COMPREHENSIVE_2025_08_30.md" "docs/DOCUMENTATION_AUDIT_COMPREHENSIVE_2025_08_30.md"
[[ -f "DOCUMENTATION_REORGANIZATION_REPORT.md" ]] && move_with_git "DOCUMENTATION_REORGANIZATION_REPORT.md" "docs/DOCUMENTATION_REORGANIZATION_REPORT.md"

echo ""
echo "PHASE 3: Moving log files to logs/"
echo "---------------------------------"

# Log files
[[ -f "main_output.log" ]] && move_with_git "main_output.log" "logs/main_output.log"
[[ -f "system_startup.log" ]] && move_with_git "system_startup.log" "logs/system_startup.log"
[[ -f "deployment.log" ]] && move_with_git "deployment.log" "logs/deployment.log"

# Intelligence validation logs
for log_file in intelligence_validation_*.log; do
    [[ -f "$log_file" ]] && move_with_git "$log_file" "logs/$log_file"
done

echo ""
echo "PHASE 4: Moving reports to reports/"
echo "----------------------------------"

# Report files
[[ -f "cache_optimization_test_results.json" ]] && move_with_git "cache_optimization_test_results.json" "reports/cache_optimization_test_results.json"
[[ -f "documentation_audit_results.json" ]] && move_with_git "documentation_audit_results.json" "reports/documentation_audit_results.json"
[[ -f "documentation_validation_report.json" ]] && move_with_git "documentation_validation_report.json" "reports/documentation_validation_report.json"
[[ -f "final_complete_report.json" ]] && move_with_git "final_complete_report.json" "reports/final_complete_report.json"
[[ -f "final_report.json" ]] && move_with_git "final_report.json" "reports/final_report.json"
[[ -f "validation_report.json" ]] && move_with_git "validation_report.json" "reports/validation_report.json"

# Intelligence validation reports
for report_file in intelligence_validation_report_*.json; do
    [[ -f "$report_file" ]] && move_with_git "$report_file" "reports/$report_file"
done

echo ""
echo "PHASE 5: Moving media files to assets/"
echo "-------------------------------------"

# Media files
[[ -f "performance_analysis_charts.png" ]] && move_with_git "performance_analysis_charts.png" "assets/performance_analysis_charts.png"
[[ -f "Virtuoso | Trello.pdf" ]] && move_with_git "Virtuoso | Trello.pdf" "assets/Virtuoso_Trello.pdf"

echo ""
echo "PHASE 6: Cleaning up temporary files"
echo "-----------------------------------"

# Clean up cache and system files
[[ -d "__pycache__" ]] && delete_item "__pycache__"
[[ -f ".DS_Store" ]] && delete_item ".DS_Store"

echo ""
echo "=============================="
echo "ORGANIZATION COMPLETE!"
echo "=============================="

if [[ "$DRY_RUN" == "false" ]]; then
    echo ""
    echo "Next steps:"
    echo "1. Review changes: git status"
    echo "2. Test application: source venv311/bin/activate && python src/main.py"
    echo "3. Commit changes: git add . && git commit -m 'Organize root directory structure'"
    echo ""
    echo "If you need to rollback, use: python organize_root_directory.py --help"
else
    echo ""
    echo "This was a dry run. Run without --dry-run to execute the changes:"
    echo "./organize_root.sh"
fi

echo ""
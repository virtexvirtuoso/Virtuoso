#!/bin/bash
# Cleanup obsolete files after DATA_FLOW_AUDIT_REPORT.md implementation

echo "=========================================="
echo "🧹 Cleaning up obsolete files"
echo "=========================================="
echo ""

# Create archive directory with timestamp
ARCHIVE_DIR="archive/pre_optimization_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ARCHIVE_DIR"

echo "📦 Archive directory: $ARCHIVE_DIR"
echo ""

# Files to archive and remove (based on DATA_FLOW_AUDIT_REPORT.md)
declare -a OBSOLETE_CACHE_FILES=(
    "src/api/cache_adapter.py"
    "src/api/cache_adapter_optimized.py"
    "src/api/cache_adapter_direct_fixed.py"
)

declare -a OBSOLETE_DASHBOARD_ROUTES=(
    "src/api/routes/dashboard_backup.py"
    "src/api/routes/dashboard_cached.py"
    "src/api/routes/dashboard_fast.py"
    "src/api/routes/dashboard_optimized.py"
    "src/api/routes/dashboard_parallel.py"
    "src/api/routes/dashboard_simple.py"
    "src/api/routes/dashboard.py.backup_*"
    "src/api/routes/dashboard.py.broken_*"
    "src/api/routes/dashboard.py.local.backup"
)

declare -a OBSOLETE_TEMPLATES=(
    "src/dashboard/templates/dashboard_v10.html"
    "src/dashboard/templates/dashboard_desktop_v1.html"
    "src/dashboard/templates/dashboard_mobile_v1_*.html"
    "src/dashboard/templates/admin_dashboard_v2.html"
    "src/dashboard/templates/*backup*.html"
)

declare -a OBSOLETE_SCRIPTS=(
    "scripts/test_mobile_dashboard_complete.sh"
    "scripts/test_cache_performance.sh"
)

# Function to archive and remove files
archive_and_remove() {
    local file=$1
    if [ -f "$file" ]; then
        echo "  ✓ Archiving: $file"
        # Create subdirectory structure in archive
        local dir=$(dirname "$file")
        mkdir -p "$ARCHIVE_DIR/$dir"
        mv "$file" "$ARCHIVE_DIR/$file"
    fi
}

echo "🗑️ Processing obsolete cache implementations..."
for file in "${OBSOLETE_CACHE_FILES[@]}"; do
    archive_and_remove "$file"
done

echo ""
echo "🗑️ Processing obsolete dashboard routes..."
for pattern in "${OBSOLETE_DASHBOARD_ROUTES[@]}"; do
    for file in $pattern; do
        if [ -f "$file" ]; then
            archive_and_remove "$file"
        fi
    done
done

echo ""
echo "🗑️ Processing obsolete templates..."
for pattern in "${OBSOLETE_TEMPLATES[@]}"; do
    for file in $pattern; do
        if [ -f "$file" ]; then
            archive_and_remove "$file"
        fi
    done
done

echo ""
echo "🗑️ Processing obsolete scripts..."
for file in "${OBSOLETE_SCRIPTS[@]}"; do
    archive_and_remove "$file"
done

# Clean up backup directories
echo ""
echo "🗑️ Cleaning up backup directories..."
if [ -d "backup/performance_fix_*" ]; then
    for dir in backup/performance_fix_*; do
        if [ -d "$dir" ]; then
            echo "  ✓ Archiving: $dir"
            mv "$dir" "$ARCHIVE_DIR/"
        fi
    done
fi

# Remove empty directories
echo ""
echo "🗑️ Removing empty directories..."
find src/api/routes -type d -empty -delete 2>/dev/null
find src/dashboard/templates -type d -empty -delete 2>/dev/null

# Show summary
echo ""
echo "=========================================="
echo "📊 Cleanup Summary"
echo "=========================================="
echo ""

# Count archived files
ARCHIVED_COUNT=$(find "$ARCHIVE_DIR" -type f | wc -l | tr -d ' ')
ARCHIVE_SIZE=$(du -sh "$ARCHIVE_DIR" 2>/dev/null | cut -f1)

echo "✅ Files archived: $ARCHIVED_COUNT"
echo "✅ Archive size: $ARCHIVE_SIZE"
echo "✅ Archive location: $ARCHIVE_DIR"
echo ""

# Show remaining active files
echo "📁 Active files (kept):"
echo "  • src/api/cache_adapter_direct.py (Multi-tier implementation)"
echo "  • src/api/routes/dashboard_unified.py (Consolidated endpoints)"
echo "  • src/api/routes/dashboard.py (Main dashboard route)"
echo "  • src/core/cache/multi_tier_cache.py (Cache architecture)"
echo "  • src/dashboard/templates/dashboard_mobile_v1.html (Active mobile)"
echo "  • src/dashboard/templates/dashboard.html (Active desktop)"
echo ""

echo "=========================================="
echo "✅ Cleanup complete!"
echo "=========================================="
echo ""
echo "💡 To restore archived files:"
echo "   cp -r $ARCHIVE_DIR/* ."
echo ""
echo "⚠️  Note: Remember to update imports if any active"
echo "    code still references the removed files."
echo ""
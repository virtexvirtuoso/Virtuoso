#!/bin/bash

# Docs Directory Cleanup Script
# Purpose: Reorganize and clean up the documentation directory

DOCS_DIR="/Users/ffv_macmini/Desktop/Virtuoso_ccxt/docs"
ARCHIVE_DIR="$DOCS_DIR/archive/obsolete_$(date +%Y%m%d)"

echo "==================================="
echo "Documentation Directory Cleanup"
echo "==================================="
echo ""

# Create archive directory for obsolete docs
echo "1. Creating archive directory for obsolete documentation..."
mkdir -p "$ARCHIVE_DIR"

# Archive old and obsolete files
echo ""
echo "2. Archiving obsolete documentation (July-August 2025)..."
echo "   Moving fake data analysis docs..."
find "$DOCS_DIR" -maxdepth 1 -name "*FAKE_DATA*" -exec mv {} "$ARCHIVE_DIR/" \; 2>/dev/null

echo "   Moving old error handling docs..."
find "$DOCS_DIR" -maxdepth 1 -name "*ERROR_HANDLING*" -exec mv {} "$ARCHIVE_DIR/" \; 2>/dev/null

echo "   Moving old cleanup summaries..."
find "$DOCS_DIR" -maxdepth 1 -name "*CLEANUP*" -exec mv {} "$ARCHIVE_DIR/" \; 2>/dev/null

echo "   Moving old VPN testing docs..."
find "$DOCS_DIR" -maxdepth 1 -name "*VPN_TESTING*" -exec mv {} "$ARCHIVE_DIR/" \; 2>/dev/null

echo "   Moving old deployment status files..."
find "$DOCS_DIR" -maxdepth 1 -name "*DEPLOYMENT_STATUS*" -exec mv {} "$ARCHIVE_DIR/" \; 2>/dev/null
find "$DOCS_DIR" -maxdepth 1 -name "*DEPLOYMENT_FINAL*" -exec mv {} "$ARCHIVE_DIR/" \; 2>/dev/null

# Create demos directory and move HTML files
echo ""
echo "3. Organizing HTML demo files..."
mkdir -p "$DOCS_DIR/demos"
find "$DOCS_DIR" -maxdepth 1 -name "*.html" -exec mv {} "$DOCS_DIR/demos/" \; 2>/dev/null

# Organize cache-related documentation
echo ""
echo "4. Organizing performance and cache documentation..."
mkdir -p "$DOCS_DIR/performance/cache"
find "$DOCS_DIR" -maxdepth 1 -name "*CACHE*" -exec mv {} "$DOCS_DIR/performance/cache/" \; 2>/dev/null
find "$DOCS_DIR" -maxdepth 1 -name "*PERFORMANCE*" -exec mv {} "$DOCS_DIR/performance/" \; 2>/dev/null

# Organize dashboard documentation
echo ""
echo "5. Organizing dashboard documentation..."
mkdir -p "$DOCS_DIR/architecture/dashboard"
find "$DOCS_DIR" -maxdepth 1 -name "*DASHBOARD*" -exec mv {} "$DOCS_DIR/architecture/dashboard/" \; 2>/dev/null
find "$DOCS_DIR" -maxdepth 1 -name "*MOBILE*" -exec mv {} "$DOCS_DIR/architecture/dashboard/" \; 2>/dev/null

# Organize API documentation
echo ""
echo "6. Organizing API documentation..."
mkdir -p "$DOCS_DIR/architecture/api"
find "$DOCS_DIR" -maxdepth 1 -name "*API*" -exec mv {} "$DOCS_DIR/architecture/api/" \; 2>/dev/null
find "$DOCS_DIR" -maxdepth 1 -name "*ENDPOINT*" -exec mv {} "$DOCS_DIR/architecture/api/" \; 2>/dev/null

# Organize deployment documentation
echo ""
echo "7. Organizing deployment documentation..."
mkdir -p "$DOCS_DIR/deployment/reports"
find "$DOCS_DIR" -maxdepth 1 -name "*DEPLOYMENT*" -exec mv {} "$DOCS_DIR/deployment/reports/" \; 2>/dev/null
find "$DOCS_DIR" -maxdepth 1 -name "*VPS*" -exec mv {} "$DOCS_DIR/deployment/" \; 2>/dev/null

# Organize service and system docs
echo ""
echo "8. Organizing service and system documentation..."
mkdir -p "$DOCS_DIR/operations/services"
find "$DOCS_DIR" -maxdepth 1 -name "*SERVICE*" -exec mv {} "$DOCS_DIR/operations/services/" \; 2>/dev/null
find "$DOCS_DIR" -maxdepth 1 -name "*SYSTEM*" -exec mv {} "$DOCS_DIR/operations/" \; 2>/dev/null

# Organize trading-specific docs
echo ""
echo "9. Organizing trading documentation..."
mkdir -p "$DOCS_DIR/trading/signals"
find "$DOCS_DIR" -maxdepth 1 -name "*SIGNAL*" -exec mv {} "$DOCS_DIR/trading/signals/" \; 2>/dev/null
find "$DOCS_DIR" -maxdepth 1 -name "*WHALE*" -exec mv {} "$DOCS_DIR/trading/" \; 2>/dev/null
find "$DOCS_DIR" -maxdepth 1 -name "*MANIPULATION*" -exec mv {} "$DOCS_DIR/trading/" \; 2>/dev/null

# Move integration and implementation docs
echo ""
echo "10. Organizing integration documentation..."
mkdir -p "$DOCS_DIR/integration/implementations"
find "$DOCS_DIR" -maxdepth 1 -name "*INTEGRATION*" -exec mv {} "$DOCS_DIR/integration/" \; 2>/dev/null
find "$DOCS_DIR" -maxdepth 1 -name "*IMPLEMENTATION*" -exec mv {} "$DOCS_DIR/implementation/" \; 2>/dev/null

# Clean up duplicate numbered directories
echo ""
echo "11. Resolving duplicate numbered directories..."
if [ -d "$DOCS_DIR/07-analysis" ] && [ -d "$DOCS_DIR/07-analysis-systems" ]; then
    echo "   Merging 07-analysis directories..."
    cp -r "$DOCS_DIR/07-analysis-systems/"* "$DOCS_DIR/07-analysis/" 2>/dev/null
    rm -rf "$DOCS_DIR/07-analysis-systems"
fi

if [ -d "$DOCS_DIR/06-maintenance" ] && [ -d "$DOCS_DIR/06-reference" ]; then
    echo "   Keeping both 06-maintenance and 06-reference (different purposes)"
fi

if [ -d "$DOCS_DIR/08-archive" ] && [ -d "$DOCS_DIR/08-cache-system" ]; then
    echo "   Moving 08-cache-system contents to performance/cache..."
    cp -r "$DOCS_DIR/08-cache-system/"* "$DOCS_DIR/performance/cache/" 2>/dev/null
    rm -rf "$DOCS_DIR/08-cache-system"
fi

# Move remaining standalone docs to appropriate places
echo ""
echo "12. Organizing remaining standalone documentation..."

# Move specific important docs to root-level categories
[ -f "$DOCS_DIR/PROPRIETARY_NOTICE.md" ] && echo "   Keeping PROPRIETARY_NOTICE.md at root"
[ -f "$DOCS_DIR/README.md" ] && echo "   Keeping README.md at root"
[ -f "$DOCS_DIR/INDEX.md" ] && echo "   Keeping INDEX.md at root"

# Archive very old docs (July 2025)
echo ""
echo "13. Archiving documentation from July 2025..."
find "$DOCS_DIR" -maxdepth 1 -name "*.md" -type f -exec bash -c '
    file="$1"
    if grep -q "Jul.*2025\|July.*2025\|2025-07\|07/.*2025" "$file" 2>/dev/null; then
        mv "$file" "'"$ARCHIVE_DIR"'/"
    fi
' _ {} \;

# Count results
echo ""
echo "==================================="
echo "Cleanup Summary"
echo "==================================="
echo "Files archived: $(find "$ARCHIVE_DIR" -type f | wc -l)"
echo "HTML demos moved: $(find "$DOCS_DIR/demos" -name "*.html" 2>/dev/null | wc -l)"
echo "Root-level .md files remaining: $(find "$DOCS_DIR" -maxdepth 1 -name "*.md" | wc -l)"
echo ""
echo "Top-level structure:"
ls -1d "$DOCS_DIR"/*/ | head -20

echo ""
echo "Cleanup complete! Review the changes and commit when ready."
echo "Archive location: $ARCHIVE_DIR"
#!/bin/bash

echo "======================================"
echo "PHASE 4 - CODE CLEANUP"
echo "======================================"
echo ""

# List of files to remove (obsolete code)
OBSOLETE_FILES=(
    # Old integration layers
    "src/dashboard/dashboard_integration.py"
    "src/core/market/top_symbols.py"
    
    # Old timeout wrappers
    "src/core/exchanges/timeout_wrapper.py"
    
    # Complex retry logic
    "src/core/exchanges/retry_manager.py"
    
    # Old connection pool configs
    "src/core/exchanges/connection_pool.py"
    
    # Temporary test files
    "scripts/test_*.py"
    "scripts/fix_*.py"
    "scripts/patch_*.py"
    "scripts/simple_*.py"
    "scripts/debug_*.py"
)

echo "📊 Analyzing code to clean up..."
echo ""

# Count lines before cleanup
total_lines_before=0
for pattern in "src/**/*.py" "scripts/*.py"; do
    lines=$(find . -path "./$pattern" -type f -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}')
    total_lines_before=$((total_lines_before + lines))
done

echo "Total Python lines before cleanup: $total_lines_before"
echo ""

# Check which files exist
echo "Files to remove:"
for file in "${OBSOLETE_FILES[@]}"; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file")
        echo "  ❌ $file ($lines lines)"
    fi
done

# Check for test/debug scripts
echo ""
echo "Test/Debug scripts to remove:"
for pattern in "scripts/test_*.py" "scripts/fix_*.py" "scripts/debug_*.py" "scripts/patch_*.py" "scripts/simple_*.py"; do
    for file in $pattern; do
        if [ -f "$file" ]; then
            lines=$(wc -l < "$file")
            echo "  ❌ $file ($lines lines)"
        fi
    done
done

echo ""
echo "Large files that might need refactoring:"
find src -name "*.py" -type f -exec wc -l {} + | sort -rn | head -10

echo ""
echo "======================================"
echo "CLEANUP RECOMMENDATIONS"
echo "======================================"
echo ""
echo "1. Remove obsolete integration layers:"
echo "   - dashboard_integration.py (300+ lines)"
echo "   - top_symbols.py (900+ lines)"
echo ""
echo "2. Simplify exchange management:"
echo "   - Remove complex timeout wrappers"
echo "   - Eliminate retry logic layers"
echo "   - Simplify connection pooling"
echo ""
echo "3. Clean up test scripts:"
echo "   - Remove temporary test files"
echo "   - Archive debug scripts"
echo ""
echo "4. Refactor large files:"
echo "   - Break down files >500 lines"
echo "   - Extract common utilities"
echo ""
echo "5. Remove unused imports and dead code"
echo ""
echo "To execute cleanup, run:"
echo "  ./scripts/phase4_cleanup.sh --execute"
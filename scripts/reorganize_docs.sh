#!/bin/bash

# Documentation Reorganization Script for Virtuoso CCXT
# Generated from DOCUMENTATION_AUDIT_COMPREHENSIVE_2025_08_30.md
# Date: August 30, 2025

set -e  # Exit on error

echo "========================================"
echo "Virtuoso CCXT Documentation Reorganization"
echo "========================================"
echo ""

# Function to create directories
create_directories() {
    echo "Creating new directory structure..."
    
    # Main documentation categories
    mkdir -p docs/01-getting-started
    mkdir -p docs/02-user-guide/dashboard
    mkdir -p docs/03-developer-guide/architecture
    mkdir -p docs/04-deployment/migration-guides
    mkdir -p docs/05-operations
    mkdir -p docs/06-reference/cache
    mkdir -p docs/06-reference/api
    mkdir -p docs/06-reference/configuration
    mkdir -p docs/07-analysis-systems
    mkdir -p docs/08-archive/reports
    mkdir -p docs/08-archive/old-docs
    mkdir -p docs/assets/images
    mkdir -p docs/assets/diagrams
    mkdir -p docs/assets/demos
    mkdir -p docs/_internal/development-notes
    mkdir -p docs/_internal/meeting-notes
    mkdir -p docs/_internal/technical-reviews
    
    echo "✓ Directory structure created"
}

# Function to move cache documentation
move_cache_docs() {
    echo "Moving cache documentation..."
    
    if ls CACHE_*.md 1> /dev/null 2>&1; then
        mv CACHE_*.md docs/06-reference/cache/ 2>/dev/null || true
        echo "✓ Cache documentation moved"
    else
        echo "⚠ No cache documentation found in root"
    fi
}

# Function to move dashboard documentation  
move_dashboard_docs() {
    echo "Moving dashboard documentation..."
    
    if ls DASHBOARD_*.md 1> /dev/null 2>&1; then
        mv DASHBOARD_*.md docs/02-user-guide/dashboard/ 2>/dev/null || true
        echo "✓ Dashboard documentation moved"
    else
        echo "⚠ No dashboard documentation found in root"
    fi
}

# Function to move deployment documentation
move_deployment_docs() {
    echo "Moving deployment documentation..."
    
    # Migration guides
    [ -f "HETZNER_MIGRATION_COMPLETE_GUIDE.md" ] && mv HETZNER_MIGRATION_COMPLETE_GUIDE.md docs/04-deployment/migration-guides/
    [ -f "MIGRATION_TO_REFACTORED.md" ] && mv MIGRATION_TO_REFACTORED.md docs/04-deployment/migration-guides/
    
    # VPS and deployment guides
    [ -f "PRODUCTION_VPS_DEPLOYMENT_GUIDE.md" ] && mv PRODUCTION_VPS_DEPLOYMENT_GUIDE.md docs/04-deployment/
    [ -f "LOCAL_SYNC_FROM_HETZNER.md" ] && mv LOCAL_SYNC_FROM_HETZNER.md docs/04-deployment/
    [ -f "VT_CONTROL_V5_SETUP.md" ] && mv VT_CONTROL_V5_SETUP.md docs/04-deployment/
    
    # Move VPS related docs
    if ls VPS_*.md 1> /dev/null 2>&1; then
        mv VPS_*.md docs/04-deployment/ 2>/dev/null || true
    fi
    
    echo "✓ Deployment documentation moved"
}

# Function to move architecture documentation
move_architecture_docs() {
    echo "Moving architecture documentation..."
    
    # Data flow documentation
    if ls VIRTUOSO_DATA_FLOW_*.md 1> /dev/null 2>&1; then
        mv VIRTUOSO_DATA_FLOW_*.md docs/03-developer-guide/architecture/ 2>/dev/null || true
    fi
    
    # Service and DI documentation
    [ -f "SERVICE_INTERFACE_REGISTRATION_AUDIT.md" ] && mv SERVICE_INTERFACE_REGISTRATION_AUDIT.md docs/03-developer-guide/architecture/
    [ -f "INTERFACE_REGISTRATION_MIGRATION_PLAN.md" ] && mv INTERFACE_REGISTRATION_MIGRATION_PLAN.md docs/03-developer-guide/architecture/
    
    # Dependency injection docs
    if ls DI_*.md 1> /dev/null 2>&1; then
        mv DI_*.md docs/03-developer-guide/architecture/ 2>/dev/null || true
    fi
    
    echo "✓ Architecture documentation moved"
}

# Function to archive reports and summaries
archive_reports() {
    echo "Archiving reports and summaries..."
    
    # Move reports
    if ls *_REPORT.md 1> /dev/null 2>&1; then
        mv *_REPORT.md docs/08-archive/reports/ 2>/dev/null || true
    fi
    
    # Move summaries
    if ls *_SUMMARY.md 1> /dev/null 2>&1; then
        mv *_SUMMARY.md docs/08-archive/reports/ 2>/dev/null || true
    fi
    
    # Move specific files
    [ -f "documentation_validation_report.md" ] && mv documentation_validation_report.md docs/08-archive/reports/
    [ -f "TECHNICAL_LEADERSHIP_REVIEW_2025.md" ] && mv TECHNICAL_LEADERSHIP_REVIEW_2025.md docs/08-archive/reports/
    [ -f "PHASE1_COMPLETION_SUMMARY.md" ] && mv PHASE1_COMPLETION_SUMMARY.md docs/08-archive/reports/
    
    echo "✓ Reports and summaries archived"
}

# Function to create index files
create_indexes() {
    echo "Creating index files..."
    
    # Create main docs index if it doesn't exist
    if [ ! -f "docs/index.md" ]; then
        cat > docs/index.md << 'EOF'
# Virtuoso CCXT Documentation

Welcome to the Virtuoso CCXT Trading System documentation.

## Documentation Categories

### [01. Getting Started](01-getting-started/)
Installation, configuration, and quick start guides.

### [02. User Guide](02-user-guide/)
Dashboard usage, trading interface, alerts, and monitoring.

### [03. Developer Guide](03-developer-guide/)
Architecture, API reference, data flow, and testing.

### [04. Deployment](04-deployment/)
Local development, VPS deployment, Docker, and migration guides.

### [05. Operations](05-operations/)
Monitoring, troubleshooting, performance tuning, and maintenance.

### [06. Reference](06-reference/)
API documentation, configuration reference, and glossary.

### [07. Analysis Systems](07-analysis-systems/)
6-dimensional analysis system documentation.

### [08. Archive](08-archive/)
Historical documentation and old reports.

---
*Last updated: August 30, 2025*
EOF
        echo "✓ Main index created"
    else
        echo "⚠ Main index already exists"
    fi
}

# Function to generate summary report
generate_report() {
    echo ""
    echo "========================================"
    echo "Reorganization Summary"
    echo "========================================"
    
    # Count remaining files in root
    ROOT_MD_COUNT=$(find . -maxdepth 1 -name "*.md" -not -name "README.md" -not -name "CHANGELOG.md" -not -name "CLAUDE*.md" | wc -l)
    DOCS_MD_COUNT=$(find docs -name "*.md" | wc -l)
    
    echo "Documentation files in root: $ROOT_MD_COUNT"
    echo "Documentation files in docs: $DOCS_MD_COUNT"
    echo ""
    echo "Next steps:"
    echo "1. Review the moved files in their new locations"
    echo "2. Update any internal links that may be broken"
    echo "3. Create CONTRIBUTING.md file"
    echo "4. Write installation and configuration guides"
    echo "5. Generate API documentation"
    echo ""
    echo "Reorganization complete!"
}

# Main execution
main() {
    echo "This script will reorganize documentation files."
    echo "Current directory: $(pwd)"
    echo ""
    read -p "Do you want to proceed? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_directories
        move_cache_docs
        move_dashboard_docs
        move_deployment_docs
        move_architecture_docs
        archive_reports
        create_indexes
        generate_report
    else
        echo "Reorganization cancelled."
        exit 0
    fi
}

# Run main function
main
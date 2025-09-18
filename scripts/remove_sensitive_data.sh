#!/bin/bash

# Script to remove sensitive data from git history
# This will rewrite ALL git history - make sure you have backups!

echo "==========================================="
echo "GIT HISTORY SECURITY CLEANUP"
echo "==========================================="
echo ""
echo "This script will:"
echo "1. Replace VPS IP (${VPS_HOST}) with environment variable"
echo "2. Add docs/ to .gitignore"
echo "3. Remove sensitive data from git history"
echo ""
echo "WARNING: This will rewrite ALL git history!"
echo "Make sure you have a backup before proceeding."
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Create backup branch
echo "Creating backup branch..."
git branch backup-before-cleanup-$(date +%Y%m%d_%H%M%S)

# Step 1: Replace VPS IP in all files
echo "Replacing VPS IP with environment variable..."
find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.yaml" -o -name "*.yml" -o -name "*.html" -o -name "*.jsx" \) \
    -not -path "./.git/*" \
    -not -path "./venv*/*" \
    -exec grep -l "5\.223\.63\.4" {} \; | while read file; do
    echo "Updating: $file"
    sed -i '' 's/5\.223\.63\.4/${VPS_HOST}/g' "$file"
done

# Step 2: Update .gitignore
echo "Updating .gitignore..."
if ! grep -q "^docs/$" .gitignore; then
    echo "" >> .gitignore
    echo "# Documentation (contains sensitive info)" >> .gitignore
    echo "docs/" >> .gitignore
fi

if ! grep -q "^\.env\.vps$" .gitignore; then
    echo "" >> .gitignore
    echo "# VPS environment variables" >> .gitignore
    echo ".env.vps" >> .gitignore
fi

# Step 3: Create .env.vps.example
echo "Creating .env.vps.example..."
cat > .env.vps.example << 'EOF'
# VPS Configuration
# Copy this to .env.vps and fill in actual values
VPS_HOST=your.vps.ip.here
VPS_USER=linuxuser
VPS_PATH=/home/linuxuser/trading/Virtuoso_ccxt
EOF

# Step 4: Commit current changes
echo "Committing security fixes..."
git add -A
git commit -m "Security: Remove hardcoded VPS IP and add docs to gitignore"

# Step 5: Use git filter-branch to remove VPS IP from history
echo "Cleaning git history..."
echo "This may take several minutes..."

# Create a filter script
cat > /tmp/git-filter-script.sh << 'SCRIPT'
#!/bin/bash
find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.yaml" -o -name "*.yml" -o -name "*.html" -o -name "*.jsx" \) \
    -exec sed -i '' 's/5\.223\.63\.4/${VPS_HOST}/g' {} \; 2>/dev/null || true
SCRIPT

chmod +x /tmp/git-filter-script.sh

# Run filter-branch
git filter-branch --tree-filter '/tmp/git-filter-script.sh' --prune-empty -f HEAD

# Clean up
rm /tmp/git-filter-script.sh

echo ""
echo "==========================================="
echo "CLEANUP COMPLETE!"
echo "==========================================="
echo ""
echo "Next steps:"
echo "1. Review the changes: git diff HEAD~1"
echo "2. Force push to GitHub: git push --force origin main"
echo "3. Create .env.vps file with actual VPS IP"
echo "4. Update all team members about the history rewrite"
echo ""
echo "IMPORTANT: All team members will need to:"
echo "  git fetch --all"
echo "  git reset --hard origin/main"
echo ""
echo "The VPS IP has been replaced with \${VPS_HOST} variable."
echo "Make sure to set VPS_HOST environment variable when running scripts."
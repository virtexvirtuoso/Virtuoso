#!/bin/bash

# Safer script to clean git history using BFG Repo-Cleaner
# This is faster and safer than git filter-branch

echo "==========================================="
echo "GIT HISTORY SECURITY CLEANUP (BFG Method)"
echo "==========================================="
echo ""
echo "This script will remove sensitive VPS IP from git history"
echo ""
echo "Prerequisites:"
echo "1. Install BFG: brew install bfg (on macOS)"
echo "2. Make sure you have a backup of your repo"
echo ""
read -p "Do you have BFG installed? (yes/no): " has_bfg

if [ "$has_bfg" != "yes" ]; then
    echo "Please install BFG first:"
    echo "  brew install bfg"
    echo "Or download from: https://rtyley.github.io/bfg-repo-cleaner/"
    exit 1
fi

# Create backup
echo "Creating backup..."
git branch backup-$(date +%Y%m%d_%H%M%S)

# Step 1: Create replacement file for BFG
echo "Creating replacement rules..."
cat > replacements.txt << 'EOF'
${VPS_HOST}==>VPS_HOST_REDACTED
regex:5\.223\.63\.4==>VPS_HOST_REDACTED
EOF

# Step 2: First, fix current files
echo "Fixing current working directory files..."
find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.yaml" -o -name "*.yml" -o -name "*.html" -o -name "*.jsx" \) \
    -not -path "./.git/*" \
    -not -path "./venv*/*" \
    -exec grep -l "5\.223\.63\.4" {} \; | while read file; do
    echo "Updating: $file"
    sed -i '' 's/5\.223\.63\.4/${VPS_HOST}/g' "$file"
done

# Step 3: Update .gitignore
echo "Updating .gitignore..."
cat >> .gitignore << 'EOF'

# Security - Documentation and sensitive configs
docs/
.env.vps
*.secret
*_credentials.json
config/production.yaml

# VPS specific files
scripts/*vps*.sh
scripts/deploy_*.sh
EOF

# Step 4: Create environment template
echo "Creating .env.vps.example..."
cat > .env.vps.example << 'EOF'
# VPS Configuration - DO NOT COMMIT ACTUAL VALUES
export VPS_HOST="your.vps.ip.here"
export VPS_USER="linuxuser"
export VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
export VPS_PORT="22"
EOF

# Step 5: Commit current changes
echo "Committing current fixes..."
git add -A
git commit -m "Security: Remove hardcoded IPs and update gitignore" || true

# Step 6: Run BFG to clean history
echo "Running BFG to clean git history..."
echo "This will remove all instances of the VPS IP from history"

# Run BFG
bfg --replace-text replacements.txt

# Step 7: Clean up git
echo "Cleaning up git repository..."
git reflog expire --expire=now --all && git gc --prune=now --aggressive

# Clean up temp files
rm replacements.txt

echo ""
echo "==========================================="
echo "CLEANUP COMPLETE!"
echo "==========================================="
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo ""
echo "1. Review the changes:"
echo "   git log --oneline -10"
echo ""
echo "2. FORCE PUSH to GitHub (this will rewrite history!):"
echo "   git push --force origin main"
echo ""
echo "3. Create .env.vps with actual values:"
echo "   cp .env.vps.example .env.vps"
echo "   # Edit .env.vps with real IP"
echo ""
echo "4. Update deployment scripts to source .env.vps:"
echo "   source .env.vps"
echo "   ssh \${VPS_USER}@\${VPS_HOST}"
echo ""
echo "5. Notify all team members to re-clone or reset:"
echo "   git fetch --all"
echo "   git reset --hard origin/main"
echo ""
echo "⚠️  The VPS IP has been replaced with VPS_HOST_REDACTED in history"
echo "⚠️  and with \${VPS_HOST} in current files"
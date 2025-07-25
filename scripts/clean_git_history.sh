#!/bin/bash
# Script to clean sensitive data from git history
# WARNING: This will rewrite git history!

echo "⚠️  WARNING: This will rewrite your git history!"
echo "Make sure you have a backup and coordinate with any collaborators."
echo ""
read -p "Do you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo "🔍 Searching for sensitive patterns in git history..."

# Patterns to remove
PATTERNS=(
    "discord.com/api/webhooks"
    "BYBIT_API_KEY"
    "BYBIT_API_SECRET"
    "INFLUXDB_TOKEN"
    "JWT_SECRET_KEY"
)

# Create a backup branch
git branch backup-before-clean-$(date +%Y%m%d-%H%M%S)

# Use git filter-repo (recommended) or BFG Repo-Cleaner
# First check if git filter-repo is installed
if command -v git-filter-repo &> /dev/null; then
    echo "Using git filter-repo..."
    for pattern in "${PATTERNS[@]}"; do
        echo "Removing: $pattern"
        git filter-repo --replace-text <(echo "$pattern==>REDACTED")
    done
else
    echo "❌ git-filter-repo not found. Please install it first:"
    echo "   pip install git-filter-repo"
    echo ""
    echo "Alternative: Use BFG Repo-Cleaner"
    echo "   1. Download from: https://rtyley.github.io/bfg-repo-cleaner/"
    echo "   2. Run: java -jar bfg.jar --replace-text passwords.txt"
    exit 1
fi

echo ""
echo "✅ Git history cleaned!"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "1. Force push to remote: git push origin --force --all"
echo "2. Tell all collaborators to re-clone the repository"
echo "3. Rotate ALL credentials that were exposed"
echo "4. Update your local .env file with new credentials"
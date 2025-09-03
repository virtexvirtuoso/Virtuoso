#!/bin/bash

# Script to remove all references to Vultr IP VPS_HOST_REDACTED from codebase
# This script will replace with placeholder or remove references

echo "🔍 Removing all references to Vultr IP VPS_HOST_REDACTED..."

# First, let's find all files with references (excluding backup folders)
echo "📋 Files containing Vultr IP references:"
find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.json" \) \
    -not -path "./vultr_backup_files/*" \
    -not -path "./vultr_evidence_package/*" \
    -exec grep -l "45\.77\.40\.77" {} \; 2>/dev/null

echo ""
echo "🔄 Starting replacement process..."

# Function to replace Vultr IP in files
replace_vultr_ip() {
    local file="$1"
    local backup_file="${file}.bak"
    
    echo "  Processing: $file"
    
    # Create backup
    cp "$file" "$backup_file"
    
    # Replace different variations of the IP
    sed -i '' 's/45\.77\.40\.77/YOUR_VPS_IP/g' "$file"
    sed -i '' 's/linuxuser@45\.77\.40\.77/linuxuser@YOUR_VPS_IP/g' "$file"
    sed -i '' 's/http:\/\/45\.77\.40\.77/http:\/\/YOUR_VPS_IP/g' "$file"
    sed -i '' 's/https:\/\/45\.77\.40\.77/https:\/\/YOUR_VPS_IP/g' "$file"
    
    # Check if changes were made
    if ! diff -q "$file" "$backup_file" >/dev/null 2>&1; then
        echo "    ✅ Updated $file"
        rm "$backup_file"
    else
        echo "    ℹ️  No changes needed in $file"
        mv "$backup_file" "$file"
    fi
}

# Process all files with references
find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.json" \) \
    -not -path "./vultr_backup_files/*" \
    -not -path "./vultr_evidence_package/*" \
    -exec grep -l "45\.77\.40\.77" {} \; 2>/dev/null | while read -r file; do
    replace_vultr_ip "$file"
done

echo ""
echo "🔍 Special handling for common patterns..."

# Handle SSH config if it exists
if [ -f ~/.ssh/config ]; then
    if grep -q "45\.77\.40\.77" ~/.ssh/config 2>/dev/null; then
        echo "  ⚠️  SSH config contains Vultr IP - manual review recommended"
        echo "      File: ~/.ssh/config"
    fi
fi

# Handle .claude settings
if [ -f ".claude/settings.local.json" ]; then
    echo "  🔧 Updating Claude settings..."
    sed -i '' 's/45\.77\.40\.77/YOUR_VPS_IP/g' ".claude/settings.local.json"
    sed -i '' 's/linuxuser@45\.77\.40\.77/linuxuser@YOUR_VPS_IP/g' ".claude/settings.local.json"
fi

echo ""
echo "✅ Vultr IP removal complete!"
echo ""
echo "📝 Summary of changes:"
echo "   - Replaced VPS_HOST_REDACTED with YOUR_VPS_IP"
echo "   - Updated SSH connection strings"
echo "   - Modified deployment scripts"
echo "   - Updated documentation"
echo ""
echo "⚠️  Next steps:"
echo "   1. Update YOUR_VPS_IP with your new VPS IP when ready"
echo "   2. Update SSH aliases if needed"
echo "   3. Test deployment scripts with new IP"
echo ""
echo "🔒 Protected folders (not modified):"
echo "   - vultr_backup_files/ (contains evidence)"
echo "   - vultr_evidence_package/ (contains complaints)"
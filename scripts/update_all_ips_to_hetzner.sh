#!/bin/bash

# Update all references from Vultr IP (VPS_HOST_REDACTED) to Hetzner IP (VPS_HOST_REDACTED)
# Created: August 29, 2025

echo "=================================================================================="
echo "Updating all IP references from Vultr (VPS_HOST_REDACTED) to Hetzner (VPS_HOST_REDACTED)"
echo "=================================================================================="

OLD_IP="VPS_HOST_REDACTED"
NEW_IP="VPS_HOST_REDACTED"

# Count occurrences before update
echo "Counting occurrences before update..."
BEFORE_COUNT=$(grep -r "$OLD_IP" . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=venv --exclude-dir=.pytest_cache --exclude="*.pyc" 2>/dev/null | wc -l)
echo "Found $BEFORE_COUNT occurrences of $OLD_IP"

# Create backup of files that will be modified
echo "Creating backup of files to be modified..."
mkdir -p .backup/ip_update_$(date +%Y%m%d_%H%M%S)

# Find all files containing the old IP
FILES=$(grep -rl "$OLD_IP" . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=venv --exclude-dir=.pytest_cache --exclude="*.pyc" 2>/dev/null)

# Update each file
for file in $FILES; do
    # Skip binary files and this script itself
    if [[ "$file" == *".sh" ]] && [[ "$file" == *"update_all_ips_to_hetzner.sh" ]]; then
        continue
    fi
    
    # Check if file is text
    if file "$file" | grep -q "text"; then
        echo "Updating: $file"
        # Create backup
        cp "$file" ".backup/ip_update_$(date +%Y%m%d_%H%M%S)/$(basename $file)"
        # Replace IP
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/$OLD_IP/$NEW_IP/g" "$file"
        else
            # Linux
            sed -i "s/$OLD_IP/$NEW_IP/g" "$file"
        fi
    fi
done

# Count occurrences after update
echo ""
echo "Verifying update..."
AFTER_COUNT=$(grep -r "$OLD_IP" . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=venv --exclude-dir=.pytest_cache --exclude="*.pyc" 2>/dev/null | wc -l)
echo "Remaining occurrences of $OLD_IP: $AFTER_COUNT"

# Show new IP count
NEW_COUNT=$(grep -r "$NEW_IP" . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=venv --exclude-dir=.pytest_cache --exclude="*.pyc" 2>/dev/null | wc -l)
echo "New occurrences of $NEW_IP: $NEW_COUNT"

echo ""
echo "=================================================================================="
echo "Update complete!"
echo "- Files updated: $(echo "$FILES" | wc -l)"
echo "- Old IP ($OLD_IP) occurrences: $BEFORE_COUNT → $AFTER_COUNT"
echo "- New IP ($NEW_IP) occurrences: $NEW_COUNT"
echo "- Backup created in: .backup/ip_update_$(date +%Y%m%d_%H%M%S)/"
echo "=================================================================================="

# Also update SSH config if it exists
if [ -f ~/.ssh/config ]; then
    echo ""
    echo "Checking SSH config..."
    if grep -q "$OLD_IP" ~/.ssh/config; then
        echo "Found old IP in SSH config, updating..."
        sed -i.bak "s/$OLD_IP/$NEW_IP/g" ~/.ssh/config
        echo "SSH config updated (backup saved as ~/.ssh/config.bak)"
    fi
fi

echo ""
echo "✅ All IP references have been updated to Hetzner VPS (VPS_HOST_REDACTED)"
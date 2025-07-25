#!/bin/bash

# Transfer script for range volume fix with directory creation
# Target: linuxuser@45.77.40.77

TARGET_HOST="linuxuser@45.77.40.77"
TARGET_BASE="~/Virtuoso_ccxt"

echo "Transferring range volume fix files to VPS..."

# First, create necessary directories on remote
echo "Creating directories on remote server..."
ssh $TARGET_HOST "mkdir -p $TARGET_BASE/src/indicators $TARGET_BASE/config $TARGET_BASE/scripts/testing"

# Create a list of files that were modified
FILES=(
    "src/indicators/price_structure_indicators.py"
    "config/config.yaml"
    "scripts/testing/test_range_volume_fix.py"
)

# Transfer each file
for file in "${FILES[@]}"; do
    echo "Transferring $file..."
    scp "$file" "$TARGET_HOST:$TARGET_BASE/$file"
    if [ $? -eq 0 ]; then
        echo "✓ Successfully transferred $file"
    else
        echo "✗ Failed to transfer $file"
    fi
done

echo ""
echo "Files transferred. You may want to:"
echo "1. SSH into the server: ssh $TARGET_HOST"
echo "2. Navigate to the project: cd $TARGET_BASE"
echo "3. Restart the application to apply changes"
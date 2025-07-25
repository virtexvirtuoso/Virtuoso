#!/bin/bash

# Transfer script for range volume fix
# Target: linuxuser@45.77.40.77

echo "Transferring range volume fix files to VPS..."

# Create a list of files that were modified
FILES=(
    "src/indicators/price_structure_indicators.py"
    "config/config.yaml"
    "scripts/testing/test_range_volume_fix.py"
)

# Transfer each file
for file in "${FILES[@]}"; do
    echo "Transferring $file..."
    scp "$file" "linuxuser@45.77.40.77:~/Virtuoso_ccxt/$file"
    if [ $? -eq 0 ]; then
        echo "✓ Successfully transferred $file"
    else
        echo "✗ Failed to transfer $file"
    fi
done

echo "Transfer complete!"
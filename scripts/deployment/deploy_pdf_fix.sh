#!/bin/bash

# Deploy PDF stop loss fix to VPS
echo "🚀 Deploying PDF stop loss fix to VPS..."

# VPS details
VPS_USER="root"
VPS_HOST="45.76.142.105"
VPS_PATH="/root/Virtuoso_ccxt"

# Files to update
FILES_TO_UPDATE=(
    "src/core/reporting/pdf_generator.py"
)

# Display what will be deployed
echo "📦 Files to be deployed:"
for file in "${FILES_TO_UPDATE[@]}"; do
    echo "  - $file"
done

# Create temporary directory for deployment
TEMP_DIR=$(mktemp -d)
echo "📂 Created temporary directory: $TEMP_DIR"

# Copy files to temporary directory maintaining structure
for file in "${FILES_TO_UPDATE[@]}"; do
    # Create directory structure in temp dir
    mkdir -p "$TEMP_DIR/$(dirname $file)"
    # Copy file
    cp "$file" "$TEMP_DIR/$file"
    echo "✅ Copied $file"
done

# Show the changes being deployed
echo ""
echo "📝 Changes being deployed:"
echo "- Updated stop loss extraction to check trade_params first"
echo "- Ensures stop loss from chart generation is used in Risk Management section"
echo "- Maintains backward compatibility with signal_data"

# Deploy to VPS
echo ""
echo "🔄 Syncing files to VPS..."
rsync -avz --relative "${FILES_TO_UPDATE[@]}" "$VPS_USER@$VPS_HOST:$VPS_PATH/"

if [ $? -eq 0 ]; then
    echo "✅ Files successfully deployed to VPS!"
    
    # Restart the application on VPS
    echo ""
    echo "🔄 Restarting application on VPS..."
    ssh "$VPS_USER@$VPS_HOST" "cd $VPS_PATH && docker-compose restart virtuoso"
    
    if [ $? -eq 0 ]; then
        echo "✅ Application restarted successfully!"
        echo ""
        echo "🎉 Deployment complete! The PDF stop loss fix is now live on the VPS."
        echo ""
        echo "📊 Next PDF reports generated will show:"
        echo "  - Stop loss values from trade_params in Risk Management section"
        echo "  - Proper percentage calculations"
        echo "  - No more 'N/A (0%)' when stop loss is available"
    else
        echo "❌ Failed to restart application on VPS"
        exit 1
    fi
else
    echo "❌ Failed to deploy files to VPS"
    exit 1
fi

# Cleanup
rm -rf "$TEMP_DIR"
echo "🧹 Cleaned up temporary files"
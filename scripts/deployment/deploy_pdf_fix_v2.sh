#!/bin/bash

# Deploy PDF stop loss fix to VPS
echo "🚀 Deploying PDF stop loss fix to VPS..."

# VPS details - using the current active VPS
VPS_USER="linuxuser"
VPS_HOST="185.162.249.241"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Files to update
FILES_TO_UPDATE=(
    "src/core/reporting/pdf_generator.py"
)

# Display what will be deployed
echo "📦 Files to be deployed:"
for file in "${FILES_TO_UPDATE[@]}"; do
    echo "  - $file"
done

echo ""
echo "📝 Changes being deployed:"
echo "- Updated stop loss extraction to check trade_params first"
echo "- Ensures stop loss from chart generation is used in Risk Management section"
echo "- Maintains backward compatibility with signal_data"

# Deploy to VPS
echo ""
echo "🔄 Syncing files to VPS..."
rsync -avz --progress "${FILES_TO_UPDATE[@]}" "$VPS_USER@$VPS_HOST:$VPS_PATH/src/core/reporting/"

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
        echo "ℹ️  You may need to manually restart the application"
    fi
else
    echo "❌ Failed to deploy files to VPS"
    exit 1
fi
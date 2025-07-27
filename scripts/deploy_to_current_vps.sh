#!/bin/bash

# Deploy PDF stop loss fix to current VPS
echo "🚀 Deploying PDF stop loss fix to VPS (45.77.40.77)..."

# VPS details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
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
    
    # Show restart instructions
    echo ""
    echo "📌 To apply the changes, restart the application on the VPS:"
    echo "   ssh $VPS_USER@$VPS_HOST"
    echo "   cd $VPS_PATH"
    echo "   docker-compose restart virtuoso"
    echo ""
    echo "📊 After restart, new PDF reports will show:"
    echo "  - Stop loss values from trade_params in Risk Management section"
    echo "  - Proper percentage calculations"
    echo "  - No more 'N/A (0%)' when stop loss is available"
else
    echo "❌ Failed to deploy files to VPS"
    echo ""
    echo "🔧 Manual deployment steps:"
    echo "1. Copy the file manually:"
    echo "   scp src/core/reporting/pdf_generator.py $VPS_USER@$VPS_HOST:$VPS_PATH/src/core/reporting/"
    echo ""
    echo "2. Or SSH to VPS and pull from git:"
    echo "   ssh $VPS_USER@$VPS_HOST"
    echo "   cd $VPS_PATH"
    echo "   git pull"
    exit 1
fi
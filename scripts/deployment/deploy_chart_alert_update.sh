#!/bin/bash

# Deploy chart alert and PDF stop loss fixes to VPS
echo "🚀 Deploying chart alert and PDF stop loss fixes to VPS (45.77.40.77)..."

# VPS details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Files to update
FILES_TO_UPDATE=(
    "src/core/reporting/pdf_generator.py"
    "src/core/reporting/report_manager.py"
    "src/monitoring/alert_manager.py"
)

# Display what will be deployed
echo "📦 Files to be deployed:"
for file in "${FILES_TO_UPDATE[@]}"; do
    echo "  - $file"
done

echo ""
echo "📝 Changes being deployed:"
echo "1. PDF Generator Updates:"
echo "   - Stop loss extraction from trade_params"
echo "   - Returns chart path along with PDF path"
echo ""
echo "2. Alert Manager Updates:"
echo "   - Sends high-resolution chart image to Discord"
echo "   - Shows TP/SL details in chart message"
echo "   - Chart sent before PDF attachment"
echo ""
echo "3. Report Manager Updates:"
echo "   - Handles chart path from PDF generator"
echo "   - Stores chart path in signal_data"

# Deploy to VPS
echo ""
echo "🔄 Syncing files to VPS..."
for file in "${FILES_TO_UPDATE[@]}"; do
    echo "  Deploying $file..."
    rsync -avz --progress "$file" "$VPS_USER@$VPS_HOST:$VPS_PATH/$file"
    if [ $? -ne 0 ]; then
        echo "❌ Failed to deploy $file"
        exit 1
    fi
done

echo ""
echo "✅ All files successfully deployed to VPS!"

# Show restart instructions
echo ""
echo "📌 To apply the changes, restart the application on the VPS:"
echo "   ssh $VPS_USER@$VPS_HOST"
echo "   cd $VPS_PATH"
echo "   docker-compose restart virtuoso"
echo ""
echo "📊 After restart:"
echo "  - PDF reports will show correct stop loss values"
echo "  - Discord alerts will include high-res chart images"
echo "  - Chart messages will display TP/SL details"
echo ""
echo "🎉 Deployment complete!"
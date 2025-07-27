#!/bin/bash

# Deploy chart branding update to VPS
echo "🚀 Deploying chart branding update to VPS (45.77.40.77)..."

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
echo "📝 Branding changes being deployed:"
echo "  - Added 'VIRTUOSO' branding to all chart PNGs"
echo "  - Orange color (#ff9900) matching mobile header"
echo "  - Dark background box with orange border"
echo "  - Positioned at bottom center with padding"
echo "  - Applied to: candlestick charts, simulated charts, component charts"

# Deploy to VPS
echo ""
echo "🔄 Syncing files to VPS..."
rsync -avz --progress "${FILES_TO_UPDATE[@]}" "$VPS_USER@$VPS_HOST:$VPS_PATH/src/core/reporting/"

if [ $? -eq 0 ]; then
    echo "✅ Branding update successfully deployed to VPS!"
    
    # Show restart instructions
    echo ""
    echo "📌 To apply the branding changes, restart the application on the VPS:"
    echo "   ssh $VPS_USER@$VPS_HOST"
    echo "   cd $VPS_PATH"
    echo "   docker-compose restart virtuoso"
    echo ""
    echo "📊 After restart, all new chart images will include:"
    echo "  - Virtuoso branding at the bottom"
    echo "  - Professional appearance with company colors"
    echo "  - Consistent branding across Discord alerts"
    echo ""
    echo "🎉 Chart branding deployment complete!"
else
    echo "❌ Failed to deploy branding update to VPS"
    exit 1
fi
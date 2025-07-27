#!/bin/bash

# Deploy final corrected chart branding to VPS
echo "🚀 Deploying final chart branding to VPS (45.77.40.77)..."

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
echo "🎨 Final branding implementation:"
echo "  - Trending-up symbol: ↗ (Unicode arrow)"
echo "  - Orange color: #ff9900 (matching mobile header)"
echo "  - Text: 'VIRTUOSO'"
echo "  - Style: Dark box with orange border"
echo "  - Position: Bottom center with proper padding"
echo ""
echo "📊 Chart styling:"
echo "  - Reverted to original color scheme"
echo "  - Entry: #4CAF50 (green)"
echo "  - Stop Loss: #ef4444 (red)"
echo "  - Targets: Orange variations"
echo "  - Background: #121212 / #1E1E1E"

# Deploy to VPS
echo ""
echo "🔄 Syncing final version to VPS..."
rsync -avz --progress "${FILES_TO_UPDATE[@]}" "$VPS_USER@$VPS_HOST:$VPS_PATH/src/core/reporting/"

if [ $? -eq 0 ]; then
    echo "✅ Final branding successfully deployed to VPS!"
    
    # Show restart instructions
    echo ""
    echo "📌 To apply the final branding, restart the application on the VPS:"
    echo "   ssh $VPS_USER@$VPS_HOST"
    echo "   cd $VPS_PATH"
    echo "   docker-compose restart virtuoso"
    echo ""
    echo "📊 After restart, chart images will have:"
    echo "  - ↗ VIRTUOSO branding in orange"
    echo "  - Original professional color scheme"
    echo "  - Consistent with mobile header styling"
    echo "  - Clean professional appearance"
    echo ""
    echo "🎉 Final chart branding deployment complete!"
else
    echo "❌ Failed to deploy final branding to VPS"
    exit 1
fi
#!/bin/bash

# Deploy corrected chart branding to VPS
echo "🚀 Deploying corrected chart branding to VPS (45.77.40.77)..."

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
echo "🔧 Corrections being deployed:"
echo "  - Removed emoji from branding (fixed rendering issue)"
echo "  - Reverted to original chart color scheme"
echo "  - Simple 'VIRTUOSO' text branding only"
echo "  - Minimal padding to avoid layout issues"
echo "  - Professional subtle appearance"

# Deploy to VPS
echo ""
echo "🔄 Syncing corrected files to VPS..."
rsync -avz --progress "${FILES_TO_UPDATE[@]}" "$VPS_USER@$VPS_HOST:$VPS_PATH/src/core/reporting/"

if [ $? -eq 0 ]; then
    echo "✅ Corrected branding successfully deployed to VPS!"
    
    # Show restart instructions
    echo ""
    echo "📌 To apply the corrected branding, restart the application on the VPS:"
    echo "   ssh $VPS_USER@$VPS_HOST"
    echo "   cd $VPS_PATH"
    echo "   docker-compose restart virtuoso"
    echo ""
    echo "📊 After restart, chart images will have:"
    echo "  - Original professional color scheme"
    echo "  - Simple 'VIRTUOSO' text branding"
    echo "  - No emoji rendering issues"
    echo "  - Clean professional appearance"
    echo ""
    echo "🎉 Corrected chart branding deployment complete!"
else
    echo "❌ Failed to deploy corrected branding to VPS"
    exit 1
fi
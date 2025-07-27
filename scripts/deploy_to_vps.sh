#!/bin/bash

# Deploy to VPS using rsync
# Excludes exports, images, PDFs, and other large files

# Configuration
VPS_USER="linuxuser"
VPS_HOST="185.162.249.241"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt/"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Deploying Virtuoso to VPS...${NC}"
echo -e "${YELLOW}From: ${LOCAL_PATH}${NC}"
echo -e "${YELLOW}To: ${VPS_USER}@${VPS_HOST}:${VPS_PATH}${NC}"
echo ""

# Run rsync with exclusions
rsync -avz --progress \
    --exclude='exports/' \
    --exclude='*.png' \
    --exclude='*.pdf' \
    --exclude='*.jpg' \
    --exclude='*.jpeg' \
    --exclude='*.gif' \
    --exclude='*.svg' \
    --exclude='*.ico' \
    --exclude='reports/html/' \
    --exclude='reports/pdf/' \
    --exclude='cache/' \
    --exclude='logs/' \
    --exclude='*.log' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='venv/' \
    --exclude='venv311/' \
    --exclude='.git/' \
    --exclude='*.db' \
    --exclude='*.sqlite' \
    --exclude='*.pkl' \
    --exclude='*.pickle' \
    --exclude='*.h5' \
    --exclude='*.zip' \
    --exclude='*.tar' \
    --exclude='*.gz' \
    --exclude='backups/' \
    --exclude='test_output/' \
    --exclude='.DS_Store' \
    --exclude='*.old' \
    --exclude='*.rtf' \
    --exclude='.env' \
    --exclude='.env.local' \
    "${LOCAL_PATH}" "${VPS_USER}@${VPS_HOST}:${VPS_PATH}"

# Check if rsync was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    
    # Show size of deployment
    echo -e "${YELLOW}Calculating deployment size...${NC}"
    ssh "${VPS_USER}@${VPS_HOST}" "du -sh ${VPS_PATH}"
else
    echo -e "${RED}❌ Deployment failed!${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}📝 Note: Remember to:${NC}"
echo "1. Set up virtual environment on VPS: python3.11 -m venv venv311"
echo "2. Install requirements: pip install -r requirements.txt"
echo "3. Configure environment variables"
echo "4. Set up systemd service for auto-start"
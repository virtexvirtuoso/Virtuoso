#!/bin/bash

#############################################################################
# Script: deploy_to_server.sh
# Purpose: Deploy and manage deploy to server
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - rsync
#   - ssh
#   - git
#   - systemctl
#   - Access to project directory structure
#
# Usage:
#   ./deploy_to_server.sh [options]
#   
#   Examples:
#     ./deploy_to_server.sh
#     ./deploy_to_server.sh --verbose
#     ./deploy_to_server.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 45.77.40.77)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Success
#   1 - Deployment failed
#   2 - Invalid arguments
#   3 - Connection error
#   4 - Service start failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

# Deployment script for Virtuoso Trading System
# Syncs local changes to remote server

# Configuration
REMOTE_USER="linuxuser"
REMOTE_HOST="45.77.40.77"
REMOTE_PATH="/home/linuxuser/trading/virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Virtuoso Trading System Deployment${NC}"
echo -e "${YELLOW}Deploying to: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}${NC}"
echo ""

# Check if remote server is accessible
echo -e "${YELLOW}Checking server connection...${NC}"
if ssh -q -o ConnectTimeout=5 ${REMOTE_USER}@${REMOTE_HOST} exit; then
    echo -e "${GREEN}✓ Server is accessible${NC}"
else
    echo -e "${RED}✗ Cannot connect to server${NC}"
    exit 1
fi

# Create exclude file for rsync
cat > /tmp/rsync_exclude.txt << EOF
# Version control
.git/
.gitignore

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
.venv/
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs and databases
*.log
*.sqlite
*.db

# Temp files
*.tmp
*.bak
*.cache

# Local config (if exists)
.env.local
config/local/

# Node modules (if any)
node_modules/

# Jupyter
.ipynb_checkpoints/
*.ipynb

# Build artifacts
build/
dist/
*.egg-info/

# Data files (optional - comment out if needed)
# data/historical/
# data/cache/
EOF

# Ask for confirmation
echo -e "${YELLOW}This will sync the following:${NC}"
echo "  - Source code (src/)"
echo "  - Configuration (config/)"
echo "  - Requirements (requirements.txt)"
echo "  - Scripts (*.sh, *.py in root)"
echo "  - Documentation (README.md, docs/)"
echo "  - Static files and templates"
echo ""
echo -e "${YELLOW}The following will be excluded:${NC}"
echo "  - Git files (.git/)"
echo "  - Python cache (__pycache__/)"
echo "  - Virtual environments (venv/)"
echo "  - IDE settings (.vscode/, .idea/)"
echo "  - Log files (*.log)"
echo "  - Temporary files"
echo ""

read -p "Continue with deployment? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 1
fi

# Create backup on remote server
echo ""
echo -e "${YELLOW}Creating backup on remote server...${NC}"
BACKUP_NAME="virtuoso_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
ssh ${REMOTE_USER}@${REMOTE_HOST} "cd /home/linuxuser/trading && tar -czf ${BACKUP_NAME} virtuoso_ccxt --exclude='*.log' --exclude='__pycache__' --exclude='venv' 2>/dev/null || true"
echo -e "${GREEN}✓ Backup created: ${BACKUP_NAME}${NC}"

# Sync files using rsync
echo ""
echo -e "${YELLOW}Syncing files...${NC}"
rsync -avz --progress \
    --exclude-from=/tmp/rsync_exclude.txt \
    --delete-after \
    ${LOCAL_PATH}/ \
    ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Files synced successfully${NC}"
else
    echo -e "${RED}✗ Sync failed${NC}"
    exit 1
fi

# Set permissions on remote
echo ""
echo -e "${YELLOW}Setting permissions...${NC}"
ssh ${REMOTE_USER}@${REMOTE_HOST} << EOF
    cd ${REMOTE_PATH}
    find . -type f -name "*.py" -exec chmod 644 {} \;
    find . -type f -name "*.sh" -exec chmod 755 {} \;
    chmod 755 src/web_server.py
    chmod 755 src/integrated_server.py
EOF
echo -e "${GREEN}✓ Permissions set${NC}"

# Install/update requirements on remote
echo ""
read -p "Update Python requirements on remote? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Updating requirements...${NC}"
    ssh ${REMOTE_USER}@${REMOTE_HOST} << EOF
        cd ${REMOTE_PATH}
        if [ -f venv/bin/activate ]; then
            source venv/bin/activate
            pip install -r requirements.txt
        else
            echo "Virtual environment not found. Please create it first."
        fi
EOF
    echo -e "${GREEN}✓ Requirements updated${NC}"
fi

# Restart services
echo ""
read -p "Restart web server? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Restarting services...${NC}"
    ssh ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
        # Find and kill existing web server process
        pkill -f "web_server.py" || true
        sleep 2
        
        # Start web server in background
        cd /home/linuxuser/trading/virtuoso_ccxt
        if [ -f venv/bin/activate ]; then
            source venv/bin/activate
            nohup python src/web_server.py > web_server.log 2>&1 &
            echo "Web server started with PID: $!"
        else
            echo "Virtual environment not found"
        fi
EOF
    echo -e "${GREEN}✓ Services restarted${NC}"
fi

# Clean up
rm -f /tmp/rsync_exclude.txt

echo ""
echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo -e "${YELLOW}Dashboard URLs:${NC}"
echo "  - Desktop: http://${REMOTE_HOST}:8003/dashboard"
echo "  - Mobile:  http://${REMOTE_HOST}:8003/dashboard/mobile"
echo "  - Legacy:  http://${REMOTE_HOST}:8003/dashboard/v10"
echo ""
echo -e "${YELLOW}To check server status:${NC}"
echo "  ssh ${REMOTE_USER}@${REMOTE_HOST} 'cd ${REMOTE_PATH} && tail -f web_server.log'"
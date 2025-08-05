#!/bin/bash

# Deploy Admin URL Update to VPS
# Changes /api/dashboard/admin to /admin

# Configuration
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying Admin URL Update to VPS...${NC}"
echo -e "${YELLOW}Target: ${VPS_USER}@${VPS_HOST}${NC}"
echo -e "${YELLOW}Changes: /api/dashboard/admin → /admin${NC}"
echo ""

# Step 1: Deploy the updated API init file
echo -e "${YELLOW}📤 Deploying updated API routes...${NC}"
scp "${LOCAL_PATH}/src/api/__init__.py" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/__init__.py"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to deploy __init__.py${NC}"
    exit 1
fi

# Step 2: Deploy all updated template files
echo -e "${YELLOW}📤 Deploying updated templates...${NC}"

# Admin dashboard
scp "${LOCAL_PATH}/src/dashboard/templates/admin_dashboard.html" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/dashboard/templates/admin_dashboard.html"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to deploy admin_dashboard.html${NC}"
    exit 1
fi

# Admin login
scp "${LOCAL_PATH}/src/dashboard/templates/admin_login.html" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/dashboard/templates/admin_login.html"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to deploy admin_login.html${NC}"
    exit 1
fi

# Config editor
scp "${LOCAL_PATH}/src/dashboard/templates/admin_config_editor.html" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/dashboard/templates/admin_config_editor.html"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to deploy admin_config_editor.html${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All files deployed successfully!${NC}"
echo ""

# Step 3: Restart the Python process
echo -e "${YELLOW}🔄 Restarting Virtuoso process...${NC}"
ssh "${VPS_USER}@${VPS_HOST}" << 'EOF'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    # Find the Python process
    PID=$(ps aux | grep "python -u src/main.py" | grep -v grep | awk '{print $2}')
    
    if [ ! -z "$PID" ]; then
        echo "Found Virtuoso process with PID: $PID"
        echo "Sending HUP signal to reload..."
        kill -HUP $PID
        sleep 2
        
        # Verify it's still running
        if ps -p $PID > /dev/null; then
            echo "✅ Process reloaded successfully"
        else
            echo "⚠️  Process may have stopped. You may need to restart manually."
        fi
    else
        echo "⚠️  Virtuoso process not found. You may need to start it manually."
    fi
EOF

echo ""
echo -e "${GREEN}🎉 Deployment completed!${NC}"
echo ""
echo -e "${BLUE}📝 URL Changes:${NC}"
echo "  OLD: http://${VPS_HOST}:8003/api/dashboard/admin/*"
echo "  NEW: http://${VPS_HOST}:8003/admin/*"
echo ""
echo -e "${YELLOW}🔗 New Admin URLs:${NC}"
echo "  Login:        http://${VPS_HOST}:8003/admin/login"
echo "  Dashboard:    http://${VPS_HOST}:8003/admin/dashboard"
echo "  Config Editor: http://${VPS_HOST}:8003/admin/config-editor"
echo ""
echo -e "${GREEN}✅ All admin features now accessible at the shorter /admin path!${NC}"
#!/bin/bash
# Sync proprietary indicator files between local and VPS
# These files are NOT in GitHub per IP protection guidelines

# Configuration
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

# Proprietary files that need syncing
PROPRIETARY_FILES=(
    "src/core/analysis/confluence.py"
    "src/indicators/orderflow_indicators.py"
    "src/indicators/volume_indicators.py"
    "src/indicators/sentiment_indicators.py"
    "src/indicators/technical_indicators.py"
    "src/indicators/orderbook_indicators.py"
    "src/indicators/price_structure_indicators.py"
)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to show usage
usage() {
    echo "Usage: $0 [push|pull|status|backup]"
    echo "  push   - Copy local proprietary files to VPS"
    echo "  pull   - Copy VPS proprietary files to local"
    echo "  status - Show modification times of all files"
    echo "  backup - Create timestamped backup of proprietary files"
    exit 1
}

# Function to create backup
backup_files() {
    BACKUP_DIR="backups/proprietary_$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}Creating backup in $BACKUP_DIR${NC}"
    
    mkdir -p "$BACKUP_DIR"
    
    for file in "${PROPRIETARY_FILES[@]}"; do
        if [ -f "$LOCAL_PATH/$file" ]; then
            mkdir -p "$BACKUP_DIR/$(dirname $file)"
            cp "$LOCAL_PATH/$file" "$BACKUP_DIR/$file"
            echo -e "${GREEN}✓${NC} Backed up $file"
        else
            echo -e "${RED}✗${NC} File not found: $file"
        fi
    done
    
    echo -e "${GREEN}Backup complete: $BACKUP_DIR${NC}"
}

# Function to push files to VPS
push_to_vps() {
    echo -e "${YELLOW}Pushing proprietary files to VPS...${NC}"
    
    # First create backup on VPS
    echo "Creating backup on VPS..."
    ssh $VPS_USER@$VPS_HOST "cd $VPS_PATH && mkdir -p backups/proprietary_$(date +%Y%m%d_%H%M%S)"
    
    for file in "${PROPRIETARY_FILES[@]}"; do
        if [ -f "$LOCAL_PATH/$file" ]; then
            # Backup existing file on VPS
            ssh $VPS_USER@$VPS_HOST "cd $VPS_PATH && [ -f $file ] && cp $file backups/proprietary_$(date +%Y%m%d_%H%M%S)/$file || true" 2>/dev/null
            
            # Copy file to VPS
            scp "$LOCAL_PATH/$file" "$VPS_USER@$VPS_HOST:$VPS_PATH/$file"
            echo -e "${GREEN}✓${NC} Pushed $file"
        else
            echo -e "${RED}✗${NC} Local file not found: $file"
        fi
    done
    
    # Restart service
    echo -e "${YELLOW}Restarting Virtuoso service...${NC}"
    ssh $VPS_USER@$VPS_HOST "sudo systemctl restart virtuoso"
    echo -e "${GREEN}Push complete!${NC}"
}

# Function to pull files from VPS
pull_from_vps() {
    echo -e "${YELLOW}Pulling proprietary files from VPS...${NC}"
    
    # First create local backup
    backup_files
    
    for file in "${PROPRIETARY_FILES[@]}"; do
        # Check if file exists on VPS
        if ssh $VPS_USER@$VPS_HOST "[ -f $VPS_PATH/$file ]"; then
            # Create directory if needed
            mkdir -p "$LOCAL_PATH/$(dirname $file)"
            
            # Copy file from VPS
            scp "$VPS_USER@$VPS_HOST:$VPS_PATH/$file" "$LOCAL_PATH/$file"
            echo -e "${GREEN}✓${NC} Pulled $file"
        else
            echo -e "${RED}✗${NC} VPS file not found: $file"
        fi
    done
    
    echo -e "${GREEN}Pull complete!${NC}"
}

# Function to show status
show_status() {
    echo -e "${YELLOW}Proprietary Files Status:${NC}"
    echo "================================================"
    
    for file in "${PROPRIETARY_FILES[@]}"; do
        echo -e "\n${GREEN}$file:${NC}"
        
        # Local file status
        if [ -f "$LOCAL_PATH/$file" ]; then
            LOCAL_TIME=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$LOCAL_PATH/$file" 2>/dev/null || stat -c "%y" "$LOCAL_PATH/$file" 2>/dev/null | cut -d'.' -f1)
            LOCAL_SIZE=$(wc -c < "$LOCAL_PATH/$file" | tr -d ' ')
            echo "  Local:  $LOCAL_TIME (${LOCAL_SIZE} bytes)"
        else
            echo "  Local:  ${RED}NOT FOUND${NC}"
        fi
        
        # VPS file status
        VPS_STAT=$(ssh $VPS_USER@$VPS_HOST "cd $VPS_PATH && [ -f $file ] && stat -c '%y %s' $file 2>/dev/null || echo 'NOT FOUND'" 2>/dev/null)
        if [[ $VPS_STAT == "NOT FOUND" ]]; then
            echo "  VPS:    ${RED}NOT FOUND${NC}"
        else
            VPS_TIME=$(echo $VPS_STAT | cut -d'.' -f1)
            VPS_SIZE=$(echo $VPS_STAT | awk '{print $NF}')
            echo "  VPS:    $VPS_TIME (${VPS_SIZE} bytes)"
        fi
    done
}

# Main script
case "${1:-}" in
    push)
        push_to_vps
        ;;
    pull)
        pull_from_vps
        ;;
    status)
        show_status
        ;;
    backup)
        backup_files
        ;;
    *)
        usage
        ;;
esac
#!/bin/bash

# Update all server references to new Hetzner server IP
# Date: 2025-08-28
# New Hetzner Server IP: VPS_HOST_REDACTED
# Old IPs to replace: 45.77.40.77 (Vultr), 174.166.193.148 (Old)

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Updating Server References to Hetzner${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}New Server IP: VPS_HOST_REDACTED${NC}"
echo -e "${YELLOW}Old IPs: 45.77.40.77, 174.166.193.148${NC}"
echo ""

# Backup important files first
echo -e "${YELLOW}Creating backups of important files...${NC}"
mkdir -p backups/server_update_$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/server_update_$(date +%Y%m%d_%H%M%S)"

# Function to update IP in file
update_ip_in_file() {
    local file="$1"
    local old_ip="$2"
    local new_ip="VPS_HOST_REDACTED"
    
    if grep -q "$old_ip" "$file"; then
        echo -e "${YELLOW}Updating $file${NC}"
        # Create backup
        cp "$file" "$BACKUP_DIR/$(basename $file).bak" 2>/dev/null || true
        # Replace IP
        sed -i '' "s/$old_ip/$new_ip/g" "$file"
        echo -e "${GREEN}✓ Updated $file${NC}"
    fi
}

# Update all shell scripts
echo -e "\n${YELLOW}Updating shell scripts...${NC}"
for script in scripts/**/*.sh scripts/*.sh; do
    if [[ -f "$script" ]]; then
        update_ip_in_file "$script" "45.77.40.77"
        update_ip_in_file "$script" "174.166.193.148"
    fi
done

# Update Python files
echo -e "\n${YELLOW}Updating Python files...${NC}"
for pyfile in scripts/**/*.py scripts/*.py src/**/*.py src/*.py *.py; do
    if [[ -f "$pyfile" ]]; then
        update_ip_in_file "$pyfile" "45.77.40.77"
        update_ip_in_file "$pyfile" "174.166.193.148"
    fi
done

# Update documentation files
echo -e "\n${YELLOW}Updating documentation files...${NC}"
for doc in *.md docs/*.md; do
    if [[ -f "$doc" ]]; then
        update_ip_in_file "$doc" "45.77.40.77"
        update_ip_in_file "$doc" "174.166.193.148"
    fi
done

# Update environment files (be careful with .env)
echo -e "\n${YELLOW}Checking environment files...${NC}"
if [[ -f ".env" ]]; then
    echo -e "${YELLOW}Found .env file - please update manually if needed${NC}"
    grep -E "45\.77\.40\.77|174\.166\.193\.148" .env || echo "No old IPs found in .env"
fi

# Update SSH config if it exists
echo -e "\n${YELLOW}Updating SSH config...${NC}"
SSH_CONFIG="$HOME/.ssh/config"
if [[ -f "$SSH_CONFIG" ]]; then
    if grep -q "45.77.40.77\|174.166.193.148" "$SSH_CONFIG"; then
        echo -e "${YELLOW}SSH config contains old IPs - updating...${NC}"
        cp "$SSH_CONFIG" "$BACKUP_DIR/ssh_config.bak"
        sed -i '' 's/45\.77\.40\.77/VPS_HOST_REDACTED/g' "$SSH_CONFIG"
        sed -i '' 's/174\.166\.193\.148/VPS_HOST_REDACTED/g' "$SSH_CONFIG"
        echo -e "${GREEN}✓ Updated SSH config${NC}"
    fi
fi

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Update Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo -e "- All scripts updated to use new IP: VPS_HOST_REDACTED"
echo -e "- Backups saved in: $BACKUP_DIR"
echo -e ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "1. Review the changes with: git diff"
echo -e "2. Test connections to new server"
echo -e "3. Update any external services/webhooks"
echo -e "4. Commit changes when verified"
echo ""

# Show files that were updated
echo -e "${YELLOW}Files updated:${NC}"
git diff --name-only | head -20

echo -e "\n${GREEN}Done!${NC}"
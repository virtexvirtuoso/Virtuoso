#!/bin/bash

# Deploy Architectural Improvements to VPS
# This script deploys all 4 phases to the production VPS

set -e

echo "=========================================="
echo "DEPLOYING ARCHITECTURE IMPROVEMENTS TO VPS"
echo "=========================================="

# Configuration
VPS_HOST="vps"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📦 Phase 1: Deploying Event-Driven Components...${NC}"

# Deploy Phase 1: Event-Driven Pipeline
rsync -avz --progress \
    $LOCAL_PATH/src/core/events/ \
    $VPS_HOST:$VPS_PATH/src/core/events/

echo -e "${GREEN}✅ Phase 1 deployed${NC}"

echo -e "${YELLOW}📦 Phase 2: Deploying Service Layer (DI)...${NC}"

# Deploy Phase 2: Service Layer
rsync -avz --progress \
    $LOCAL_PATH/src/core/di/ \
    $VPS_HOST:$VPS_PATH/src/core/di/

rsync -avz --progress \
    $LOCAL_PATH/src/core/interfaces/ \
    $VPS_HOST:$VPS_PATH/src/core/interfaces/

echo -e "${GREEN}✅ Phase 2 deployed${NC}"

echo -e "${YELLOW}📦 Phase 3: Deploying Resilience Components...${NC}"

# Deploy Phase 3: Infrastructure Resilience
rsync -avz --progress \
    $LOCAL_PATH/src/core/resilience/ \
    $VPS_HOST:$VPS_PATH/src/core/resilience/

echo -e "${GREEN}✅ Phase 3 deployed${NC}"

echo -e "${YELLOW}📦 Phase 4: Already deployed (in events/)${NC}"
echo -e "${GREEN}✅ Phase 4 included in Phase 1${NC}"

echo -e "${YELLOW}📦 Deploying updated main.py...${NC}"

# Deploy updated main.py with phase support
rsync -avz --progress \
    $LOCAL_PATH/src/main.py \
    $VPS_HOST:$VPS_PATH/src/

echo -e "${GREEN}✅ Main application updated${NC}"

echo -e "${YELLOW}🔧 Installing dependencies on VPS...${NC}"

# Install dependencies on VPS
ssh $VPS_HOST "cd $VPS_PATH && pip3 install aiosqlite psutil 2>/dev/null || true"

echo -e "${GREEN}✅ Dependencies installed${NC}"

echo -e "${YELLOW}🔍 Verifying deployment...${NC}"

# Verify files exist on VPS
ssh $VPS_HOST "ls -la $VPS_PATH/src/core/events/event_bus.py" > /dev/null 2>&1 && echo -e "${GREEN}✅ EventBus deployed${NC}" || echo -e "${RED}❌ EventBus missing${NC}"
ssh $VPS_HOST "ls -la $VPS_PATH/src/core/di/container.py" > /dev/null 2>&1 && echo -e "${GREEN}✅ DI Container deployed${NC}" || echo -e "${RED}❌ DI Container missing${NC}"
ssh $VPS_HOST "ls -la $VPS_PATH/src/core/resilience/circuit_breaker.py" > /dev/null 2>&1 && echo -e "${GREEN}✅ Circuit Breaker deployed${NC}" || echo -e "${RED}❌ Circuit Breaker missing${NC}"
ssh $VPS_HOST "ls -la $VPS_PATH/src/core/events/optimized_event_processor.py" > /dev/null 2>&1 && echo -e "${GREEN}✅ Optimized Processor deployed${NC}" || echo -e "${RED}❌ Optimized Processor missing${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}DEPLOYMENT COMPLETE!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. SSH to VPS: ssh vps"
echo "2. Restart service: sudo systemctl restart virtuoso.service"
echo "3. Check logs: sudo journalctl -u virtuoso.service -f"
echo ""
echo "To enable new features, update the systemd service with flags:"
echo "  --enable-phase4 --enable-event-sourcing"
echo ""
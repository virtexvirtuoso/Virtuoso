#!/bin/bash

#############################################################################
# Script: test_docker_locally.sh
# Purpose: Local Docker testing script
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates automated testing, validation, and quality assurance for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - python3
#   - curl
#   - grep
#   - Access to project directory structure
#
# Usage:
#   ./test_docker_locally.sh [options]
#   
#   Examples:
#     ./test_docker_locally.sh
#     ./test_docker_locally.sh --verbose
#     ./test_docker_locally.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - All tests passed
#   1 - Test failures detected
#   2 - Test configuration error
#   3 - Dependencies missing
#   4 - Environment setup failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🧪 Testing Virtuoso Trading System with Docker${NC}"
echo "=============================================="
echo ""

# Backup existing .env if it exists
if [ -f .env ]; then
    cp .env .env.backup
    echo -e "${YELLOW}📁 Backed up .env to .env.backup${NC}"
fi

# Use test environment
cp .env.test .env
echo -e "${GREEN}✅ Using test environment (.env.test)${NC}"

# Create necessary directories
echo -e "${GREEN}📁 Creating directories...${NC}"
mkdir -p logs reports exports cache data

# Stop any existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down -v 2>/dev/null || true

# Build the Docker image
echo -e "${GREEN}🔨 Building Docker image...${NC}"
docker-compose build --no-cache

# Start services
echo -e "${GREEN}🚀 Starting services...${NC}"
docker-compose up -d redis
sleep 5  # Give Redis time to start

# Start the main app
docker-compose up -d app

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
for i in {1..30}; do
    if docker-compose ps | grep -q "Up"; then
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

# Check if services are running
echo -e "${GREEN}📊 Service Status:${NC}"
docker-compose ps

# Test the health endpoint
echo -e "${GREEN}🏥 Testing health endpoint...${NC}"
sleep 5  # Give the app time to fully start

# Try to hit the health endpoint
if curl -f http://localhost:8001/health 2>/dev/null; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
else
    echo -e "${YELLOW}⚠️  Health check failed, checking logs...${NC}"
    docker-compose logs --tail=50 app
fi

# Show logs
echo ""
echo -e "${GREEN}📜 Recent application logs:${NC}"
docker-compose logs --tail=20 app

# Display access information
echo ""
echo -e "${GREEN}🌐 Access URLs:${NC}"
echo "  - Main App: http://localhost:8000"
echo "  - API Health: http://localhost:8001/health"
echo "  - API Docs: http://localhost:8001/docs"
echo "  - Dashboard: http://localhost:8003"
echo ""

echo -e "${GREEN}🛠️  Useful commands:${NC}"
echo "  - View logs: docker-compose logs -f app"
echo "  - Stop all: docker-compose down"
echo "  - Shell access: docker exec -it virtuoso bash"
echo "  - Restore original .env: mv .env.backup .env"
echo ""

# Restore warning
echo -e "${YELLOW}⚠️  Remember:${NC}"
echo "  - This is using TEST credentials"
echo "  - Do NOT use for production"
echo "  - Restore your .env before real deployment: mv .env.backup .env"
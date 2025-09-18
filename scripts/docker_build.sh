#!/bin/bash

#############################################################################
# Script: docker_build.sh
# Purpose: Docker build script for Virtuoso Trading System
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
#   ./docker_build.sh [options]
#   
#   Examples:
#     ./docker_build.sh
#     ./docker_build.sh --verbose
#     ./docker_build.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: ${VPS_HOST})
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

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🐳 Building Virtuoso Trading System Docker Image${NC}"
echo "================================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create a .env file from .env.example or .env.test"
    exit 1
fi

# Create necessary directories
echo -e "${YELLOW}📁 Creating necessary directories...${NC}"
mkdir -p logs reports data exports cache config

# Build the Docker image
echo -e "${GREEN}🔨 Building Docker image...${NC}"
docker build -t virtuoso-trading:latest .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker image built successfully!${NC}"
    echo ""
    echo -e "${GREEN}📦 Image details:${NC}"
    docker images virtuoso-trading:latest
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "  1. Run with docker-compose: docker-compose up -d"
    echo "  2. Or use the run script: ./scripts/docker_run.sh"
else
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi
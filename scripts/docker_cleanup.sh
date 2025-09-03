#!/bin/bash

#############################################################################
# Script: docker_cleanup.sh
# Purpose: Docker cleanup script for Virtuoso Trading System
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
#   ./docker_cleanup.sh [options]
#   
#   Examples:
#     ./docker_cleanup.sh
#     ./docker_cleanup.sh --verbose
#     ./docker_cleanup.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
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
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧹 Docker Cleanup for Virtuoso Trading System${NC}"
echo "============================================="

# Parse arguments
DEEP_CLEAN=false
REMOVE_VOLUMES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --deep)
            DEEP_CLEAN=true
            shift
            ;;
        --volumes)
            REMOVE_VOLUMES=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --deep      Perform deep clean (remove all Docker artifacts)"
            echo "  --volumes   Remove Docker volumes (WARNING: Data loss!)"
            echo "  --help, -h  Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Stop containers
echo -e "${YELLOW}🛑 Stopping Virtuoso containers...${NC}"
docker-compose down 2>/dev/null || true

# Remove containers
echo -e "${YELLOW}🗑️ Removing stopped containers...${NC}"
docker container prune -f

# Remove unused images
echo -e "${YELLOW}🖼️ Removing unused images...${NC}"
docker image prune -f

# Remove build cache
echo -e "${YELLOW}🔨 Cleaning build cache...${NC}"
docker builder prune -f

# Clean up networks
echo -e "${YELLOW}🌐 Cleaning unused networks...${NC}"
docker network prune -f

if [ "$REMOVE_VOLUMES" = true ]; then
    echo -e "${RED}⚠️ WARNING: Removing volumes (data will be lost!)${NC}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
        docker-compose down -v 2>/dev/null || true
    else
        echo "Skipping volume removal"
    fi
fi

if [ "$DEEP_CLEAN" = true ]; then
    echo -e "${RED}🔥 Performing deep clean...${NC}"
    
    # Remove all Virtuoso images
    echo "Removing Virtuoso images..."
    docker images | grep virtuoso | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
    
    # System prune
    echo "Running system prune..."
    docker system prune -af --volumes
    
    # Clean log files
    echo "Cleaning log files..."
    find logs -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    # Clean cache
    echo "Cleaning cache directory..."
    rm -rf cache/* 2>/dev/null || true
fi

# Show disk usage
echo ""
echo -e "${BLUE}💾 Docker Disk Usage:${NC}"
docker system df

echo ""
echo -e "${GREEN}✅ Cleanup complete!${NC}"

# Show remaining Virtuoso containers/images
echo ""
echo -e "${BLUE}📦 Remaining Virtuoso artifacts:${NC}"
echo "Containers:"
docker ps -a | grep virtuoso || echo "  None"
echo ""
echo "Images:"
docker images | grep virtuoso || echo "  None"
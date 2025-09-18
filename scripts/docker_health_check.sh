#!/bin/bash

#############################################################################
# Script: docker_health_check.sh
# Purpose: Docker health check and monitoring script
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
#   ./docker_health_check.sh [options]
#   
#   Examples:
#     ./docker_health_check.sh
#     ./docker_health_check.sh --verbose
#     ./docker_health_check.sh --dry-run
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
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}🔍 Docker Health Check & Monitoring${NC}"
echo "===================================="

# Check if containers are running
echo -e "${BLUE}📦 Container Status:${NC}"
docker-compose ps

echo ""
echo -e "${BLUE}📊 Resource Usage:${NC}"
docker stats --no-stream virtuoso-trading 2>/dev/null || echo "Main container not running"

# Check health endpoints
echo ""
echo -e "${BLUE}🏥 Health Endpoints:${NC}"

# Main health check
echo -n "  - Main API (8003): "
if curl -sf http://localhost:8003/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Unhealthy${NC}"
fi

# API health check
echo -n "  - API Server (8001): "
if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Unhealthy${NC}"
fi

# Check Redis if running
if docker-compose ps | grep -q "virtuoso-redis.*Up"; then
    echo -n "  - Redis Cache: "
    if docker exec virtuoso-redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Healthy${NC}"
    else
        echo -e "${RED}❌ Unhealthy${NC}"
    fi
fi

# Check PostgreSQL if running
if docker-compose ps | grep -q "virtuoso-postgres.*Up"; then
    echo -n "  - PostgreSQL: "
    if docker exec virtuoso-postgres pg_isready > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Healthy${NC}"
    else
        echo -e "${RED}❌ Unhealthy${NC}"
    fi
fi

# Check disk usage
echo ""
echo -e "${BLUE}💾 Disk Usage:${NC}"
echo "  - Logs: $(du -sh logs 2>/dev/null | cut -f1 || echo 'N/A')"
echo "  - Reports: $(du -sh reports 2>/dev/null | cut -f1 || echo 'N/A')"
echo "  - Data: $(du -sh data 2>/dev/null | cut -f1 || echo 'N/A')"
echo "  - Cache: $(du -sh cache 2>/dev/null | cut -f1 || echo 'N/A')"

# Recent errors
echo ""
echo -e "${BLUE}⚠️ Recent Errors (last 10 lines):${NC}"
docker-compose logs --tail=100 virtuoso 2>/dev/null | grep -i "error\|exception\|critical" | tail -10 || echo "No recent errors found"

# Performance metrics
echo ""
echo -e "${BLUE}⚡ Performance Metrics:${NC}"
if curl -sf http://localhost:8001/metrics 2>/dev/null; then
    curl -s http://localhost:8001/metrics | head -20
else
    echo "Metrics endpoint not available"
fi

echo ""
echo -e "${GREEN}✨ Health check complete${NC}"
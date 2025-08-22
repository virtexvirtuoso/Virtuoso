#!/bin/bash
# Docker health check and monitoring script

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
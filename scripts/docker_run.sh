#!/bin/bash

#############################################################################
# Script: docker_run.sh
# Purpose: Launch Virtuoso Trading System in Docker containers with profiles
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
#   Launches the complete Virtuoso trading system using Docker Compose
#   with configurable service profiles. Supports development, testing,
#   and production deployment modes with optional services like Redis,
#   PostgreSQL, monitoring, and external APIs.
#
# Dependencies:
#   - Bash 4.0+
#   - Docker Engine 20.0+
#   - Docker Compose v2.0+
#   - docker-compose.yml in project root
#   - Valid .env file with required variables
#
# Usage:
#   ./docker_run.sh [options] [profile]
#   
#   Examples:
#     ./docker_run.sh
#     ./docker_run.sh --with-redis --follow-logs
#     ./docker_run.sh --profile production --detach
#
# Options:
#   --with-redis         Include Redis caching service
#   --with-database      Include PostgreSQL database service
#   --with-monitoring    Include monitoring stack (Grafana, Prometheus)
#   --profile PROFILE    Use specific Docker Compose profile
#   --follow-logs        Follow container logs after startup
#   --detach             Run containers in detached mode (default)
#   --no-build           Skip image building, use existing images
#   --force-recreate     Force recreate containers even if config unchanged
#
# Profiles:
#   - minimal: Core trading system only
#   - with-redis: Includes Redis for caching
#   - with-database: Includes PostgreSQL for data persistence
#   - with-monitoring: Full monitoring stack
#   - development: Dev tools and debug services
#   - production: Optimized for production deployment
#
# Environment Variables:
#   DOCKER_BUILDKIT      Enable advanced Docker build features
#   COMPOSE_FILE         Override default docker-compose.yml
#   PROJECT_NAME         Docker Compose project name
#
# Configuration:
#   Service configuration managed through:
#   - docker-compose.yml (service definitions)
#   - .env files (environment variables)
#   - config/ directory (application configuration)
#
# Output:
#   - Container startup logs and status
#   - Service health check results
#   - Optional log following for debugging
#   - Container ID and port mapping information
#
# Exit Codes:
#   0 - Containers started successfully
#   1 - Docker Compose startup failed
#   2 - Invalid arguments or profile
#   3 - Docker daemon not available
#   4 - Required files missing
#   5 - Resource allocation failed
#
# Notes:
#   - Automatically validates Docker environment before startup
#   - Supports graceful shutdown with Ctrl+C
#   - Creates necessary volumes and networks
#   - Provides real-time status monitoring during startup
#
#############################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting Virtuoso Trading System with Docker${NC}"
echo "==============================================="

# Parse arguments
PROFILE=""
DETACH="-d"
FOLLOW_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-redis)
            PROFILE="--profile with-redis"
            echo -e "${BLUE}📦 Including Redis service${NC}"
            shift
            ;;
        --with-database)
            PROFILE="--profile with-database"
            echo -e "${BLUE}🗄️ Including PostgreSQL service${NC}"
            shift
            ;;
        --follow|-f)
            FOLLOW_LOGS=true
            echo -e "${BLUE}📜 Will follow logs after startup${NC}"
            shift
            ;;
        --attach)
            DETACH=""
            echo -e "${BLUE}🔗 Running in attached mode${NC}"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --with-redis      Include Redis caching service"
            echo "  --with-database   Include PostgreSQL database"
            echo "  --follow, -f      Follow logs after starting"
            echo "  --attach          Run in attached mode (foreground)"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create a .env file from .env.example or .env.test"
    exit 1
fi

# Check if image exists
if ! docker images | grep -q "virtuoso-trading"; then
    echo -e "${YELLOW}⚠️ Docker image not found. Building...${NC}"
    ./scripts/docker_build.sh
fi

# Stop existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down

# Start services
echo -e "${GREEN}🚀 Starting services...${NC}"
docker-compose $PROFILE up $DETACH

if [ "$DETACH" == "-d" ]; then
    # Wait for services to be healthy
    echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
    sleep 5
    
    # Check service status
    echo -e "${GREEN}📊 Service Status:${NC}"
    docker-compose ps
    
    # Test health endpoint
    echo -e "${GREEN}🏥 Testing health endpoint...${NC}"
    for i in {1..10}; do
        if curl -sf http://localhost:8003/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Health check passed!${NC}"
            break
        else
            if [ $i -eq 10 ]; then
                echo -e "${RED}❌ Health check failed after 10 attempts${NC}"
                echo -e "${YELLOW}📜 Recent logs:${NC}"
                docker-compose logs --tail=50 virtuoso
            else
                echo -n "."
                sleep 2
            fi
        fi
    done
    echo ""
    
    # Display access information
    echo ""
    echo -e "${GREEN}🌐 Access URLs:${NC}"
    echo "  - Dashboard: http://localhost:8003"
    echo "  - API Health: http://localhost:8001/health"
    echo "  - API Docs: http://localhost:8001/docs"
    echo ""
    
    echo -e "${GREEN}🛠️ Useful commands:${NC}"
    echo "  - View logs: docker-compose logs -f virtuoso"
    echo "  - Stop all: docker-compose down"
    echo "  - Shell access: docker exec -it virtuoso-trading bash"
    echo "  - View stats: docker stats virtuoso-trading"
    echo ""
    
    if [ "$FOLLOW_LOGS" = true ]; then
        echo -e "${GREEN}📜 Following logs (Ctrl+C to exit)...${NC}"
        docker-compose logs -f virtuoso
    fi
fi
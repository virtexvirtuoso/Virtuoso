#!/bin/bash
# Docker run script for Virtuoso Trading System

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
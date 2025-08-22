#!/bin/bash
# Docker build script for Virtuoso Trading System

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
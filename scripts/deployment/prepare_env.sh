#!/bin/bash
# Environment Preparation Script for Virtuoso Trading System

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔧 Virtuoso Trading System - Environment Setup${NC}"
echo "============================================="
echo ""

# Function to generate secure random string
generate_secret() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# Check if .env exists
if [ -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
    read -p "Do you want to backup and create a new one? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        echo -e "${GREEN}✅ Backed up existing .env${NC}"
    else
        echo "Keeping existing .env file"
        exit 0
    fi
fi

# Copy from example
if [ -f .env.example ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env from .env.example${NC}"
else
    echo -e "${RED}❌ No .env.example found!${NC}"
    exit 1
fi

echo ""
echo "Setting up your environment variables..."
echo ""

# Get user inputs
read -p "Enter your Bybit API Key (or press Enter to skip): " BYBIT_KEY
read -s -p "Enter your Bybit API Secret (or press Enter to skip): " BYBIT_SECRET
echo
read -p "Enter your Discord Webhook URL (or press Enter to skip): " DISCORD_WEBHOOK
read -p "Enter your InfluxDB URL [http://localhost:8086]: " INFLUX_URL
INFLUX_URL=${INFLUX_URL:-http://localhost:8086}

# Generate secure tokens
echo ""
echo -e "${GREEN}Generating secure tokens...${NC}"
INFLUX_TOKEN=$(generate_secret)
JWT_SECRET=$(generate_secret)

# Update .env file
if [ ! -z "$BYBIT_KEY" ]; then
    sed -i.bak "s|BYBIT_API_KEY=.*|BYBIT_API_KEY=$BYBIT_KEY|" .env
fi

if [ ! -z "$BYBIT_SECRET" ]; then
    sed -i.bak "s|BYBIT_API_SECRET=.*|BYBIT_API_SECRET=$BYBIT_SECRET|" .env
fi

if [ ! -z "$DISCORD_WEBHOOK" ]; then
    sed -i.bak "s|DISCORD_WEBHOOK_URL=.*|DISCORD_WEBHOOK_URL=$DISCORD_WEBHOOK|" .env
fi

# Always update these with secure values
sed -i.bak "s|INFLUXDB_URL=.*|INFLUXDB_URL=$INFLUX_URL|" .env
sed -i.bak "s|INFLUXDB_TOKEN=.*|INFLUXDB_TOKEN=$INFLUX_TOKEN|" .env
sed -i.bak "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|" .env

# Set production mode
sed -i.bak "s|DEBUG=.*|DEBUG=false|" .env
sed -i.bak "s|DEVELOPMENT_MODE=.*|DEVELOPMENT_MODE=false|" .env

# Clean up backup files
rm -f .env.bak

echo ""
echo -e "${GREEN}✅ Environment setup complete!${NC}"
echo ""
echo "Generated secure tokens for:"
echo "  - InfluxDB Token"
echo "  - JWT Secret Key"
echo ""
echo -e "${YELLOW}⚠️  Important next steps:${NC}"
echo "1. Review .env file and update any remaining placeholders"
echo "2. Ensure all API credentials are valid"
echo "3. Keep your .env file secure and never commit it to git"
echo ""
echo "You can now run the deployment:"
echo "  - Docker: ./scripts/deployment/deploy_docker.sh"
echo "  - Manual: ./scripts/deployment/deploy_vps.sh"
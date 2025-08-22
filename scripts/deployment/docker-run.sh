#!/bin/bash

# Docker run script for Virtuoso Trading System

set -e

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your settings."
    exit 1
fi

# Create necessary directories
mkdir -p logs reports data

# Run the container
docker run -d \
    --name virtuoso-trading \
    --restart unless-stopped \
    -p 8003:8003 \
    -v $(pwd)/logs:/app/logs \
    -v $(pwd)/reports:/app/reports \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/config:/app/config:ro \
    --env-file .env \
    --memory="4g" \
    --memory-swap="5g" \
    --cpus="2" \
    virtuoso-trading:latest

echo "Virtuoso Trading System started!"
echo ""
echo "Container name: virtuoso-trading"
echo "API endpoint: http://localhost:8003"
echo ""
echo "View logs:"
echo "  docker logs -f virtuoso-trading"
echo ""
echo "Stop container:"
echo "  docker stop virtuoso-trading"
echo ""
echo "Remove container:"
echo "  docker rm virtuoso-trading"
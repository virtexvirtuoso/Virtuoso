#!/bin/bash

# Docker build script for Virtuoso Trading System

set -e

echo "Building Virtuoso Trading System Docker image..."

# Build the Docker image
docker build -t virtuoso-trading:latest .

echo "Build complete!"
echo ""
echo "To run the container:"
echo "  ./docker-run.sh"
echo ""
echo "Or use docker-compose:"
echo "  docker-compose up -d"
#!/bin/bash
# Simple Docker test script

set -e

echo "🧪 Simple Docker Test for Virtuoso Trading System"
echo "================================================"
echo ""

# Clean up any existing containers
echo "🧹 Cleaning up..."
docker-compose down 2>/dev/null || true
docker system prune -f

# Build only the app service
echo "🔨 Building Docker image..."
docker-compose build app

echo ""
echo "✅ Docker build completed successfully!"
echo ""
echo "To run the full test:"
echo "  docker-compose up -d"
echo ""
echo "To check logs:"
echo "  docker-compose logs -f"
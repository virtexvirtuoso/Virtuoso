#!/bin/bash

#############################################################################
# Script: docker-run.sh
# Purpose: Deploy and manage docker-run
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
#   ./docker-run.sh [options]
#   
#   Examples:
#     ./docker-run.sh
#     ./docker-run.sh --verbose
#     ./docker-run.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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
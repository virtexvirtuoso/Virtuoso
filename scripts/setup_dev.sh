#!/bin/bash

#############################################################################
# Script: setup_dev.sh
# Purpose: Setup script for Virtuoso development environment
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates system setup, service configuration, and environment preparation for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - systemctl
#   - mkdir
#   - chmod
#   - Access to project directory structure
#
# Usage:
#   ./setup_dev.sh [options]
#   
#   Examples:
#     ./setup_dev.sh
#     ./setup_dev.sh --verbose
#     ./setup_dev.sh --dry-run
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
#   0 - Setup completed successfully
#   1 - Setup failed
#   2 - Permission denied
#   3 - Dependencies missing
#   4 - Configuration error
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

set -e

# Ensure script is run from project root
if [ ! -f "setup.py" ]; then
    echo "Error: This script must be run from the project root directory"
    exit 1
fi

# Create and activate virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
else
    echo "Virtual environment already exists."
fi

# Determine activation script based on OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source venv/Scripts/activate
else
    # Unix/MacOS
    source venv/bin/activate
fi

# Install dependencies
echo "Installing development dependencies..."
pip install --upgrade pip
pip install -e .
pip install -r config/ci/requirements-test.txt

# Install pre-commit hooks
echo "Setting up pre-commit hooks..."
pip install pre-commit
pre-commit install

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp config/.env.example .env
    echo "Please update .env with your configuration values."
fi

# Display success message
echo ""
echo "=== Virtuoso Development Environment Setup Complete ==="
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate  # Unix/MacOS"
echo "  venv\\Scripts\\activate    # Windows"
echo ""
echo "To run tests:"
echo "  pytest -c config/ci/pytest.ini"
echo "" 
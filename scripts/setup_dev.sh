#!/bin/bash
# Setup script for Virtuoso development environment

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
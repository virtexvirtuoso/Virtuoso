#!/bin/bash
# Virtuoso MCP Server - Development Init Script
# Run this to set up and test the MCP server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== Virtuoso MCP Server Development Environment ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# Check Python version
echo "Checking Python..."
python3 --version

# Check if venv exists and activate
if [ -d "$PROJECT_ROOT/venv311" ]; then
    echo "Activating venv311..."
    source "$PROJECT_ROOT/venv311/bin/activate"
else
    echo "Warning: venv311 not found, using system Python"
fi

# Check dependencies
echo ""
echo "Checking dependencies..."
pip show fastmcp > /dev/null 2>&1 && echo "✓ fastmcp installed" || echo "✗ fastmcp NOT installed (run: pip install fastmcp)"
pip show httpx > /dev/null 2>&1 && echo "✓ httpx installed" || echo "✗ httpx NOT installed (run: pip install httpx)"
pip show pydantic-settings > /dev/null 2>&1 && echo "✓ pydantic-settings installed" || echo "✗ pydantic-settings NOT installed (run: pip install pydantic-settings)"

# Check VPS connectivity (uses environment variables)
echo ""
echo "Checking VPS connectivity..."
VPS_HOST="${VIRTUOSO_MCP_VPS_HOST:-localhost}"
API_URL="${VIRTUOSO_MCP_VIRTUOSO_API_URL:-http://$VPS_HOST:8002}"
DERIV_URL="${VIRTUOSO_MCP_VIRTUOSO_DERIVATIVES_URL:-http://$VPS_HOST:8888}"

if curl -s --connect-timeout 5 "$API_URL/api/health" > /dev/null 2>&1; then
    echo "✓ API server reachable ($API_URL)"
else
    echo "✗ API server not reachable ($API_URL) - may affect testing"
fi

if curl -s --connect-timeout 5 "$DERIV_URL/health" > /dev/null 2>&1; then
    echo "✓ Derivatives server reachable ($DERIV_URL)"
else
    echo "✗ Derivatives server not reachable ($DERIV_URL) - may affect testing"
fi

# Run MCP server in development mode
echo ""
echo "=== Starting MCP Server ==="
echo "Press Ctrl+C to stop"
echo ""

cd "$SCRIPT_DIR"
python -m server

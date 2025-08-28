#!/bin/bash

# Install missing dependencies on VPS for refactored components

echo "📦 Installing Dependencies on VPS"
echo "================================="

VPS="linuxuser@45.77.40.77"

echo "Installing required Python packages..."

ssh $VPS << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "🔍 Checking and installing missing packages..."

# Install missing packages
pip3 install --user prettytable cachetools --quiet

# Check if packages are installed
python3 -c "
import sys
print('Checking installed packages:')
try:
    import prettytable
    print('  ✅ prettytable installed')
except ImportError:
    print('  ❌ prettytable missing')
    
try:
    import cachetools
    print('  ✅ cachetools installed')
except ImportError:
    print('  ❌ cachetools missing')
"

echo "✅ Dependencies installation complete"
ENDSSH

echo ""
echo "Dependencies installed. Ready to test refactored components!"
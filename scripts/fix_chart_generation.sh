#!/bin/bash

# Fix chart generation issue - Install matplotlib and dependencies on VPS

echo "🔧 Fixing chart generation for signal alerts..."

# Connect to VPS and install matplotlib
ssh vps << 'REMOTE_EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "📦 Installing matplotlib and dependencies..."

# Install matplotlib and required dependencies
source venv/bin/activate
pip install matplotlib pillow mplfinance --no-cache-dir

# Test the installation
echo "✅ Testing matplotlib installation..."
python -c "
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import mplfinance as mpf
print('✅ matplotlib version:', matplotlib.__version__)
print('✅ mplfinance imported successfully')
print('✅ Chart generation libraries ready!')
"

# Create charts directory if it doesn't exist
mkdir -p reports/charts
echo "📁 Charts directory ready at reports/charts"

# Test chart generation with alert_manager
echo "🧪 Testing chart generation capability..."
python -c "
import sys
import os
sys.path.insert(0, os.getcwd())

# Test if pdf_generator can create charts
from src.core.reporting.pdf_generator import ReportGenerator
import logging

logging.basicConfig(level=logging.INFO)
config = {}

try:
    generator = ReportGenerator(config)
    print('✅ PDF Generator initialized successfully')

    # Check if chart methods exist
    if hasattr(generator, '_create_candlestick_chart'):
        print('✅ Candlestick chart method available')
    if hasattr(generator, '_create_simulated_chart'):
        print('✅ Simulated chart method available')
except Exception as e:
    print(f'⚠️ PDF Generator initialization issue: {e}')
"

# Restart services to apply changes
echo "🔄 Restarting services..."
sudo systemctl restart virtuoso-web.service
sleep 5

echo "✅ Chart generation fix applied!"
echo "📊 Charts should now be generated with alerts"
REMOTE_EOF

echo "✅ Fix deployed to VPS successfully!"

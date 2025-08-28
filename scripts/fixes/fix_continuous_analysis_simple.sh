#!/bin/bash

echo "🔧 Applying simple fix for ContinuousAnalysisManager..."

# Create backup
ssh linuxuser@45.77.40.77 "cp /home/linuxuser/trading/Virtuoso_ccxt/src/main.py /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_simple"

# Fix 1: Add market_data_manager to global declaration at line 3183
ssh linuxuser@45.77.40.77 "sed -i '3183s/global confluence_analyzer, top_symbols_manager, market_monitor/global confluence_analyzer, top_symbols_manager, market_monitor, market_data_manager/' /home/linuxuser/trading/Virtuoso_ccxt/src/main.py"

# Fix 2: Extract market_data_manager from components after line 3204
ssh linuxuser@45.77.40.77 "sed -i '/market_monitor = components\[.market_monitor.\]/a\    market_data_manager = components[\"market_data_manager\"]  # Extract for ContinuousAnalysisManager' /home/linuxuser/trading/Virtuoso_ccxt/src/main.py"

# Validate syntax
echo "🔍 Validating Python syntax..."
if ssh linuxuser@45.77.40.77 "cd /home/linuxuser/trading/Virtuoso_ccxt && /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -m py_compile src/main.py 2>&1"; then
    echo "✅ Python syntax validation passed!"
    
    # Restart service
    echo "🔄 Restarting service..."
    ssh linuxuser@45.77.40.77 "sudo systemctl restart virtuoso.service"
    
    # Wait for startup
    sleep 10
    
    # Check for success
    echo "📊 Checking if ContinuousAnalysisManager started..."
    if ssh linuxuser@45.77.40.77 "sudo journalctl -u virtuoso.service --since '1 minute ago' | grep -q 'Continuous analysis manager started'"; then
        echo "✅ SUCCESS! ContinuousAnalysisManager is now running!"
    else
        echo "⚠️ Check logs to verify status"
    fi
    
    # Show recent logs
    echo -e "\n📝 Recent logs:"
    ssh linuxuser@45.77.40.77 "sudo journalctl -u virtuoso.service --since '30 seconds ago' | grep -E 'ContinuousAnalysisManager|analysis.*cache|WARNING.*market_data_manager' | tail -5"
else
    echo "❌ Syntax validation failed - restoring backup"
    ssh linuxuser@45.77.40.77 "mv /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_simple /home/linuxuser/trading/Virtuoso_ccxt/src/main.py"
fi

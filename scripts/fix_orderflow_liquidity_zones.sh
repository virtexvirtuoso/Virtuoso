#!/bin/bash

echo "Fixing liquidity_zones undefined error in orderflow_indicators.py"

# Apply the fix directly on VPS
ssh linuxuser@45.77.40.77 << 'REMOTE_FIX'
# Fix the undefined liquidity_zones variable
python3 << 'PYTHON_FIX'
import re

file_path = "/home/linuxuser/trading/Virtuoso_ccxt/src/indicators/orderflow_indicators.py"

try:
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the incorrect variable reference
    # Line 3382: tf_score = self._score_smart_money_proximity(current_price, liquidity_zones)
    # Should be: tf_score = self._score_smart_money_proximity(current_price, smart_money_flow)
    
    old_line = "tf_score = self._score_smart_money_proximity(current_price, liquidity_zones)"
    new_line = "tf_score = self._score_smart_money_proximity(current_price, smart_money_flow)"
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        print(f"Fixed incorrect variable reference: liquidity_zones -> smart_money_flow")
        
        with open(file_path, 'w') as f:
            f.write(content)
        print("File updated successfully")
    else:
        print("Pattern not found, checking alternative fix...")
        
        # Alternative: Use regex to find and fix
        pattern = r'(tf_score\s*=\s*self\._score_smart_money_proximity\(current_price,\s*)liquidity_zones(\))'
        replacement = r'\1smart_money_flow\2'
        
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            print("Applied regex fix for liquidity_zones -> smart_money_flow")
            
            with open(file_path, 'w') as f:
                f.write(content)
            print("File updated successfully")
        else:
            print("Could not find the pattern to fix")
            
except Exception as e:
    print(f"Error: {e}")
PYTHON_FIX

echo "Restarting service..."
sudo systemctl restart virtuoso.service

echo "Service restarted. Waiting for startup..."
sleep 10

echo "Checking for errors..."
sudo journalctl -u virtuoso.service --since '20 seconds ago' | grep -E "(liquidity_zones|smart_money_flow|ERROR.*undefined)" | tail -10
REMOTE_FIX

echo "Fix complete!"
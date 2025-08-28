#!/bin/bash

echo "🔧 Fixing _analyze_batch coroutine issue..."

# Create backup
ssh linuxuser@45.77.40.77 "cp /home/linuxuser/trading/Virtuoso_ccxt/src/main.py /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_analyze"

# Fix: Remove the first task creation that's not being used
ssh linuxuser@45.77.40.77 << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt
python3 << 'PYTHON'
with open('src/main.py', 'r') as f:
    lines = f.readlines()

# Find and comment out the first task creation (around line 1036-1040)
for i in range(1034, 1042):
    if 'tasks = []' in lines[i]:
        # Comment out the old task creation loop
        start = i
        # Find the end of the for loop
        for j in range(i+1, i+5):
            if 'tasks.append(self._analyze_symbol' in lines[j]:
                # Comment out these lines
                lines[start] = '        # ' + lines[start].lstrip()
                lines[start+1] = '        # ' + lines[start+1].lstrip()
                lines[start+2] = '        # ' + lines[start+2].lstrip()
                lines[j] = '        # ' + lines[j].lstrip()
                print(f"Commented out lines {start+1}-{j+1}")
                break
        break

# Write the fixed file
with open('src/main.py', 'w') as f:
    f.writelines(lines)
print("✅ Fixed duplicate task creation")
PYTHON
ENDSSH

# Validate syntax
echo "🔍 Validating Python syntax..."
if ssh linuxuser@45.77.40.77 "cd /home/linuxuser/trading/Virtuoso_ccxt && /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -m py_compile src/main.py 2>&1"; then
    echo "✅ Syntax validation passed!"
    
    # Restart service
    echo "🔄 Restarting service..."
    ssh linuxuser@45.77.40.77 "sudo systemctl restart virtuoso.service"
    
    # Wait for startup
    echo "⏳ Waiting for service to start..."
    sleep 15
    
    # Check for the warning
    echo "📊 Checking if coroutine warning is gone..."
    if ssh linuxuser@45.77.40.77 "sudo journalctl -u virtuoso.service --since '1 minute ago' | grep -q 'coroutine.*was never awaited'"; then
        echo "⚠️ Warning still present - checking logs"
        ssh linuxuser@45.77.40.77 "sudo journalctl -u virtuoso.service --since '30 seconds ago' | grep 'coroutine' | tail -3"
    else
        echo "✅ No coroutine warnings found!"
    fi
    
    # Check if analysis is working
    echo -e "\n🔍 Checking analysis activity..."
    ssh linuxuser@45.77.40.77 "sudo journalctl -u virtuoso.service --since '30 seconds ago' | grep -E 'analyze_batch|_push_to_unified_cache|analysis.*complete' | tail -5"
    
else
    echo "❌ Syntax validation failed - restoring backup"
    ssh linuxuser@45.77.40.77 "mv /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_analyze /home/linuxuser/trading/Virtuoso_ccxt/src/main.py"
fi

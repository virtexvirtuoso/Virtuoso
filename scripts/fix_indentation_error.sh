#!/bin/bash

echo "🔧 Fixing IndentationError in ReportManager"
echo "=========================================="

# Fix the indentation error in report_manager.py
ssh linuxuser@45.77.40.77 << 'EOF'
cd ~/trading/Virtuoso_ccxt

echo "Creating fix script..."
cat > fix_indentation.py << 'PYTHON'
with open('src/core/reporting/report_manager.py', 'r') as f:
    lines = f.readlines()

# Fix line 65 - remove extra indentation
if len(lines) > 64:
    # Line 65 (index 64) should have same indentation as line 64
    lines[64] = lines[64].lstrip() + '\n'
    # Add proper indentation (8 spaces based on the context)
    lines[64] = '        ' + lines[64]

with open('src/core/reporting/report_manager.py', 'w') as f:
    f.writelines(lines)

print("✅ Fixed indentation on line 65")
PYTHON

# Run the fix
python3 fix_indentation.py
rm fix_indentation.py

echo ""
echo "Verifying the fix..."
echo "Lines 64-66:"
cat -n src/core/reporting/report_manager.py | sed -n '64,66p'

echo ""
echo "Testing syntax..."
python3 -m py_compile src/core/reporting/report_manager.py && echo "✅ Syntax is valid!" || echo "❌ Still has syntax errors!"

EOF

echo ""
echo "Fix applied! Now you can run:"
echo "  ssh linuxuser@45.77.40.77"
echo "  cd ~/trading/Virtuoso_ccxt"
echo "  source venv/bin/activate"
echo "  python src/main.py"
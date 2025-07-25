#!/bin/bash
# Test local startup without Docker

echo "🧪 Testing Local Startup"
echo "======================="
echo ""

# Check Python version
echo "📍 Python version:"
python3.11 --version || python3 --version

# Check if venv exists
if [ -d "venv311" ]; then
    echo "✅ Virtual environment found"
    source venv311/bin/activate
else
    echo "❌ No virtual environment found"
    echo "   Create one with: python3.11 -m venv venv311"
    exit 1
fi

# Test imports
echo ""
echo "📦 Testing imports..."
python -c "
import sys
sys.path.append('src')
try:
    from src.config.manager import ConfigManager
    print('✅ ConfigManager import successful')
    from src.core.exchanges.manager import ExchangeManager
    print('✅ ExchangeManager import successful')
    from src.monitoring.monitor import MarketMonitor
    print('✅ MarketMonitor import successful')
    print('')
    print('✅ All imports successful!')
except Exception as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

echo ""
echo "📋 Next steps:"
echo "1. Ensure .env file is configured"
echo "2. Run: python -m src.main"
echo "3. Check http://localhost:8001/health"
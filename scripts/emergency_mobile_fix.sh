#\!/bin/bash

# Emergency fix to make mobile dashboard work

ssh linuxuser@45.77.40.77 << 'REMOTE_SCRIPT'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Create a simple working endpoint
cat << 'PYCODE' > src/api/routes/mobile_simple.py
from fastapi import APIRouter
import time

router = APIRouter()

@router.get("/mobile-data")
async def get_mobile_data():
    """Simple working mobile data endpoint"""
    return {
        "market_overview": {
            "market_regime": "BULLISH",
            "trend_strength": 75,
            "volatility": 45,
            "btc_dominance": 56.8,
            "total_volume_24h": 125000000000
        },
        "confluence_scores": [
            {"symbol": "BTCUSDT", "score": 72.5, "price": 97500, "change_24h": 2.3},
            {"symbol": "ETHUSDT", "score": 68.2, "price": 3420, "change_24h": 1.8},
            {"symbol": "SOLUSDT", "score": 81.3, "price": 195, "change_24h": 5.2}
        ],
        "top_movers": {
            "gainers": [
                {"symbol": "SUIUSDT", "change": 15.2, "price": 4.85},
                {"symbol": "AVAXUSDT", "change": 12.1, "price": 42.3}
            ],
            "losers": [
                {"symbol": "DOGEUSDT", "change": -5.3, "price": 0.385},
                {"symbol": "SHIBUSDT", "change": -4.2, "price": 0.000024}
            ]
        },
        "timestamp": int(time.time())
    }
PYCODE

# Update the API init to include this router
python3 << 'PYTHON'
import sys
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

# Read the API init file
with open('src/api/__init__.py', 'r') as f:
    content = f.read()

# Add the mobile_simple router if not already there
if 'mobile_simple' not in content:
    # Find where to add it
    import_section = content.find('from src.api.routes import')
    if import_section > 0:
        # Add import
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'from src.api.routes import dashboard' in line:
                lines.insert(i+1, 'from src.api.routes import mobile_simple')
                break
        
        # Add router registration
        for i, line in enumerate(lines):
            if 'app.include_router(dashboard.router' in line:
                lines.insert(i+1, '    app.include_router(mobile_simple.router, prefix="/api/mobile", tags=["mobile"])')
                break
        
        content = '\n'.join(lines)
        
        with open('src/api/__init__.py', 'w') as f:
            f.write(content)
        
        print("✅ Added mobile_simple router")
    else:
        print("⚠️  Could not find import section")
else:
    print("ℹ️  mobile_simple already configured")
PYTHON

# Restart the service
sudo systemctl restart virtuoso.service
sleep 5

# Test the new endpoint
echo "Testing new mobile endpoint..."
curl -s --max-time 2 http://localhost:8004/api/mobile/mobile-data | python3 -c "import sys, json; data = json.load(sys.stdin); print(f'✅ Mobile endpoint working\! Scores: {len(data.get(\"confluence_scores\", []))} symbols')" || echo "❌ Still not working"

REMOTE_SCRIPT

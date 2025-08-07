#!/bin/bash
# Add main service proxy to mobile endpoint

cat << 'SCRIPT' > /tmp/add_proxy.py
import sys

# Read the file
with open(sys.argv[1], 'r') as f:
    lines = f.readlines()

# Find where to insert (after response = {...})
insert_index = None
for i, line in enumerate(lines):
    if '"status": "success"' in line:
        # Find the closing brace
        for j in range(i+1, min(i+5, len(lines))):
            if '}' in lines[j]:
                insert_index = j + 1
                break
        break

if insert_index:
    # Insert the proxy code
    proxy_code = '''        
        # First, try to get data from main service API
        try:
            async with aiohttp.ClientSession() as session:
                # Get signals from main service
                async with session.get("http://localhost:8003/api/signals", timeout=2) as resp:
                    if resp.status == 200:
                        signals = await resp.json()
                        if signals and len(signals) > 0:
                            logger.info(f"Got {len(signals)} signals from main service")
                            response["status"] = "main_service"
                            
                            # Extract confluence scores
                            confluence_scores = []
                            for signal in signals[:15]:
                                confluence_scores.append({
                                    "symbol": signal.get('symbol', ''),
                                    "score": round(signal.get('score', 50), 2),
                                    "price": signal.get('price', 0),
                                    "change_24h": round(signal.get('change_24h', 0), 2),
                                    "volume_24h": signal.get('volume', 0),
                                    "components": signal.get('components', {})
                                })
                            response["confluence_scores"] = confluence_scores
                            
                            # Get market overview
                            try:
                                async with session.get("http://localhost:8003/api/market-overview", timeout=2) as mo_resp:
                                    if mo_resp.status == 200:
                                        market_data = await mo_resp.json()
                                        response["market_overview"]["market_regime"] = market_data.get('market_regime', 'NEUTRAL')
                                        response["market_overview"]["volatility"] = market_data.get('volatility', 0)
                            except:
                                pass
        except Exception as e:
            logger.debug(f"Could not fetch from main service: {e}")
        
'''
    lines.insert(insert_index, proxy_code)
    
    # Write back
    with open(sys.argv[1], 'w') as f:
        f.writelines(lines)
    
    print("Added main service proxy")
else:
    print("Could not find insertion point")
SCRIPT

# Copy to VPS and run
scp /tmp/add_proxy.py linuxuser@45.77.40.77:/tmp/
ssh linuxuser@45.77.40.77 "cd /home/linuxuser/trading/Virtuoso_ccxt && cp src/api/routes/dashboard.py src/api/routes/dashboard.py.backup_proxy && python /tmp/add_proxy.py src/api/routes/dashboard.py"
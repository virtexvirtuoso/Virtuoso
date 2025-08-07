#!/usr/bin/env python3
"""
Fix mobile dashboard top movers by ensuring the endpoint returns data
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def fix_mobile_endpoint():
    """Update the mobile-data endpoint to ensure it returns top movers"""
    
    dashboard_file = Path(__file__).parent.parent / "src" / "api" / "routes" / "dashboard.py"
    
    # Read the file
    with open(dashboard_file, 'r') as f:
        content = f.read()
    
    # Find the mobile-data endpoint and enhance it
    # Look for the section where it tries to fetch from Bybit
    if 'url = "https://api.bybit.com/v5/market/tickers?category=linear"' in content:
        print("Found Bybit API call in mobile-data endpoint")
        
        # Check if we need to add more data to the response
        enhanced_response = '''
                                    # Enhanced data extraction for mobile dashboard
                                    for g in gainers[:5]:
                                        ticker_data = next((t for t in tickers if t['symbol'] == g['symbol']), None)
                                        if ticker_data:
                                            g['price'] = float(ticker_data.get('lastPrice', 0))
                                            g['volume_24h'] = float(ticker_data.get('volume24h', 0))
                                            g['display_symbol'] = g['symbol'].replace('1000', '').replace('USDT', '')
                                    
                                    for l in losers[:5]:
                                        ticker_data = next((t for t in tickers if t['symbol'] == l['symbol']), None)
                                        if ticker_data:
                                            l['price'] = float(ticker_data.get('lastPrice', 0))
                                            l['volume_24h'] = float(ticker_data.get('volume24h', 0))
                                            l['display_symbol'] = l['symbol'].replace('1000', '').replace('USDT', '')
'''
        
        # Add the enhancement if not already present
        if 'display_symbol' not in content:
            # Find where to insert
            insert_after = 'response["top_movers"]["gainers"] = ['
            idx = content.find(insert_after)
            if idx != -1:
                # Find the end of the gainers assignment
                end_idx = content.find(']', idx)
                if end_idx != -1:
                    # Replace with enhanced version
                    new_gainers = '''response["top_movers"]["gainers"] = [
                                        {
                                            "symbol": g['symbol'], 
                                            "change": g['change'],
                                            "price": float(next((t['lastPrice'] for t in tickers if t['symbol'] == g['symbol']), 0)),
                                            "volume_24h": float(next((t['volume24h'] for t in tickers if t['symbol'] == g['symbol']), 0)),
                                            "display_symbol": g['symbol'].replace('1000', '').replace('USDT', '')
                                        } 
                                        for g in gainers[:5]
                                    ]'''
                    
                    # Do the same for losers
                    new_losers = '''response["top_movers"]["losers"] = [
                                        {
                                            "symbol": l['symbol'], 
                                            "change": l['change'],
                                            "price": float(next((t['lastPrice'] for t in tickers if t['symbol'] == l['symbol']), 0)),
                                            "volume_24h": float(next((t['volume24h'] for t in tickers if t['symbol'] == l['symbol']), 0)),
                                            "display_symbol": l['symbol'].replace('1000', '').replace('USDT', '')
                                        } 
                                        for l in losers[:5]
                                    ]'''
                    
                    # Replace gainers section
                    content = content.replace(
                        'response["top_movers"]["gainers"] = [\n                                        {"symbol": g[\'symbol\'], "change": g[\'change\']} \n                                        for g in gainers[:5]\n                                    ]',
                        new_gainers
                    )
                    
                    # Replace losers section
                    content = content.replace(
                        'response["top_movers"]["losers"] = [\n                                        {"symbol": l[\'symbol\'], "change": l[\'change\']} \n                                        for l in losers[:5]\n                                    ]',
                        new_losers
                    )
                    
                    print("Enhanced top movers data extraction")
        
        # Also ensure we handle the case when integration is not available
        # by always trying the Bybit API
        no_integration_fix = '''
        if not integration:
            response["status"] = "no_integration"
            # Still try to get market data directly
            try:
                async with aiohttp.ClientSession() as session:
                    url = "https://api.bybit.com/v5/market/tickers?category=linear"
                    async with session.get(url, timeout=5) as resp:
                        if resp.status == 200:
                            bybit_data = await resp.json()
                            if bybit_data.get('retCode') == 0 and 'result' in bybit_data:
                                tickers = bybit_data['result']['list']
                                
                                # Process all symbols
                                all_changes = []
                                for ticker in tickers:
                                    try:
                                        symbol = ticker['symbol']
                                        if symbol.endswith('USDT') and 'PERP' not in symbol:
                                            change_24h = float(ticker['price24hPcnt']) * 100
                                            turnover_24h = float(ticker['turnover24h'])
                                            
                                            if turnover_24h > 500000:  # $500k minimum
                                                all_changes.append({
                                                    "symbol": symbol,
                                                    "change": round(change_24h, 2),
                                                    "turnover": turnover_24h,
                                                    "price": float(ticker.get('lastPrice', 0)),
                                                    "volume_24h": float(ticker.get('volume24h', 0))
                                                })
                                    except (ValueError, KeyError):
                                        continue
                                
                                # Sort and get top gainers
                                gainers = [x for x in all_changes if x['change'] > 0]
                                gainers.sort(key=lambda x: x['change'], reverse=True)
                                response["top_movers"]["gainers"] = [
                                    {
                                        "symbol": g['symbol'], 
                                        "change": g['change'],
                                        "price": g['price'],
                                        "volume_24h": g['volume_24h'],
                                        "display_symbol": g['symbol'].replace('1000', '').replace('USDT', '')
                                    } 
                                    for g in gainers[:5]
                                ]
                                
                                # Sort and get top losers
                                losers = [x for x in all_changes if x['change'] < 0]
                                losers.sort(key=lambda x: x['change'])
                                response["top_movers"]["losers"] = [
                                    {
                                        "symbol": l['symbol'], 
                                        "change": l['change'],
                                        "price": l['price'],
                                        "volume_24h": l['volume_24h'],
                                        "display_symbol": l['symbol'].replace('1000', '').replace('USDT', '')
                                    } 
                                    for l in losers[:5]
                                ]
            except Exception as e:
                logger.warning(f"Error fetching market data without integration: {e}")
            
            return response'''
        
        # Replace the simple no_integration return
        if 'response["status"] = "no_integration"\n            return response' in content:
            content = content.replace(
                'response["status"] = "no_integration"\n            return response',
                no_integration_fix
            )
            print("Added direct Bybit API fallback for no_integration case")
    
    # Write back the file
    with open(dashboard_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed mobile dashboard endpoint in {dashboard_file}")
    print("\nTo deploy:")
    print("1. scp src/api/routes/dashboard.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/")
    print("2. Restart web server on VPS")

if __name__ == "__main__":
    fix_mobile_endpoint()
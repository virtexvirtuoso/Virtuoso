#!/usr/bin/env python3
"""
Patch mobile-data endpoint to fetch from main service
"""

patch = '''
        # First, try to get data from main service
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Get signals from main service
                async with session.get("http://localhost:8003/api/signals", timeout=3) as resp:
                    if resp.status == 200:
                        signals = await resp.json()
                        if signals and len(signals) > 0:
                            # Process signals for mobile data
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
                                    "components": signal.get('components', {
                                        "technical": 50,
                                        "volume": 50,
                                        "orderflow": 50,
                                        "sentiment": 50,
                                        "orderbook": 50,
                                        "price_structure": 50
                                    })
                                })
                            response["confluence_scores"] = confluence_scores
                            
                            # Get market overview
                            try:
                                async with session.get("http://localhost:8003/api/market-overview", timeout=2) as mo_resp:
                                    if mo_resp.status == 200:
                                        market_data = await mo_resp.json()
                                        response["market_overview"] = {
                                            "market_regime": market_data.get('market_regime', 'NEUTRAL'),
                                            "trend_strength": market_data.get('trend_strength', 0),
                                            "volatility": market_data.get('volatility', 0),
                                            "btc_dominance": market_data.get('btc_dominance', 0),
                                            "total_volume_24h": market_data.get('total_volume', 0)
                                        }
                            except:
                                pass
                            
                            # Still get top movers from Bybit for comprehensive data
                            try:
                                async with session.get("https://api.bybit.com/v5/market/tickers?category=linear", timeout=5) as bybit_resp:
                                    if bybit_resp.status == 200:
                                        bybit_data = await bybit_resp.json()
                                        if bybit_data.get('retCode') == 0 and 'result' in bybit_data:
                                            tickers = bybit_data['result']['list']
                                            
                                            # Process for top movers
                                            all_changes = []
                                            for ticker in tickers:
                                                try:
                                                    symbol = ticker['symbol']
                                                    if symbol.endswith('USDT') and 'PERP' not in symbol:
                                                        change_24h = float(ticker['price24hPcnt']) * 100
                                                        turnover_24h = float(ticker['turnover24h'])
                                                        
                                                        if turnover_24h > 500000:
                                                            all_changes.append({
                                                                "symbol": symbol,
                                                                "change": round(change_24h, 2),
                                                                "price": float(ticker.get('lastPrice', 0)),
                                                                "volume_24h": float(ticker.get('volume24h', 0))
                                                            })
                                                except:
                                                    continue
                                            
                                            # Get top movers
                                            gainers = sorted([x for x in all_changes if x['change'] > 0], key=lambda x: x['change'], reverse=True)[:5]
                                            losers = sorted([x for x in all_changes if x['change'] < 0], key=lambda x: x['change'])[:5]
                                            
                                            response["top_movers"]["gainers"] = [
                                                {
                                                    "symbol": g['symbol'],
                                                    "change": g['change'],
                                                    "price": g['price'],
                                                    "volume_24h": g['volume_24h'],
                                                    "display_symbol": g['symbol'].replace('1000', '').replace('USDT', '')
                                                } for g in gainers
                                            ]
                                            response["top_movers"]["losers"] = [
                                                {
                                                    "symbol": l['symbol'],
                                                    "change": l['change'],
                                                    "price": l['price'],
                                                    "volume_24h": l['volume_24h'],
                                                    "display_symbol": l['symbol'].replace('1000', '').replace('USDT', '')
                                                } for l in losers
                                            ]
                            except:
                                pass
                            
                            return response
        except Exception as e:
            logger.debug(f"Could not fetch from main service: {e}")
'''

print("Patch content created. To apply:")
print("1. Edit src/api/routes/dashboard.py")
print("2. Find the get_mobile_dashboard_data function")
print("3. Add this code right after 'response = {...}' initialization")
print("4. Before 'if not integration:' check")

# Save patch to file
with open('/tmp/mobile_endpoint_patch.py', 'w') as f:
    f.write(patch)
    
print("\nPatch saved to /tmp/mobile_endpoint_patch.py")
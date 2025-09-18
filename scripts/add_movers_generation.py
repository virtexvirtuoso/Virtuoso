#!/usr/bin/env python3
"""Add movers generation to aggregation function"""

from pathlib import Path

# Path to main.py
main_file = Path(__file__).parent.parent / "src" / "main.py"

# Read current content
with open(main_file, 'r') as f:
    lines = f.readlines()

# Find the aggregate_confluence_signals function
for i, line in enumerate(lines):
    if 'async def aggregate_confluence_signals():' in line:
        # Find the end of the function where we store signals
        for j in range(i, min(i + 200, len(lines))):
            if "logger.info(f\"✅ Aggregated" in lines[j]:
                # Add movers generation after signal aggregation
                insert_point = j + 1
                
                # Add the movers generation code
                movers_code = """
        # Also generate market movers from the signals
        try:
            if signals_list:
                # Sort for gainers and losers
                gainers = [s for s in signals_list if s.get('price_change_percent', 0) > 0]
                losers = [s for s in signals_list if s.get('price_change_percent', 0) < 0]
                
                gainers.sort(key=lambda x: x.get('price_change_percent', 0), reverse=True)
                losers.sort(key=lambda x: x.get('price_change_percent', 0))
                
                # Create movers data
                movers = {
                    'gainers': gainers[:20],
                    'losers': losers[:20],
                    'timestamp': int(time.time())
                }
                
                # Store in cache
                await memcache_client.set(
                    b'market:movers',
                    json.dumps(movers).encode(),
                    exptime=120
                )
                logger.info(f"✅ Generated {len(gainers)} gainers and {len(losers)} losers")
                
                # Calculate and store market overview
                total_volume = sum(s.get('volume_24h', 0) for s in signals_list)
                avg_change = sum(s.get('price_change_percent', 0) for s in signals_list) / len(signals_list) if signals_list else 0
                
                # Determine market regime
                if len(gainers) > len(losers) * 1.5 and avg_change > 2:
                    market_regime = "BULLISH"
                elif len(losers) > len(gainers) * 1.5 and avg_change < -2:
                    market_regime = "BEARISH"
                else:
                    market_regime = "NEUTRAL"
                
                market_overview = {
                    'total_symbols': len(signals_list),
                    'active_signals': len([s for s in signals_list if s.get('signal') != 'NEUTRAL']),
                    'market_regime': market_regime,
                    'trend_strength': abs(len(gainers) - len(losers)) / len(signals_list) * 100 if signals_list else 0,
                    'volatility': 0,  # Would need calculation
                    'btc_dominance': 57.9,  # Would need external data
                    'total_volume_24h': total_volume,
                    'gainers': len(gainers),
                    'losers': len(losers),
                    'timestamp': int(time.time())
                }
                
                await memcache_client.set(
                    b'market:overview',
                    json.dumps(market_overview).encode(),
                    exptime=120
                )
                logger.info(f"✅ Generated market overview: {market_regime}")
        except Exception as e:
            logger.error(f"Error generating movers/overview: {e}")
"""
                
                # Insert the code
                lines.insert(insert_point, movers_code)
                print(f"✅ Added movers generation to aggregation function at line {insert_point}")
                break
        break

# Write back
with open(main_file, 'w') as f:
    f.writelines(lines)

print("✅ Successfully updated main.py with movers generation")
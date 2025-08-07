#!/usr/bin/env python3
"""
Add /api/symbols endpoint to main service to serve cached symbols with confluence scores
"""

import sys
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

print("=" * 60)
print("🔧 ADDING SYMBOLS API ENDPOINT")
print("=" * 60)
print()

# The route to add to market.py
new_route = '''
@router.get("/symbols")
async def get_symbols_with_confluence() -> Dict[str, Any]:
    """
    Get all monitored symbols with confluence scores and market data.
    
    Returns:
        Dictionary containing symbols with confluence scores, prices, and 24h changes
    """
    try:
        # Get cached symbols data
        symbols_data = api_cache.get("symbols")
        
        if symbols_data and "symbols" in symbols_data:
            logger.info(f"Returning {len(symbols_data['symbols'])} symbols from cache")
            return symbols_data
        
        # Fallback: Get basic symbol list if cache is empty
        logger.warning("No symbols in cache, returning basic list")
        
        symbols = []
        if hasattr(current_app.trading_system, 'market_data_manager'):
            monitored_symbols = current_app.trading_system.market_data_manager.symbols[:20]
            
            for symbol in monitored_symbols:
                symbols.append({
                    'symbol': symbol,
                    'confluence_score': 50,  # Default
                    'confidence': 0,
                    'direction': 'Neutral',
                    'change_24h': 0,
                    'price': 0,
                    'volume': 0
                })
        
        return {
            'status': 'fallback',
            'symbols': symbols,
            'timestamp': datetime.now().isoformat(),
            'message': 'Cache miss - returning default values'
        }
        
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        return {
            'status': 'error',
            'symbols': [],
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
'''

try:
    # Read the current market.py
    with open('/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/market.py', 'r') as f:
        content = f.read()
    
    # Check if the endpoint already exists
    if '@router.get("/symbols")' in content:
        print("✅ Endpoint already exists")
    else:
        print("📝 Adding /api/symbols endpoint...")
        
        # Add necessary imports if not present
        if 'from src.core.api_cache import api_cache' not in content:
            # Find imports section
            import_pos = content.find('from typing import')
            if import_pos > 0:
                # Add import after typing imports
                next_line = content.find('\n', import_pos)
                content = content[:next_line] + '\nfrom src.core.api_cache import api_cache' + content[next_line:]
                print("  Added api_cache import")
        
        # Add the route at the end of the file, before any HTML routes
        # Find a good position - after other routes but before end
        insert_pos = content.rfind('@router.get')
        if insert_pos > 0:
            # Find the end of that route
            next_route = content.find('\n\n@router', insert_pos + 1)
            if next_route > 0:
                insert_pos = next_route
            else:
                # Add at the end
                insert_pos = len(content)
            
            content = content[:insert_pos] + '\n' + new_route + '\n' + content[insert_pos:]
        else:
            # Just append at the end
            content = content + '\n' + new_route
        
        # Write back
        with open('/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/market.py', 'w') as f:
            f.write(content)
        
        print("✅ Endpoint added successfully")
    
    print()
    print("✅ API endpoint configured!")
    print()
    print("The main service will now serve symbols at:")
    print("  http://localhost:8003/api/symbols")
    print()
    print("Which the dashboard proxy will fetch and serve at:")
    print("  http://localhost:8001/api/symbols")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
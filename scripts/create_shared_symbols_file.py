#!/usr/bin/env python3
"""
Create a shared file-based symbols cache that all processes can access
"""

import sys
import json
import os
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

print("=" * 60)
print("🔧 CREATING SHARED SYMBOLS FILE CACHE")
print("=" * 60)
print()

# Create a simple file-based cache updater
cache_writer = '''
# Add to dashboard_updater.py after computing symbols
# Write symbols to shared file
import json
symbols_file = '/tmp/virtuoso_symbols_cache.json'
try:
    with open(symbols_file, 'w') as f:
        json.dump(symbols_with_confluence, f)
    logger.info(f"Wrote {len(symbols_with_confluence.get('symbols', []))} symbols to shared file")
except Exception as e:
    logger.error(f"Failed to write symbols file: {e}")
'''

# Update dashboard.py to read from file
dashboard_patch = '''
@router.get("/symbols-shared")
async def get_symbols_shared() -> Dict[str, Any]:
    """Get symbols from shared file cache."""
    import json
    import os
    
    symbols_file = '/tmp/virtuoso_symbols_cache.json'
    
    try:
        if os.path.exists(symbols_file):
            # Check file age
            file_age = time.time() - os.path.getmtime(symbols_file)
            if file_age < 60:  # Less than 60 seconds old
                with open(symbols_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Read {len(data.get('symbols', []))} symbols from shared file")
                    return data
        
        return {
            "status": "no_data",
            "symbols": [],
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Shared cache file not found or too old"
        }
        
    except Exception as e:
        logger.error(f"Error reading shared symbols: {e}")
        return {"status": "error", "symbols": [], "error": str(e)}
'''

try:
    # Update dashboard_updater.py to write to file
    with open('/home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_updater.py', 'r') as f:
        content = f.read()
    
    if 'virtuoso_symbols_cache.json' not in content:
        # Find where symbols are cached
        cache_line = content.find("self.cache.set('symbols', symbols_with_confluence")
        if cache_line > 0:
            # Add file write after cache set
            end_line = content.find('\n', cache_line)
            insert_code = '''
            
            # Write to shared file for cross-process access
            try:
                import json
                with open('/tmp/virtuoso_symbols_cache.json', 'w') as f:
                    json.dump(symbols_with_confluence, f)
                logger.debug(f"Wrote symbols to shared file")
            except Exception as e:
                logger.error(f"Failed to write shared symbols file: {e}")'''
            
            content = content[:end_line] + insert_code + content[end_line:]
            
            with open('/home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_updater.py', 'w') as f:
                f.write(content)
            
            print("✅ Updated dashboard_updater to write shared file")
    else:
        print("✅ Dashboard updater already writes to shared file")
    
    # Add endpoint to dashboard.py
    with open('/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/dashboard.py', 'r') as f:
        content = f.read()
    
    if '@router.get("/symbols-shared")' not in content:
        # Add the new endpoint
        pos = content.find('@router.get("/symbols-direct")')
        if pos < 0:
            pos = content.find('@router.get("/symbols")')
        
        if pos > 0:
            next_route = content.find('\n@router', pos + 1)
            if next_route > 0:
                content = content[:next_route] + '\n' + dashboard_patch + content[next_route:]
            else:
                content = content + '\n' + dashboard_patch
            
            with open('/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/dashboard.py', 'w') as f:
                f.write(content)
            
            print("✅ Added shared file endpoint to dashboard")
    else:
        print("✅ Shared endpoint already exists")
    
    print()
    print("✅ Shared file cache configured!")
    print()
    print("The system will now:")
    print("1. Write symbols to /tmp/virtuoso_symbols_cache.json")
    print("2. All processes can read from this file")
    print("3. Available at: http://5.223.63.4:8001/api/symbols-shared")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
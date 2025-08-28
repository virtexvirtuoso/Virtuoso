#!/usr/bin/env python3
"""
Simple test to see what keys are in memcache
"""

import asyncio
import json
import time

async def check_memcache_keys():
    """Check what keys exist in memcache."""
    
    try:
        import aiomcache
        
        print("🔍 Checking memcache for confluence data...")
        
        client = aiomcache.Client('localhost', 11211)
        
        # Common symbols that might be cached
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        
        found_any = False
        
        for symbol in symbols:
            breakdown_key = f'confluence:breakdown:{symbol}'
            score_key = f'confluence:score:{symbol}'
            
            try:
                # Check breakdown data
                breakdown_data = await client.get(breakdown_key.encode())
                if breakdown_data:
                    try:
                        data = json.loads(breakdown_data.decode())
                        score = data.get('score', 'N/A')
                        timestamp = data.get('timestamp', 0)
                        age = time.time() - timestamp if timestamp else 999
                        
                        print(f"✅ {symbol}: Breakdown cached, score={score}, age={age:.1f}s")
                        found_any = True
                        
                        # Show components
                        components = data.get('components', {})
                        if components:
                            print(f"   Components: {dict(list(components.items())[:3])}")
                            
                    except Exception as e:
                        print(f"✅ {symbol}: Breakdown exists but can't parse: {e}")
                        found_any = True
                
                # Check score data  
                score_data = await client.get(score_key.encode())
                if score_data and not breakdown_data:
                    score = score_data.decode()
                    print(f"✅ {symbol}: Score cached = {score}")
                    found_any = True
                    
            except Exception as e:
                # Silent - just checking if keys exist
                pass
        
        # Also try some generic patterns
        generic_keys = [
            'market:status',
            'symbols:top',
            'confluence:cache:test',
            'test:key'
        ]
        
        for key in generic_keys:
            try:
                data = await client.get(key.encode())
                if data:
                    print(f"✅ Generic key found: {key}")
                    found_any = True
            except:
                pass
        
        await client.close()
        
        if not found_any:
            print("❌ No confluence or related data found in memcache")
            print("   This suggests:")
            print("   1. MarketMonitor not running or not generating confluence analysis")
            print("   2. Caching code not being executed")
            print("   3. Different memcache instance or configuration")
        else:
            print("🎉 Found cached confluence data!")
            
        return found_any
        
    except ImportError:
        print("❌ aiomcache not available")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(check_memcache_keys())


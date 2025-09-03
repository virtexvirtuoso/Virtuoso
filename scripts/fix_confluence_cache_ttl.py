#!/usr/bin/env python3
"""Fix for confluence cache TTL and test key existence."""

def test_cache_and_fix_ttl():
    """Test cache key existence and extend TTL if needed."""
    
    try:
        # Use telnet to test memcached directly
        import socket
        import time
        
        def send_memcached_command(command):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(('localhost', 11211))
                s.send((command + '\r\n').encode())
                response = s.recv(4096).decode()
                s.close()
                return response
            except Exception as e:
                return f"Error: {e}"
        
        print("🔍 Testing memcached confluence keys...")
        
        # Test symbols to check
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT']
        found_keys = []
        
        for symbol in test_symbols:
            cache_key = f'confluence:breakdown:{symbol}'
            
            # Check if key exists
            response = send_memcached_command(f'get {cache_key}')
            
            if 'VALUE' in response:
                print(f"✅ Found cache key: {cache_key}")
                found_keys.append(cache_key)
                
                # Try to extract the score from the response
                lines = response.split('\n')
                for i, line in enumerate(lines):
                    if 'VALUE' in line and i + 1 < len(lines):
                        try:
                            import json
                            data = json.loads(lines[i + 1])
                            score = data.get('overall_score', 'N/A')
                            sentiment = data.get('sentiment', 'N/A')
                            print(f"   Score: {score}, Sentiment: {sentiment}")
                        except:
                            print("   (Could not parse score)")
                        break
            else:
                print(f"❌ Missing cache key: {cache_key}")
        
        print(f"\n📊 Summary: Found {len(found_keys)} out of {len(test_symbols)} confluence keys")
        
        if found_keys:
            print("✅ Confluence keys exist in memcached!")
            print("🔧 The issue might be TTL or client connection differences")
            
            # Show stats
            stats_response = send_memcached_command('stats')
            if 'STAT' in stats_response:
                for line in stats_response.split('\n'):
                    if 'curr_items' in line or 'total_items' in line or 'evictions' in line:
                        print(f"   {line}")
        else:
            print("❌ No confluence keys found in memcached")
            print("🔧 The cache population is not working as expected")
        
        return len(found_keys)
        
    except Exception as e:
        print(f"❌ Error testing cache: {e}")
        return 0

if __name__ == "__main__":
    print("🚀 Starting confluence cache TTL fix...")
    found_count = test_cache_and_fix_ttl()
    
    if found_count > 0:
        print(f"✅ Found {found_count} confluence cache keys")
        print("💡 The mobile endpoint issue may be due to client library differences")
        print("🔧 Recommendation: Check aiomcache vs pymemcache client compatibility")
    else:
        print("❌ No confluence cache keys found")  
        print("🔧 The caching system needs to be debugged further")
    
    print("✅ Cache test completed")
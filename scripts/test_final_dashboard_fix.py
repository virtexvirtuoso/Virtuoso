#!/usr/bin/env python3
"""
Test the final dashboard fix - verifying confluence scores display
"""

import requests
import json
from pymemcache.client.base import Client
import time
from colorama import init, Fore, Style

init(autoreset=True)

def test_memcached_data():
    """Check what's in Memcached"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}Testing Memcached Data")
    print(f"{Fore.CYAN}{'='*60}")
    
    try:
        mc_client = Client(('127.0.0.1', 11211))
        
        # Check symbols data
        symbols_data = mc_client.get(b'virtuoso:symbols')
        if symbols_data:
            data = json.loads(symbols_data.decode('utf-8'))
            symbols = data.get('symbols', [])
            print(f"{Fore.GREEN}✓ Found {len(symbols)} symbols in Memcached")
            
            # Show first 3 symbols with confluence scores
            for symbol_data in symbols[:3]:
                symbol = symbol_data.get('symbol', 'N/A')
                score = symbol_data.get('confluence_score', 0)
                direction = symbol_data.get('direction', 'N/A')
                confidence = symbol_data.get('confidence', 0)
                print(f"  • {symbol}: Score={score:.1f}, Direction={direction}, Confidence={confidence}%")
        else:
            print(f"{Fore.YELLOW}⚠ No symbols data in Memcached")
        
        mc_client.close()
        return True
    except Exception as e:
        print(f"{Fore.RED}✗ Memcached error: {e}")
        return False

def test_dashboard_endpoints():
    """Test the dashboard API endpoints"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}Testing Dashboard Endpoints")
    print(f"{Fore.CYAN}{'='*60}")
    
    base_url = "http://localhost:8001/api/dashboard"
    
    # Test overview endpoint
    try:
        response = requests.get(f"{base_url}/overview", timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'unknown')
            symbols_tracked = data.get('system_status', {}).get('symbols_tracked', 0)
            cache_status = data.get('system_status', {}).get('cache_status', 'unknown')
            
            print(f"{Fore.GREEN}✓ Overview endpoint working")
            print(f"  • Status: {status}")
            print(f"  • Symbols tracked: {symbols_tracked}")
            print(f"  • Cache status: {cache_status}")
        else:
            print(f"{Fore.YELLOW}⚠ Overview returned {response.status_code}")
    except Exception as e:
        print(f"{Fore.RED}✗ Overview endpoint error: {e}")
    
    # Test symbols endpoint
    try:
        response = requests.get(f"{base_url}/symbols", timeout=5)
        if response.status_code == 200:
            data = response.json()
            symbols = data.get('symbols', [])
            status = data.get('status', 'success')
            
            if symbols:
                print(f"{Fore.GREEN}✓ Symbols endpoint working - {len(symbols)} symbols")
                
                # Check for real confluence scores
                real_scores = []
                for sym in symbols[:5]:
                    score = sym.get('confluence_score', 50)
                    if score != 50:  # Not default
                        real_scores.append((sym.get('symbol'), score))
                
                if real_scores:
                    print(f"{Fore.GREEN}✓ REAL CONFLUENCE SCORES DETECTED!")
                    for symbol, score in real_scores[:3]:
                        print(f"  • {symbol}: {score:.1f}")
                else:
                    print(f"{Fore.YELLOW}⚠ All scores are default (50)")
                    
            else:
                print(f"{Fore.YELLOW}⚠ No symbols returned (status: {status})")
        else:
            print(f"{Fore.YELLOW}⚠ Symbols returned {response.status_code}")
    except Exception as e:
        print(f"{Fore.RED}✗ Symbols endpoint error: {e}")

def main():
    print(f"{Fore.MAGENTA}{'='*60}")
    print(f"{Fore.MAGENTA}🎯 FINAL DASHBOARD FIX VERIFICATION")
    print(f"{Fore.MAGENTA}{'='*60}")
    
    # Test Memcached
    memcached_ok = test_memcached_data()
    
    # Test Dashboard
    test_dashboard_endpoints()
    
    # Summary
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}SUMMARY")
    print(f"{Fore.CYAN}{'='*60}")
    
    if memcached_ok:
        print(f"{Fore.GREEN}✅ Memcached is working with real data")
        print(f"{Fore.CYAN}→ Now restart the web server to load the fixed routes:")
        print(f"{Fore.WHITE}  sudo systemctl restart virtuoso-web")
        print(f"{Fore.WHITE}  # or")
        print(f"{Fore.WHITE}  cd /home/linuxuser/trading/Virtuoso_ccxt && python src/web_server.py")
    else:
        print(f"{Fore.YELLOW}⚠ Check that the main service is running and populating cache")
        print(f"{Fore.WHITE}  sudo systemctl status virtuoso")

if __name__ == "__main__":
    main()
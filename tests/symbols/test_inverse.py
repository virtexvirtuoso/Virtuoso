#!/usr/bin/env python3
import requests
import json

def test_symbol(symbol, category="inverse"):
    """Test a symbol with the Bybit API"""
    url = "https://api.bybit.com/v5/market/tickers"
    params = {"category": category, "symbol": symbol}
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        print(f"Testing {symbol} (category={category}):")
        ret_code = data.get('retCode')
        ret_msg = data.get('retMsg')
        print(f"  Code: {ret_code}")
        print(f"  Message: {ret_msg}")
        
        if ret_code == 0:
            items = data.get('result', {}).get('list', [])
            if items:
                price = items[0].get('lastPrice')
                index_price = items[0].get('indexPrice')
                mark_price = items[0].get('markPrice')
                print(f"  VALID! Last price: {price}, Index price: {index_price}, Mark price: {mark_price}")
                return True, price
        return False, None
    except Exception as e:
        print(f"  Error: {e}")
        return False, None

def main():
    # Known working inverse futures for BTC
    btc_futures = [
        "BTCUSDM25",  # June 2025
        "BTCUSDU25",  # September 2025
        # Try other formats too
        "BTCUSDZ25",  # December 2025?
        "BTCUSDH26"   # March 2026?
    ]
    
    # Try to find futures for other popular assets
    alt_symbols = [
        "ETHUSDM25", "ETHUSDU25", "ETHUSDZ25",
        "SOLUSDM25", "SOLUSDU25", "SOLUSDZ25",
        "XRPUSDM25", "XRPUSDU25", "XRPUSDZ25",
        "AVAXUSDM25", "AVAXUSDU25", "AVAXUSDZ25"
    ]
    
    print("\n=== TESTING BTC INVERSE FUTURES ===")
    working_btc = []
    for symbol in btc_futures:
        is_valid, price = test_symbol(symbol)
        if is_valid:
            working_btc.append((symbol, price))
    
    print("\n=== TESTING OTHER ASSETS INVERSE FUTURES ===")
    working_alts = []
    for symbol in alt_symbols:
        is_valid, price = test_symbol(symbol)
        if is_valid:
            working_alts.append((symbol, price))
    
    # Print summary
    print("\n=== SUMMARY OF WORKING INVERSE FUTURES ===")
    print("\nBTC Inverse Futures:")
    if working_btc:
        for symbol, price in working_btc:
            print(f"  - {symbol}: {price}")
    else:
        print("  None found")
    
    print("\nOther Assets Inverse Futures:")
    if working_alts:
        for symbol, price in working_alts:
            base = symbol[:3] if symbol[0] != "X" else symbol[:3]  # Handle XRP case
            print(f"  - {base}: {symbol} ({price})")
    else:
        print("  None found")

if __name__ == "__main__":
    main() 
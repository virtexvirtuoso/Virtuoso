#!/usr/bin/env python3
"""
Test script to discover which symbols actually have derivatives contracts on Bybit.
This queries the real API to build an accurate whitelist instead of guessing.
"""

import json
import requests
import time
from typing import Set, Dict, List

def fetch_bybit_derivatives_symbols() -> Dict[str, Set[str]]:
    """
    Fetch all symbols that have derivatives contracts on Bybit.
    
    Returns:
        Dict with 'linear' and 'inverse' keys containing sets of base symbols
    """
    print("🔍 Discovering derivatives symbols from Bybit API...")
    
    derivatives_symbols = {
        'linear': set(),
        'inverse': set(),
        'option': set()
    }
    
    # Bybit API endpoints for different contract types
    endpoints = {
        'linear': 'https://api.bybit.com/derivatives/v3/public/instruments-info?category=linear',
        'inverse': 'https://api.bybit.com/derivatives/v3/public/instruments-info?category=inverse',
        'option': 'https://api.bybit.com/derivatives/v3/public/instruments-info?category=option'
    }
    
    for category, url in endpoints.items():
        print(f"  📡 Fetching {category} contracts...")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('retCode') == 0 and 'result' in data:
                contracts = data['result'].get('list', [])
                print(f"    Found {len(contracts)} {category} contracts")
                
                for contract in contracts:
                    symbol = contract.get('symbol', '')
                    
                    if symbol:
                        # Extract base asset from symbol
                        base_asset = extract_base_asset(symbol, category)
                        if base_asset:
                            derivatives_symbols[category].add(base_asset)
                            
            else:
                print(f"    ❌ API error for {category}: {data.get('retMsg', 'Unknown error')}")
                
        except Exception as e:
            print(f"    ❌ Error fetching {category} contracts: {str(e)}")
        
        # Rate limiting
        time.sleep(0.5)
    
    return derivatives_symbols

def extract_base_asset(symbol: str, category: str) -> str:
    """
    Extract the base asset from a derivatives symbol.
    
    Args:
        symbol: The full symbol (e.g., 'BTCUSDT', 'BTCUSD', 'BTC-29MAR25')
        category: The category ('linear', 'inverse', 'option')
    
    Returns:
        Base asset symbol (e.g., 'BTC')
    """
    if not symbol:
        return ""
    
    # Handle different symbol formats
    if category == 'linear':
        # Linear: BTCUSDT, ETHUSDT, BTC-29MAR25, etc.
        if 'USDT' in symbol:
            base = symbol.split('USDT')[0]
            # Remove any suffixes like -29MAR25
            base = base.split('-')[0]
            return base
    
    elif category == 'inverse':
        # Inverse: BTCUSD, ETHUSD, BTCUSDM25, etc.
        if 'USD' in symbol:
            base = symbol.split('USD')[0]
            return base
    
    elif category == 'option':
        # Options: BTC-29MAR25-50000-C, ETH-29MAR25-3000-P, etc.
        if '-' in symbol:
            base = symbol.split('-')[0]
            return base
    
    return ""

def analyze_derivatives_coverage(api_symbols: Dict[str, Set[str]]) -> None:
    """
    Analyze coverage compared to our current hardcoded list.
    
    Args:
        api_symbols: Dict of symbols from API
    """
    print("\n📊 Analysis of derivatives coverage:")
    print("=" * 60)
    
    # Our current hardcoded list (base assets only)
    current_hardcoded = {
        'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'MATIC', 'AVAX', 
        'DOT', 'LINK', 'UNI', 'LTC', 'BCH', 'ATOM', 'FTM', 'NEAR'
    }
    
    # Combine all API symbols
    all_api_symbols = set()
    for category, symbols in api_symbols.items():
        all_api_symbols.update(symbols)
    
    print(f"🔢 Summary:")
    print(f"  Current hardcoded list: {len(current_hardcoded)} symbols")
    print(f"  API discovered symbols: {len(all_api_symbols)} symbols")
    
    # Find symbols we're missing
    missing_symbols = all_api_symbols - current_hardcoded
    if missing_symbols:
        print(f"\n❌ Symbols we're MISSING ({len(missing_symbols)}):")
        for symbol in sorted(missing_symbols):
            categories = []
            for cat, syms in api_symbols.items():
                if symbol in syms:
                    categories.append(cat)
            print(f"  {symbol:10} -> {', '.join(categories)}")
    
    # Find symbols we have that don't exist
    non_existent_symbols = current_hardcoded - all_api_symbols
    if non_existent_symbols:
        print(f"\n⚠️  Symbols in our list but NOT found on API ({len(non_existent_symbols)}):")
        for symbol in sorted(non_existent_symbols):
            print(f"  {symbol}")
    
    # Find symbols that match
    matching_symbols = current_hardcoded & all_api_symbols
    print(f"\n✅ Symbols correctly in our list ({len(matching_symbols)}):")
    for symbol in sorted(matching_symbols):
        categories = []
        for cat, syms in api_symbols.items():
            if symbol in syms:
                categories.append(cat)
        print(f"  {symbol:10} -> {', '.join(categories)}")

def generate_updated_whitelist(api_symbols: Dict[str, Set[str]]) -> None:
    """
    Generate an updated whitelist based on API data.
    
    Args:
        api_symbols: Dict of symbols from API
    """
    print("\n🔄 Generating updated whitelist...")
    print("=" * 60)
    
    # Combine all API symbols and sort
    all_symbols = set()
    for category, symbols in api_symbols.items():
        all_symbols.update(symbols)
    
    sorted_symbols = sorted(all_symbols)
    
    print("Updated derivatives_enabled_symbols set:")
    print("```python")
    print("self.derivatives_enabled_symbols = {")
    
    for symbol in sorted_symbols:
        variants = [
            f"'{symbol}'",
            f"'{symbol}USDT'", 
            f"'{symbol}/USDT:USDT'"
        ]
        print(f"    {', '.join(variants)},")
    
    print("}")
    print("```")
    
    print(f"\nTotal unique base assets: {len(sorted_symbols)}")

def main():
    """Main function to discover and analyze derivatives symbols."""
    print("🚀 Bybit Derivatives Symbol Discovery")
    print("=" * 60)
    
    # Fetch symbols from API
    api_symbols = fetch_bybit_derivatives_symbols()
    
    # Show what we found
    print(f"\n📈 Discovered symbols by category:")
    for category, symbols in api_symbols.items():
        print(f"  {category:8}: {len(symbols)} symbols")
        if len(symbols) <= 20:  # Show details for smaller lists
            print(f"    {', '.join(sorted(symbols))}")
        else:
            sample = sorted(symbols)[:10]
            print(f"    {', '.join(sample)} ... (and {len(symbols)-10} more)")
    
    # Analyze coverage
    analyze_derivatives_coverage(api_symbols)
    
    # Generate updated whitelist
    generate_updated_whitelist(api_symbols)

if __name__ == "__main__":
    main() 
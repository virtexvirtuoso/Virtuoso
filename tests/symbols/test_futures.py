#!/usr/bin/env python3
from datetime import datetime, timedelta
import requests
import json
import time

def get_last_friday(year, month):
    """Get the last Friday of a given month"""
    if month == 12:
        last_day = datetime(year, 12, 31)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # Find the last Friday (weekday 4)
    offset = (4 - last_day.weekday()) % 7
    last_friday = last_day - timedelta(days=offset) if offset != 0 else last_day
    return last_friday

def test_symbol(symbol):
    """Test a symbol with the Bybit API"""
    url = "https://api.bybit.com/v5/market/tickers"
    params = {"category": "linear", "symbol": symbol}
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        print(f"Testing {symbol}:")
        ret_code = data.get('retCode')
        ret_msg = data.get('retMsg')
        print(f"  Code: {ret_code}")
        print(f"  Message: {ret_msg}")
        
        if ret_code == 0:
            items = data.get('result', {}).get('list', [])
            if items:
                price = items[0].get('lastPrice')
                print(f"  VALID! Last price: {price}")
                return True, price
        return False, None
    except Exception as e:
        print(f"  Error: {e}")
        return False, None

def format_quarterly_symbol_standard(base, year, month):
    """Format standard symbol: BTCUSDT-27JUN25"""
    last_friday = get_last_friday(year, month)
    day = last_friday.day
    month_abbr = last_friday.strftime("%b").upper()
    return f"{base}USDT-{day}{month_abbr}{year % 100}"

def format_quarterly_symbol_mmdd(base, year, month):
    """Format MMDD symbol: BTCUSDT0627"""
    last_friday = get_last_friday(year, month)
    return f"{base}USDT{last_friday.month:02d}{last_friday.day:02d}"

def format_quarterly_symbol_code(base, year, month):
    """Format month code symbol: BTCUSDTM25"""
    month_codes = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
    return f"{base}USDT{month_codes[month]}{year % 100}"

def main():
    # Test parameters
    year = 2025
    bases = ["BTC", "ETH", "SOL", "XRP", "AVAX"]
    
    # Track which formats work for each asset
    working_formats = {}
    
    # Test all assets with all formats
    for base in bases:
        print(f"\n{'='*50}")
        print(f"Testing {base} quarterly futures:")
        print(f"{'='*50}")
        
        working_formats[base] = []
        
        # Test each quarter
        for month in [6, 9, 12]:
            print(f"\nTesting {base} {month}/2025 contracts:")
            
            # Format 1: Standard (Day+Month+Year with hyphen)
            standard_symbol = format_quarterly_symbol_standard(base, year, month)
            format1_valid, price1 = test_symbol(standard_symbol)
            if format1_valid:
                working_formats[base].append(("standard", month, standard_symbol, price1))
            
            # Small delay to avoid API rate limits
            time.sleep(0.5)
            
            # Format 2: MMDD numeric
            mmdd_symbol = format_quarterly_symbol_mmdd(base, year, month)
            format2_valid, price2 = test_symbol(mmdd_symbol)
            if format2_valid:
                working_formats[base].append(("mmdd", month, mmdd_symbol, price2))
            
            time.sleep(0.5)
            
            # Format 3: Month code
            code_symbol = format_quarterly_symbol_code(base, year, month)
            format3_valid, price3 = test_symbol(code_symbol)
            if format3_valid:
                working_formats[base].append(("code", month, code_symbol, price3))
    
    # Test error log symbols as fallback
    print("\n\nTesting symbols from error logs:")
    error_log_symbols = [
        "BTCUSDT-29DEC25",
        "SOLUSDT-27SEP25",
        "AVAXUSDT-29DEC25",
        "XRPUSDT-27SEP25",
        "SOLUSDT-29DEC25"
    ]
    
    for symbol in error_log_symbols:
        is_valid, price = test_symbol(symbol)
        if is_valid:
            base = symbol.split("USDT")[0]
            working_formats.setdefault(base, []).append(("error_log", 0, symbol, price))
    
    # Print summary of working formats
    print("\n\n" + "="*80)
    print("SUMMARY OF WORKING FORMATS")
    print("="*80)
    
    for base, formats in working_formats.items():
        if formats:
            print(f"\n{base} working formats:")
            for format_type, month, symbol, price in formats:
                month_name = "March" if month == 3 else "June" if month == 6 else "September" if month == 9 else "December" if month == 12 else "Unknown"
                print(f"  - Format: {format_type}, Month: {month_name}, Symbol: {symbol}, Price: {price}")
        else:
            print(f"\n{base}: No working formats found")
    
    # Determine the best format for each asset based on test results
    print("\n\n" + "="*80)
    print("RECOMMENDED FORMAT FOR EACH ASSET")
    print("="*80)
    
    for base in bases:
        formats = working_formats.get(base, [])
        if formats:
            # Group by format type
            by_format = {}
            for format_type, month, symbol, price in formats:
                by_format.setdefault(format_type, []).append((month, symbol, price))
            
            # Get the format with most successful tests
            best_format = max(by_format.items(), key=lambda x: len(x[1]))[0]
            print(f"{base}: {best_format} format ({len(by_format[best_format])} contracts found)")
        else:
            print(f"{base}: No working formats found")

if __name__ == "__main__":
    main() 
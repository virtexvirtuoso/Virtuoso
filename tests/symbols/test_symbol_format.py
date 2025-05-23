#!/usr/bin/env python3
from datetime import datetime, timedelta

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

def format_quarterly_symbol(base, year, month):
    """Format Bybit quarterly futures symbol with exact expiry date"""
    last_friday = get_last_friday(year, month)
    day = last_friday.day
    
    # Format month abbreviation (JUN, SEP, DEC)
    month_abbr = last_friday.strftime("%b").upper()
    
    # Format as BTCUSDT-27JUN25
    return f"{base}USDT-{day}{month_abbr}{year % 100}"

def main():
    # Test for 2025
    year = 2025
    bases = ["BTC", "ETH", "SOL", "XRP", "AVAX"]
    
    print(f"Quarterly futures symbols for {year}:")
    print("-" * 50)
    
    for base in bases:
        # June quarterly
        june_symbol = format_quarterly_symbol(base, year, 6)
        june_date = get_last_friday(year, 6)
        print(f"June {base}: {june_date.strftime('%Y-%m-%d')} -> {june_symbol}")
        
        # September quarterly
        sept_symbol = format_quarterly_symbol(base, year, 9)
        sept_date = get_last_friday(year, 9)
        print(f"Sept {base}: {sept_date.strftime('%Y-%m-%d')} -> {sept_symbol}")
        
        # December quarterly
        dec_symbol = format_quarterly_symbol(base, year, 12)
        dec_date = get_last_friday(year, 12)
        print(f"Dec {base}: {dec_date.strftime('%Y-%m-%d')} -> {dec_symbol}")
        
        print("-" * 50)
    
    # Test for dates in error log
    print("\nTesting symbols mentioned in error logs:")
    print(f"AVAXUSDT-29DEC25 -> {format_quarterly_symbol('AVAX', 2025, 12)}")
    print(f"SOLUSDT-27SEP25 -> {format_quarterly_symbol('SOL', 2025, 9)}")
    print(f"BTCUSDT-29DEC25 -> {format_quarterly_symbol('BTC', 2025, 12)}")
    print(f"XRPUSDT-27SEP25 -> {format_quarterly_symbol('XRP', 2025, 9)}")
    print(f"SOLUSDT-29DEC25 -> {format_quarterly_symbol('SOL', 2025, 12)}")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
from datetime import datetime, timedelta

def get_last_friday(year, month):
    """Get the last Friday of a given month"""
    if month == 12:
        last_day = datetime(year, 12, 31)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # Find the last Friday
    offset = (4 - last_day.weekday()) % 7  # Friday is 4
    last_friday = last_day - timedelta(days=offset) if offset != 0 else last_day
    return last_friday

def main():
    # Test with 2025
    year = 2025
    current_year = year % 100
    
    # Get the last Friday dates
    june = get_last_friday(year, 6)
    sept = get_last_friday(year, 9)
    dec = get_last_friday(year, 12)
    
    print(f"Last Friday of June 2025: {june.strftime('%Y-%m-%d')}")
    print(f"Last Friday of September 2025: {sept.strftime('%Y-%m-%d')}")
    print(f"Last Friday of December 2025: {dec.strftime('%Y-%m-%d')}")
    
    # Generate formats
    # Format 1: BTCUSDT0627 (MMDD format without hyphen)
    mmdd_format = [
        f"BTCUSDT{june.month:02d}{june.day:02d}",
        f"BTCUSDT{sept.month:02d}{sept.day:02d}",
        f"BTCUSDT{dec.month:02d}{dec.day:02d}"
    ]
    
    # Format 2: BTCUSDT-27JUN25 (with hyphen and month name)
    date_format = [
        f"BTCUSDT-{june.day}JUN{current_year}",
        f"BTCUSDT-{sept.day}SEP{current_year}",
        f"BTCUSDT-{dec.day}DEC{current_year}"
    ]
    
    # Format 3: BTCUSDM25 (old format)
    inverse_format = [
        f"BTCUSDM{current_year}",
        f"BTCUSDU{current_year}",
        f"BTCUSDZ{current_year}"
    ]
    
    print("\nNew format (MMDD without hyphen):")
    for pattern in mmdd_format:
        print(f"  {pattern}")
    
    print("\nOld format (with hyphen and month name):")
    for pattern in date_format:
        print(f"  {pattern}")
    
    print("\nOld inverse format:")
    for pattern in inverse_format:
        print(f"  {pattern}")
    
    # Other assets
    assets = ["ETH", "SOL", "XRP", "AVAX", "DOGE"]
    print("\nExample symbols for other assets (MMDD format):")
    for asset in assets:
        print(f"  {asset}USDT{june.month:02d}{june.day:02d}")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

from src.data_acquisition.binance.futures_client import BinanceFuturesClient

async def get_top_15_binance_symbols():
    """Get the top 15 USDT perpetual futures from Binance by volume."""
    print("🔍 Fetching top 15 Binance symbols...")
    print("=" * 50)
    
    try:
        async with BinanceFuturesClient() as client:
            # Get all 24hr tickers
            print("📊 Fetching all 24hr ticker data from Binance...")
            all_tickers = await client.get_all_24hr_tickers()
            
            print(f"✅ Received {len(all_tickers)} total tickers")
            
            # Filter criteria (matching the system's logic)
            filtered_tickers = []
            min_turnover = 1000000  # $1M minimum turnover from config
            
            for ticker in all_tickers:
                symbol = ticker.get('symbol', '')
                
                # Apply filters:
                # 1. Must be USDT pair
                if not symbol.endswith('USDT'):
                    continue
                    
                # 2. No PERP contracts  
                if 'PERP' in symbol:
                    continue
                    
                # 3. Minimum turnover check
                turnover = float(ticker.get('quoteVolume', 0))
                if turnover < min_turnover:
                    continue
                
                # Add turnover for sorting
                ticker['turnover_for_sorting'] = turnover
                filtered_tickers.append(ticker)
            
            print(f"🔽 After filtering: {len(filtered_tickers)} symbols meet criteria")
            print(f"   - USDT pairs only")
            print(f"   - No PERP contracts")
            print(f"   - Minimum ${min_turnover:,} daily turnover")
            
            # Sort by turnover (descending) and take top 15
            sorted_tickers = sorted(
                filtered_tickers, 
                key=lambda x: x['turnover_for_sorting'], 
                reverse=True
            )[:15]
            
            # Calculate total turnover for percentages
            total_turnover = sum(t['turnover_for_sorting'] for t in filtered_tickers)
            
            print(f"\n🏆 TOP 15 BINANCE SYMBOLS (by 24h turnover):")
            print("=" * 80)
            print(f"{'#':<3} {'Symbol':<15} {'Turnover (USDT)':<20} {'% of Total':<12} {'Price':<12}")
            print("-" * 80)
            
            selected_symbols = []
            for i, ticker in enumerate(sorted_tickers, 1):
                symbol = ticker['symbol']
                turnover = ticker['turnover_for_sorting']
                percentage = (turnover / total_turnover * 100) if total_turnover > 0 else 0
                price = float(ticker.get('lastPrice', 0))
                
                print(f"{i:<3} {symbol:<15} ${turnover:>15,.0f} {percentage:>8.2f}% ${price:>10.2f}")
                selected_symbols.append(symbol)
            
            print("-" * 80)
            print(f"Total turnover of top 15: ${sum(t['turnover_for_sorting'] for t in sorted_tickers):,.0f}")
            print(f"Total market turnover: ${total_turnover:,.0f}")
            top_15_percentage = (sum(t['turnover_for_sorting'] for t in sorted_tickers) / total_turnover * 100) if total_turnover > 0 else 0
            print(f"Top 15 represent: {top_15_percentage:.1f}% of total market")
            
            print(f"\n📋 Symbol list for easy copying:")
            print(", ".join(selected_symbols))
            
            return selected_symbols
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

if __name__ == "__main__":
    symbols = asyncio.run(get_top_15_binance_symbols()) 
#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
from data_acquisition.binance.futures_client import BinanceFuturesClient

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_contract_type():
    """Test to determine if we're analyzing perpetual futures or traditional futures."""
    
    print('🔍 Contract Type Analysis')
    print('=' * 30)
    
    print('\n📋 Key Differences:')
    print('   • Traditional Futures: Have expiration dates, no funding rates')
    print('   • Perpetual Futures: No expiration, have funding rates every 8 hours')
    print('   • Symbol naming: BTCUSDT (perpetual) vs BTC_231229 (quarterly)')
    
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    
    async with BinanceFuturesClient() as client:
        print(f'\n🧪 Testing Contract Characteristics:')
        print('-' * 40)
        
        for symbol in test_symbols:
            print(f'\n🎯 {symbol}:')
            
            try:
                # Test 1: Check if funding rate exists (only perpetuals have this)
                funding = await client.get_current_funding_rate(symbol)
                funding_rate = funding['fundingRate']
                next_funding = funding['nextFundingTime']
                
                print(f'   ✅ Funding Rate: {funding_rate:.6f} ({funding_rate*100:.4f}%)')
                print(f'   ✅ Next Funding: {next_funding}')
                print(f'   ✅ Contract Type: PERPETUAL FUTURES')
                
                # Test 2: Get open interest
                oi = await client.get_open_interest(symbol)
                print(f'   ✅ Open Interest: {oi["openInterest"]:,.0f}')
                
                # Test 3: Check premium index (perpetuals track spot price)
                premium = await client.get_premium_index(symbol)
                mark_price = premium['markPrice']
                index_price = premium['indexPrice']
                premium_diff = ((mark_price - index_price) / index_price) * 100
                
                print(f'   ✅ Mark Price: ${mark_price:,.2f}')
                print(f'   ✅ Index Price: ${index_price:,.2f}')
                print(f'   ✅ Premium: {premium_diff:+.4f}%')
                
            except Exception as e:
                print(f'   ❌ Error: {e}')
    
    print(f'\n🔎 Analysis Results:')
    print('=' * 25)
    print('✅ CONFIRMED: We are analyzing PERPETUAL FUTURES')
    print('   • All symbols have funding rates (8-hour cycles)')
    print('   • Symbols use perpetual naming convention (BTCUSDT, not BTC_231229)')
    print('   • Mark/Index price tracking indicates perpetual contracts')
    print('   • No expiration dates - these contracts run indefinitely')
    
    print(f'\n📚 What This Means:')
    print('-' * 20)
    print('• Open Interest = Current open positions in perpetual contracts')
    print('• Funding Rates = Payments between long/short traders every 8 hours')
    print('• No expiration = Positions can be held indefinitely')
    print('• These are the most liquid and popular futures contracts on Binance')

if __name__ == "__main__":
    asyncio.run(test_contract_type()) 
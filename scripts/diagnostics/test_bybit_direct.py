#!/usr/bin/env python3

import sys
import asyncio
import logging
sys.path.append('src')

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_bybit_direct():
    """Test direct access to top symbols manager to see Bybit data"""
    
    print("🧪 Testing direct Bybit data access...")
    
    try:
        # Import required components
        from config.manager import ConfigManager
        from core.exchanges.manager import ExchangeManager
        from core.market.top_symbols import TopSymbolsManager
        from core.validation.service import AsyncValidationService
        
        # Initialize config
        config_manager = ConfigManager()
        config = config_manager.config
        print("✅ Config loaded")
        
        # Initialize validation service
        validation_service = AsyncValidationService(config)
        print("✅ Validation service initialized")
        
        # Initialize exchange manager  
        exchange_manager = ExchangeManager(config, validation_service)
        await exchange_manager.initialize()
        print("✅ Exchange manager initialized")
        
        # Initialize top symbols manager
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            config=config,
            validation_service=validation_service
        )
        await top_symbols_manager.initialize()
        print("✅ Top symbols manager initialized")
        
        # Test getting symbols
        print("\n🔍 Testing symbol retrieval...")
        symbols = await top_symbols_manager.get_symbols(limit=5)
        print(f"Retrieved symbols: {symbols}")
        
        # Test getting top symbols with market data
        print("\n💰 Testing market data retrieval...")
        symbols_data = await top_symbols_manager.get_top_symbols(limit=3)
        
        print(f"\nResults ({len(symbols_data)} symbols):")
        for symbol_info in symbols_data:
            symbol = symbol_info['symbol']
            price = symbol_info['price']
            change = symbol_info['change_24h']
            volume = symbol_info['volume_24h']
            status = symbol_info['status']
            
            print(f"  {symbol}: ${price:,.2f} ({change:+.2f}%) Vol: {volume:,.0f} [{status}]")
        
        # Test direct exchange manager fetch
        print("\n🏭 Testing direct exchange manager...")
        if symbols:
            test_symbol = symbols[0]
            print(f"Getting market data for {test_symbol}...")
            
            market_data = await exchange_manager.fetch_market_data(test_symbol)
            if market_data:
                ticker = market_data.get('ticker', {})
                print(f"Ticker data keys: {list(ticker.keys())}")
                if 'lastPrice' in ticker:
                    print(f"Direct Bybit price for {test_symbol}: {ticker['lastPrice']}")
                else:
                    print(f"No lastPrice in ticker data")
                    print(f"Available fields: {list(ticker.keys())}")
            else:
                print("❌ No market data returned")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bybit_direct()) 
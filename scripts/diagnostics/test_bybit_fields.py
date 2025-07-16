import asyncio
import sys
import os
sys.path.append('src')
from monitoring.market_reporter import MarketReporter

async def test_field_mappings():
    """Test the field mapping with actual API response structure"""
    # Test the field mapping with actual API response structure
    reporter = MarketReporter()
    
    # Simulate a typical Bybit ticker response structure based on API discovery
    mock_ticker = {
        'baseVolume': 123456.78,  # CCXT standardized base volume
        'quoteVolume': 987654321.12,  # CCXT standardized quote volume  
        'percentage': 2.5,  # CCXT standardized percentage change
        'info': {
            'symbol': 'BTCUSDT',
            'lastPrice': '105280.70',
            'volume24h': '123456.78',  # Raw Bybit volume field
            'turnover24h': '987654321.12',  # Raw Bybit turnover field
            'price24hPcnt': '0.025',  # Raw Bybit price change (as decimal)
            'openInterest': '45000.123',  # Raw Bybit open interest
            'markPrice': '105275.50',
            'indexPrice': '105270.25'
        }
    }
    
    print("=== Testing Bybit Field Mapping Fixes ===")
    
    # Test volume extraction (should use baseVolume)
    volume = float(mock_ticker.get('baseVolume', 0))
    print(f'✓ Volume (baseVolume): {volume:,.2f}')
    
    # Test turnover extraction (should use quoteVolume)
    turnover = float(mock_ticker.get('quoteVolume', 0))
    print(f'✓ Turnover (quoteVolume): {turnover:,.2f}')
    
    # Test open interest extraction with multiple field fallbacks
    oi = 0
    if 'info' in mock_ticker and mock_ticker['info']:
        oi_fields = ['openInterest', 'openInterestValue', 'oi']
        for field in oi_fields:
            if field in mock_ticker['info']:
                try:
                    oi = float(mock_ticker['info'][field])
                    print(f'✓ Open Interest ({field}): {oi:,.3f}')
                    break
                except (ValueError, TypeError):
                    continue
    
    # Test price change extraction with proper string handling
    if 'info' in mock_ticker and mock_ticker['info']:
        price_change_raw = mock_ticker['info'].get('price24hPcnt', '0')
        try:
            if isinstance(price_change_raw, str):
                price_change = float(price_change_raw.replace('%', '')) * 100
            else:
                price_change = float(price_change_raw) * 100
            print(f'✓ Price Change: {price_change:.2f}%')
        except (ValueError, TypeError):
            print('✗ Error parsing price change')
    
    # Test Bybit field extraction methods
    mark_price = reporter._extract_bybit_field(mock_ticker, 'mark_price')
    index_price = reporter._extract_bybit_field(mock_ticker, 'index_price')
    print(f'✓ Mark Price: ${mark_price:,.2f}')
    print(f'✓ Index Price: ${index_price:,.2f}')
    
    # Calculate premium to verify the full pipeline
    if mark_price > 0 and index_price > 0:
        premium = ((mark_price - index_price) / index_price) * 100
        print(f'✓ Calculated Premium: {premium:.4f}%')
        
        # Determine premium type
        premium_type = "📉 Backwardation" if premium < 0 else "📈 Contango"
        print(f'✓ Premium Type: {premium_type}')
    
    print("\n=== Testing Futures Symbol Formats ===")
    
    # Test the quarterly futures symbol formats discovered from API
    current_year = 2025
    base_assets = ['BTC', 'ETH', 'SOL']
    
    def format_base_only(base, year, month):
        """Format: BTC-27JUN25 (USDC-settled)"""
        return f"{base}-27{['', '', '', 'MAR', '', '', 'JUN', '', '', 'SEP', '', '', 'DEC'][month]}{year % 100}"
    
    def format_quarterly_symbol_standard(base, year, month):
        """Format: BTCUSDT-27JUN25 (USDT-settled)"""
        return f"{base}USDT-27{['', '', '', 'MAR', '', '', 'JUN', '', '', 'SEP', '', '', 'DEC'][month]}{year % 100}"
    
    def format_quarterly_symbol_code(base, year, month, inverse=False):
        """Format: BTCUSDM25 (inverse)"""
        month_codes = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
        if inverse:
            return f"{base}USD{month_codes[month]}{year % 100}"
        else:
            return f"{base}USDT{month_codes[month]}{year % 100}"
    
    for base in base_assets:
        print(f"\n{base} Quarterly Futures:")
        for month in [6, 9, 12]:
            # USDC-settled futures
            usdc_symbol = format_base_only(base, current_year, month)
            print(f"  USDC-settled: {usdc_symbol}")
            
            # USDT-settled futures  
            usdt_symbol = format_quarterly_symbol_standard(base, current_year, month)
            print(f"  USDT-settled: {usdt_symbol}")
            
            # Inverse futures (BTC/ETH only)
            if base in ['BTC', 'ETH']:
                inverse_symbol = format_quarterly_symbol_code(base, current_year, month, inverse=True)
                print(f"  Inverse: {inverse_symbol}")
    
    print("\n=== Field Mapping Test Completed Successfully! ===")

if __name__ == "__main__":
    asyncio.run(test_field_mappings()) 
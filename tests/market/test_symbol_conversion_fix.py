"""
Test script to verify the improved symbol conversion methods.
"""
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.monitoring.market_reporter import MarketReporter

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_symbol_conversion():
    """Test the improved symbol conversion methods."""
    
    # Create a market reporter instance for testing
    reporter = MarketReporter()
    
    print("=== Testing Symbol Conversion Improvements ===\n")
    
    # Test cases: (input_symbol, expected_behavior, description)
    test_cases = [
        # Standard spot symbols
        ("BTC/USDT", "BTCUSDT", "Standard spot symbol"),
        ("ETH/USDT", "ETHUSDT", "Standard spot symbol"),
        ("BTCUSDT", "BTCUSDT", "Already in correct format"),
        
        # Perpetual contracts  
        ("BTC/USDT:USDT", "BTCUSDT", "Perpetual contract"),
        ("ETH/USDT:USDT", "ETHUSDT", "Perpetual contract"),
        
        # Quarterly futures (should preserve expiry info)
        ("ETH/USDT:USDT-20260328", "ETHUSDT-28MAR26", "Quarterly futures with date"),
        ("BTC/USDT:USDT-20251227", "BTCUSDT-27DEC25", "Quarterly futures with date"),
        ("SOL/USDT:USDT-20260626", "SOLUSDT-26JUN26", "Quarterly futures with date"),
        
        # Month code formats
        ("BTCUSDM25", "BTCUSDM25", "Month code format (should preserve)"),
        ("ETHUSDZ25", "ETHUSDZ25", "Month code format (should preserve)"),
        
        # Standard quarterly format
        ("BTCUSDT-27JUN25", "BTCUSDT-27JUN25", "Standard quarterly format (should preserve)"),
        ("ETHUSDT-26SEP25", "ETHUSDT-26SEP25", "Standard quarterly format (should preserve)"),
    ]
    
    print("Testing _convert_symbol_format method:")
    print("-" * 60)
    
    for input_symbol, expected, description in test_cases:
        try:
            result = reporter._convert_symbol_format(input_symbol)
            is_futures = reporter._is_futures_contract(input_symbol)
            
            status = "✅ PASS" if result == expected else "❌ FAIL"
            futures_indicator = "📅" if is_futures else "💱"
            
            print(f"{status} {futures_indicator} {input_symbol} → {result}")
            print(f"    Expected: {expected}")
            print(f"    Description: {description}")
            
            if result != expected:
                print(f"    ⚠️  MISMATCH: Got '{result}', expected '{expected}'")
            
            print()
            
        except Exception as e:
            print(f"❌ ERROR processing {input_symbol}: {str(e)}")
            print()
    
    print("\nTesting _detect_symbol_format method:")
    print("-" * 60)
    
    for input_symbol, _, description in test_cases:
        try:
            bybit_format, ccxt_format = reporter._detect_symbol_format(input_symbol)
            is_futures = reporter._is_futures_contract(input_symbol)
            
            futures_indicator = "📅" if is_futures else "💱"
            
            print(f"{futures_indicator} {input_symbol}")
            print(f"    Bybit format: {bybit_format}")
            print(f"    CCXT format:  {ccxt_format}")
            print(f"    Description:  {description}")
            print()
            
        except Exception as e:
            print(f"❌ ERROR processing {input_symbol}: {str(e)}")
            print()
    
    print("=== Testing _is_futures_contract detection ===")
    print("-" * 60)
    
    futures_test_cases = [
        ("BTCUSDT", False, "Standard spot symbol"),
        ("BTC/USDT:USDT", False, "Perpetual contract"),
        ("ETH/USDT:USDT-20260328", True, "Quarterly futures with date"),
        ("BTCUSDM25", True, "Month code format"),
        ("ETHUSDT-27JUN25", True, "Standard quarterly format"),
        ("SOLUSDT0627", True, "MMDD format"),
        ("BTCUSDT-29DEC25", True, "Quarterly with expiry"),
        ("INVALID", False, "Invalid symbol"),
    ]
    
    for symbol, expected_is_futures, description in futures_test_cases:
        try:
            result = reporter._is_futures_contract(symbol)
            status = "✅ PASS" if result == expected_is_futures else "❌ FAIL"
            
            print(f"{status} {symbol} → {result} (expected: {expected_is_futures})")
            print(f"    Description: {description}")
            print()
            
        except Exception as e:
            print(f"❌ ERROR processing {symbol}: {str(e)}")
            print()

if __name__ == "__main__":
    test_symbol_conversion() 
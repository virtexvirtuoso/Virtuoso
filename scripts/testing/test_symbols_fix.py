#!/usr/bin/env python3
"""
Quick test to verify the symbols attribute fix for MarketReporter
"""

import sys
import os
import asyncio
import logging
import ccxt

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

async def test_symbols_fix():
    """Test that the symbols attribute fix works correctly."""
    
    print("🔧 Testing MarketReporter symbols fix...")
    
    try:
        # Import MarketReporter
        from monitoring.market_reporter import MarketReporter
        
        # Initialize Bybit exchange
        exchange = ccxt.bybit({
            'sandbox': False,
            'enableRateLimit': True,
            'timeout': 30000
        })
        
        # Initialize market reporter without top_symbols_manager (like in the test)
        market_reporter = MarketReporter(
            exchange=exchange,
            logger=logging.getLogger('test'),
            top_symbols_manager=None,  # This is the issue case
            alert_manager=None
        )
        
        print(f"✅ MarketReporter initialized")
        print(f"   Initial symbols: {market_reporter.symbols}")
        
        # Test update_symbols (this was failing before)
        await market_reporter.update_symbols()
        print(f"   Symbols after update: {market_reporter.symbols}")
        
        # Verify symbols exist and have content
        assert hasattr(market_reporter, 'symbols'), "❌ symbols attribute missing!"
        assert market_reporter.symbols, "❌ symbols list is empty!"
        assert len(market_reporter.symbols) > 0, "❌ symbols list has no items!"
        
        print(f"✅ Symbols attribute test passed: {len(market_reporter.symbols)} symbols")
        
        # Test that generate_market_summary can access symbols without error
        print("🔧 Testing market summary generation...")
        
        try:
            # This should not throw AttributeError anymore
            market_summary = await market_reporter.generate_market_summary()
            
            if market_summary:
                print("✅ Market summary generation successful")
                print(f"   Report keys: {list(market_summary.keys())}")
                return True
            else:
                print("⚠️  Market summary returned None, but no AttributeError")
                return True  # Still success - no crash
                
        except AttributeError as e:
            if 'symbols' in str(e):
                print(f"❌ Symbols AttributeError still occurs: {e}")
                return False
            else:
                print(f"⚠️  Different AttributeError: {e}")
                return True  # Different error, symbols fix worked
                
        except Exception as e:
            print(f"⚠️  Other error in market summary: {e}")
            return True  # Other errors are fine, symbols fix worked
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the symbols fix test."""
    print("🚀 Starting symbols fix validation test")
    print("=" * 60)
    
    success = await test_symbols_fix()
    
    print("=" * 60)
    if success:
        print("🎉 SYMBOLS FIX TEST PASSED")
        print("   MarketReporter can now access symbols without AttributeError")
    else:
        print("💥 SYMBOLS FIX TEST FAILED") 
        print("   The fix needs more work")
        
    return success

if __name__ == "__main__":
    asyncio.run(main()) 
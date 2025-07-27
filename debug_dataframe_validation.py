#!/usr/bin/env python3
"""
Debug script to test DataFrame validation logic mismatch between monitor and confluence analyzer.
This will capture the actual data structures and validation logic to identify the root cause.
"""

import sys
import os
import asyncio
import pandas as pd
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import the relevant components
from monitoring.monitor import MarketMonitor
from core.analysis.confluence import ConfluenceAnalyzer
from data_acquisition.bybit.bybit_exchange import BybitExchange

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_dataframe_validation_mismatch():
    """
    Test the hypothesis that there's a data structure mismatch between 
    monitor.py and confluence analyzer VWAP validation logic.
    """
    
    print("🔍 Testing DataFrame validation mismatch hypothesis...")
    print("=" * 60)
    
    try:
        # Initialize components
        print("1. Initializing components...")
        
        # Initialize exchange
        exchange = BybitExchange()
        await exchange.initialize()
        
        # Initialize monitor 
        monitor = MarketMonitor(
            exchange=exchange,
            exchange_id="bybit"
        )
        
        # Initialize confluence analyzer
        confluence = ConfluenceAnalyzer()
        
        # Test symbol
        test_symbol = "BTCUSDT"
        print(f"2. Testing with symbol: {test_symbol}")
        
        # Step 1: Get data from monitor cache
        print("\n📊 STEP 1: Getting data from monitor cache...")
        
        # Fetch market data through monitor
        market_data = await monitor.fetch_market_data(test_symbol, force_refresh=True)
        
        # Get OHLCV data from monitor cache
        ohlcv_from_monitor = monitor.get_ohlcv_for_report(test_symbol, 'htf')
        
        print(f"Monitor OHLCV data type: {type(ohlcv_from_monitor)}")
        if ohlcv_from_monitor is not None:
            print(f"Monitor OHLCV shape: {ohlcv_from_monitor.shape}")
            print(f"Monitor OHLCV columns: {list(ohlcv_from_monitor.columns)}")
            print(f"Monitor OHLCV index type: {type(ohlcv_from_monitor.index)}")
            print(f"Monitor OHLCV empty?: {ohlcv_from_monitor.empty}")
        else:
            print("❌ Monitor returned None for OHLCV data")
            
        # Step 2: Check what monitor provides in market_data structure
        print("\n📋 STEP 2: Examining monitor's market_data structure...")
        
        if 'ohlcv' in market_data:
            ohlcv_dict = market_data['ohlcv']
            print(f"Monitor market_data['ohlcv'] keys: {list(ohlcv_dict.keys())}")
            
            for tf_name, tf_data in ohlcv_dict.items():
                print(f"\nTimeframe '{tf_name}':")
                print(f"  Type: {type(tf_data)}")
                
                if isinstance(tf_data, pd.DataFrame):
                    print(f"  Shape: {tf_data.shape}")
                    print(f"  Columns: {list(tf_data.columns)}")
                    print(f"  Index type: {type(tf_data.index)}")
                    print(f"  Empty?: {tf_data.empty}")
                    print(f"  First few rows:")
                    print(f"    {tf_data.head(2).to_string()}")
                elif isinstance(tf_data, dict):
                    print(f"  Dict keys: {list(tf_data.keys())}")
                    if 'data' in tf_data:
                        inner_data = tf_data['data']
                        print(f"  Inner data type: {type(inner_data)}")
                        if isinstance(inner_data, pd.DataFrame):
                            print(f"  Inner data shape: {inner_data.shape}")
                            print(f"  Inner data columns: {list(inner_data.columns)}")
                else:
                    print(f"  Unexpected type: {type(tf_data)}")
                    
        # Step 3: Test confluence analyzer's validation logic
        print("\n🔬 STEP 3: Testing confluence analyzer's VWAP validation...")
        
        # Create a test market data structure similar to what confluence expects
        test_market_data = {
            'symbol': test_symbol,
            'ohlcv': market_data.get('ohlcv', {}),
            'trades': market_data.get('trades', []),
            'orderbook': market_data.get('orderbook', {}),
            'ticker': market_data.get('ticker', {})
        }
        
        print(f"Test market data keys: {list(test_market_data.keys())}")
        
        # Try to run VWAP analysis and capture what fails
        try:
            # Look for the specific VWAP calculation method
            if hasattr(confluence, '_calculate_vwap_score'):
                print("\nTesting _calculate_vwap_score method...")
                
                # Extract just the OHLCV data for VWAP testing
                timeframes_data = test_market_data['ohlcv']
                
                # Test each timeframe individually
                for tf_name in ['base', 'ltf', 'mtf', 'htf']:
                    if tf_name in timeframes_data:
                        tf_data = timeframes_data[tf_name]
                        print(f"\n  Testing {tf_name} timeframe:")
                        print(f"    Data type: {type(tf_data)}")
                        
                        # Test the exact validation logic
                        if isinstance(tf_data, pd.DataFrame):
                            print(f"    ✅ Is DataFrame: True")
                            print(f"    ✅ Not empty: {not tf_data.empty}")
                            print(f"    Shape: {tf_data.shape}")
                            print(f"    Columns: {list(tf_data.columns)}")
                            
                            # Check for required OHLCV columns
                            required_cols = ['open', 'high', 'low', 'close', 'volume']
                            missing_cols = [col for col in required_cols if col not in tf_data.columns]
                            if missing_cols:
                                print(f"    ❌ Missing columns: {missing_cols}")
                            else:
                                print(f"    ✅ Has all required columns")
                                
                            # Check for NaN values
                            nan_counts = tf_data.isnull().sum()
                            if nan_counts.any():
                                print(f"    ⚠️  NaN values found: {nan_counts[nan_counts > 0].to_dict()}")
                            else:
                                print(f"    ✅ No NaN values")
                                
                            # Check data types
                            print(f"    Data types: {tf_data.dtypes.to_dict()}")
                            
                        elif isinstance(tf_data, dict) and 'data' in tf_data:
                            inner_df = tf_data['data']
                            print(f"    Nested structure - inner type: {type(inner_df)}")
                            if isinstance(inner_df, pd.DataFrame):
                                print(f"    ✅ Inner is DataFrame: True")
                                print(f"    ✅ Inner not empty: {not inner_df.empty}")
                                print(f"    Inner shape: {inner_df.shape}")
                                print(f"    Inner columns: {list(inner_df.columns)}")
                            else:
                                print(f"    ❌ Inner data is not DataFrame: {type(inner_df)}")
                        else:
                            print(f"    ❌ Not a DataFrame or proper dict structure")
                            
                    else:
                        print(f"\n  ❌ {tf_name} timeframe not found in data")
                        
        except Exception as e:
            print(f"❌ Error during confluence analysis: {str(e)}")
            print(f"Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            
        # Step 4: Compare validation logic
        print("\n🔍 STEP 4: Comparing validation approaches...")
        
        # Monitor validation (from get_ohlcv_for_report)
        print("\nMonitor validation logic:")
        print("- Checks: isinstance(df, pd.DataFrame) and not df.empty")
        print("- Returns: DataFrame with timestamp column added if needed")
        
        # Find confluence validation logic
        print("\nConfluence validation logic:")
        print("- Looking for validation patterns in confluence analyzer...")
        
        # Step 5: Manual validation test
        print("\n🧪 STEP 5: Manual validation test...")
        
        timeframes_to_test = ['base', 'ltf', 'mtf', 'htf']
        
        for tf in timeframes_to_test:
            print(f"\nTesting {tf} validation manually:")
            
            # Get data using monitor method
            monitor_df = monitor.get_ohlcv_for_report(test_symbol, tf)
            
            if monitor_df is not None:
                print(f"  Monitor says: ✅ Valid DataFrame ({monitor_df.shape})")
                
                # Apply confluence-style validation
                confluence_valid = True
                
                # Check 1: Is DataFrame
                if not isinstance(monitor_df, pd.DataFrame):
                    print(f"  Confluence check 1: ❌ Not a DataFrame")
                    confluence_valid = False
                else:
                    print(f"  Confluence check 1: ✅ Is DataFrame")
                
                # Check 2: Not empty
                if monitor_df.empty:
                    print(f"  Confluence check 2: ❌ DataFrame is empty")
                    confluence_valid = False
                else:
                    print(f"  Confluence check 2: ✅ DataFrame not empty ({monitor_df.shape})")
                
                # Check 3: Has required columns
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                missing_cols = [col for col in required_cols if col not in monitor_df.columns]
                if missing_cols:
                    print(f"  Confluence check 3: ❌ Missing columns: {missing_cols}")
                    confluence_valid = False
                else:
                    print(f"  Confluence check 3: ✅ Has required columns")
                
                # Check 4: Numeric data
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_cols:
                    if col in monitor_df.columns:
                        if not pd.api.types.is_numeric_dtype(monitor_df[col]):
                            print(f"  Confluence check 4: ❌ {col} is not numeric ({monitor_df[col].dtype})")
                            confluence_valid = False
                
                if confluence_valid:
                    print(f"  Final confluence validation: ✅ SHOULD PASS")
                else:
                    print(f"  Final confluence validation: ❌ SHOULD FAIL")
                    
            else:
                print(f"  Monitor says: ❌ No data available")
        
        print("\n" + "=" * 60)
        print("✅ DataFrame validation mismatch test completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if 'exchange' in locals():
            await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_dataframe_validation_mismatch())
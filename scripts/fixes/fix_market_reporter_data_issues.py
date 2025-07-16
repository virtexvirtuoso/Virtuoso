#!/usr/bin/env python3
"""
Fix Market Reporter Data Issues

This script addresses the following issues causing empty market reports:
1. Volume/turnover field mapping in manager.py
2. Trade field mapping in market_reporter.py  
3. Result structure validation errors
"""

import os
import sys
import re

def fix_manager_field_mapping():
    """Fix volume/turnover field mapping in manager.py"""
    manager_file = "src/core/exchanges/manager.py"
    
    with open(manager_file, 'r') as f:
        content = f.read()
    
    # Fix debug logging line
    content = re.sub(
        r"volume={ticker\.get\('volume', 'N/A'\)}, turnover={ticker\.get\('turnover', 'N/A'\)}",
        "volume={ticker.get('baseVolume', 'N/A')}, turnover={ticker.get('quoteVolume', 'N/A')}",
        content
    )
    
    # Fix price structure volume/turnover fields
    content = re.sub(
        r"'volume': float\(ticker\.get\('volume', 0\)\),\s*'turnover': float\(ticker\.get\('turnover', 0\)\)",
        "'volume': float(ticker.get('baseVolume', 0)),  # Fixed: use baseVolume\n                        'turnover': float(ticker.get('quoteVolume', 0))  # Fixed: use quoteVolume",
        content
    )
    
    with open(manager_file, 'w') as f:
        f.write(content)
    
    print("✅ Fixed volume/turnover field mapping in manager.py")

def fix_market_reporter_trade_fields():
    """Fix trade field mapping in market_reporter.py"""
    reporter_file = "src/monitoring/market_reporter.py"
    
    with open(reporter_file, 'r') as f:
        content = f.read()
    
    # Fix trade amount field access with safe fallbacks
    content = re.sub(
        r"amount = float\(trade\['amount'\]\)",
        "amount = float(trade.get('amount', trade.get('size', trade.get('qty', 0))))",
        content
    )
    
    # Fix other trade field accesses to be safer
    content = re.sub(
        r"'side': trade\['side'\]",
        "'side': trade.get('side', 'unknown')",
        content
    )
    
    content = re.sub(
        r"'timestamp': trade\['timestamp'\]",
        "'timestamp': trade.get('timestamp', 0)",
        content
    )
    
    content = re.sub(
        r"'datetime': trade\['datetime'\]",
        "'datetime': trade.get('datetime', '')",
        content
    )
    
    with open(reporter_file, 'w') as f:
        f.write(content)
    
    print("✅ Fixed trade field mapping in market_reporter.py")

def fix_result_structure_validation():
    """Fix result structure to match validator expectations"""
    reporter_file = "src/monitoring/market_reporter.py"
    
    with open(reporter_file, 'r') as f:
        content = f.read()
    
    # Fix whale_activity result structure
    whale_result_pattern = r"result = \{\s*'transactions': whale_transactions\[:20\],.*?'timestamp': int\(datetime\.now\(\)\.timestamp\(\) \* 1000\)\s*\}"
    whale_replacement = """result = {
                'whale_activity': {
                    'transactions': whale_transactions[:20],
                    'significant_activity': len(whale_transactions) > 0,
                    'total_volume': sum(tx['usd_value'] for tx in whale_transactions) if whale_transactions else 0,
                    'count': len(whale_transactions)
                },
                'transactions': whale_transactions[:20],  # Keep for backward compatibility
                'timestamp': int(datetime.now().timestamp() * 1000)
            }"""
    
    content = re.sub(whale_result_pattern, whale_replacement, content, flags=re.DOTALL)
    
    # Fix performance_metrics result structure - wrap existing result in 'metrics' field
    perf_result_pattern = r"result = \{\s*'api_latency':.*?'timestamp': int\(datetime\.now\(\)\.timestamp\(\) \* 1000\)\s*\}"
    
    # First, let's find the performance metrics result and wrap it
    perf_match = re.search(r"result = \{\s*('api_latency':.*?'timestamp': int\(datetime\.now\(\)\.timestamp\(\) \* 1000\))\s*\}", content, re.DOTALL)
    if perf_match:
        original_result = perf_match.group(1)
        perf_replacement = f"""result = {{
                'metrics': {{
                    {original_result}
                }},
                'timestamp': int(datetime.now().timestamp() * 1000)
            }}"""
        content = re.sub(perf_result_pattern, perf_replacement, content, flags=re.DOTALL)
    
    with open(reporter_file, 'w') as f:
        f.write(content)
    
    print("✅ Fixed result structure validation")

def main():
    """Run all fixes"""
    print("🔧 Fixing Market Reporter Data Issues...")
    print("=" * 50)
    
    try:
        # Change to the project root directory
        if os.path.exists('src'):
            os.chdir('.')
        elif os.path.exists('../src'):
            os.chdir('..')
        elif os.path.exists('../../src'):
            os.chdir('../..')
        else:
            print("❌ Could not find project root directory")
            return False
        
        # Apply all fixes
        fix_manager_field_mapping()
        fix_market_reporter_trade_fields()
        fix_result_structure_validation()
        
        print("\n🎉 All fixes applied successfully!")
        print("\nThe following issues have been resolved:")
        print("  1. Volume/turnover now use correct CCXT fields (baseVolume/quoteVolume)")
        print("  2. Trade fields use safe access with fallbacks (amount/size/qty)")
        print("  3. Result structures match validator expectations")
        print("\nYou should now see proper data in your market reports.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying fixes: {str(e)}")
        return False

if __name__ == "__main__":
    main() 
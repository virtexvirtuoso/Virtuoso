#!/usr/bin/env python3
"""
Rename 'liquidity_zones' to 'smart_money_flow' throughout the codebase.
This better represents what the indicator actually measures - smart money order flow patterns.
"""

import os
import re
from pathlib import Path

def rename_in_file(filepath, dry_run=False):
    """Rename liquidity_zones to smart_money_flow in a single file."""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    replacements = 0
    
    # Replace various forms of the term
    patterns = [
        # Direct references
        (r"'liquidity_zones'", "'smart_money_flow'"),
        (r'"liquidity_zones"', '"smart_money_flow"'),
        (r'liquidity_zones:', 'smart_money_flow:'),
        (r'liquidity_zones =', 'smart_money_flow ='),
        (r'self\.liquidity_zones', 'self.smart_money_flow'),
        
        # Function names
        (r'_calculate_liquidity_zones', '_calculate_smart_money_flow'),
        (r'_detect_liquidity_zones', '_detect_smart_money_flow'),
        (r'_score_liquidity_proximity', '_score_smart_money_proximity'),
        (r'calculate_liquidity_zones', 'calculate_smart_money_flow'),
        
        # Comments and docstrings (keeping the concept explanation)
        (r'# Smart Money Concepts - Liquidity Zones', '# Smart Money Concepts - Order Flow'),
        (r'Liquidity zones', 'Smart money flow zones'),
        (r'liquidity zones', 'smart money flow zones'),
        (r'Liquidity Zones', 'Smart Money Flow'),
        
        # Variable names
        (r'zones_score', 'flow_score'),
        (r'liquidity_zones_score', 'smart_money_flow_score'),
    ]
    
    for pattern, replacement in patterns:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            replacements += len(re.findall(pattern, content))
            content = new_content
    
    if replacements > 0:
        if not dry_run:
            with open(filepath, 'w') as f:
                f.write(content)
        return replacements
    return 0

def main():
    """Main function to rename liquidity_zones across the codebase."""
    
    base_path = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')
    
    # Files to process
    files_to_process = [
        'indicators/orderflow_indicators.py',
        'analysis/core/alpha_scanner.py',
        'analysis/core/interpretation_generator.py',
        'analysis/market_analyzer.py',
        'analysis/market/interpretation_generator.py',
        'analysis/market/market_analyzer.py',
        'api/models/alpha.py',
        'config/schema.py',
        'core/analysis/alpha_scanner.py',
        'core/analysis/interpretation_generator.py',
        'core/interpretation/interpretation_manager.py',
        'core/reporting/examples/generate_test_report.py',
        'indicators/orderbook_indicators.py',
    ]
    
    print("=" * 60)
    print("🔄 Renaming 'liquidity_zones' to 'smart_money_flow'")
    print("=" * 60)
    
    total_replacements = 0
    
    # First, do a dry run to show what will be changed
    print("\n📋 Dry run - files that will be modified:")
    for file_path in files_to_process:
        full_path = base_path / file_path
        if full_path.exists():
            count = rename_in_file(full_path, dry_run=True)
            if count > 0:
                print(f"   ✓ {file_path}: {count} replacements")
                total_replacements += count
        else:
            print(f"   ⚠️  {file_path}: File not found")
    
    if total_replacements == 0:
        print("\n❌ No replacements found. Terms may have already been renamed.")
        return
    
    print(f"\nTotal replacements to be made: {total_replacements}")
    
    # Perform actual replacements
    print("\n🔧 Applying changes...")
    for file_path in files_to_process:
        full_path = base_path / file_path
        if full_path.exists():
            count = rename_in_file(full_path, dry_run=False)
            if count > 0:
                print(f"   ✅ Modified {file_path}")
    
    print("\n" + "=" * 60)
    print("✅ Renaming complete!")
    print("\n📝 Summary:")
    print("   - 'liquidity_zones' → 'smart_money_flow'")
    print("   - This better represents Smart Money order flow analysis")
    print("   - The indicator still tracks stop loss clusters and sweeps")
    print("=" * 60)

if __name__ == "__main__":
    main()
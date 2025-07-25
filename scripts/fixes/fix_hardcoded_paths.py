#!/usr/bin/env python3
"""
Fix all hardcoded Mac paths to use relative paths or dynamic path resolution.
"""

import os
import re
import sys
from pathlib import Path

def fix_python_files():
    """Fix hardcoded paths in Python files."""
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    
    # Pattern to match hardcoded Mac paths
    mac_path_pattern = re.compile(r'/Users/ffv_macmini/Desktop/Virtuoso_ccxt')
    
    # Files to fix
    python_files_with_paths = [
        'tests/test_rich_alert.py',
        'tests/market/test_ticker.py',
        'scripts/additional_binance_tests.py',
        'scripts/test_1_fetch_markets.py',
        'scripts/test_2_fetch_ohlcv.py',
        'scripts/test_3_watch_ticker.py',
        'scripts/test_4_fetch_order_book.py',
        'scripts/test_5_fetch_trades.py',
        'scripts/test_6_create_order.py',
        'scripts/test_7_fetch_balance.py',
        'scripts/test_8_fetch_positions.py',
        'scripts/run_all_binance_integration_tests.py',
        'scripts/restart_application.py',
        'scripts/testing/test_market_report_pdf_fix.py',
        'scripts/testing/test_config.py',
        'scripts/testing/test_volume_enhanced_price_structure.py',
        'scripts/testing/test_pdf_attachment_fix.py',
        'scripts/testing/test_binance_symbols.py',
    ]
    
    fixed_count = 0
    
    for file_path in python_files_with_paths:
        full_path = project_root / file_path
        if not full_path.exists():
            print(f"Skipping {file_path} - file not found")
            continue
            
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Check if file has hardcoded paths
            if mac_path_pattern.search(content):
                # Replace sys.path.append with dynamic path
                content = re.sub(
                    r"sys\.path\.append\('/Users/ffv_macmini/Desktop/Virtuoso_ccxt'\)",
                    "sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))",
                    content
                )
                
                # Replace other hardcoded paths
                content = mac_path_pattern.sub("os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))", content)
                
                # Add import os if not present
                if 'import os' not in content and 'os.' in content:
                    lines = content.split('\n')
                    import_added = False
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            lines.insert(i + 1, 'import os')
                            import_added = True
                            break
                    if not import_added:
                        lines.insert(0, 'import os')
                    content = '\n'.join(lines)
                
                with open(full_path, 'w') as f:
                    f.write(content)
                print(f"✅ Fixed {file_path}")
                fixed_count += 1
                
        except Exception as e:
            print(f"❌ Error fixing {file_path}: {e}")
    
    return fixed_count

def main():
    """Main function."""
    print("🔧 Fixing hardcoded Mac paths in Python files...")
    
    fixed_count = fix_python_files()
    
    print(f"\n✅ Fixed {fixed_count} files with hardcoded paths")
    print("\n📝 Shell scripts should be fixed manually as they've already been updated")
    print("\n⚠️  Don't forget to:")
    print("  1. Update config/templates_config.json on VPS")
    print("  2. Sync all fixed files to VPS")
    print("  3. Restart the application on VPS")

if __name__ == "__main__":
    main()
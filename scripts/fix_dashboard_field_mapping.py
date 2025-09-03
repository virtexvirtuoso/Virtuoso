#!/usr/bin/env python3
"""
Fix Dashboard Field Mapping Issues
Addresses the data structure mismatches between expected and actual Bybit API responses
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def backup_file(filepath):
    """Create timestamped backup of file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = PROJECT_ROOT / "backups" / f"pre_field_mapping_fix_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    rel_path = Path(filepath).relative_to(PROJECT_ROOT)
    backup_path = backup_dir / rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up: {rel_path}")
    return backup_dir

def fix_bybit_exchange_fields():
    """Fix volume field mapping in Bybit exchange integration"""
    bybit_file = PROJECT_ROOT / "src/core/exchanges/bybit.py"
    
    if not bybit_file.exists():
        print(f"❌ File not found: {bybit_file}")
        return False
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Fix volume field mapping
    fixes = [
        # Map volume24h to volume for consistency
        ("'volume': float(ticker.get('volume', 0))",
         "'volume': float(ticker.get('volume24h', ticker.get('volume', 0)))"),
        
        # Ensure lastPrice fallback to last
        ("'price': float(ticker.get('lastPrice', 0))",
         "'price': float(ticker.get('lastPrice', ticker.get('last', 0)))"),
         
        # Fix percentage field
        ("'change_24h': float(ticker.get('percentage', 0))",
         "'change_24h': float(ticker.get('percentage', ticker.get('percent', 0)))")
    ]
    
    modified = False
    for old, new in fixes:
        if old in content and new not in content:
            content = content.replace(old, new)
            modified = True
            print(f"  ✅ Fixed: {old[:30]}... -> {new[:30]}...")
    
    if modified:
        with open(bybit_file, 'w') as f:
            f.write(content)
        print(f"✅ Updated: {bybit_file.name}")
    else:
        print(f"ℹ️  No changes needed: {bybit_file.name}")
    
    return True

def fix_dashboard_integration_fields():
    """Fix field references in dashboard integration"""
    dashboard_file = PROJECT_ROOT / "src/dashboard/dashboard_integration.py"
    
    if not dashboard_file.exists():
        print(f"❌ File not found: {dashboard_file}")
        return False
    
    with open(dashboard_file, 'r') as f:
        content = f.read()
    
    # Add field mapping helper function
    field_mapper = '''
def get_ticker_field(ticker, field_name, default=0):
    """Get field from ticker with fallback support"""
    if not ticker:
        return default
    
    # Field mapping for different exchange formats
    field_map = {
        'price': ['last', 'lastPrice', 'price'],
        'volume': ['volume24h', 'baseVolume', 'volume'],
        'change_24h': ['percentage', 'percent', 'change24h'],
        'bid': ['bid', 'bidPrice'],
        'ask': ['ask', 'askPrice']
    }
    
    if field_name in field_map:
        for possible_field in field_map[field_name]:
            if possible_field in ticker:
                return float(ticker.get(possible_field, default))
    
    return float(ticker.get(field_name, default))
'''
    
    # Add helper function if not exists
    if "def get_ticker_field" not in content:
        # Add after imports
        import_end = content.find('\n\nclass')
        if import_end > 0:
            content = content[:import_end] + '\n' + field_mapper + content[import_end:]
            print("  ✅ Added field mapping helper function")
    
    # Fix field accesses to use helper
    replacements = [
        ("ticker.get('last', 0)", "get_ticker_field(ticker, 'price', 0)"),
        ("ticker.get('lastPrice', 0)", "get_ticker_field(ticker, 'price', 0)"),
        ("ticker.get('volume', 0)", "get_ticker_field(ticker, 'volume', 0)"),
        ("ticker.get('baseVolume', 0)", "get_ticker_field(ticker, 'volume', 0)"),
        ("ticker.get('percentage', 0)", "get_ticker_field(ticker, 'change_24h', 0)"),
    ]
    
    for old, new in replacements:
        if old in content and new not in content:
            content = content.replace(old, new)
            print(f"  ✅ Fixed: {old} -> {new}")
    
    with open(dashboard_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated: {dashboard_file.name}")
    return True

def fix_cache_adapter_fields():
    """Fix field mapping in cache adapter"""
    cache_file = PROJECT_ROOT / "src/api/cache_adapter_direct.py"
    
    if not cache_file.exists():
        print(f"❌ File not found: {cache_file}")
        return False
    
    with open(cache_file, 'r') as f:
        content = f.read()
    
    # Ensure proper field extraction with fallbacks
    fixes = [
        ("'price': market_data.get('price', 0)",
         "'price': market_data.get('ticker', {}).get('last', market_data.get('ticker', {}).get('lastPrice', 0))"),
        
        ("'volume_24h': market_data.get('volume_24h', 0)",
         "'volume_24h': market_data.get('ticker', {}).get('volume24h', market_data.get('ticker', {}).get('baseVolume', 0))"),
         
        ("'change_24h': market_data.get('change_24h', 0)",
         "'change_24h': market_data.get('ticker', {}).get('percentage', market_data.get('ticker', {}).get('percent', 0))")
    ]
    
    modified = False
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            modified = True
            print(f"  ✅ Fixed: {old[:40]}...")
    
    if modified:
        with open(cache_file, 'w') as f:
            f.write(content)
        print(f"✅ Updated: {cache_file.name}")
    else:
        print(f"ℹ️  No changes needed: {cache_file.name}")
    
    return True

def main():
    """Apply all field mapping fixes"""
    print("=" * 60)
    print("🔧 DASHBOARD FIELD MAPPING FIX")
    print("=" * 60)
    
    # Create backup
    print("\n📦 Creating backups...")
    backup_dir = None
    
    files_to_backup = [
        "src/core/exchanges/bybit.py",
        "src/dashboard/dashboard_integration.py",
        "src/api/cache_adapter_direct.py"
    ]
    
    for file_path in files_to_backup:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists():
            if not backup_dir:
                backup_dir = backup_file(full_path)
            else:
                backup_file(full_path)
    
    if backup_dir:
        print(f"\n💾 Backup location: {backup_dir}")
    
    # Apply fixes
    print("\n🔧 Applying fixes...")
    
    print("\n1. Fixing Bybit exchange fields...")
    fix_bybit_exchange_fields()
    
    print("\n2. Fixing dashboard integration fields...")
    fix_dashboard_integration_fields()
    
    print("\n3. Fixing cache adapter fields...")
    fix_cache_adapter_fields()
    
    print("\n" + "=" * 60)
    print("✅ FIELD MAPPING FIXES COMPLETE")
    print("=" * 60)
    
    print("\n📋 Next steps:")
    print("1. Test locally: python3 scripts/test_dashboard_fixes_comprehensive.py")
    print("2. If tests pass, deploy: ./scripts/deploy_field_mapping_fix.sh")
    print(f"3. To rollback: cp -r {backup_dir}/* {PROJECT_ROOT}/src/")

if __name__ == "__main__":
    main()
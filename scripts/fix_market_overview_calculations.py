#!/usr/bin/env python3
"""
Fix Market Overview Calculations
Ensures market overview data is properly calculated and cached
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
    backup_dir = PROJECT_ROOT / "backups" / f"pre_market_overview_fix_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    rel_path = Path(filepath).relative_to(PROJECT_ROOT)
    backup_path = backup_dir / rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up: {rel_path}")
    return backup_dir

def fix_cache_adapter_market_overview():
    """Fix market overview calculation in cache adapter"""
    cache_file = PROJECT_ROOT / "src/api/cache_adapter_direct.py"
    
    if not cache_file.exists():
        print(f"❌ File not found: {cache_file}")
        return False
    
    with open(cache_file, 'r') as f:
        content = f.read()
    
    # Add market overview calculation helper
    market_overview_helper = '''
    def _calculate_market_overview(self) -> dict:
        """Calculate market overview from available data"""
        try:
            # Get all market data from cache
            symbols_data = []
            total_volume = 0
            active_symbols = 0
            up_count = 0
            down_count = 0
            
            # Try to get confluence scores which have market data
            confluence_key = "confluence:scores"
            confluence_data = self.cache_manager.get(confluence_key) if self.cache_manager else None
            
            if confluence_data and isinstance(confluence_data, list):
                for item in confluence_data:
                    if isinstance(item, dict):
                        active_symbols += 1
                        volume = item.get('volume_24h', 0)
                        total_volume += volume
                        change = item.get('change_24h', 0)
                        
                        if change > 0:
                            up_count += 1
                        elif change < 0:
                            down_count += 1
            
            # Also check for signals data
            signals_key = "analysis:signals"
            signals_data = self.cache_manager.get(signals_key) if self.cache_manager else None
            
            if signals_data and isinstance(signals_data, list) and active_symbols == 0:
                for signal in signals_data:
                    if isinstance(signal, dict):
                        active_symbols += 1
                        volume = signal.get('volume', 0)
                        total_volume += volume
                        change = signal.get('change_24h', 0)
                        
                        if change > 0:
                            up_count += 1
                        elif change < 0:
                            down_count += 1
            
            return {
                'active_symbols': active_symbols,
                'total_volume': total_volume,
                'total_volume_24h': total_volume,
                'market_breadth': {
                    'up': up_count,
                    'down': down_count,
                    'neutral': active_symbols - up_count - down_count
                },
                'timestamp': datetime.now().timestamp()
            }
            
        except Exception as e:
            logger.error(f"Error calculating market overview: {e}")
            return {
                'active_symbols': 0,
                'total_volume': 0,
                'total_volume_24h': 0,
                'market_breadth': {'up': 0, 'down': 0, 'neutral': 0},
                'timestamp': datetime.now().timestamp()
            }
'''
    
    # Check if we need to add the helper function
    if "_calculate_market_overview" not in content:
        # Find a good place to add it (after __init__ method)
        import_end = content.find('    def get_dashboard_data')
        if import_end > 0:
            content = content[:import_end] + market_overview_helper + '\n' + content[import_end:]
            print("  ✅ Added market overview calculation helper")
    
    # Fix the get_dashboard_data method to use calculated overview if cache is empty
    old_overview = '''overview = self.cache_manager.get("market:overview") if self.cache_manager else None'''
    new_overview = '''overview = self.cache_manager.get("market:overview") if self.cache_manager else None
        if not overview or overview.get('total_volume', 0) == 0:
            # Calculate from available data
            overview = self._calculate_market_overview()
            if overview['active_symbols'] > 0 and self.cache_manager:
                # Cache the calculated overview
                self.cache_manager.set("market:overview", overview, ttl=30)'''
    
    if old_overview in content and new_overview not in content:
        content = content.replace(old_overview, new_overview)
        print("  ✅ Updated get_dashboard_data to calculate overview when missing")
    
    # Also fix the mobile data endpoint
    old_mobile = '''market_overview = {
            'total_volume_24h': 0,
            'active_symbols': 0,
            'market_breadth': {'up': 0, 'down': 0}
        }'''
    
    new_mobile = '''# Calculate from confluence scores if no overview
        market_overview = self._calculate_market_overview()
        if market_overview['active_symbols'] == 0:
            # Fallback to basic structure
            market_overview = {
                'total_volume_24h': 0,
                'active_symbols': 0,
                'market_breadth': {'up': 0, 'down': 0}
            }'''
    
    if old_mobile in content:
        content = content.replace(old_mobile, new_mobile)
        print("  ✅ Updated mobile data to calculate overview")
    
    with open(cache_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated: {cache_file.name}")
    return True

def fix_dashboard_integration_overview():
    """Ensure dashboard integration properly calculates market overview"""
    dashboard_file = PROJECT_ROOT / "src/dashboard/dashboard_integration.py"
    
    if not dashboard_file.exists():
        print(f"❌ File not found: {dashboard_file}")
        return False
    
    with open(dashboard_file, 'r') as f:
        content = f.read()
    
    # Fix market overview aggregation
    old_code = '''total_volume += ticker.get('quoteVolume', 0)'''
    new_code = '''# Use the field mapping helper for volume
                            volume = get_ticker_field(ticker, 'volume', 0)
                            if volume == 0:  # Fallback to quoteVolume
                                volume = ticker.get('quoteVolume', ticker.get('volume24h', 0))
                            total_volume += volume'''
    
    if old_code in content and new_code not in content:
        content = content.replace(old_code, new_code)
        print("  ✅ Fixed volume aggregation in market overview")
    
    with open(dashboard_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated: {dashboard_file.name}")
    return True

def main():
    """Apply all market overview fixes"""
    print("=" * 60)
    print("🔧 MARKET OVERVIEW FIX")
    print("=" * 60)
    
    # Create backup
    print("\n📦 Creating backups...")
    backup_dir = None
    
    files_to_backup = [
        "src/api/cache_adapter_direct.py",
        "src/dashboard/dashboard_integration.py"
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
    
    print("\n1. Fixing cache adapter market overview...")
    fix_cache_adapter_market_overview()
    
    print("\n2. Fixing dashboard integration overview...")
    fix_dashboard_integration_overview()
    
    print("\n" + "=" * 60)
    print("✅ MARKET OVERVIEW FIXES COMPLETE")
    print("=" * 60)
    
    print("\n📋 Next steps:")
    print("1. Deploy to VPS: ./scripts/deploy_market_overview_fix.sh")
    print("2. Test: python3 scripts/test_dashboard_fixes_comprehensive.py --vps")
    print(f"3. To rollback: cp -r {backup_dir}/* {PROJECT_ROOT}/src/")

if __name__ == "__main__":
    main()
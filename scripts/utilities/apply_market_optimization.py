#!/usr/bin/env python3
"""Script to apply market API optimizations."""

import os
import shutil
from pathlib import Path

def apply_optimizations():
    """Apply the optimized market routes to the existing file."""
    
    # Paths
    project_root = Path(__file__).parent
    original_file = project_root / "src/api/routes/market.py"
    optimized_file = project_root / "src/api/routes/market_optimized.py"
    backup_file = project_root / "src/api/routes/market_original.py"
    
    print("🔧 Applying Market API Optimizations")
    print("=" * 50)
    
    # Check if files exist
    if not original_file.exists():
        print(f"❌ Original file not found: {original_file}")
        return False
    
    if not optimized_file.exists():
        print(f"❌ Optimized file not found: {optimized_file}")
        return False
    
    # Create backup
    print(f"1. Creating backup: {backup_file}")
    shutil.copy2(original_file, backup_file)
    print("   ✅ Backup created")
    
    # Read both files
    with open(original_file, 'r') as f:
        original_content = f.read()
    
    with open(optimized_file, 'r') as f:
        optimized_content = f.read()
    
    # Find the get_market_overview function in original
    import_section = original_content.split('@router.get("/overview")')[0]
    
    # Combine imports and optimized code
    print("2. Merging optimized code...")
    
    # Add asyncio import if not present
    if "import asyncio" not in import_section:
        import_lines = import_section.split('\n')
        for i, line in enumerate(import_lines):
            if line.startswith('from typing import'):
                import_lines.insert(i, 'import asyncio')
                import_lines.insert(i+1, 'import time')
                break
        import_section = '\n'.join(import_lines)
    
    # Extract the optimized functions from the optimized file
    optimized_functions = optimized_content.split('# In-memory cache')[1]
    
    # Combine
    new_content = import_section + '\n# In-memory cache' + optimized_functions
    
    # Write the updated file
    print("3. Writing updated market.py...")
    with open(original_file, 'w') as f:
        f.write(new_content)
    print("   ✅ File updated")
    
    print("\n✅ Optimization applied successfully!")
    print("\nNext steps:")
    print("1. Deploy to server: scp src/api/routes/market.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/")
    print("2. Restart server: ssh linuxuser@45.77.40.77 '...'")
    
    return True

if __name__ == "__main__":
    apply_optimizations()
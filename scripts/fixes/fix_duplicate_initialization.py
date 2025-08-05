#!/usr/bin/env python3
"""
Fix duplicate initialization issue in monitor.py
The monitor.start() method is re-initializing an already initialized exchange.
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def backup_file(filepath):
    """Create a backup of the file before modifying."""
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up {filepath} to {backup_path}")
    return backup_path

def fix_monitor_duplicate_init():
    """Fix the duplicate initialization in monitor.py."""
    monitor_file = project_root / "src/monitoring/monitor.py"
    
    if not monitor_file.exists():
        print(f"❌ File not found: {monitor_file}")
        return False
    
    backup_file(monitor_file)
    
    with open(monitor_file, 'r') as f:
        content = f.read()
    
    # Fix: Check if exchange is already initialized before re-initializing
    old_init = """            self.logger.debug(f"Exchange instance retrieved: {bool(self.exchange)}")
            self.logger.debug("Initializing exchange...")
            
            # Initialize exchange
            await self.exchange.initialize()"""
    
    new_init = """            self.logger.debug(f"Exchange instance retrieved: {bool(self.exchange)}")
            
            # Check if exchange is already initialized
            if hasattr(self.exchange, 'initialized') and self.exchange.initialized:
                self.logger.debug("Exchange already initialized, skipping re-initialization")
            else:
                self.logger.debug("Initializing exchange...")
                # Initialize exchange with timeout
                try:
                    init_success = await asyncio.wait_for(
                        self.exchange.initialize(),
                        timeout=30.0  # 30 second timeout
                    )
                    if not init_success:
                        self.logger.error("Failed to initialize exchange")
                        return
                except asyncio.TimeoutError:
                    self.logger.error("Exchange initialization timed out after 30s")
                    return"""
    
    if old_init in content:
        content = content.replace(old_init, new_init)
        print("✅ Fixed duplicate initialization in monitor.start()")
    else:
        print("⚠️  Monitor initialization pattern not found or already modified")
    
    # Add asyncio import if needed
    if "asyncio.wait_for" in content and "import asyncio" not in content:
        # Find the imports section
        import_lines = content.split('\n')
        for i, line in enumerate(import_lines):
            if line.startswith('import ') or line.startswith('from '):
                # Add after the first import
                import_lines.insert(i + 1, 'import asyncio')
                content = '\n'.join(import_lines)
                print("✅ Added asyncio import")
                break
    
    with open(monitor_file, 'w') as f:
        f.write(content)
    
    print("✅ Monitor.py fixes applied")
    return True

def main():
    """Apply duplicate initialization fix."""
    print("🔧 Fixing duplicate initialization issue")
    print("=" * 60)
    
    success = fix_monitor_duplicate_init()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Duplicate initialization fix applied successfully!")
        print("\nThe issue was: monitor.start() was re-initializing an already")
        print("initialized exchange, causing a hang on the second init attempt.")
    else:
        print("❌ Fix failed. Please check the output above.")
    
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
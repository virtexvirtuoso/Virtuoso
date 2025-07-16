#!/usr/bin/env python3
"""
Script to verify that template fix has been applied successfully.
"""

import os
import time
from pathlib import Path

def verify_template_fix():
    """Verify that template duplication issue has been resolved."""
    
    print("🔍 Verifying Template Fix...")
    
    # Updated paths after consolidation
    canonical_template = "src/core/reporting/templates/market_report_dark.html"
    backup_template = "templates.bak/market_report_dark.html"
    symlink_path = "templates"
    
    # Check that canonical template exists
    if os.path.exists(canonical_template):
        size = os.path.getsize(canonical_template)
        print(f"✅ Canonical template exists: {canonical_template} ({size} bytes)")
    else:
        print(f"❌ Canonical template missing: {canonical_template}")
        return False
    
    # Check symlink status
    if os.path.islink(symlink_path):
        target = os.readlink(symlink_path)
        print(f"✅ Symlink exists: {symlink_path} -> {target}")
        print(f"   This allows backward compatibility access to templates")
    elif os.path.exists(symlink_path):
        print(f"⚠️  {symlink_path} exists but is not a symlink")
    else:
        print(f"ℹ️  No symlink at {symlink_path}")
    
    # Check that old duplicate locations are removed (excluding symlink access)
    old_duplicate_locations = [
        "src/core/reporting/templates/market_report_dark.html"  # Check canonical template location
    ]
    
    duplicates_found = False
    for location in old_duplicate_locations:
        if os.path.exists(location) and not os.path.islink(os.path.dirname(location)):
            print(f"⚠️  Actual duplicate found: {location}")
            duplicates_found = True
        else:
            print(f"✅ No duplicate at: {location}")
    
    if duplicates_found:
        print("❌ Template duplication still exists!")
        return False
    
    # Check backup exists
    if os.path.exists(backup_template):
        size = os.path.getsize(backup_template)
        print(f"✅ Backup template exists: {backup_template} ({size} bytes)")
    else:
        print(f"ℹ️  No backup template found (optional): {backup_template}")
    
    # Verify template access through symlink works
    symlink_template = "templates/market_report_dark.html"
    if os.path.exists(symlink_template) and os.path.islink("templates"):
        print(f"✅ Template accessible via symlink: {symlink_template}")
        # Verify it's the same file
        canonical_stat = os.stat(canonical_template)
        symlink_stat = os.stat(symlink_template)
        if canonical_stat.st_ino == symlink_stat.st_ino:
            print(f"✅ Symlink points to same file (inode: {canonical_stat.st_ino})")
        else:
            print(f"⚠️  Symlink points to different file!")
            return False
    
    print("✅ Template consolidation successful - single canonical file with symlink access!")
    return True

if __name__ == "__main__":
    success = verify_template_fix()
    exit(0 if success else 1) 
#!/usr/bin/env python3
"""
Fix silent failures in the alert system by adding proper error handling and logging.
This script identifies and patches bare except blocks and missing error handlers.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

def find_silent_failures(file_path: Path) -> List[Tuple[int, str]]:
    """Find lines with silent failure patterns."""
    issues = []
    
    if not file_path.exists():
        return issues
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        # Check for bare except
        if re.match(r'^\s*except:\s*$', line):
            issues.append((i, 'bare_except'))
        # Check for except: pass
        elif re.match(r'^\s*except.*:\s*pass\s*$', line):
            issues.append((i, 'except_pass'))
        # Check for broad exception catching without logging
        elif re.match(r'^\s*except\s+Exception.*:\s*$', line):
            # Check if next line has logging
            if i < len(lines) and 'log' not in lines[i].lower() and 'print' not in lines[i].lower():
                issues.append((i, 'unlogged_exception'))
    
    return issues

def fix_file(file_path: Path, backup: bool = True) -> int:
    """Fix silent failures in a file."""
    issues = find_silent_failures(file_path)
    
    if not issues:
        return 0
    
    print(f"\n📁 Fixing {file_path.name}...")
    print(f"   Found {len(issues)} issues to fix")
    
    # Create backup
    if backup:
        backup_path = file_path.with_suffix(file_path.suffix + '.backup')
        with open(file_path, 'r') as f:
            content = f.read()
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"   Created backup: {backup_path.name}")
    
    # Read file
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Apply fixes
    fixes_applied = 0
    for line_num, issue_type in reversed(issues):  # Work backwards to maintain line numbers
        idx = line_num - 1
        
        if issue_type == 'bare_except':
            # Replace bare except with Exception
            indent = len(lines[idx]) - len(lines[idx].lstrip())
            lines[idx] = ' ' * indent + 'except Exception as e:\n'
            # Add logging
            if idx + 1 < len(lines):
                next_indent = len(lines[idx + 1]) - len(lines[idx + 1].lstrip())
                if next_indent <= indent:
                    # No body, add logging
                    lines.insert(idx + 1, ' ' * (indent + 4) + 'logger.error(f"Alert error: {e}")\n')
            fixes_applied += 1
            
        elif issue_type == 'except_pass':
            # Replace except: pass with proper logging
            indent = len(lines[idx]) - len(lines[idx].lstrip())
            exception_match = re.match(r'^\s*except\s+(.*?):\s*pass', lines[idx])
            exception_type = exception_match.group(1) if exception_match else 'Exception'
            
            lines[idx] = f"{' ' * indent}except {exception_type} as e:\n"
            lines.insert(idx + 1, ' ' * (indent + 4) + 'logger.error(f"Alert error (silent): {e}")\n')
            fixes_applied += 1
            
        elif issue_type == 'unlogged_exception':
            # Add logging after exception
            indent = len(lines[idx]) - len(lines[idx].lstrip())
            lines.insert(idx + 1, ' ' * (indent + 4) + 'logger.error(f"Unhandled exception: {e}", exc_info=True)\n')
            fixes_applied += 1
    
    # Add logger import if not present
    has_logger = any('logger' in line for line in lines[:50])
    if not has_logger and fixes_applied > 0:
        # Find imports section
        import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_idx = i + 1
        
        lines.insert(import_idx, 'import logging\n')
        lines.insert(import_idx + 1, '\n')
        lines.insert(import_idx + 2, 'logger = logging.getLogger(__name__)\n')
        lines.insert(import_idx + 3, '\n')
    
    # Write fixed file
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    print(f"   ✅ Applied {fixes_applied} fixes")
    return fixes_applied

def main():
    """Fix silent failures in alert-related files."""
    print("🔧 FIXING SILENT FAILURES IN ALERT SYSTEM")
    print("=" * 60)
    
    # Files to fix
    alert_files = [
        'src/monitoring/alert_manager.py',
        'src/monitoring/components/alerts/alert_manager_refactored.py',
        'src/monitoring/components/alerts/alert_delivery.py',
        'src/core/analysis/liquidation_detector.py',
        'src/monitoring/smart_money_detector.py',
        'src/core/analysis/confluence.py',
        'src/monitoring/monitor.py',
        'src/websocket/handler.py',
        'src/core/streaming/realtime_pipeline.py'
    ]
    
    total_fixes = 0
    fixed_files = 0
    
    for file_path in alert_files:
        full_path = Path(file_path)
        if not full_path.exists():
            full_path = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt') / file_path
        
        if full_path.exists():
            fixes = fix_file(full_path)
            if fixes > 0:
                fixed_files += 1
                total_fixes += fixes
        else:
            print(f"⚠️ File not found: {file_path}")
    
    print("\n" + "=" * 60)
    print("📊 FIX SUMMARY")
    print("-" * 60)
    print(f"Files fixed: {fixed_files}")
    print(f"Total fixes applied: {total_fixes}")
    
    if total_fixes > 0:
        print("\n💡 Next Steps:")
        print("1. Review the changes in each file")
        print("2. Test the alert system to ensure fixes work")
        print("3. Deploy to VPS using deployment script")
        print("4. Monitor alert health with monitoring script")
    
    print("\n✅ Silent failure fix complete!")

if __name__ == "__main__":
    main()
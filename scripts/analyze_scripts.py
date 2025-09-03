#!/usr/bin/env python3
"""
Script Categorization and Analysis Tool
Analyzes all shell scripts in the project and categorizes them for documentation.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def categorize_script(filename, first_lines):
    """Categorize a script based on its filename and initial content."""
    name = filename.lower()
    content = '\n'.join(first_lines[:10]).lower()
    
    # Service Management
    if any(keyword in name for keyword in ['setup_', 'start_', 'stop_', 'restart_', 'launch_', 'service']):
        return 'Service Management'
    
    # Docker/Container
    if any(keyword in name for keyword in ['docker_', 'container']):
        return 'Docker & Containers'
    
    # Testing
    if any(keyword in name for keyword in ['test_', '_test', 'validate', 'benchmark', 'check']):
        return 'Testing & Validation'
    
    # Deployment
    if any(keyword in name for keyword in ['deploy_', 'transfer_', 'sync_']):
        return 'Deployment'
    
    # Installation & Setup
    if any(keyword in name for keyword in ['install_', 'setup_', 'config', 'init']):
        return 'Installation & Setup'
    
    # Fix & Patch
    if any(keyword in name for keyword in ['fix_', 'patch_', 'repair_']) or 'fixes/' in name:
        return 'Fix & Patch'
    
    # Monitoring & Diagnostics
    if any(keyword in name for keyword in ['monitor_', 'diagnostic', 'health', 'status']):
        return 'Monitoring & Diagnostics'
    
    # Utility & Maintenance
    if any(keyword in name for keyword in ['cleanup_', 'backup_', 'update_', 'manage']):
        return 'Utility & Maintenance'
    
    # VPS Operations
    if any(keyword in name for keyword in ['vps_', '_vps']):
        return 'VPS Operations'
    
    return 'Other'

def get_script_info(script_path):
    """Extract basic information from a script."""
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        first_lines = [line.strip() for line in lines[:10]]
        
        # Check for existing documentation
        has_header = any('# Description:' in line or '# Purpose:' in line for line in first_lines)
        
        # Get script size
        line_count = len(lines)
        
        return {
            'path': str(script_path),
            'lines': line_count,
            'has_documentation': has_header,
            'first_lines': first_lines
        }
    except Exception as e:
        return {
            'path': str(script_path),
            'lines': 0,
            'has_documentation': False,
            'first_lines': [],
            'error': str(e)
        }

def main():
    project_root = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')
    scripts_dir = project_root / 'scripts'
    
    # Find all shell scripts
    shell_scripts = list(scripts_dir.rglob('*.sh'))
    
    categories = defaultdict(list)
    total_scripts = 0
    documented_scripts = 0
    
    print(f"Found {len(shell_scripts)} shell scripts")
    print("=" * 60)
    
    for script_path in sorted(shell_scripts):
        info = get_script_info(script_path)
        category = categorize_script(script_path.name, info['first_lines'])
        
        categories[category].append({
            'name': script_path.name,
            'path': str(script_path.relative_to(project_root)),
            'lines': info['lines'],
            'documented': info['has_documentation']
        })
        
        total_scripts += 1
        if info['has_documentation']:
            documented_scripts += 1
    
    # Print categorization results
    for category, scripts in sorted(categories.items()):
        documented = sum(1 for s in scripts if s['documented'])
        print(f"\n{category} ({len(scripts)} scripts, {documented} documented):")
        print("-" * 50)
        
        # Sort by priority (larger scripts first, then alphabetically)
        scripts.sort(key=lambda x: (-x['lines'], x['name']))
        
        for script in scripts[:10]:  # Show top 10 per category
            status = "✓" if script['documented'] else "✗"
            print(f"  {status} {script['name']} ({script['lines']} lines)")
        
        if len(scripts) > 10:
            print(f"  ... and {len(scripts) - 10} more scripts")
    
    print(f"\n" + "=" * 60)
    print(f"SUMMARY: {documented_scripts}/{total_scripts} scripts documented ({documented_scripts/total_scripts*100:.1f}%)")
    
    # Identify high priority scripts for documentation
    high_priority = []
    for category in ['Service Management', 'Docker & Containers', 'Testing & Validation', 'Installation & Setup']:
        if category in categories:
            undocumented = [s for s in categories[category] if not s['documented']]
            high_priority.extend(undocumented[:5])  # Top 5 from each category
    
    print(f"\nHIGH PRIORITY FOR DOCUMENTATION ({len(high_priority)} scripts):")
    print("-" * 50)
    for script in high_priority:
        print(f"  • {script['path']}")

if __name__ == "__main__":
    main()
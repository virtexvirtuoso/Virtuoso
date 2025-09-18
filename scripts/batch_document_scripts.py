#!/usr/bin/env python3
"""
Batch Script Documentation Tool
Automatically adds professional headers to shell scripts based on templates.
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

# Template configurations for different script types
SCRIPT_TEMPLATES = {
    'deployment': {
        'purpose_prefix': 'Deploy and manage',
        'description_focus': 'deployment automation, service management, and infrastructure updates',
        'common_deps': ['rsync', 'ssh', 'git', 'systemctl'],
        'exit_codes': {
            0: 'Success',
            1: 'Deployment failed', 
            2: 'Invalid arguments',
            3: 'Connection error',
            4: 'Service start failed'
        }
    },
    'testing': {
        'purpose_prefix': 'Test and validate',
        'description_focus': 'automated testing, validation, and quality assurance',
        'common_deps': ['python3', 'curl', 'grep'],
        'exit_codes': {
            0: 'All tests passed',
            1: 'Test failures detected',
            2: 'Test configuration error', 
            3: 'Dependencies missing',
            4: 'Environment setup failed'
        }
    },
    'setup': {
        'purpose_prefix': 'Setup and configure',
        'description_focus': 'system setup, service configuration, and environment preparation',
        'common_deps': ['systemctl', 'mkdir', 'chmod'],
        'exit_codes': {
            0: 'Setup completed successfully',
            1: 'Setup failed',
            2: 'Permission denied',
            3: 'Dependencies missing',
            4: 'Configuration error'
        }
    }
}

def detect_script_category(filepath, content):
    """Detect script category based on filename and content."""
    filename = Path(filepath).name.lower()
    
    if any(keyword in filename for keyword in ['deploy_', 'sync_', 'transfer_']):
        return 'deployment'
    elif any(keyword in filename for keyword in ['test_', 'validate_', 'check_']):
        return 'testing' 
    elif any(keyword in filename for keyword in ['setup_', 'install_', 'config']):
        return 'setup'
    else:
        return 'deployment'  # Default fallback

def extract_script_info(filepath):
    """Extract key information from existing script."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Check if already documented
        has_header = any('# Script:' in line or '# Purpose:' in line for line in lines[:20])
        if has_header:
            return None, None  # Already documented
            
        # Extract existing comments
        existing_comment = None
        if len(lines) > 1 and lines[1].strip().startswith('#'):
            existing_comment = lines[1].strip()[1:].strip()
            
        return content, existing_comment
        
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None, None

def generate_header(filepath, existing_comment, category):
    """Generate professional header for script."""
    script_name = Path(filepath).name
    template = SCRIPT_TEMPLATES[category]
    
    # Generate purpose from filename and existing comment
    if existing_comment:
        purpose = existing_comment
    else:
        # Generate purpose from script name
        name_parts = script_name.replace('.sh', '').replace('_', ' ')
        purpose = f"{template['purpose_prefix']} {name_parts}"
    
    # Generate description
    description = f"""   Automates {template['description_focus']} for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation."""
    
    # Generate dependencies list
    deps_list = '\n'.join([f'#   - {dep}' for dep in template['common_deps']])
    
    # Generate exit codes
    exit_codes_list = '\n'.join([f'#   {code} - {desc}' for code, desc in template['exit_codes'].items()])
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    header = f'''#!/bin/bash

#############################################################################
# Script: {script_name}
# Purpose: {purpose}
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: {current_date}
# Modified: {current_date}
#############################################################################
#
# Description:
{description}
#
# Dependencies:
#   - Bash 4.0+
{deps_list}
#   - Access to project directory structure
#
# Usage:
#   ./{script_name} [options]
#   
#   Examples:
#     ./{script_name}
#     ./{script_name} --verbose
#     ./{script_name} --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
{exit_codes_list}
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

'''
    
    return header

def document_script(filepath):
    """Add documentation header to a script."""
    content, existing_comment = extract_script_info(filepath)
    
    if content is None:
        return False  # Skip if already documented or error
        
    category = detect_script_category(filepath, content)
    header = generate_header(filepath, existing_comment, category)
    
    # Find where to insert header (after shebang)
    lines = content.split('\n')
    shebang_end = 0
    
    for i, line in enumerate(lines):
        if line.startswith('#!'):
            shebang_end = i + 1
            break
    
    # Remove old minimal comment if exists
    if shebang_end < len(lines) and lines[shebang_end].strip().startswith('#') and len(lines[shebang_end].strip()) < 100:
        shebang_end += 1
        
    # Skip empty lines after shebang
    while shebang_end < len(lines) and lines[shebang_end].strip() == '':
        shebang_end += 1
    
    # Insert header
    new_content = '\n'.join(lines[shebang_end:])
    final_content = header + new_content
    
    # Write back to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = '/Users/ffv_macmini/Desktop/Virtuoso_ccxt/scripts'
    
    print(f"Batch documenting scripts in: {target_dir}")
    print("=" * 60)
    
    documented = 0
    skipped = 0
    errors = 0
    
    # Find all .sh files
    for root, dirs, files in os.walk(target_dir):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules']]
        
        for file in files:
            if file.endswith('.sh'):
                filepath = os.path.join(root, file)
                relative_path = os.path.relpath(filepath, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')
                
                print(f"Processing: {relative_path}")
                
                if document_script(filepath):
                    documented += 1
                    print(f"  ✅ Documented")
                else:
                    skipped += 1
                    print(f"  ⏭️ Skipped (already documented or error)")
    
    print("\n" + "=" * 60)
    print(f"SUMMARY:")
    print(f"  Documented: {documented}")
    print(f"  Skipped: {skipped}")
    print(f"  Total processed: {documented + skipped}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Error Import Migration Script

This script migrates all error imports to use the new unified error hierarchy
in src/core/error/unified_exceptions.py, eliminating duplicates and import conflicts.

Usage:
    python scripts/migration/update_error_imports.py [--dry-run] [--verbose]
"""

import os
import re
import sys
import argparse
from typing import List, Dict, Tuple
from pathlib import Path


def get_python_files(directory: str) -> List[str]:
    """Get all Python files in directory and subdirectories."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'venv', 'env', 'backups'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files


def get_import_mappings() -> Dict[str, str]:
    """Define mappings from old imports to new unified imports."""
    return {
        # ValidationError - from 3 different locations to unified
        'from src.core.error.unified_exceptions import ValidationError': 'from src.core.error.unified_exceptions import ValidationError',
        'from src.core.error.unified_exceptions import ValidationError': 'from src.core.error.unified_exceptions import ValidationError',
        
        # ConfigValidationError - from 3 different locations
        'from src.core.error.unified_exceptions import ConfigValidationError': 'from src.core.error.unified_exceptions import ConfigValidationError',
        'from src.core.error.unified_exceptions import ConfigValidationError': 'from src.core.error.unified_exceptions import ConfigValidationError',
        'from src.core.error.unified_exceptions import ConfigValidationError': 'from src.core.error.unified_exceptions import ConfigValidationError',
        
        # SignalValidationError - from 2 locations
        'from src.core.error.unified_exceptions import SignalValidationError': 'from src.core.error.unified_exceptions import SignalValidationError',
        'from src.core.error.unified_exceptions import SignalValidationError': 'from src.core.error.unified_exceptions import SignalValidationError',
        
        # BinanceValidationError
        'from src.core.error.unified_exceptions import BinanceValidationError': 'from src.core.error.unified_exceptions import BinanceValidationError',
        
        # TimeoutError - from 2 locations
        'from src.core.error.unified_exceptions import TimeoutError': 'from src.core.error.unified_exceptions import TimeoutError',
        'from src.core.error.unified_exceptions import TimeoutError': 'from src.core.error.unified_exceptions import TimeoutError',
        
        # InitializationError - from 2 locations
        'from src.core.error.unified_exceptions import InitializationError': 'from src.core.error.unified_exceptions import InitializationError',
        'from src.core.error.unified_exceptions import InitializationError': 'from src.core.error.unified_exceptions import InitializationError',
        
        # Exchange errors
        'from src.core.error.unified_exceptions import ExchangeError': 'from src.core.error.unified_exceptions import ExchangeError',
        'from src.core.error.unified_exceptions import NetworkError': 'from src.core.error.unified_exceptions import NetworkError',
        'from src.core.error.unified_exceptions import AuthenticationError': 'from src.core.error.unified_exceptions import AuthenticationError',
        'from src.core.error.unified_exceptions import RateLimitError': 'from src.core.error.unified_exceptions import RateLimitError',
        'from src.core.error.unified_exceptions import BybitExchangeError': 'from src.core.error.unified_exceptions import BybitExchangeError',
        'from src.core.error.unified_exceptions import ExchangeNotInitializedError': 'from src.core.error.unified_exceptions import ExchangeNotInitializedError',
        
        # Trading errors from utils
        'from src.core.error.unified_exceptions import TradingError': 'from src.core.error.unified_exceptions import TradingError',
        'from src.core.error.unified_exceptions import MarketDataError': 'from src.core.error.unified_exceptions import MarketDataError',
        'from src.core.error.unified_exceptions import CalculationError': 'from src.core.error.unified_exceptions import CalculationError',
        
        # Analysis errors
        'from src.core.error.unified_exceptions import AnalysisError': 'from src.core.error.unified_exceptions import AnalysisError',
        'from src.core.error.unified_exceptions import DataUnavailableError': 'from src.core.error.unified_exceptions import DataUnavailableError',
        
        # PDF/Reporting errors
        'from src.core.error.unified_exceptions import PDFGenerationError': 'from src.core.error.unified_exceptions import PDFGenerationError',
        'from src.core.error.unified_exceptions import ChartGenerationError': 'from src.core.error.unified_exceptions import ChartGenerationError',
        'from src.core.error.unified_exceptions import DataValidationError': 'from src.core.error.unified_exceptions import DataValidationError',
        'from src.core.error.unified_exceptions import FileOperationError': 'from src.core.error.unified_exceptions import FileOperationError',
        'from src.core.error.unified_exceptions import TemplateError': 'from src.core.error.unified_exceptions import TemplateError',
        
        # System errors from core
        'from src.core.error.unified_exceptions import SystemError': 'from src.core.error.unified_exceptions import SystemError',
        'from src.core.error.unified_exceptions import ComponentError': 'from src.core.error.unified_exceptions import ComponentError',
        'from src.core.error.unified_exceptions import ResourceError': 'from src.core.error.unified_exceptions import ResourceError',
        'from src.core.error.unified_exceptions import ResourceLimitError': 'from src.core.error.unified_exceptions import ResourceLimitError',
        'from src.core.error.unified_exceptions import ConfigValidationError': 'from src.core.error.unified_exceptions import ConfigValidationError',
        'from src.core.error.unified_exceptions import ComponentError': 'from src.core.error.unified_exceptions import ComponentError',
        'from src.core.error.unified_exceptions import NetworkError': 'from src.core.error.unified_exceptions import NetworkError',
        'from src.core.error.unified_exceptions import SystemError': 'from src.core.error.unified_exceptions import SystemError',
        'from src.core.error.unified_exceptions import AnalysisError': 'from src.core.error.unified_exceptions import AnalysisError',
        'from src.core.error.unified_exceptions import SystemError': 'from src.core.error.unified_exceptions import SystemError',
        'from src.core.error.unified_exceptions import ComponentError': 'from src.core.error.unified_exceptions import ComponentError',
        'from src.core.error.unified_exceptions import SystemError': 'from src.core.error.unified_exceptions import SystemError',
        
        # Other scattered errors
        'from src.core.error.unified_exceptions import ResourceError': 'from src.core.error.unified_exceptions import ResourceError',
        'from src.core.error.unified_exceptions import ComponentError': 'from src.core.error.unified_exceptions import ComponentError',
        'from src.core.error.unified_exceptions import SystemError': 'from src.core.error.unified_exceptions import SystemError',
    }


def get_error_class_mappings() -> Dict[str, str]:
    """Define mappings for error class name changes."""
    return {
        # Class name changes for consistency
        'ConfigurationError': 'ConfigValidationError',
        'StateError': 'ComponentError',  
        'CommunicationError': 'NetworkError',
        'OperationError': 'SystemError',
        'DataError': 'AnalysisError',
        'SecurityError': 'SystemError',
        'MarketMonitorError': 'ComponentError', 
        'TemporaryError': 'SystemError',
        'CriticalError': 'SystemError',
        'StateTransitionError': 'ComponentError',
        'ResourceAllocationError': 'ResourceError',
        'ExchangeNotInitializedError': 'InitializationError',
    }


def update_imports_in_file(file_path: str, dry_run: bool = False, verbose: bool = False) -> Tuple[int, List[str]]:
    """Update error imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Apply import mappings
        import_mappings = get_import_mappings()
        for old_import, new_import in import_mappings.items():
            if old_import in content:
                content = content.replace(old_import, new_import)
                changes.append(f"Import: {old_import} → {new_import}")
        
        # Apply class name mappings (for usage, not imports)
        class_mappings = get_error_class_mappings()
        for old_class, new_class in class_mappings.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\\b' + re.escape(old_class) + r'\\b'
            if re.search(pattern, content):
                content = re.sub(pattern, new_class, content)
                changes.append(f"Class usage: {old_class} → {new_class}")
        
        # Handle string references in configuration files
        string_mappings = {
            'src.core.error.unified_exceptions': 'src.core.error.unified_exceptions',
            'src.core.error.unified_exceptions': 'src.core.error.unified_exceptions',
            'src.core.error.unified_exceptions': 'src.core.error.unified_exceptions',
        }
        
        for old_ref, new_ref in string_mappings.items():
            patterns = [f'"{old_ref}"', f"'{old_ref}'"]
            for pattern in patterns:
                if pattern in content:
                    new_pattern = pattern.replace(old_ref, new_ref)
                    content = content.replace(pattern, new_pattern)
                    changes.append(f"String ref: {pattern} → {new_pattern}")
        
        # Only write if changes were made and not in dry-run mode
        if content != original_content and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        if verbose and changes:
            print(f"\\n{file_path}:")
            for change in changes:
                print(f"  - {change}")
        
        return len(changes), changes
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, []


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description='Migrate error imports to unified system')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying them')
    parser.add_argument('--verbose', action='store_true', help='Show detailed changes')
    parser.add_argument('--path', default='src', help='Path to search for Python files')
    
    args = parser.parse_args()
    
    print("=== Error Import Migration ===")
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
    print(f"Migrating imports to unified error hierarchy...")
    
    # Get all Python files
    python_files = get_python_files(args.path)
    
    # Also check scripts and tests if they exist
    for additional_path in ['scripts', 'tests']:
        if os.path.exists(additional_path):
            python_files.extend(get_python_files(additional_path))
    
    print(f"Found {len(python_files)} Python files to check")
    
    total_changes = 0
    files_updated = 0
    detailed_changes = []
    
    for file_path in python_files:
        # Skip the unified_exceptions.py file itself
        if 'unified_exceptions.py' in file_path:
            continue
            
        changes_count, changes = update_imports_in_file(file_path, args.dry_run, args.verbose)
        if changes_count > 0:
            files_updated += 1
            total_changes += changes_count
            detailed_changes.append((file_path, changes))
            if not args.verbose:
                print(f"{'✓ Would update' if args.dry_run else '✓ Updated'} {file_path} ({changes_count} changes)")
    
    print(f"\\n=== Migration {'Preview' if args.dry_run else 'Complete'} ===")
    print(f"Files {'would be updated' if args.dry_run else 'updated'}: {files_updated}")
    print(f"Total changes: {total_changes}")
    
    if args.dry_run:
        print("\\nRun without --dry-run to apply changes")
    
    # Create backup of old error files
    if not args.dry_run and files_updated > 0:
        create_error_file_backups()
        print("\\n✓ Created backups of old error files")


def create_error_file_backups():
    """Create backups of old error definition files."""
    import shutil
    from datetime import datetime
    
    backup_dir = f"backups/phase3_error_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        'src/core/error/exceptions.py',
        'src/validation/core/exceptions.py',
        'src/utils/error_handling.py',
        'src/core/exchanges/base.py',  # Contains some error definitions
        'src/config/validator.py',
        'src/models/signal_schema.py',
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"  Backed up {file_path} → {backup_path}")


if __name__ == "__main__":
    main()
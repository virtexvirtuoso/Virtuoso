#!/usr/bin/env python3
"""Consolidate remaining duplicate classes to canonical implementations."""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
import shutil
from datetime import datetime

# Define the canonical locations for each class
CANONICAL_CLASSES = {
    'HealthStatus': {
        'canonical_path': 'src/monitoring/components/health_monitor.py',
        'canonical_import': 'from src.monitoring.components.health_monitor import HealthStatus',
        'duplicates': [
            'src/monitoring/health_monitor.py',
            'src/core/monitoring.py',
            'src/core/models/component.py',
            'src/core/models.py'
        ]
    },
    'ResourceManager': {
        'canonical_path': 'src/analysis/resource_manager.py',
        'canonical_import': 'from src.analysis.resource_manager import ResourceManager',
        'duplicates': [
            'src/core/resource_manager.py',
            'src/core/resources/manager.py',
            'src/utils/resource_manager.py'
        ]
    },
    'ResourceLimits': {
        'canonical_path': 'src/core/models/component.py',
        'canonical_import': 'from src.core.models.component import ResourceLimits',
        'duplicates': [
            'src/core/resource_manager.py',
            'src/core/resources/manager.py',
            'src/core/models.py'
        ]
    },
    'MarketDataValidator': {
        'canonical_path': 'src/data_processing/market_validator.py',
        'canonical_import': 'from src.data_processing.market_validator import MarketDataValidator',
        'duplicates': [
            'src/monitoring/monitor.py'
        ]
    },
    'ErrorSeverity': {
        'canonical_path': 'src/core/models.py',
        'canonical_import': 'from src.core.models import ErrorSeverity',
        'duplicates': [
            'src/core/error/models.py',
            'src/core/models/errors.py',
            'src/monitoring/error_tracker.py',
            'src/core/reporting/pdf_generator.py'
        ]
    },
    'ErrorContext': {
        'canonical_path': 'src/core/models.py',
        'canonical_import': 'from src.core.models import ErrorContext',
        'duplicates': [
            'src/core/error/models.py',
            'src/core/models/component.py',
            'src/core/exchanges/bybit.py'
        ]
    },
    'ComponentState': {
        'canonical_path': 'src/core/lifecycle/states.py',
        'canonical_import': 'from src.core.lifecycle.states import ComponentState',
        'duplicates': [
            'src/core/models/component.py',
            'src/core/state_manager.py',
            'src/core/models.py'
        ]
    }
}

def create_import_mappings() -> List[Tuple[str, str]]:
    """Create regex patterns for import replacement."""
    mappings = []
    
    for class_name, info in CANONICAL_CLASSES.items():
        canonical_import = info['canonical_import']
        
        # Create patterns for various import styles
        patterns = [
            # Direct imports from files
            (f'from src\\.[\\w\\.]+\\s+import\\s+.*{class_name}', canonical_import),
            (f'from \\.[\\w\\.]+\\s+import\\s+.*{class_name}', canonical_import),
            # Import with other items
            (f'from src\\.[\\w\\.]+\\s+import\\s+([\\w,\\s]*),?\\s*{class_name}([\\w,\\s]*)',
             lambda m: canonical_import if not m.group(1).strip() and not m.group(2).strip()
                      else f'from src.{{module}} import {m.group(1).strip()},{m.group(2).strip()}'.strip(', ') + f'\\n{canonical_import}'),
        ]
        
        for pattern, replacement in patterns:
            mappings.append((pattern, replacement))
    
    return mappings

def backup_files(files: List[Path], backup_dir: Path):
    """Create backups of files before modification."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"consolidation_backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)
    
    for file_path in files:
        if file_path.exists():
            relative_path = file_path.relative_to(file_path.parent.parent.parent)
            backup_file = backup_path / relative_path
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_file)
    
    print(f"📁 Created backup in: {backup_path}")
    return backup_path

def update_imports_in_file(file_path: Path, mappings: List[Tuple[str, str]], dry_run: bool = False) -> List[str]:
    """Update imports in a single file."""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return changes
    
    original_content = content
    
    # Track which classes were imported
    imported_classes = set()
    
    # Apply mappings
    for pattern, replacement in mappings:
        if re.search(pattern, content):
            # Extract class name from pattern
            for cls_name in CANONICAL_CLASSES.keys():
                if cls_name in pattern:
                    class_name = cls_name
                    break
            else:
                class_name = None
                
                # Skip if we already added this import
                if class_name in imported_classes:
                    continue
                
                if callable(replacement):
                    content = re.sub(pattern, replacement, content)
                else:
                    content = re.sub(pattern, replacement, content)
                    imported_classes.add(class_name)
                
                changes.append(f"Updated import for {class_name}")
    
    # Remove duplicate imports
    lines = content.split('\n')
    seen_imports = set()
    new_lines = []
    
    for line in lines:
        if line.strip().startswith('from ') and ' import ' in line:
            if line.strip() not in seen_imports:
                seen_imports.add(line.strip())
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Write changes
    if content != original_content:
        if not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Updated {file_path.name}")
            except Exception as e:
                print(f"❌ Error writing {file_path}: {e}")
        else:
            print(f"Would update {file_path.name}")
        
        return changes
    
    return []

def remove_duplicate_class_definitions(file_path: Path, class_names: List[str], dry_run: bool = False) -> bool:
    """Remove duplicate class definitions from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    original_content = content
    
    for class_name in class_names:
        # Pattern to match class definition and its body
        pattern = rf'class\s+{class_name}.*?(?=\nclass|\n\n|\Z)'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    if content != original_content:
        if not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Removed {class_names} from {file_path.name}")
                return True
            except Exception as e:
                print(f"❌ Error writing {file_path}: {e}")
        else:
            print(f"Would remove {class_names} from {file_path.name}")
            return True
    
    return False

def find_python_files(root_dir: Path, exclude_dirs: List[str] = None) -> List[Path]:
    """Find all Python files in the project."""
    if exclude_dirs is None:
        exclude_dirs = ['venv', 'venv311', '__pycache__', '.git', 'backups', '.pytest_cache']
    
    python_files = []
    
    for path in root_dir.rglob('*.py'):
        # Skip excluded directories
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        
        python_files.append(path)
    
    return python_files

def main():
    """Main consolidation function."""
    project_root = Path(__file__).parent.parent.parent
    
    print("🔍 Starting duplicate class consolidation...\n")
    
    # Create backup directory
    backup_dir = project_root / 'backups'
    
    # Find all Python files
    print("📂 Finding Python files...")
    python_files = find_python_files(project_root)
    print(f"Found {len(python_files)} Python files\n")
    
    # Collect all files that need backing up
    files_to_backup = set()
    for info in CANONICAL_CLASSES.values():
        files_to_backup.add(project_root / info['canonical_path'])
        for dup in info['duplicates']:
            files_to_backup.add(project_root / dup)
    
    # Create backups
    print("💾 Creating backups...")
    backup_path = backup_files(list(files_to_backup), backup_dir)
    
    # Create import mappings
    mappings = create_import_mappings()
    
    # Phase 1: Update imports
    print("\n📝 Phase 1: Updating imports...")
    total_updates = 0
    
    for file_path in python_files:
        changes = update_imports_in_file(file_path, mappings, dry_run=False)
        if changes:
            total_updates += len(changes)
    
    print(f"\n✅ Updated {total_updates} imports\n")
    
    # Phase 2: Remove duplicate class definitions
    print("🗑️  Phase 2: Removing duplicate class definitions...")
    
    for class_name, info in CANONICAL_CLASSES.items():
        canonical_path = project_root / info['canonical_path']
        
        for duplicate_path in info['duplicates']:
            duplicate_file = project_root / duplicate_path
            
            if duplicate_file.exists() and duplicate_file != canonical_path:
                # Check if this file only contains this class
                with open(duplicate_file, 'r') as f:
                    content = f.read()
                
                # Count meaningful lines (not empty, not just imports)
                meaningful_lines = [line for line in content.split('\n') 
                                  if line.strip() and not line.strip().startswith('import') 
                                  and not line.strip().startswith('from')]
                
                # If file is mostly just this class, consider deleting it
                if len(meaningful_lines) < 50:  # Arbitrary threshold
                    print(f"  ⚠️  {duplicate_path} might be deletable (only {len(meaningful_lines)} meaningful lines)")
                else:
                    # Just remove the class definition
                    remove_duplicate_class_definitions(duplicate_file, [class_name], dry_run=False)
    
    print("\n✅ Consolidation complete!")
    print(f"\n📋 Summary:")
    print(f"  - Backed up files to: {backup_path}")
    print(f"  - Updated {total_updates} imports")
    print(f"  - Processed {len(CANONICAL_CLASSES)} duplicate classes")
    
    print("\n⚠️  Please run tests to ensure everything works correctly!")
    print("⚠️  Some files might be deletable if they only contained the duplicate classes.")

if __name__ == "__main__":
    main()
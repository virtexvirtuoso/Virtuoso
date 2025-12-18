#!/usr/bin/env python3
"""
Phase 1: Migrate validation files to new structure
"""
import os
import shutil
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
import ast
import json

class ValidationMigrator:
    def __init__(self, src_path: str, dry_run: bool = True):
        self.src_path = Path(src_path)
        self.dry_run = dry_run
        self.backup_dir = Path("validation_backup")
        self.migration_log = []
        
    def backup_files(self, files: List[str]):
        """Create backups of files before migration"""
        if not self.dry_run:
            self.backup_dir.mkdir(exist_ok=True)
            
        for file_path in files:
            src_file = self.src_path / file_path
            if src_file.exists():
                backup_path = self.backup_dir / file_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                
                if not self.dry_run:
                    shutil.copy2(src_file, backup_path)
                    
                self.migration_log.append(f"Backed up: {file_path}")
    
    def merge_duplicate_content(self, file1: Path, file2: Path) -> str:
        """Merge content from duplicate files intelligently"""
        content1 = file1.read_text(encoding='utf-8')
        content2 = file2.read_text(encoding='utf-8')
        
        # Parse both files
        try:
            tree1 = ast.parse(content1)
            tree2 = ast.parse(content2)
        except:
            # If parsing fails, return the newer file content
            if file1.stat().st_mtime > file2.stat().st_mtime:
                return content1
            return content2
        
        # Extract imports, classes, and functions from both files
        imports1 = set()
        imports2 = set()
        classes = {}
        functions = {}
        
        for node in ast.walk(tree1):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports1.add(ast.unparse(node))
            elif isinstance(node, ast.ClassDef):
                classes[node.name] = ast.unparse(node)
            elif isinstance(node, ast.FunctionDef):
                functions[node.name] = ast.unparse(node)
                
        for node in ast.walk(tree2):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports2.add(ast.unparse(node))
            elif isinstance(node, ast.ClassDef):
                if node.name not in classes:
                    classes[node.name] = ast.unparse(node)
            elif isinstance(node, ast.FunctionDef):
                if node.name not in functions:
                    functions[node.name] = ast.unparse(node)
        
        # Combine everything
        merged_content = []
        
        # Add module docstring
        merged_content.append('"""')
        merged_content.append('Merged validation module')
        merged_content.append(f'Merged from: {file1.relative_to(self.src_path)} and {file2.relative_to(self.src_path)}')
        merged_content.append('"""')
        merged_content.append('')
        
        # Add imports
        all_imports = sorted(imports1.union(imports2))
        for imp in all_imports:
            merged_content.append(imp)
        
        if all_imports:
            merged_content.append('')
        
        # Add classes
        for class_name, class_code in sorted(classes.items()):
            merged_content.append(class_code)
            merged_content.append('')
        
        # Add functions
        for func_name, func_code in sorted(functions.items()):
            merged_content.append(func_code)
            merged_content.append('')
        
        return '\n'.join(merged_content)
    
    def migrate_file(self, old_path: str, new_path: str):
        """Migrate a single file to new location"""
        old_file = self.src_path / old_path
        new_file = self.src_path / new_path
        
        if not old_file.exists():
            self.migration_log.append(f"SKIP: {old_path} does not exist")
            return
        
        # Check if destination already exists
        if new_file.exists():
            # Merge content if both files exist
            merged_content = self.merge_duplicate_content(old_file, new_file)
            
            if not self.dry_run:
                new_file.write_text(merged_content, encoding='utf-8')
                old_file.unlink()
                
            self.migration_log.append(f"MERGED: {old_path} -> {new_path}")
        else:
            # Simple move
            if not self.dry_run:
                new_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_file), str(new_file))
                
            self.migration_log.append(f"MOVED: {old_path} -> {new_path}")
    
    def update_imports_in_file(self, file_path: Path, import_map: Dict[str, str]):
        """Update imports in a single file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # Update imports
            for old_import, new_import in import_map.items():
                # Handle different import patterns
                patterns = [
                    (f'from {old_import} import', f'from {new_import} import'),
                    (f'from {old_import}', f'from {new_import}'),
                    (f'import {old_import}', f'import {new_import}'),
                ]
                
                for old_pattern, new_pattern in patterns:
                    content = content.replace(old_pattern, new_pattern)
            
            # Only write if changed
            if content != original_content:
                if not self.dry_run:
                    file_path.write_text(content, encoding='utf-8')
                    
                self.migration_log.append(f"UPDATED IMPORTS: {file_path.relative_to(self.src_path)}")
                
        except Exception as e:
            self.migration_log.append(f"ERROR updating {file_path}: {e}")
    
    def run_migration(self):
        """Execute the full migration"""
        # Define migration map
        migration_map = {
            # Core validation files
            'core/validation/base.py': 'validation/core/base.py',
            'core/validation/manager.py': 'validation/services/manager.py',
            'core/validation/service.py': 'validation/services/sync_service.py',
            'core/validation/cache.py': 'validation/cache/cache.py',
            'core/validation/context.py': 'validation/core/context.py',
            'core/validation/models.py': 'validation/core/models.py',
            'core/validation/protocols.py': 'validation/core/protocols.py',
            'core/validation/rules.py': 'validation/rules/base.py',
            'core/validation/schemas.py': 'validation/core/schemas.py',
            'core/validation/handler.py': 'validation/core/handler.py',
            
            # Validators
            'core/validation/startup_validator.py': 'validation/validators/startup_validator.py',
            'core/validation/validators.py': 'validation/validators/core_validators.py',
            'core/config/validators/binance_validator.py': 'validation/validators/binance_validator.py',
            'data_processing/market_validator.py': 'validation/validators/market_validator.py',
            'utils/data_validator.py': 'validation/validators/data_validator.py',
            'utils/market_context_validator.py': 'validation/validators/context_validator.py',
            'utils/validation.py': 'validation/utils/helpers.py',
            'analysis/data/validation.py': 'validation/data/analysis_validation.py',
            'analysis/data/validator.py': 'validation/data/analysis_validator.py',
            'config/validator.py': 'validation/config/config_validator.py',
        }
        
        # Create import map
        import_map = {
            'core.validation': 'validation.core',
            'src.core.validation': 'src.validation.core',
            'core.config.validators': 'validation.validators',
            'src.core.config.validators': 'src.validation.validators',
            'utils.validation': 'validation.utils.helpers',
            'src.utils.validation': 'src.validation.utils.helpers',
            'utils.data_validator': 'validation.validators.data_validator',
            'src.utils.data_validator': 'src.validation.validators.data_validator',
            'utils.market_context_validator': 'validation.validators.context_validator',
            'src.utils.market_context_validator': 'src.validation.validators.context_validator',
            'data_processing.market_validator': 'validation.validators.market_validator',
            'src.data_processing.market_validator': 'src.validation.validators.market_validator',
            'analysis.data.validation': 'validation.data.analysis_validation',
            'src.analysis.data.validation': 'src.validation.data.analysis_validation',
            'config.validator': 'validation.config.config_validator',
            'src.config.validator': 'src.validation.config.config_validator',
        }
        
        print(f"Starting validation migration (dry_run={self.dry_run})")
        print("=" * 60)
        
        # Step 1: Backup files
        print("\nStep 1: Creating backups...")
        self.backup_files(list(migration_map.keys()))
        
        # Step 2: Migrate files
        print("\nStep 2: Migrating files...")
        for old_path, new_path in migration_map.items():
            self.migrate_file(old_path, new_path)
        
        # Step 3: Update imports
        print("\nStep 3: Updating imports...")
        for root, dirs, files in os.walk(self.src_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    self.update_imports_in_file(file_path, import_map)
        
        # Step 4: Clean up old directories (only if not dry run)
        if not self.dry_run:
            print("\nStep 4: Cleaning up old directories...")
            old_dirs = [
                self.src_path / 'core' / 'validation',
                self.src_path / 'core' / 'config' / 'validators',
            ]
            
            for old_dir in old_dirs:
                if old_dir.exists() and not any(old_dir.iterdir()):
                    old_dir.rmdir()
                    self.migration_log.append(f"REMOVED: {old_dir.relative_to(self.src_path)}")
        
        # Save migration log
        log_file = Path('validation_migration_log.txt')
        with open(log_file, 'w') as f:
            f.write('\n'.join(self.migration_log))
        
        print(f"\nMigration complete! Log saved to: {log_file}")
        print(f"Total operations: {len(self.migration_log)}")

def main():
    import argparse

    # Default to project src directory relative to script location
    default_src = str(Path(__file__).parent.parent.parent / 'src')

    parser = argparse.ArgumentParser(description='Migrate validation files to new structure')
    parser.add_argument('--execute', action='store_true', help='Execute migration (default is dry-run)')
    parser.add_argument('--src', default=default_src, help='Source directory')
    
    args = parser.parse_args()
    
    migrator = ValidationMigrator(args.src, dry_run=not args.execute)
    migrator.run_migration()

if __name__ == "__main__":
    main()
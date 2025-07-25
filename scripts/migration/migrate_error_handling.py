#!/usr/bin/env python3
"""
Phase 3: Consolidate remaining error handling files
"""
import os
import shutil
import ast
from pathlib import Path
from typing import Dict, List, Optional

class ErrorHandlingMigrator:
    def __init__(self, src_path: str, dry_run: bool = True):
        self.src_path = Path(src_path)
        self.dry_run = dry_run
        self.migration_log = []
        
        # Define migration mapping
        self.migration_map = {
            'utils/error_handling.py': 'core/error/utils.py',
            'core/models/error_context.py': 'core/error/context.py',
            'core/models/errors.py': 'core/error/models.py',  # Merge with existing
        }
        
        # Define import mappings
        self.import_map = {
            'from utils.error_handling import': 'from core.error.utils import',
            'from src.utils.error_handling import': 'from src.core.error.utils import',
            'from core.models.error_context import': 'from core.error.context import',
            'from src.core.models.error_context import': 'from src.core.error.context import',
            'from core.models.errors import': 'from core.error.models import',
            'from src.core.models.errors import': 'from src.core.error.models import',
            'utils.error_handling': 'core.error.utils',
            'core.models.error_context': 'core.error.context',
            'core.models.errors': 'core.error.models',
        }
        
    def log(self, message: str):
        """Log a message"""
        self.migration_log.append(message)
        print(message)
        
    def analyze_error_files(self):
        """Analyze current error handling files"""
        self.log("Analyzing error handling files...")
        
        for old_path, new_path in self.migration_map.items():
            old_file = self.src_path / old_path
            new_file = self.src_path / new_path
            
            if old_file.exists():
                self.log(f"  Found: {old_path}")
                
                # Analyze content
                try:
                    content = old_file.read_text(encoding='utf-8')
                    tree = ast.parse(content)
                    
                    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.col_offset == 0]
                    
                    self.log(f"    Classes: {classes}")
                    self.log(f"    Functions: {functions}")
                    
                    if new_file.exists():
                        self.log(f"    Target exists: {new_path} (will merge)")
                    else:
                        self.log(f"    Target missing: {new_path} (will move)")
                        
                except Exception as e:
                    self.log(f"    Error analyzing: {e}")
            else:
                self.log(f"  Missing: {old_path}")
                
    def migrate_file(self, old_path: str, new_path: str) -> bool:
        """Migrate a single error handling file"""
        old_file = self.src_path / old_path
        new_file = self.src_path / new_path
        
        if not old_file.exists():
            self.log(f"  SKIP: {old_path} does not exist")
            return False
            
        # Check if we need to merge
        if new_file.exists() and old_path.endswith('errors.py'):
            # Special handling for errors.py - merge with models.py
            self.log(f"  MERGE: {old_path} -> {new_path}")
            
            if not self.dry_run:
                # Read both files
                old_content = old_file.read_text(encoding='utf-8')
                new_content = new_file.read_text(encoding='utf-8')
                
                # Parse to find unique elements
                old_tree = ast.parse(old_content)
                new_tree = ast.parse(new_content)
                
                # Extract class names
                old_classes = {node.name for node in ast.walk(old_tree) if isinstance(node, ast.ClassDef)}
                new_classes = {node.name for node in ast.walk(new_tree) if isinstance(node, ast.ClassDef)}
                
                unique_classes = old_classes - new_classes
                
                if unique_classes:
                    # Append unique classes
                    self.log(f"    Adding unique classes: {unique_classes}")
                    
                    # Simple append for now
                    merged = new_content.rstrip() + '\n\n'
                    merged += f"# Merged from {old_path}\n"
                    
                    # Extract unique class definitions
                    for node in ast.walk(old_tree):
                        if isinstance(node, ast.ClassDef) and node.name in unique_classes:
                            merged += '\n' + ast.unparse(node) + '\n'
                    
                    new_file.write_text(merged, encoding='utf-8')
                
                # Remove old file
                old_file.unlink()
                
        else:
            # Simple move
            self.log(f"  MOVE: {old_path} -> {new_path}")
            
            if not self.dry_run:
                new_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_file), str(new_file))
                
        return True
        
    def update_imports(self):
        """Update imports across the codebase"""
        self.log("\nUpdating imports...")
        
        updated_count = 0
        
        for root, dirs, files in os.walk(self.src_path):
            # Skip __pycache__
            if '__pycache__' in root:
                continue
                
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        original = content
                        
                        # Apply import mappings
                        for old_import, new_import in self.import_map.items():
                            if old_import in content:
                                content = content.replace(old_import, new_import)
                        
                        # Save if changed
                        if content != original:
                            if not self.dry_run:
                                file_path.write_text(content, encoding='utf-8')
                            
                            rel_path = file_path.relative_to(self.src_path)
                            self.log(f"  Updated: {rel_path}")
                            updated_count += 1
                            
                    except Exception as e:
                        self.log(f"  Error updating {file_path}: {e}")
                        
        self.log(f"\nUpdated {updated_count} files")
        
    def run_migration(self):
        """Execute the error handling migration"""
        self.log(f"Error Handling Migration (dry_run={self.dry_run})")
        self.log("=" * 60)
        
        # Step 1: Analyze current state
        self.analyze_error_files()
        
        # Step 2: Migrate files
        self.log("\nMigrating error handling files...")
        for old_path, new_path in self.migration_map.items():
            self.migrate_file(old_path, new_path)
        
        # Step 3: Update imports
        self.update_imports()
        
        # Save log
        log_file = Path('error_handling_migration_log.txt')
        with open(log_file, 'w') as f:
            f.write('\n'.join(self.migration_log))
        
        self.log(f"\nMigration complete! Log saved to: {log_file}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate error handling files')
    parser.add_argument('--execute', action='store_true', help='Execute migration (default is dry-run)')
    parser.add_argument('--src', default='/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src', help='Source directory')
    
    args = parser.parse_args()
    
    migrator = ErrorHandlingMigrator(args.src, dry_run=not args.execute)
    migrator.run_migration()

if __name__ == "__main__":
    main()
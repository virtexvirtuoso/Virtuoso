#!/usr/bin/env python3
"""
Phase 5: Utility Package Cleanup Migration
"""
import os
import shutil
from pathlib import Path
from typing import Dict, List, Set

class UtilsCleanupMigrator:
    def __init__(self, src_path: str, dry_run: bool = True):
        self.src_path = Path(src_path)
        self.dry_run = dry_run
        self.migration_log = []
        
        # Define migration mapping
        self.migration_map = {
            'utils/indicators.py': 'indicators/utils/indicators.py',
            'utils/liquidation_cache.py': 'core/cache/liquidation_cache.py',
            'utils/cache.py': 'core/cache/utils_cache.py',  # Rename to avoid conflict
            'utils/types.py': 'core/types.py',  # Move to core
        }
        
        # Define import mappings
        self.import_map = {
            'from utils.indicators import': 'from indicators.utils.indicators import',
            'from src.utils.indicators import': 'from src.indicators.utils.indicators import',
            'from utils.liquidation_cache import': 'from core.cache.liquidation_cache import',
            'from src.utils.liquidation_cache import': 'from src.core.cache.liquidation_cache import',
            'from utils.cache import': 'from core.cache.utils_cache import',
            'from src.utils.cache import': 'from src.core.cache.utils_cache import',
            'from utils.types import': 'from core.types import',
            'from src.utils.types import': 'from src.core.types import',
            'utils.indicators': 'indicators.utils.indicators',
            'utils.liquidation_cache': 'core.cache.liquidation_cache',
            'utils.cache': 'core.cache.utils_cache',
            'utils.types': 'core.types',
        }
        
    def log(self, message: str):
        """Log a message"""
        self.migration_log.append(message)
        print(message)
        
    def analyze_current_state(self):
        """Analyze current state of utils directory"""
        self.log("Analyzing utils directory...")
        
        utils_files = []
        utils_path = self.src_path / 'utils'
        
        if utils_path.exists():
            for item in utils_path.iterdir():
                if item.is_file() and item.suffix == '.py':
                    utils_files.append(item.name)
                    
        self.log(f"Found {len(utils_files)} Python files in utils/")
        
        # Check which files need migration
        to_migrate = []
        for old_path in self.migration_map.keys():
            if (self.src_path / old_path).exists():
                to_migrate.append(old_path)
                
        self.log(f"Files to migrate: {len(to_migrate)}")
        for path in to_migrate:
            self.log(f"  - {path}")
            
        return to_migrate
        
    def migrate_file(self, old_path: str, new_path: str) -> bool:
        """Migrate a single file"""
        old_file = self.src_path / old_path
        new_file = self.src_path / new_path
        
        if not old_file.exists():
            self.log(f"  SKIP: {old_path} does not exist")
            return False
            
        self.log(f"  MOVE: {old_path} -> {new_path}")
        
        if not self.dry_run:
            # Create target directory if needed
            new_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Move the file
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
        
    def cleanup_utils_directory(self):
        """Final cleanup of utils directory"""
        self.log("\nChecking utils directory cleanup...")
        
        utils_path = self.src_path / 'utils'
        if not utils_path.exists():
            self.log("  Utils directory doesn't exist")
            return
            
        # List remaining files
        remaining = []
        for item in utils_path.iterdir():
            if item.is_file() and item.suffix == '.py' and item.name != '__init__.py':
                remaining.append(item.name)
                
        if remaining:
            self.log(f"  Remaining utility files ({len(remaining)}):")
            for file in sorted(remaining):
                self.log(f"    - {file}")
        else:
            self.log("  No domain-specific files remaining in utils/")
            
    def run_migration(self):
        """Execute the utils cleanup migration"""
        self.log(f"Utils Cleanup Migration (dry_run={self.dry_run})")
        self.log("=" * 60)
        
        # Step 1: Analyze current state
        files_to_migrate = self.analyze_current_state()
        
        if not files_to_migrate:
            self.log("\nNo files to migrate!")
            return
            
        # Step 2: Migrate files
        self.log("\nMigrating files...")
        for old_path, new_path in self.migration_map.items():
            if old_path in files_to_migrate:
                self.migrate_file(old_path, new_path)
        
        # Step 3: Update imports
        self.update_imports()
        
        # Step 4: Final cleanup check
        self.cleanup_utils_directory()
        
        # Save log
        log_file = Path('utils_cleanup_migration_log.txt')
        with open(log_file, 'w') as f:
            f.write('\n'.join(self.migration_log))
        
        self.log(f"\nMigration complete! Log saved to: {log_file}")

def main():
    import argparse

    # Default to project src directory relative to script location
    default_src = str(Path(__file__).parent.parent.parent / 'src')

    parser = argparse.ArgumentParser(description='Clean up utils directory')
    parser.add_argument('--execute', action='store_true', help='Execute migration (default is dry-run)')
    parser.add_argument('--src', default=default_src, help='Source directory')
    
    args = parser.parse_args()
    
    migrator = UtilsCleanupMigrator(args.src, dry_run=not args.execute)
    migrator.run_migration()

if __name__ == "__main__":
    main()
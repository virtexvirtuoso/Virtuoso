#!/usr/bin/env python3
"""
Execute the complete validation migration process
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

class ValidationMigrationExecutor:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.src_path = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')
        self.scripts_path = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/scripts/migration')
        self.logs = []
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def log(self, message: str):
        """Log a message"""
        self.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        print(message)
        
    def run_command(self, command: str, description: str) -> tuple:
        """Run a command and return success status and output"""
        self.log(f"\n{description}...")
        self.log(f"Running: {command}")
        
        if self.dry_run and '--execute' in command:
            # Remove --execute for dry run
            command = command.replace(' --execute', '')
            
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.src_path.parent)
            )
            
            if result.returncode == 0:
                self.log(f"✓ Success")
                return True, result.stdout
            else:
                self.log(f"✗ Failed with code {result.returncode}")
                self.log(f"Error: {result.stderr}")
                return False, result.stderr
                
        except Exception as e:
            self.log(f"✗ Exception: {e}")
            return False, str(e)
            
    def backup_current_state(self):
        """Create a backup of current validation files"""
        backup_dir = Path(f'validation_backup_{self.timestamp}')
        
        if not self.dry_run:
            backup_dir.mkdir(exist_ok=True)
            
        # List of directories and files to backup
        backup_targets = [
            'src/core/validation',
            'src/core/config/validators',
            'src/utils/validation.py',
            'src/utils/data_validator.py',
            'src/utils/market_context_validator.py',
            'src/data_processing/market_validator.py',
            'src/analysis/data/validation.py',
            'src/analysis/data/validator.py',
            'src/config/validator.py',
            'src/validation'  # New validation directory if it exists
        ]
        
        self.log(f"Creating backup in {backup_dir}")
        
        for target in backup_targets:
            source = self.src_path.parent / target
            if source.exists():
                dest = backup_dir / target
                
                if not self.dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    
                    if source.is_file():
                        shutil.copy2(source, dest)
                    else:
                        shutil.copytree(source, dest)
                        
                self.log(f"  Backed up: {target}")
                
    def verify_prerequisites(self):
        """Verify all prerequisites are met"""
        self.log("\nVerifying prerequisites...")
        
        issues = []
        
        # Check if scripts exist
        if not (self.scripts_path / 'migrate_validation_phase1.py').exists():
            issues.append("migrate_validation_phase1.py not found")
            
        if not (self.scripts_path / 'update_validation_imports.py').exists():
            issues.append("update_validation_imports.py not found")
            
        # Check if source directories exist
        if not self.src_path.exists():
            issues.append(f"Source directory not found: {self.src_path}")
            
        # Check if old validation directories exist
        old_validation_paths = [
            self.src_path / 'core' / 'validation',
            self.src_path / 'core' / 'config' / 'validators'
        ]
        
        found_old = False
        for path in old_validation_paths:
            if path.exists():
                found_old = True
                self.log(f"  Found old validation directory: {path}")
                
        if not found_old:
            self.log("  No old validation directories found - migration may have already been completed")
            
        # Check if new validation directory exists
        if (self.src_path / 'validation').exists():
            self.log("  New validation directory already exists - will merge files")
            
        if issues:
            self.log("\n✗ Prerequisites check failed:")
            for issue in issues:
                self.log(f"  - {issue}")
            return False
            
        self.log("✓ Prerequisites check passed")
        return True
        
    def execute_migration(self):
        """Execute the full migration process"""
        self.log(f"\n{'='*60}")
        self.log(f"Validation Migration Executor")
        self.log(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        self.log(f"{'='*60}")
        
        # Step 1: Verify prerequisites
        if not self.verify_prerequisites():
            return False
            
        # Step 2: Create backup
        self.backup_current_state()
        
        # Step 3: Run migration script
        execute_flag = '' if self.dry_run else ' --execute'
        success, output = self.run_command(
            f"python scripts/migration/migrate_validation_phase1.py{execute_flag}",
            "Running validation file migration"
        )
        
        if not success:
            self.log("\n✗ Migration failed!")
            return False
            
        # Step 4: Update imports
        success, output = self.run_command(
            f"python scripts/migration/update_validation_imports.py{execute_flag}",
            "Updating validation imports"
        )
        
        if not success:
            self.log("\n✗ Import update failed!")
            return False
            
        # Step 5: Verify migration
        if not self.dry_run:
            self.verify_migration_success()
            
        # Step 6: Clean up old directories (only in execute mode)
        if not self.dry_run:
            self.cleanup_old_directories()
            
        # Save log
        log_file = f'validation_migration_executor_{self.timestamp}.log'
        with open(log_file, 'w') as f:
            f.write('\n'.join(self.logs))
            
        self.log(f"\n✓ Migration process completed!")
        self.log(f"Log saved to: {log_file}")
        
        return True
        
    def verify_migration_success(self):
        """Verify the migration was successful"""
        self.log("\nVerifying migration success...")
        
        # Check new validation structure exists
        new_validation = self.src_path / 'validation'
        if not new_validation.exists():
            self.log("✗ New validation directory not created")
            return False
            
        # Check subdirectories
        expected_dirs = ['core', 'validators', 'services', 'cache', 'rules', 'utils', 'data', 'config']
        for dir_name in expected_dirs:
            if not (new_validation / dir_name).exists():
                self.log(f"⚠ Missing expected directory: validation/{dir_name}")
                
        # Check if old directories are empty or removed
        old_dirs = [
            self.src_path / 'core' / 'validation',
            self.src_path / 'core' / 'config' / 'validators'
        ]
        
        for old_dir in old_dirs:
            if old_dir.exists():
                files = list(old_dir.glob('*.py'))
                if files:
                    self.log(f"⚠ Old directory still contains files: {old_dir}")
                    for f in files[:3]:
                        self.log(f"    - {f.name}")
                        
        self.log("✓ Migration verification complete")
        
    def cleanup_old_directories(self):
        """Remove old validation directories if empty"""
        self.log("\nCleaning up old directories...")
        
        old_dirs = [
            self.src_path / 'core' / 'validation',
            self.src_path / 'core' / 'config' / 'validators'
        ]
        
        for old_dir in old_dirs:
            if old_dir.exists():
                try:
                    # Only remove if empty
                    if not any(old_dir.iterdir()):
                        old_dir.rmdir()
                        self.log(f"✓ Removed empty directory: {old_dir}")
                    else:
                        self.log(f"⚠ Directory not empty, keeping: {old_dir}")
                except Exception as e:
                    self.log(f"✗ Error removing {old_dir}: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Execute validation migration')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute migration (default is dry-run)')
    parser.add_argument('--skip-backup', action='store_true',
                       help='Skip backup creation')
    
    args = parser.parse_args()
    
    executor = ValidationMigrationExecutor(dry_run=not args.execute)
    
    if args.skip_backup:
        executor.backup_current_state = lambda: executor.log("Skipping backup as requested")
        
    success = executor.execute_migration()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
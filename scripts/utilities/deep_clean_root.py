#!/usr/bin/env python3
"""
Deep Clean Root Directory - Aggressive cleanup and organization
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
import argparse
import json

class DeepCleaner:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.root = Path('.')
        self.moves = []
        self.deletes = []
        self.creates = []
        
    def log(self, action, detail):
        """Log action with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        mode = "[DRY RUN]" if self.dry_run else "[EXECUTE]"
        print(f"{timestamp} {mode} {action}: {detail}")
        
    def execute_move(self, src, dst):
        """Move file with logging"""
        if self.dry_run:
            self.log("MOVE", f"{src} -> {dst}")
            self.moves.append((str(src), str(dst)))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            self.log("MOVED", f"{src} -> {dst}")
            self.moves.append((str(src), str(dst)))
            
    def clean_organization_scripts(self):
        """Move organization scripts to utilities"""
        print("\n=== PHASE 1: Moving Organization Scripts ===")
        scripts_to_move = [
            ('organize_root_directory.py', 'scripts/utilities/organize_root_directory.py'),
            ('organize_root.sh', 'scripts/utilities/organize_root.sh'),
            ('rollback_organization.py', 'scripts/utilities/rollback_organization.py'),
        ]
        
        for src, dst in scripts_to_move:
            src_path = self.root / src
            dst_path = self.root / dst
            if src_path.exists():
                self.execute_move(src_path, dst_path)
                
    def consolidate_analysis_outputs(self):
        """Move analysis outputs to organized structure"""
        print("\n=== PHASE 2: Consolidating Analysis Outputs ===")
        
        # Move to reports/analysis/
        analysis_dirs = {
            'analysis_output': 'reports/analysis/talib_optimization',
            'performance_analysis': 'reports/analysis/performance',
            'cache_rationalization': 'reports/analysis/cache_rationalization',
        }
        
        for src_dir, dst_dir in analysis_dirs.items():
            src_path = self.root / src_dir
            if src_path.exists() and src_path.is_dir():
                dst_path = self.root / dst_dir
                self.execute_move(src_path, dst_path)
                
    def consolidate_backups(self):
        """Consolidate all backup directories"""
        print("\n=== PHASE 3: Consolidating Backup Directories ===")
        
        # Find all backup-related directories
        backup_dirs = []
        for item in self.root.iterdir():
            if item.is_dir() and 'backup' in item.name.lower():
                if item.name != 'backups':  # Keep main backups dir
                    backup_dirs.append(item)
                    
        # Move to backups/consolidated/
        for backup_dir in backup_dirs:
            dst = self.root / 'backups' / 'consolidated' / backup_dir.name
            self.execute_move(backup_dir, dst)
            
    def clean_empty_directories(self):
        """Remove or add .gitkeep to empty directories"""
        print("\n=== PHASE 4: Handling Empty Directories ===")
        
        important_dirs = ['data', 'logs', 'cache', 'exports', 'reports']
        
        for item in self.root.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if directory is empty
                contents = list(item.iterdir())
                if not contents:
                    if item.name in important_dirs:
                        # Add .gitkeep
                        gitkeep = item / '.gitkeep'
                        if self.dry_run:
                            self.log("CREATE", f"{gitkeep}")
                        else:
                            gitkeep.touch()
                            self.log("CREATED", f"{gitkeep}")
                        self.creates.append(str(gitkeep))
                    else:
                        # Consider for deletion
                        self.log("EMPTY_DIR", f"{item} (consider removing)")
                        
    def move_docker_files(self):
        """Move Docker files to docker/ directory"""
        print("\n=== PHASE 5: Organizing Docker Files ===")
        
        docker_files = [
            ('Dockerfile', 'docker/Dockerfile'),
            ('docker-compose.yml', 'docker/docker-compose.yml'),
        ]
        
        for src, dst in docker_files:
            src_path = self.root / src
            dst_path = self.root / dst
            if src_path.exists():
                self.execute_move(src_path, dst_path)
                
    def create_project_structure(self):
        """Ensure proper project structure exists"""
        print("\n=== PHASE 6: Creating Standard Project Structure ===")
        
        standard_dirs = [
            'tests',           # Test files
            'notebooks',       # Jupyter notebooks
            'scripts/utilities',  # Utility scripts
            'scripts/deployment', # Deployment scripts
            'scripts/analysis',   # Analysis scripts
            'data/raw',        # Raw data
            'data/processed',  # Processed data
            'reports/daily',   # Daily reports
            'reports/analysis', # Analysis reports
            'docs/api',        # API documentation
            'docs/guides',     # User guides
        ]
        
        for dir_path in standard_dirs:
            full_path = self.root / dir_path
            if not full_path.exists():
                if self.dry_run:
                    self.log("CREATE_DIR", dir_path)
                else:
                    full_path.mkdir(parents=True, exist_ok=True)
                    self.log("CREATED_DIR", dir_path)
                self.creates.append(str(dir_path))
                
    def suggest_additional_cleanup(self):
        """Suggest additional cleanup opportunities"""
        print("\n=== ADDITIONAL CLEANUP SUGGESTIONS ===")
        
        suggestions = []
        
        # Check for old cache directories
        cache_dir = self.root / 'cache'
        if cache_dir.exists():
            cache_files = list(cache_dir.glob('**/*'))
            if cache_files:
                suggestions.append(f"Cache directory contains {len(cache_files)} files - consider clearing")
                
        # Check for large log files
        log_dir = self.root / 'logs'
        if log_dir.exists():
            for log_file in log_dir.glob('*.log'):
                size_mb = log_file.stat().st_size / (1024 * 1024)
                if size_mb > 10:
                    suggestions.append(f"Large log file: {log_file.name} ({size_mb:.1f} MB)")
                    
        # Check for duplicate reports
        report_dir = self.root / 'reports'
        if report_dir.exists():
            json_files = list(report_dir.glob('**/*.json'))
            if len(json_files) > 20:
                suggestions.append(f"Many report files ({len(json_files)} JSON files) - consider archiving old ones")
                
        for suggestion in suggestions:
            print(f"  • {suggestion}")
            
    def generate_summary(self):
        """Generate cleanup summary"""
        print("\n" + "="*60)
        print("DEEP CLEANUP SUMMARY")
        print("="*60)
        print(f"Files to be moved: {len(self.moves)}")
        print(f"Directories to be created: {len(self.creates)}")
        
        if not self.dry_run:
            # Save rollback script
            rollback_data = {
                'timestamp': datetime.now().isoformat(),
                'moves': self.moves,
                'creates': self.creates,
            }
            rollback_file = self.root / 'rollback_deep_clean.json'
            with open(rollback_file, 'w') as f:
                json.dump(rollback_data, f, indent=2)
            print(f"\n✅ Rollback data saved to: {rollback_file}")
            
        print("\n📋 This was a dry run. Use --execute to apply changes." if self.dry_run else "\n✅ Deep cleanup completed!")
        
    def run(self):
        """Execute all cleanup phases"""
        print("="*60)
        print("VIRTUOSO CCXT DEEP ROOT CLEANUP")
        print("="*60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        print("="*60)
        
        self.clean_organization_scripts()
        self.consolidate_analysis_outputs()
        self.consolidate_backups()
        self.move_docker_files()
        self.create_project_structure()
        self.clean_empty_directories()
        self.suggest_additional_cleanup()
        self.generate_summary()

def main():
    parser = argparse.ArgumentParser(description='Deep clean and organize project root')
    parser.add_argument('--execute', action='store_true', help='Execute changes (default is dry-run)')
    args = parser.parse_args()
    
    cleaner = DeepCleaner(dry_run=not args.execute)
    cleaner.run()

if __name__ == '__main__':
    main()
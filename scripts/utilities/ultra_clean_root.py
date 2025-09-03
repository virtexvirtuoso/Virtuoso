#!/usr/bin/env python3
"""
Ultra Clean Root - Maximum cleanup and archiving
"""
import os
import shutil
import gzip
from pathlib import Path
from datetime import datetime
import argparse

class UltraCleaner:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.root = Path('.')
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def log(self, action, detail):
        """Log action with timestamp"""
        mode = "[DRY RUN]" if self.dry_run else "[EXECUTE]"
        print(f"{mode} {action}: {detail}")
        
    def archive_large_logs(self):
        """Archive large log files"""
        print("\n=== ARCHIVING LARGE LOGS ===")
        log_dir = self.root / 'logs'
        archive_dir = self.root / 'archives' / 'logs' / self.timestamp
        
        if not log_dir.exists():
            return
            
        for log_file in log_dir.glob('*.log'):
            size_mb = log_file.stat().st_size / (1024 * 1024)
            if size_mb > 10:  # Archive logs > 10MB
                if self.dry_run:
                    self.log("ARCHIVE", f"{log_file.name} ({size_mb:.1f} MB)")
                else:
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    # Compress and move
                    compressed = archive_dir / f"{log_file.name}.gz"
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    log_file.unlink()
                    self.log("ARCHIVED", f"{log_file.name} -> {compressed}")
                    
    def archive_old_reports(self):
        """Archive old JSON reports"""
        print("\n=== ARCHIVING OLD REPORTS ===")
        reports_dir = self.root / 'reports'
        archive_dir = self.root / 'archives' / 'reports' / self.timestamp
        
        if not reports_dir.exists():
            return
            
        json_files = list(reports_dir.glob('**/*.json'))
        if len(json_files) > 50:  # Archive if too many reports
            old_reports = sorted(json_files, key=lambda x: x.stat().st_mtime)[:len(json_files)-20]
            
            for report in old_reports:
                if self.dry_run:
                    self.log("ARCHIVE", f"{report.relative_to(reports_dir)}")
                else:
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    rel_path = report.relative_to(reports_dir)
                    dest = archive_dir / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(report), str(dest))
                    self.log("ARCHIVED", f"{rel_path}")
                    
    def clean_additional_directories(self):
        """Clean up additional directories"""
        print("\n=== CLEANING ADDITIONAL DIRECTORIES ===")
        
        moves = [
            ('static', 'src/web/static'),
            ('templates', 'src/web/templates'),
            ('examples', 'docs/examples'),
            ('optimization', 'scripts/optimization'),
            ('patches', 'scripts/patches'),
            ('sample_reports', 'docs/examples/sample_reports'),
            ('test_output', 'tests/output'),
            ('test_reports', 'tests/reports'),
            ('temp', None),  # Delete temp
            ('vultr_evidence_package', 'archives/vultr_evidence'),
            ('profiling', 'reports/profiling'),
        ]
        
        for src, dst in moves:
            src_path = self.root / src
            if src_path.exists():
                if dst is None:
                    # Delete
                    if self.dry_run:
                        self.log("DELETE", src)
                    else:
                        if src_path.is_dir():
                            shutil.rmtree(src_path)
                        else:
                            src_path.unlink()
                        self.log("DELETED", src)
                else:
                    # Move
                    dst_path = self.root / dst
                    if self.dry_run:
                        self.log("MOVE", f"{src} -> {dst}")
                    else:
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(src_path), str(dst_path))
                        self.log("MOVED", f"{src} -> {dst}")
                        
    def clean_cache_directory(self):
        """Clean cache directory"""
        print("\n=== CLEANING CACHE ===")
        cache_dir = self.root / 'cache'
        
        if cache_dir.exists():
            cache_files = list(cache_dir.glob('**/*'))
            if cache_files:
                if self.dry_run:
                    self.log("CLEAN", f"Would remove {len(cache_files)} cache files")
                else:
                    for cache_file in cache_files:
                        if cache_file.is_file():
                            cache_file.unlink()
                    self.log("CLEANED", f"Removed {len(cache_files)} cache files")
                    
    def remove_strange_files(self):
        """Remove strange or corrupted files"""
        print("\n=== REMOVING STRANGE FILES ===")
        
        strange_files = [
            '${DATABASE_URL:sqlite:',
            '.DS_Store',
            'Thumbs.db',
        ]
        
        for filename in strange_files:
            file_path = self.root / filename
            if file_path.exists():
                if self.dry_run:
                    self.log("DELETE", filename)
                else:
                    file_path.unlink()
                    self.log("DELETED", filename)
                    
    def consolidate_archives(self):
        """Consolidate all archive directories"""
        print("\n=== CONSOLIDATING ARCHIVES ===")
        
        archive_patterns = ['archive*', '*_archive', '*_old', '*_backup']
        archives_main = self.root / 'archives'
        
        for pattern in archive_patterns:
            for item in self.root.glob(pattern):
                if item.is_dir() and item != archives_main:
                    dest = archives_main / 'consolidated' / item.name
                    if self.dry_run:
                        self.log("CONSOLIDATE", f"{item.name} -> archives/consolidated/")
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(item), str(dest))
                        self.log("CONSOLIDATED", item.name)
                        
    def final_cleanup(self):
        """Final cleanup pass"""
        print("\n=== FINAL CLEANUP ===")
        
        # Move deep_clean scripts
        for script in ['deep_clean_root.py', 'ultra_clean_root.py']:
            if (self.root / script).exists():
                dest = self.root / 'scripts' / 'utilities' / script
                if self.dry_run:
                    self.log("MOVE", f"{script} -> scripts/utilities/")
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(script, str(dest))
                    self.log("MOVED", script)
                    
        # Add .gitkeep to important empty directories
        important_dirs = ['data/raw', 'data/processed', 'logs', 'cache', 'exports']
        for dir_name in important_dirs:
            dir_path = self.root / dir_name
            if dir_path.exists() and not list(dir_path.glob('*')):
                gitkeep = dir_path / '.gitkeep'
                if not gitkeep.exists():
                    if self.dry_run:
                        self.log("CREATE", f"{gitkeep}")
                    else:
                        gitkeep.touch()
                        self.log("CREATED", f"{gitkeep}")
                        
    def show_summary(self):
        """Show final summary"""
        print("\n" + "="*60)
        print("ULTRA CLEANUP COMPLETE")
        print("="*60)
        
        # Count remaining items in root
        root_items = [item for item in self.root.iterdir() 
                     if not item.name.startswith('.')]
        
        essential_items = [
            'src', 'scripts', 'config', 'tests', 'docs',
            'data', 'logs', 'reports', 'assets', 'archives',
            'backups', 'docker', 'notebooks', 'cache', 'exports',
            'README.md', 'LICENSE', 'CONTRIBUTING.md', 'CHANGELOG.md',
            'requirements.txt', 'setup.py', 'Makefile',
            'CLAUDE.md', 'CLAUDE.local.md'
        ]
        
        non_essential = [item.name for item in root_items 
                        if item.name not in essential_items and not item.name.startswith('venv')]
        
        print(f"Root directory items: {len(root_items)}")
        print(f"Essential items: {len([i for i in root_items if i.name in essential_items])}")
        
        if non_essential:
            print(f"\nRemaining non-essential items ({len(non_essential)}):")
            for item in non_essential[:10]:
                print(f"  • {item}")
            if len(non_essential) > 10:
                print(f"  ... and {len(non_essential)-10} more")
                
        if self.dry_run:
            print("\n📋 This was a dry run. Use --execute to apply changes.")
        else:
            print("\n✅ Ultra cleanup completed!")
            
    def run(self):
        """Execute all cleanup phases"""
        print("="*60)
        print("ULTRA ROOT CLEANUP")
        print("="*60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        print("="*60)
        
        self.archive_large_logs()
        self.archive_old_reports()
        self.clean_additional_directories()
        self.clean_cache_directory()
        self.remove_strange_files()
        self.consolidate_archives()
        self.final_cleanup()
        self.show_summary()

def main():
    parser = argparse.ArgumentParser(description='Ultra clean project root')
    parser.add_argument('--execute', action='store_true', help='Execute changes')
    args = parser.parse_args()
    
    cleaner = UltraCleaner(dry_run=not args.execute)
    cleaner.run()

if __name__ == '__main__':
    main()
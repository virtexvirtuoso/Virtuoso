#!/usr/bin/env python3
"""
Virtuoso CCXT Log Cleanup Utility
Intelligently cleans and archives log files based on age, size, and importance
"""
import os
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import json
import re

class VirtuosoLogCleaner:
    def __init__(self, logs_dir, dry_run=True):
        self.logs_dir = Path(logs_dir)
        self.dry_run = dry_run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.archive_dir = self.logs_dir / 'archives' / self.timestamp
        
        # Define log categories and retention policies
        self.policies = {
            'critical': {
                'patterns': ['critical*.log', 'error*.log', 'alerts*.log'],
                'keep_days': 30,
                'compress_after_days': 7,
                'max_size_mb': 50
            },
            'operational': {
                'patterns': ['app*.log', 'startup*.log', 'restart*.log', 'service*.log'],
                'keep_days': 14,
                'compress_after_days': 3,
                'max_size_mb': 10
            },
            'debug': {
                'patterns': ['debug*.log', 'test*.log', 'diagnostics*.log'],
                'keep_days': 7,
                'compress_after_days': 1,
                'max_size_mb': 5
            },
            'analysis': {
                'patterns': ['bitcoin_beta*.log', 'confluence*.log', 'market*.log', 
                           'enhanced_scoring*.log', 'interpretation*.log'],
                'keep_days': 14,
                'compress_after_days': 3,
                'max_size_mb': 20
            },
            'reports': {
                'patterns': ['*_report*.log', 'pdf_generator*.log', '*_html*.log'],
                'keep_days': 7,
                'compress_after_days': 1,
                'max_size_mb': 5
            },
            'intelligence': {
                'patterns': ['intelligence_validation*.log'],
                'keep_days': 3,
                'compress_after_days': 1,
                'max_size_mb': 1
            }
        }
        
        self.stats = {
            'files_compressed': 0,
            'files_archived': 0,
            'files_deleted': 0,
            'space_freed_mb': 0,
            'errors': []
        }
    
    def log(self, level, message):
        """Log action with timestamp"""
        mode = "[DRY RUN]" if self.dry_run else "[EXECUTE]"
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{timestamp} {mode} [{level}] {message}")
    
    def get_file_age_days(self, file_path):
        """Get file age in days"""
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        return (datetime.now() - mtime).days
    
    def get_file_size_mb(self, file_path):
        """Get file size in MB"""
        return file_path.stat().st_size / (1024 * 1024)
    
    def compress_file(self, file_path):
        """Compress a log file using gzip"""
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        
        if self.dry_run:
            self.log("COMPRESS", f"{file_path.name} -> {compressed_path.name}")
            return compressed_path
        
        try:
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Preserve timestamps
            shutil.copystat(file_path, compressed_path)
            
            # Remove original
            file_path.unlink()
            
            self.log("COMPRESSED", f"{file_path.name} -> {compressed_path.name}")
            self.stats['files_compressed'] += 1
            self.stats['space_freed_mb'] += self.get_file_size_mb(file_path) * 0.7  # Estimate 70% compression
            
            return compressed_path
        except Exception as e:
            self.log("ERROR", f"Failed to compress {file_path.name}: {e}")
            self.stats['errors'].append(str(e))
            return None
    
    def archive_file(self, file_path, reason="old"):
        """Archive a file to the archive directory"""
        if not self.dry_run:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        archive_path = self.archive_dir / file_path.name
        
        if self.dry_run:
            self.log("ARCHIVE", f"{file_path.name} ({reason})")
        else:
            try:
                shutil.move(str(file_path), str(archive_path))
                self.log("ARCHIVED", f"{file_path.name} ({reason})")
                self.stats['files_archived'] += 1
                self.stats['space_freed_mb'] += self.get_file_size_mb(file_path)
            except Exception as e:
                self.log("ERROR", f"Failed to archive {file_path.name}: {e}")
                self.stats['errors'].append(str(e))
    
    def delete_file(self, file_path, reason="expired"):
        """Delete a file"""
        size_mb = self.get_file_size_mb(file_path)
        
        if self.dry_run:
            self.log("DELETE", f"{file_path.name} ({reason}, {size_mb:.1f} MB)")
        else:
            try:
                file_path.unlink()
                self.log("DELETED", f"{file_path.name} ({reason})")
                self.stats['files_deleted'] += 1
                self.stats['space_freed_mb'] += size_mb
            except Exception as e:
                self.log("ERROR", f"Failed to delete {file_path.name}: {e}")
                self.stats['errors'].append(str(e))
    
    def clean_debug_directory(self):
        """Clean the debug directory specifically"""
        debug_dir = self.logs_dir / 'debug'
        if not debug_dir.exists():
            return
        
        self.log("INFO", "Cleaning debug directory...")
        
        for debug_file in debug_dir.glob('*.log'):
            age_days = self.get_file_age_days(debug_file)
            size_mb = self.get_file_size_mb(debug_file)
            
            if age_days > 7:
                self.delete_file(debug_file, f"debug log older than 7 days")
            elif size_mb > 1:
                self.compress_file(debug_file)
    
    def clean_old_archives(self):
        """Clean old archive directories"""
        archives_dir = self.logs_dir / 'archives'
        if not archives_dir.exists():
            return
        
        self.log("INFO", "Cleaning old archives...")
        
        for archive in archives_dir.iterdir():
            if archive.is_dir():
                # Parse timestamp from directory name
                try:
                    dir_date = datetime.strptime(archive.name[:8], "%Y%m%d")
                    age_days = (datetime.now() - dir_date).days
                    
                    if age_days > 30:
                        if self.dry_run:
                            self.log("DELETE", f"Old archive: {archive.name}")
                        else:
                            shutil.rmtree(archive)
                            self.log("DELETED", f"Old archive: {archive.name}")
                            self.stats['files_deleted'] += 1
                except:
                    pass  # Skip if can't parse date
    
    def clean_intelligence_logs(self):
        """Clean intelligence validation logs specifically"""
        pattern = re.compile(r'intelligence_validation_\d+\.log')
        
        for log_file in self.logs_dir.glob('intelligence_validation_*.log'):
            if pattern.match(log_file.name):
                age_days = self.get_file_age_days(log_file)
                
                if age_days > 3:
                    self.delete_file(log_file, "old intelligence log")
                elif age_days > 1:
                    self.compress_file(log_file)
    
    def process_logs_by_policy(self):
        """Process logs according to defined policies"""
        for category, policy in self.policies.items():
            self.log("INFO", f"Processing {category} logs...")
            
            for pattern in policy['patterns']:
                for log_file in self.logs_dir.glob(pattern):
                    if log_file.is_file() and not log_file.suffix == '.gz':
                        age_days = self.get_file_age_days(log_file)
                        size_mb = self.get_file_size_mb(log_file)
                        
                        # Delete if too old
                        if age_days > policy['keep_days']:
                            self.delete_file(log_file, f"older than {policy['keep_days']} days")
                        
                        # Archive if too large
                        elif size_mb > policy['max_size_mb']:
                            self.archive_file(log_file, f"exceeds {policy['max_size_mb']} MB")
                        
                        # Compress if old enough
                        elif age_days > policy['compress_after_days']:
                            self.compress_file(log_file)
    
    def clean_empty_directories(self):
        """Remove empty log directories"""
        for dirpath, dirnames, filenames in os.walk(self.logs_dir, topdown=False):
            if not dirnames and not filenames and dirpath != str(self.logs_dir):
                dir_path = Path(dirpath)
                if self.dry_run:
                    self.log("DELETE", f"Empty directory: {dir_path.name}")
                else:
                    try:
                        dir_path.rmdir()
                        self.log("DELETED", f"Empty directory: {dir_path.name}")
                    except:
                        pass
    
    def generate_summary(self):
        """Generate cleanup summary"""
        print("\n" + "="*60)
        print("LOG CLEANUP SUMMARY")
        print("="*60)
        print(f"Files compressed: {self.stats['files_compressed']}")
        print(f"Files archived: {self.stats['files_archived']}")
        print(f"Files deleted: {self.stats['files_deleted']}")
        print(f"Space freed: {self.stats['space_freed_mb']:.1f} MB")
        
        if self.stats['errors']:
            print(f"\nErrors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:
                print(f"  - {error}")
        
        # Calculate remaining space usage
        total_size = sum(f.stat().st_size for f in self.logs_dir.rglob('*') if f.is_file())
        total_mb = total_size / (1024 * 1024)
        print(f"\nTotal logs size after cleanup: {total_mb:.1f} MB")
        
        if self.dry_run:
            print("\n📋 This was a dry run. Use --execute to apply changes.")
        else:
            print("\n✅ Log cleanup completed!")
    
    def run(self):
        """Execute all cleanup phases"""
        print("="*60)
        print("VIRTUOSO LOG CLEANUP")
        print("="*60)
        print(f"Logs directory: {self.logs_dir}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        print("="*60)
        
        # Phase 1: Process logs by policy
        self.process_logs_by_policy()
        
        # Phase 2: Clean specific directories
        self.clean_debug_directory()
        self.clean_intelligence_logs()
        
        # Phase 3: Clean old archives
        self.clean_old_archives()
        
        # Phase 4: Remove empty directories
        self.clean_empty_directories()
        
        # Generate summary
        self.generate_summary()

def main():
    parser = argparse.ArgumentParser(description='Clean Virtuoso CCXT log files')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute cleanup (default is dry-run)')
    parser.add_argument('--logs-dir', default='~/Desktop/Virtuoso_ccxt/logs',
                       help='Path to logs directory')
    parser.add_argument('--aggressive', action='store_true',
                       help='Use more aggressive cleanup settings')
    
    args = parser.parse_args()
    
    logs_dir = Path(args.logs_dir).expanduser()
    
    if not logs_dir.exists():
        print(f"Error: Logs directory not found: {logs_dir}")
        return
    
    cleaner = VirtuosoLogCleaner(logs_dir, dry_run=not args.execute)
    
    # Adjust policies for aggressive mode
    if args.aggressive:
        for policy in cleaner.policies.values():
            policy['keep_days'] = max(3, policy['keep_days'] // 2)
            policy['compress_after_days'] = 1
            policy['max_size_mb'] = policy['max_size_mb'] // 2
    
    cleaner.run()

if __name__ == '__main__':
    main()
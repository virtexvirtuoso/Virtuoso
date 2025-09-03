#!/usr/bin/env python3
"""
Virtuoso CCXT Root Directory Organization Script

This script organizes the root directory by moving misplaced files to their proper locations
according to Python project best practices and the project's existing directory structure.

Usage:
    python organize_root_directory.py [--dry-run] [--backup]

Options:
    --dry-run    Show what would be moved without actually moving files
    --backup     Create a backup of the current state before reorganizing
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime


class RootDirectoryOrganizer:
    def __init__(self, project_root: str, dry_run: bool = False, backup: bool = False):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.backup = backup
        self.moves_performed = []
        self.errors = []

    def log_action(self, action: str, details: str = ""):
        """Log actions taken during organization."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status = "[DRY RUN]" if self.dry_run else "[EXECUTE]"
        print(f"{timestamp} {status} {action}: {details}")

    def ensure_directory_exists(self, directory: Path):
        """Ensure target directory exists."""
        if not self.dry_run:
            directory.mkdir(parents=True, exist_ok=True)
        self.log_action("CREATE_DIR", str(directory))

    def move_file_with_git(self, source: Path, target: Path):
        """Move file using git mv to preserve history."""
        try:
            # Ensure target directory exists
            self.ensure_directory_exists(target.parent)
            
            if not self.dry_run:
                # Use git mv if in a git repository
                try:
                    subprocess.run(['git', 'mv', str(source), str(target)], 
                                 check=True, capture_output=True, cwd=self.project_root)
                    self.log_action("GIT_MV", f"{source} -> {target}")
                except subprocess.CalledProcessError:
                    # Fallback to regular move if git mv fails
                    shutil.move(str(source), str(target))
                    self.log_action("MOVE", f"{source} -> {target}")
            else:
                self.log_action("GIT_MV", f"{source} -> {target}")
            
            self.moves_performed.append((str(source), str(target)))
        except Exception as e:
            error_msg = f"Failed to move {source} to {target}: {str(e)}"
            self.errors.append(error_msg)
            self.log_action("ERROR", error_msg)

    def delete_file(self, file_path: Path):
        """Safely delete file."""
        try:
            if not self.dry_run:
                if file_path.is_file():
                    file_path.unlink()
                elif file_path.is_dir():
                    shutil.rmtree(str(file_path))
            self.log_action("DELETE", str(file_path))
        except Exception as e:
            error_msg = f"Failed to delete {file_path}: {str(e)}"
            self.errors.append(error_msg)
            self.log_action("ERROR", error_msg)

    def create_backup(self):
        """Create a backup of current root directory state."""
        if not self.backup or self.dry_run:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.project_root / f"backups/root_backup_{timestamp}"
        
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup key files that will be moved
            files_to_backup = list(self.get_files_to_move().keys())
            
            for file_path in files_to_backup:
                source_path = self.project_root / file_path
                if source_path.exists():
                    backup_path = backup_dir / file_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if source_path.is_file():
                        shutil.copy2(str(source_path), str(backup_path))
                    elif source_path.is_dir():
                        shutil.copytree(str(source_path), str(backup_path))
            
            self.log_action("BACKUP_CREATED", str(backup_dir))
            
        except Exception as e:
            self.log_action("BACKUP_ERROR", str(e))

    def get_files_to_move(self) -> dict:
        """Define the mapping of files to their new locations."""
        return {
            # Python utility scripts to scripts/
            "analyze_scripts.py": "scripts/analyze_scripts.py",
            "batch_document_scripts.py": "scripts/batch_document_scripts.py", 
            "test_cache_debug.py": "scripts/test_cache_debug.py",
            "test_cache_performance.py": "scripts/test_cache_performance.py",
            "test_cache_rationalization.py": "scripts/test_cache_rationalization.py",
            "test_di_refactored_components.py": "scripts/test_di_refactored_components.py",
            "test_startup.py": "scripts/test_startup.py",
            
            # Deployment and fix scripts to scripts/
            "deploy_confluence_cache_fix.sh": "scripts/deploy_confluence_cache_fix.sh",
            "deploy_di_fixes.py": "scripts/deploy_di_fixes.py",
            "emergency_bridge_fix.py": "scripts/emergency_bridge_fix.py",
            "fix_cache_bridge_dashboard_data.py": "scripts/fix_cache_bridge_dashboard_data.py",
            "fix_confluence_caching.py": "scripts/fix_confluence_caching.py",
            "fix_confluence_caching_integration.py": "scripts/fix_confluence_caching_integration.py",
            
            # Documentation files to docs/
            "CACHE_ARCHITECTURE_CHANGES.md": "docs/CACHE_ARCHITECTURE_CHANGES.md",
            "CACHE_BRIDGE_FIX_IMPLEMENTATION.md": "docs/CACHE_BRIDGE_FIX_IMPLEMENTATION.md",
            "CACHE_ENHANCEMENT_COMPLETE.md": "docs/CACHE_ENHANCEMENT_COMPLETE.md",
            "CACHE_OPTIMIZATION_DEPLOYMENT_SUMMARY.md": "docs/CACHE_OPTIMIZATION_DEPLOYMENT_SUMMARY.md",
            "CACHE_RATIONALIZATION_SUMMARY_REPORT.md": "docs/CACHE_RATIONALIZATION_SUMMARY_REPORT.md",
            "DEPLOYMENT_MONITORING_REPORT.md": "docs/DEPLOYMENT_MONITORING_REPORT.md",
            "DOCUMENTATION_AUDIT_COMPREHENSIVE_2025_08_30.md": "docs/DOCUMENTATION_AUDIT_COMPREHENSIVE_2025_08_30.md",
            "DOCUMENTATION_REORGANIZATION_REPORT.md": "docs/DOCUMENTATION_REORGANIZATION_REPORT.md",
            
            # Log files to logs/
            "main_output.log": "logs/main_output.log",
            "system_startup.log": "logs/system_startup.log", 
            "deployment.log": "logs/deployment.log",
            
            # Report files to reports/
            "cache_optimization_test_results.json": "reports/cache_optimization_test_results.json",
            "documentation_audit_results.json": "reports/documentation_audit_results.json",
            "documentation_validation_report.json": "reports/documentation_validation_report.json",
            "final_complete_report.json": "reports/final_complete_report.json",
            "final_report.json": "reports/final_report.json",
            "validation_report.json": "reports/validation_report.json",
            
            # Media files to assets/
            "performance_analysis_charts.png": "assets/performance_analysis_charts.png",
            "Virtuoso | Trello.pdf": "assets/Virtuoso_Trello.pdf",  # Rename for compatibility
        }

    def get_intelligence_files(self) -> dict:
        """Get intelligence validation files (there are many with timestamps)."""
        intelligence_files = {}
        
        # Look for intelligence validation files
        for file_path in self.project_root.glob("intelligence_validation_*.log"):
            filename = file_path.name
            intelligence_files[filename] = f"logs/{filename}"
            
        for file_path in self.project_root.glob("intelligence_validation_report_*.json"):
            filename = file_path.name  
            intelligence_files[filename] = f"reports/{filename}"
            
        return intelligence_files

    def get_files_to_delete(self) -> list:
        """Files that can be safely deleted."""
        return [
            "__pycache__",
            ".DS_Store",
        ]

    def organize(self):
        """Perform the complete organization process."""
        print(f"\n{'='*60}")
        print("VIRTUOSO CCXT ROOT DIRECTORY ORGANIZATION")
        print(f"{'='*60}")
        print(f"Project Root: {self.project_root}")
        print(f"Dry Run: {self.dry_run}")
        print(f"Create Backup: {self.backup}")
        print(f"{'='*60}\n")

        # Create backup if requested
        if self.backup:
            self.create_backup()

        # Move predefined files
        print("PHASE 1: Moving predefined files...")
        files_to_move = self.get_files_to_move()
        for source_rel, target_rel in files_to_move.items():
            source_path = self.project_root / source_rel
            target_path = self.project_root / target_rel
            
            if source_path.exists():
                self.move_file_with_git(source_path, target_path)
            else:
                self.log_action("SKIP", f"{source_rel} (not found)")

        # Move intelligence files
        print("\nPHASE 2: Moving intelligence validation files...")
        intelligence_files = self.get_intelligence_files()
        for source_rel, target_rel in intelligence_files.items():
            source_path = self.project_root / source_rel
            target_path = self.project_root / target_rel
            
            if source_path.exists():
                self.move_file_with_git(source_path, target_path)

        # Delete temporary files
        print("\nPHASE 3: Cleaning up temporary files...")
        for file_to_delete in self.get_files_to_delete():
            file_path = self.project_root / file_to_delete
            if file_path.exists():
                self.delete_file(file_path)

        # Summary
        self.print_summary()

    def print_summary(self):
        """Print organization summary."""
        print(f"\n{'='*60}")
        print("ORGANIZATION SUMMARY")
        print(f"{'='*60}")
        print(f"Files moved: {len(self.moves_performed)}")
        print(f"Errors encountered: {len(self.errors)}")
        
        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  ❌ {error}")
        
        if not self.dry_run:
            print("\n✅ Organization completed successfully!")
            print("\nNext steps:")
            print("1. Review the changes with: git status")
            print("2. Test that the application still runs properly")
            print("3. Commit the changes: git add . && git commit -m 'Organize root directory structure'")
        else:
            print("\n📋 This was a dry run. Use without --dry-run to execute the changes.")

    def create_rollback_script(self):
        """Create a script to rollback the changes if needed."""
        if self.dry_run or not self.moves_performed:
            return

        rollback_script = self.project_root / "rollback_organization.py"
        rollback_content = f'''#!/usr/bin/env python3
"""
Rollback script for root directory organization.
Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

import subprocess
from pathlib import Path

project_root = Path(__file__).parent

# Reverse the moves
moves_to_reverse = {reversed(self.moves_performed)}

for target, source in moves_to_reverse:
    try:
        subprocess.run(['git', 'mv', target, source], check=True, cwd=project_root)
        print(f"Reversed: {{target}} -> {{source}}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to reverse: {{target}} -> {{source}}: {{e}}")

print("Rollback completed!")
'''
        
        with open(rollback_script, 'w') as f:
            f.write(rollback_content)
        
        rollback_script.chmod(0o755)
        self.log_action("ROLLBACK_SCRIPT", str(rollback_script))


def main():
    parser = argparse.ArgumentParser(description="Organize Virtuoso CCXT root directory")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be done without actually doing it")
    parser.add_argument("--backup", action="store_true",
                       help="Create backup before organizing")
    
    args = parser.parse_args()
    
    # Get project root (directory containing this script)
    project_root = Path(__file__).parent
    
    # Create and run organizer
    organizer = RootDirectoryOrganizer(
        project_root=str(project_root),
        dry_run=args.dry_run,
        backup=args.backup
    )
    
    try:
        organizer.organize()
        
        # Create rollback script if changes were made
        if not args.dry_run:
            organizer.create_rollback_script()
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
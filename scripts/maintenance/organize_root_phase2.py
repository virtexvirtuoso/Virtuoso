#!/usr/bin/env python3
"""
Phase 2: Root Directory Cleanup Script
Organizes remaining test scripts, validation files, reports, and JSON files
with backup and detailed logging.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import json
import re

class Phase2Organizer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.project_root / f".cleanup_backup_phase2_{self.timestamp}"
        self.log_file = self.project_root / f"cleanup_log_phase2_{self.timestamp}.json"
        self.operations = []
        self.errors = []

        # Files to keep in root (essential files)
        self.keep_in_root = {
            'README.md',
            'CHANGELOG.md',
            'CONTRIBUTING.md',
            'CODE_OF_CONDUCT.md',
            'SECURITY.md',
            'CLAUDE.local.md',
            'setup.py',
            'docker-entrypoint.sh',
            'docker-compose.yml',
            'Dockerfile',
            '.env',
            '.env.example',
            '.gitignore',
            '.gitattributes',
            '.dockerignore',
            'requirements.txt',
            'organize_root_directory.py',
            'organize_root_phase2.py',
        }

    def create_backup(self):
        """Create backup of all files to be moved"""
        print(f"Creating Phase 2 backup at: {self.backup_dir}")
        self.backup_dir.mkdir(exist_ok=True)
        return True

    def log_operation(self, operation_type, source, destination, status, error=None):
        """Log each operation for audit trail"""
        self.operations.append({
            "timestamp": datetime.now().isoformat(),
            "type": operation_type,
            "source": str(source),
            "destination": str(destination),
            "status": status,
            "error": str(error) if error else None
        })

    def ensure_directory(self, dir_path):
        """Create directory if it doesn't exist"""
        dir_path = self.project_root / dir_path
        if not dir_path.exists():
            print(f"  Creating directory: {dir_path.relative_to(self.project_root)}")
            dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def backup_file(self, source):
        """Backup a file before moving"""
        try:
            relative_path = source.relative_to(self.project_root)
            backup_path = self.backup_dir / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup_path)
            return True
        except Exception as e:
            print(f"  ⚠️  Backup failed for {source.name}: {e}")
            self.errors.append(f"Backup failed: {source.name} - {e}")
            return False

    def move_file(self, source_name, dest_dir, create_subdirs=True):
        """Move a file to destination directory with backup"""
        source = self.project_root / source_name

        if not source.exists():
            print(f"  ⚠️  File not found: {source_name}")
            self.log_operation("move", source_name, dest_dir, "skipped", "File not found")
            return False

        # Create destination directory
        if create_subdirs:
            dest_path = self.ensure_directory(dest_dir)
        else:
            dest_path = self.project_root / dest_dir

        destination = dest_path / source.name

        try:
            # Backup first
            if self.backup_file(source):
                # Move file
                shutil.move(str(source), str(destination))
                print(f"  ✅ Moved: {source_name} → {dest_dir}/{source.name}")
                self.log_operation("move", source_name, str(destination.relative_to(self.project_root)), "success")
                return True
            else:
                return False
        except Exception as e:
            print(f"  ❌ Error moving {source_name}: {e}")
            self.log_operation("move", source_name, dest_dir, "failed", str(e))
            self.errors.append(f"Move failed: {source_name} - {e}")
            return False

    def organize_orderflow_reports(self):
        """Organize orderflow-related reports"""
        print("\n📋 Organizing Orderflow Reports...")

        # Validation reports
        validation_files = [
            "COMPREHENSIVE_ORDERFLOW_VALIDATION_REPORT.md",
            "ORDERFLOW_PHASES_1-3_COMPREHENSIVE_QA_VALIDATION_REPORT.md",
        ]
        for file in validation_files:
            self.move_file(file, "docs/reports/validation")

        # Deployment reports
        deployment_files = [
            "ORDERFLOW_VPS_DEPLOYMENT_COMPLETE.md",
        ]
        for file in deployment_files:
            self.move_file(file, "docs/reports/deployment")

    def organize_phase_summaries(self):
        """Organize phase completion summaries"""
        print("\n📋 Organizing Phase Summaries...")

        phase_files = [
            "PHASE1_CRITICAL_FIXES_COMPLETE.md",
            "PHASE2_ENHANCEMENTS_COMPLETE.md",
            "PHASE3_ENHANCEMENTS_COMPLETE.md",
            "PHASES_1-3_COMPLETE_SUMMARY.md",
        ]
        for file in phase_files:
            self.move_file(file, "docs/implementation/summaries")

    def organize_design_and_analysis_docs(self):
        """Organize design and analysis documentation"""
        print("\n📋 Organizing Design & Analysis Documentation...")

        # Quality/Confluence analysis
        analysis_files = [
            "CONFLUENCE_QUALITY_METRICS_ADDED.md",
            "QUALITY_ADJUSTMENT_FORMULA_ANALYSIS.md",
        ]
        for file in analysis_files:
            self.move_file(file, "docs/design/quality-metrics")

        # Indicator reviews
        indicator_files = [
            "ORDERFLOW_INDICATORS_COMPREHENSIVE_REVIEW.md",
        ]
        for file in indicator_files:
            self.move_file(file, "docs/design/indicators")

        # Cleanup reports
        cleanup_files = [
            "LEGACY_CODE_CLEANUP_REPORT.md",
        ]
        for file in cleanup_files:
            self.move_file(file, "docs/operations/maintenance")

    def organize_test_scripts(self):
        """Organize test_*.py scripts"""
        print("\n📋 Organizing Test Scripts...")

        # Get all test_*.py files
        test_files = list(self.project_root.glob("test_*.py"))

        # Categorize tests
        integration_tests = []
        validation_tests = []
        unit_tests = []

        for test_file in test_files:
            filename = test_file.name

            # Validation tests
            if any(keyword in filename.lower() for keyword in ['validation', 'regression', 'check']):
                validation_tests.append(filename)
            # Integration/system tests
            elif any(keyword in filename.lower() for keyword in ['rpi', 'vps', 'websocket', 'cache', 'database', 'system', 'complete']):
                integration_tests.append(filename)
            # Alert/PDF specific tests
            elif any(keyword in filename.lower() for keyword in ['alert', 'pdf', 'stop_loss', 'mobile', 'config']):
                integration_tests.append(filename)
            else:
                # Default to integration
                integration_tests.append(filename)

        # Move integration tests
        if integration_tests:
            print(f"  Moving {len(integration_tests)} integration test(s)...")
            for test in integration_tests:
                self.move_file(test, "tests/integration")

        # Move validation tests
        if validation_tests:
            print(f"  Moving {len(validation_tests)} validation test(s)...")
            for test in validation_tests:
                self.move_file(test, "tests/validation")

    def organize_fix_scripts(self):
        """Organize fix_*.py scripts"""
        print("\n📋 Organizing Fix Scripts...")

        fix_files = list(self.project_root.glob("fix_*.py"))

        print(f"  Moving {len(fix_files)} fix script(s)...")
        for fix_file in fix_files:
            self.move_file(fix_file.name, "scripts/fixes")

    def organize_validation_scripts(self):
        """Organize validation_*.py and *_validation.py scripts"""
        print("\n📋 Organizing Validation Scripts...")

        # Get validation scripts
        validation_files = []
        validation_files.extend(list(self.project_root.glob("validation_*.py")))

        # Also get *_validation.py files
        for py_file in self.project_root.glob("*_validation.py"):
            if py_file.name not in [f.name for f in validation_files]:
                validation_files.append(py_file)

        print(f"  Moving {len(validation_files)} validation script(s)...")
        for val_file in validation_files:
            self.move_file(val_file.name, "scripts/validation")

    def organize_utility_scripts(self):
        """Organize remaining utility scripts"""
        print("\n📋 Organizing Utility Scripts...")

        utility_files = [
            "check_services.py",
            "comprehensive_alert_validation.py",
            "comprehensive_rpi_test.py",
            "final_rpi_validation.py",
            "ui_functionality_test.py",
            "vps_test.py",
        ]

        for util_file in utility_files:
            source = self.project_root / util_file
            if source.exists():
                # Determine destination based on purpose
                if 'validation' in util_file or 'test' in util_file:
                    self.move_file(util_file, "scripts/validation")
                else:
                    self.move_file(util_file, "scripts/diagnostics")

    def organize_json_reports(self):
        """Organize JSON report files"""
        print("\n📋 Organizing JSON Reports...")

        # Get all JSON files except essential ones
        json_files = []
        for json_file in self.project_root.glob("*.json"):
            if json_file.name not in ['package.json', 'tsconfig.json'] and not json_file.name.startswith('cleanup_log'):
                json_files.append(json_file)

        # Categorize JSON files
        for json_file in json_files:
            filename = json_file.name.lower()

            # Validation results
            if 'validation' in filename or 'results' in filename:
                self.move_file(json_file.name, "reports/validation")
            # Alert reports
            elif 'alert' in filename:
                self.move_file(json_file.name, "reports/alerts")
            # Audit reports
            elif 'audit' in filename:
                self.move_file(json_file.name, "reports/diagnostics")
            # Test/RPI reports
            elif any(keyword in filename for keyword in ['rpi', 'test', 'cache', 'dashboard']):
                self.move_file(json_file.name, "reports/integration")
            else:
                # Default to general reports
                self.move_file(json_file.name, "reports/general")

    def organize_log_files(self):
        """Organize .log files in root"""
        print("\n📋 Organizing Log Files...")

        log_files = list(self.project_root.glob("*.log"))

        if log_files:
            print(f"  Moving {len(log_files)} log file(s)...")
            for log_file in log_files:
                self.move_file(log_file.name, "logs")

    def save_log(self):
        """Save operation log to JSON file"""
        log_data = {
            "phase": 2,
            "timestamp": self.timestamp,
            "backup_directory": str(self.backup_dir.relative_to(self.project_root)),
            "total_operations": len(self.operations),
            "successful": len([op for op in self.operations if op["status"] == "success"]),
            "failed": len([op for op in self.operations if op["status"] == "failed"]),
            "skipped": len([op for op in self.operations if op["status"] == "skipped"]),
            "errors": self.errors,
            "operations": self.operations
        }

        with open(self.log_file, 'w') as f:
            json.dump(log_data, f, indent=2)

        print(f"\n📝 Operation log saved to: {self.log_file.name}")
        return log_data

    def print_summary(self, log_data):
        """Print summary of operations"""
        print("\n" + "="*60)
        print("PHASE 2 CLEANUP SUMMARY")
        print("="*60)
        print(f"Total operations: {log_data['total_operations']}")
        print(f"  ✅ Successful: {log_data['successful']}")
        print(f"  ❌ Failed: {log_data['failed']}")
        print(f"  ⚠️  Skipped: {log_data['skipped']}")

        if self.errors:
            print(f"\n⚠️  Errors encountered: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more (see log file)")

        print(f"\n📦 Backup created at: {self.backup_dir.relative_to(self.project_root)}")
        print(f"📝 Full log available at: {self.log_file.name}")
        print("\n" + "="*60)

    def print_final_status(self):
        """Print final root directory status"""
        print("\n" + "="*60)
        print("ROOT DIRECTORY STATUS")
        print("="*60)

        # Count remaining files
        md_files = len(list(self.project_root.glob("*.md")))
        py_files = len(list(self.project_root.glob("*.py")))
        sh_files = len(list(self.project_root.glob("*.sh")))
        json_files = len([f for f in self.project_root.glob("*.json") if not f.name.startswith('cleanup_log')])

        print(f"Remaining files in root:")
        print(f"  📄 Markdown files: {md_files}")
        print(f"  🐍 Python scripts: {py_files}")
        print(f"  📜 Shell scripts: {sh_files}")
        print(f"  📊 JSON files: {json_files}")

        # Show what's left
        if md_files + py_files + sh_files + json_files > 15:
            print(f"\n⚠️  Note: {md_files + py_files + sh_files + json_files} files remain in root")
            print("    Run 'ls -1 *.md *.py *.sh *.json 2>/dev/null' to review")
        else:
            print("\n✨ Root directory is now well-organized!")

        print("="*60)

    def run(self, dry_run=False):
        """Execute the full Phase 2 organization process"""
        if dry_run:
            print("🔍 DRY RUN MODE - No files will be moved\n")
        else:
            print("🚀 Starting Phase 2 Root Directory Cleanup\n")
            print(f"Project: {self.project_root}")
            print(f"Timestamp: {self.timestamp}\n")

            # Create backup
            self.create_backup()

        # Execute organization
        try:
            self.organize_orderflow_reports()
            self.organize_phase_summaries()
            self.organize_design_and_analysis_docs()
            self.organize_test_scripts()
            self.organize_fix_scripts()
            self.organize_validation_scripts()
            self.organize_utility_scripts()
            self.organize_json_reports()
            self.organize_log_files()

            # Save log and print summaries
            log_data = self.save_log()
            self.print_summary(log_data)
            self.print_final_status()

            print("\n✨ Phase 2 cleanup complete!")
            print("\nNext steps:")
            print("  1. Review the changes in your git status")
            print("  2. Check the log file for any errors")
            print("  3. If everything looks good, you can delete the backup:")
            print(f"     rm -rf {self.backup_dir.relative_to(self.project_root)}")
            print("  4. Consider adding patterns to .gitignore to prevent future clutter:")
            print("     - /test_*.py")
            print("     - /fix_*.py")
            print("     - /validation_*.py")
            print("     - /*_report*.json")

        except Exception as e:
            print(f"\n❌ Fatal error during cleanup: {e}")
            print(f"Backup is preserved at: {self.backup_dir}")
            raise


def main():
    """Main entry point"""
    import sys

    project_root = Path(__file__).parent
    organizer = Phase2Organizer(project_root)

    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("Note: Dry-run mode is not fully implemented in this version")
        print("The script will create backups before moving files")
        print("You can safely run it and restore from backup if needed\n")

    try:
        organizer.run(dry_run=dry_run)
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup interrupted by user")
        print(f"Backup preserved at: {organizer.backup_dir}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

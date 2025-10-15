#!/usr/bin/env python3
"""
Automated Root Directory Cleanup Script
Organizes documentation and scripts into proper directory structure
with backup and detailed logging.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import json
import re

class RootOrganizer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.project_root / f".cleanup_backup_{self.timestamp}"
        self.log_file = self.project_root / f"cleanup_log_{self.timestamp}.json"
        self.operations = []
        self.errors = []

    def create_backup(self):
        """Create backup of all files to be moved"""
        print(f"Creating backup at: {self.backup_dir}")
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

    def organize_alert_docs(self):
        """Organize alert-related documentation"""
        print("\n📋 Organizing Alert Documentation...")

        # Design documents
        design_files = [
            "ALERT_DESIGN_PRINCIPLES_COMPREHENSIVE.md",
            "ALERT_DESIGN_PRINCIPLES_APPLICATION_REVIEW.md",
            "ENHANCED_MANIPULATION_ALERTS.md",
        ]
        for file in design_files:
            self.move_file(file, "docs/design/alerts")

        # Reports
        report_files = [
            "ALERT_ENHANCEMENTS_SUMMARY.md",
            "ALERT_ENHANCEMENT_DEPLOYMENT_REPORT.md",
            "ALERT_OPTIMIZATION_IMPLEMENTATION_SUMMARY.md",
            "ALERT_OPTIMIZATION_SUMMARY.md",
            "MANIPULATION_ALERT_DEPLOYMENT_REPORT.md",
            "MANIPULATION_ALERT_SYSTEM_VALIDATION_REPORT.md",
            "MANIPULATION_ALERT_VALIDATION_EXECUTIVE_SUMMARY.md",
        ]
        for file in report_files:
            self.move_file(file, "docs/reports/alerts")

        # Fixes
        fix_files = [
            "MANIPULATION_ALERT_QUICK_FIX_GUIDE.md",
            "CRITICAL_MANIPULATION_ALERT_FIX.patch",
        ]
        for file in fix_files:
            self.move_file(file, "docs/fixes/alerts")

    def organize_validation_reports(self):
        """Organize validation reports"""
        print("\n📋 Organizing Validation Reports...")

        validation_files = [
            "COMPREHENSIVE_QA_VALIDATION_REPORT.md",
            "COMPREHENSIVE_QA_VALIDATION_REPORT_20250929_203000.md",
            "COMPREHENSIVE_ASYNCIO_VALIDATION_REPORT.md",
            "COMPREHENSIVE_DASHBOARD_BREAKDOWN_VALIDATION_REPORT.md",
            "COMPREHENSIVE_END_TO_END_VALIDATION_REPORT.md",
            "COMPREHENSIVE_SHARED_CACHE_BRIDGE_QA_VALIDATION_REPORT.md",
            "COMPREHENSIVE_VPS_END_TO_END_VALIDATION_REPORT.md",
            "DASHBOARD_BREAKDOWN_VALIDATION_REPORT.md",
            "HEALTH_CHECK_PERMISSIONS_FIX_VALIDATION_REPORT.md",
            "HYBRID_QUALITY_SCORE_QA_VALIDATION_REPORT.md",
            "MARKET_OVERVIEW_FIX_VALIDATION_REPORT.md",
            "POST_REMEDIATION_VALIDATION_REPORT.md",
            "RPI_INTEGRATION_COMPREHENSIVE_VALIDATION_REPORT.md",
            "RPI_INTEGRATION_VALIDATION_REPORT.md",
            "RPI_VALIDATION_REPORT.md",
            "SHARED_CACHE_BRIDGE_COMPREHENSIVE_VALIDATION_REPORT.md",
            "VPS_PRODUCTION_VALIDATION_REPORT_20250930.md",
            "QA_EXECUTIVE_SUMMARY.md",
            "QA_VALIDATION_REPORT_WEEK1_QUICK_WINS.md",
        ]
        for file in validation_files:
            self.move_file(file, "docs/reports/validation")

    def organize_deployment_reports(self):
        """Organize deployment reports"""
        print("\n📋 Organizing Deployment Reports...")

        deployment_files = [
            "CVD_OBV_DEPLOYMENT_SUCCESS_REPORT.md",
            "PHASE1_VPS_DEPLOYMENT_COMPLETE.md",
            "SHARED_CACHE_BRIDGE_IMPLEMENTATION_REPORT.md",
            "UNIFIED_SCHEMA_DEPLOYMENT_REPORT.md",
            "MANIPULATION_ALERT_DEPLOYMENT_REPORT.md",
            "ALERT_ENHANCEMENT_DEPLOYMENT_REPORT.md",
        ]
        for file in deployment_files:
            self.move_file(file, "docs/reports/deployment")

    def organize_implementation_plans(self):
        """Organize implementation plans and summaries"""
        print("\n📋 Organizing Implementation Plans...")

        plan_files = [
            "MOBILE_DASHBOARD_FIX_IMPLEMENTATION_PLAN.md",
            "UNIFIED_SCHEMA_IMPLEMENTATION_PLAN.md",
            "UNIFIED_SCHEMA_PLAN_REVIEW.md",
            "CVD_OBV_ROLLING_WINDOW_IMPLEMENTATION_REPORT.md",
        ]
        for file in plan_files:
            self.move_file(file, "docs/implementation/plans")

        summary_files = [
            "PHASE1_COMPLETE_SUMMARY.md",
            "MONITORING_ACTIVE_SUMMARY.md",
        ]
        for file in summary_files:
            self.move_file(file, "docs/implementation/summaries")

    def organize_design_docs(self):
        """Organize design documents"""
        print("\n📋 Organizing Design Documents...")

        # Confluence design
        confluence_files = [
            "QUALITY_ADJUSTED_CONFLUENCE_SCORE_DESIGN.md",
            "CONFLUENCE_ANALYSIS_SYSTEM_REVIEW.md",
            "CONFLUENCE_WEIGHT_OPTIMIZATION_2025_10_11.md",
            "ENHANCED_CONFLUENCE_REPLACEMENT_COMPLETE.md",
        ]
        for file in confluence_files:
            self.move_file(file, "docs/design/confluence")

        # Indicator design
        indicator_files = [
            "INDICATOR_DETAILED_REVIEW_2025_10_08.md",
            "RECOMMENDED_CVD_OBV_FIX.md",
        ]
        for file in indicator_files:
            self.move_file(file, "docs/design/indicators")

        # Cache design
        cache_files = [
            "CACHE_SCHEMA_MISMATCH_FINDINGS.md",
            "CROSS_PROCESS_CACHE_FIX.md",
        ]
        for file in cache_files:
            self.move_file(file, "docs/design/cache")

        # Quality metrics
        quality_files = [
            "QUALITY_FILTERING_IMPLEMENTATION_COMPLETE.md",
        ]
        for file in quality_files:
            self.move_file(file, "docs/design/quality-metrics")

    def organize_diagnostic_reports(self):
        """Organize diagnostic and investigation reports"""
        print("\n📋 Organizing Diagnostic Reports...")

        diagnostic_files = [
            "CRITICAL_ISSUES_DIAGNOSTIC_REPORT_20250924_103957.md",
            "CRITICAL_ISSUES_DIAGNOSTIC_REPORT_20250924_104457.md",
            "MOBILE_ENDPOINT_NO_DATA_DIAGNOSTIC_REPORT.md",
            "ENVIRONMENT_INCONSISTENCY_INVESTIGATION_REPORT.md",
            "ORDERBOOK_INDEXING_ERRORS_INVESTIGATION.md",
            "COMPREHENSIVE_API_GAP_INVESTIGATION_REPORT.md",
            "VPS_DASHBOARD_AUDIT_REPORT.md",
        ]
        for file in diagnostic_files:
            self.move_file(file, "docs/reports/diagnostics")

    def organize_fix_reports(self):
        """Organize fix documentation"""
        print("\n📋 Organizing Fix Reports...")

        # Critical fixes
        critical_files = [
            "CRITICAL_ISSUES_RESOLUTION_FINAL_REPORT.md",
        ]
        for file in critical_files:
            self.move_file(file, "docs/fixes/critical")

        # Mobile dashboard fixes
        mobile_files = [
            "DASHBOARD_BREAKDOWN_FIX_REFERENCE.md",
            "DASHBOARD_BREAKDOWN_QA_EXECUTIVE_SUMMARY.md",
            "MOBILE_DASHBOARD_COMPLETE_FIX_SUMMARY.md",
            "MOBILE_DASHBOARD_COMPONENT_FIX_REPORT.md",
            "MOBILE_DASHBOARD_CROSS_PROCESS_CACHE_FIX_REPORT.md",
            "MOBILE_DASHBOARD_FINAL_FIX_REPORT.md",
            "MOBILE_DASHBOARD_FIX_DEPLOYMENT_REPORT.md",
            "MOBILE_DASHBOARD_FIX_REPORT.md",
        ]
        for file in mobile_files:
            self.move_file(file, "docs/fixes/mobile-dashboard")

        # Health check fixes
        health_files = [
            "HEALTH_CHECK_FIX_REPORT.md",
        ]
        for file in health_files:
            self.move_file(file, "docs/fixes/health-checks")

        # Market overview fixes
        market_files = [
            "MARKET_OVERVIEW_FIX_REPORT.md",
        ]
        for file in market_files:
            self.move_file(file, "docs/fixes/market-overview")

        # Database fixes
        database_files = [
            "DATABASE_JSON_SERIALIZATION_FIX_REPORT.md",
        ]
        for file in database_files:
            self.move_file(file, "docs/fixes/database")

    def organize_phase1_docs(self):
        """Organize Phase 1 documentation"""
        print("\n📋 Organizing Phase 1 Documentation...")

        phase1_files = [
            "PHASE1_COMPREHENSIVE_QA_VALIDATION_REPORT.md",
            "PHASE1_DIVISION_GUARDS_DEPLOYMENT_SUMMARY.md",
            "PHASE1_LOCAL_VALIDATION_RESULTS.md",
        ]
        for file in phase1_files:
            self.move_file(file, "docs/operations/phase1")

    def organize_performance_docs(self):
        """Organize performance and quality documentation"""
        print("\n📋 Organizing Performance Documentation...")

        performance_files = [
            "MEMORY_OPTIMIZATION_REPORT_20250924_104357.md",
        ]
        for file in performance_files:
            self.move_file(file, "docs/reports/performance")

        qa_files = [
            "QUALITY_FILTERING_SYSTEM_QA_REPORT.md",
        ]
        for file in qa_files:
            self.move_file(file, "docs/reports/qa")

    def organize_python_scripts(self):
        """Organize Python scripts from root"""
        print("\n📋 Organizing Python Scripts...")

        # Diagnostic scripts
        diagnostic_scripts = [
            "api_gap_audit.py",
            "debug_mobile_data.py",
            "quick_health_diagnostic.py",
            "monitor_vps_performance.py",
        ]
        for script in diagnostic_scripts:
            self.move_file(script, "scripts/diagnostics")

        # Fix scripts
        fix_scripts = [
            "alert_formatting_fixes.py",
            "apply_health_diagnostics.py",
            "convert_asyncio_tasks.py",
            "health_diagnostic_patch.py",
        ]
        for script in fix_scripts:
            self.move_file(script, "scripts/fixes")

        # Deployment scripts
        deployment_scripts = [
            "deploy_health_fixes.py",
        ]
        for script in deployment_scripts:
            self.move_file(script, "scripts/deployment")

        # Validation scripts
        validation_scripts = [
            "validate_asyncio_fixes.py",
            "validate_vps_performance.py",
        ]
        for script in validation_scripts:
            self.move_file(script, "scripts/validation")

    def organize_shell_scripts(self):
        """Organize shell scripts from root"""
        print("\n📋 Organizing Shell Scripts...")

        deployment_scripts = [
            "deploy_asyncio_task_tracking.sh",
            "deploy_complete_asyncio_fixes.sh",
            "vt_command_v5.sh",
        ]
        for script in deployment_scripts:
            self.move_file(script, "scripts/deployment")

    def organize_docker_files(self):
        """Organize Docker files"""
        print("\n📋 Organizing Docker Files...")

        docker_files = [
            "docker-compose.development.yml",
            "docker-compose.monitoring.yml",
            "docker-compose.production.yml",
            "docker-compose.test.yml",
            "Dockerfile.development",
        ]
        for file in docker_files:
            self.move_file(file, "docker")

    def save_log(self):
        """Save operation log to JSON file"""
        log_data = {
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
        print("CLEANUP SUMMARY")
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

    def run(self, dry_run=False):
        """Execute the full organization process"""
        if dry_run:
            print("🔍 DRY RUN MODE - No files will be moved\n")
        else:
            print("🚀 Starting Root Directory Cleanup\n")
            print(f"Project: {self.project_root}")
            print(f"Timestamp: {self.timestamp}\n")

            # Create backup
            self.create_backup()

        # Execute organization
        try:
            self.organize_alert_docs()
            self.organize_validation_reports()
            self.organize_deployment_reports()
            self.organize_implementation_plans()
            self.organize_design_docs()
            self.organize_diagnostic_reports()
            self.organize_fix_reports()
            self.organize_phase1_docs()
            self.organize_performance_docs()
            self.organize_python_scripts()
            self.organize_shell_scripts()
            self.organize_docker_files()

            # Save log and print summary
            log_data = self.save_log()
            self.print_summary(log_data)

            print("\n✨ Cleanup complete!")
            print("\nNext steps:")
            print("  1. Review the changes in your git status")
            print("  2. Check the log file for any errors")
            print("  3. If everything looks good, you can delete the backup:")
            print(f"     rm -rf {self.backup_dir.relative_to(self.project_root)}")
            print("  4. Update any documentation links if needed")

        except Exception as e:
            print(f"\n❌ Fatal error during cleanup: {e}")
            print(f"Backup is preserved at: {self.backup_dir}")
            raise


def main():
    """Main entry point"""
    import sys

    project_root = Path(__file__).parent
    organizer = RootOrganizer(project_root)

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

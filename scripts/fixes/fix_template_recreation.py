#!/usr/bin/env python3
"""
Script to fix the templates/market_report_dark.html recreation issue.
This script identifies and fixes all sources that might be creating templates in the root directory.
"""

import os
import shutil
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("template_fix")

def check_and_remove_root_template():
    """Check if the root template exists and remove it."""
    root_template = os.path.join(os.getcwd(), "templates", "market_report_dark.html")
    
    if os.path.exists(root_template):
        logger.warning(f"Found problematic template at: {root_template}")
        try:
            os.remove(root_template)
            logger.info("Removed problematic root template")
            return True
        except Exception as e:
            logger.error(f"Failed to remove root template: {e}")
            return False
    return False

def update_backup_files():
    """Update backup files to use correct template paths."""
    backup_files = [
        "src/monitoring/market_reporter.py.bak2",
        "src/monitoring/market_reporter.py.bak3", 
        "src/monitoring/market_reporter.py.bak4",
        "src/monitoring/market_reporter.py.bak5",
        "src/monitoring/market_reporter.py.backup_validation_fix"
    ]
    
    updated_count = 0
    for backup_file in backup_files:
        if os.path.exists(backup_file):
            try:
                with open(backup_file, 'r') as f:
                    content = f.read()
                
                # Replace problematic template path
                old_path = 'os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "market_report_dark.html")'
                new_path = 'os.path.join(os.getcwd(), "src", "templates", "market_report_dark.html")'
                
                if old_path in content:
                    content = content.replace(old_path, new_path)
                    with open(backup_file, 'w') as f:
                        f.write(content)
                    logger.info(f"Updated backup file: {backup_file}")
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to update backup file {backup_file}: {e}")
    
    return updated_count

def check_for_problematic_references():
    """Scan for any remaining problematic template references."""
    problematic_patterns = [
        '"templates"',
        'templates/',
        'os.path.join(os.getcwd(), "templates")'
    ]
    
    exclude_dirs = {'.git', '__pycache__', 'node_modules', 'venv', 'environments'}
    problematic_files = []
    
    for root, dirs, files in os.walk(os.getcwd()):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith(('.py', '.json', '.md', '.txt')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    for pattern in problematic_patterns:
                        if pattern in content and 'market_report_dark' in content:
                            problematic_files.append(file_path)
                            break
                            
                except Exception:
                    continue
    
    return problematic_files

def monitor_template_recreation():
    """Monitor for template recreation and log details."""
    root_template_dir = os.path.join(os.getcwd(), "templates")
    root_template_file = os.path.join(root_template_dir, "market_report_dark.html")
    
    logger.info("Starting template recreation monitoring...")
    logger.info(f"Monitoring: {root_template_file}")
    
    initial_exists = os.path.exists(root_template_file)
    logger.info(f"Initial state: {'EXISTS' if initial_exists else 'NOT EXISTS'}")
    
    for i in range(60):  # Monitor for 1 minute
        time.sleep(1)
        current_exists = os.path.exists(root_template_file)
        
        if current_exists != initial_exists:
            if current_exists:
                logger.warning(f"❌ TEMPLATE RECREATED at {time.strftime('%H:%M:%S')}")
                logger.warning(f"File size: {os.path.getsize(root_template_file)} bytes")
                logger.warning(f"File modified: {time.ctime(os.path.getmtime(root_template_file))}")
                
                # Check what process might have created it
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                        if proc.info['create_time'] > time.time() - 5:  # Created in last 5 seconds
                            logger.info(f"Recent process: {proc.info['name']} (PID: {proc.info['pid']})")
                except ImportError:
                    logger.info("Install psutil for detailed process monitoring")
                
                return True
            else:
                logger.info(f"✅ Template was removed at {time.strftime('%H:%M:%S')}")
                
            initial_exists = current_exists
    
    logger.info("✅ No template recreation detected during monitoring period")
    return False

def main():
    """Main function to fix template recreation issues."""
    logger.info("=== Template Recreation Fix Script ===")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Step 1: Remove existing root template
    logger.info("\n1. Checking for root template...")
    removed = check_and_remove_root_template()
    
    # Step 2: Update backup files
    logger.info("\n2. Updating backup files...")
    updated_count = update_backup_files()
    logger.info(f"Updated {updated_count} backup files")
    
    # Step 3: Check for problematic references
    logger.info("\n3. Scanning for problematic references...")
    problematic_files = check_for_problematic_references()
    if problematic_files:
        logger.warning(f"Found {len(problematic_files)} files with problematic references:")
        for file_path in problematic_files[:10]:  # Show first 10
            logger.warning(f"  - {file_path}")
        if len(problematic_files) > 10:
            logger.warning(f"  ... and {len(problematic_files) - 10} more")
    else:
        logger.info("✅ No problematic references found")
    
    # Step 4: Monitor for recreation
    logger.info("\n4. Monitoring for template recreation...")
    recreated = monitor_template_recreation()
    
    # Final summary
    logger.info("\n=== SUMMARY ===")
    logger.info(f"Root template removed: {'Yes' if removed else 'No (not found)'}")
    logger.info(f"Backup files updated: {updated_count}")
    logger.info(f"Problematic references: {len(problematic_files)}")
    logger.info(f"Template recreated during monitoring: {'Yes' if recreated else 'No'}")
    
    if recreated:
        logger.warning("⚠️  Template was recreated - investigation needed")
        logger.warning("Check recent process activity and configuration files")
    else:
        logger.info("✅ Fix appears successful - no recreation detected")

if __name__ == "__main__":
    main() 
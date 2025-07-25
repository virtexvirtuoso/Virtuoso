#!/usr/bin/env python3
"""
Fix Scheduled Reports Early Cache Warning

This script adds a startup delay to scheduled reports to allow cache population
before the first report generation attempt.

This prevents the "Symbol FARTCOINUSDT not in cache" warning that appears
early during application startup.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import re

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import Logger

def fix_scheduled_reports_delay(logger):
    """Add startup delay to scheduled reports."""
    logger.info("Adding startup delay to scheduled reports...")
    
    # Update market_reporter.py
    reporter_file = project_root / 'src' / 'monitoring' / 'market_reporter.py'
    
    if not reporter_file.exists():
        logger.error(f"market_reporter.py not found at {reporter_file}")
        return False
        
    try:
        # Read the file
        with open(reporter_file, 'r') as f:
            content = f.read()
        
        # Backup the file
        backup_file = reporter_file.with_suffix('.py.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
        with open(backup_file, 'w') as f:
            f.write(content)
        logger.info(f"Created backup: {backup_file.name}")
        
        # Find the run_scheduled_reports method
        method_pattern = r'(async def run_scheduled_reports\(self\):\s*"""[^"]*"""\s*)'
        
        # Check if delay already exists
        if 'startup_delay' in content and 'run_scheduled_reports' in content:
            logger.info("Startup delay already implemented")
            return True
        
        # Add startup delay configuration to __init__ method
        init_pattern = r'(self\.report_times = report_times or \[.*?\])'
        init_replacement = r'\1\n        \n        # Startup delay to allow cache population\n        self.startup_delay_minutes = 2  # Wait 2 minutes before first scheduled report\n        self._startup_time = datetime.utcnow()'
        
        if re.search(init_pattern, content):
            content = re.sub(init_pattern, init_replacement, content)
            logger.info("Added startup delay configuration to __init__")
        
        # Add delay logic to run_scheduled_reports
        delay_code = '''
        try:
            # Add startup delay to allow cache population
            if hasattr(self, '_startup_time'):
                elapsed = (datetime.utcnow() - self._startup_time).total_seconds() / 60
                if elapsed < self.startup_delay_minutes:
                    remaining = self.startup_delay_minutes - elapsed
                    self.logger.info(f"Waiting {remaining:.1f} more minutes before starting scheduled reports (cache population)")
                    await asyncio.sleep(remaining * 60)
                    self.logger.info("Startup delay complete, beginning scheduled reports")
            
            while True:'''
        
        # Replace the beginning of the while loop
        old_loop_start = r'try:\s*while True:'
        
        if re.search(old_loop_start, content):
            content = re.sub(old_loop_start, delay_code, content)
            logger.info("Added startup delay to run_scheduled_reports")
        else:
            logger.warning("Could not find while loop pattern, trying alternative approach")
            # Try to find the method and add after the docstring
            method_match = re.search(method_pattern + r'(\s*try:)', content)
            if method_match:
                insert_pos = method_match.end(1)
                delay_block = '''
        
        # Add startup delay to allow cache population
        if hasattr(self, '_startup_time'):
            elapsed = (datetime.utcnow() - self._startup_time).total_seconds() / 60
            if elapsed < self.startup_delay_minutes:
                remaining = self.startup_delay_minutes - elapsed
                self.logger.info(f"Waiting {remaining:.1f} more minutes before starting scheduled reports (cache population)")
                await asyncio.sleep(remaining * 60)
                self.logger.info("Startup delay complete, beginning scheduled reports")
'''
                content = content[:insert_pos] + delay_block + content[insert_pos:]
                logger.info("Added startup delay using alternative method")
        
        # Write the updated content
        with open(reporter_file, 'w') as f:
            f.write(content)
            
        logger.info("✓ Successfully added scheduled reports startup delay")
        return True
        
    except Exception as e:
        logger.error(f"Error adding startup delay: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def fix_cache_warning_level(logger):
    """Change cache miss warning to info level for startup period."""
    logger.info("\nChanging initial cache miss log level...")
    
    manager_file = project_root / 'src' / 'core' / 'market' / 'market_data_manager.py'
    
    if not manager_file.exists():
        logger.error(f"market_data_manager.py not found at {manager_file}")
        return False
        
    try:
        # Read the file
        with open(manager_file, 'r') as f:
            content = f.read()
        
        # Backup the file
        backup_file = manager_file.with_suffix('.py.backup_cache_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
        with open(backup_file, 'w') as f:
            f.write(content)
        
        # Find the cache miss warning
        old_warning = r'self\.logger\.warning\(f"Symbol {symbol} not in cache, initializing"\)'
        
        # Replace with conditional logging based on startup time
        new_logging = '''# Use info level for first 2 minutes to reduce startup noise
        if hasattr(self, '_init_time') and (time.time() - self._init_time) < 120:
            self.logger.info(f"Symbol {symbol} not in cache, initializing (startup phase)")
        else:
            self.logger.warning(f"Symbol {symbol} not in cache, initializing")'''
        
        if re.search(old_warning, content):
            content = re.sub(old_warning, new_logging, content)
            logger.info("Updated cache miss logging")
            
            # Add init time tracking to __init__
            init_pattern = r'(def __init__\(self.*?\):\s*"""[^"]*"""\s*)'
            init_match = re.search(init_pattern, content, re.DOTALL)
            if init_match:
                insert_pos = init_match.end()
                # Find the first line of actual code after docstring
                lines_after = content[insert_pos:].split('\n')
                for i, line in enumerate(lines_after):
                    if line.strip() and not line.strip().startswith('#'):
                        # Insert before this line
                        lines_after.insert(i, '        self._init_time = time.time()  # Track initialization time')
                        content = content[:insert_pos] + '\n'.join(lines_after)
                        break
                logger.info("Added initialization time tracking")
        
        # Write the updated content
        with open(manager_file, 'w') as f:
            f.write(content)
            
        logger.info("✓ Successfully updated cache warning level")
        return True
        
    except Exception as e:
        logger.error(f"Error updating cache warning level: {e}")
        return False

def main():
    """Apply fixes for early cache warnings."""
    logger = Logger('fix_cache_warnings')
    
    logger.info("="*60)
    logger.info("Scheduled Reports Startup Delay Fix")
    logger.info("="*60)
    logger.info(f"Time: {datetime.now()}")
    
    try:
        success = True
        
        # Apply both fixes
        if not fix_scheduled_reports_delay(logger):
            success = False
            
        if not fix_cache_warning_level(logger):
            success = False
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("Fix Summary")
        logger.info("="*60)
        
        if success:
            logger.info("\n✅ All fixes applied successfully!")
            logger.info("\nChanges made:")
            logger.info("1. Added 2-minute startup delay to scheduled reports")
            logger.info("2. Changed cache miss warnings to info level during startup")
            logger.info("\nBenefits:")
            logger.info("- Prevents early cache warnings during startup")
            logger.info("- Allows cache to populate before reports run")
            logger.info("- Reduces log noise during initialization")
            logger.info("\nNext steps:")
            logger.info("1. Restart the application")
            logger.info("2. Monitor logs - you should see:")
            logger.info('   - "Waiting X more minutes before starting scheduled reports"')
            logger.info('   - Cache messages as INFO instead of WARNING for first 2 minutes')
        else:
            logger.error("\n⚠️  Some fixes may have failed. Check the logs above.")
            
    except Exception as e:
        logger.error(f"Error applying fixes: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
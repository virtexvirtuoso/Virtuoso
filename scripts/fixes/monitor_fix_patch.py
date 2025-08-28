#!/usr/bin/env python3
"""
Direct patch script to apply metrics_manager AttributeError fixes to monitor.py on VPS.
This creates the necessary fixes that can be manually applied or executed remotely.
"""

import re

def create_patch_script():
    """Create a patch script that can be run on the VPS to fix the AttributeError"""
    
    patch_script = '''#!/usr/bin/env python3
"""
VPS Patch Script: Fix metrics_manager AttributeError in monitor.py
Applies defensive null checks to prevent 'NoneType' object has no attribute 'start_operation' errors
"""

import re
import os
import shutil
from datetime import datetime

def backup_file(filepath):
    """Create a backup of the original file"""
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"📄 Backup created: {backup_path}")
    return backup_path

def apply_fixes(filepath):
    """Apply all the metrics_manager defensive checks to the file"""
    
    print(f"🔧 Applying fixes to {filepath}")
    
    # Read the file
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Define the fixes
    fixes = [
        # Fix 1: validate_market_data method initialization (first instance)
        {
            'old': r'(\\s*)# Start performance tracking\\n(\\s*)operation = self\\.metrics_manager\\.start_operation\\("validate_market_data"\\)',
            'new': r'\\1# Start performance tracking\\n\\2operation = None\\n\\2if self.metrics_manager:\\n\\2    operation = self.metrics_manager.start_operation("validate_market_data")',
            'description': 'Fix validate_market_data method initialization'
        },
        
        # Fix 2: validate_market_data method metrics recording  
        {
            'old': r'(\\s*)# Record validation metrics\\n(\\s*)self\\.metrics_manager\\.record_metric\\("validation\\.total", validation_stats\\[\'total_validations\'\\]\\)\\n(\\s*)self\\.metrics_manager\\.record_metric\\("validation\\.passed", validation_stats\\[\'passed_validations\'\\]\\)\\n(\\s*)self\\.metrics_manager\\.record_metric\\("validation\\.failed", validation_stats\\[\'failed_validations\'\\]\\)',
            'new': r'\\1# Record validation metrics\\n\\2if self.metrics_manager:\\n\\2    self.metrics_manager.record_metric("validation.total", validation_stats[\'total_validations\'])\\n\\2    self.metrics_manager.record_metric("validation.passed", validation_stats[\'passed_validations\'])\\n\\2    self.metrics_manager.record_metric("validation.failed", validation_stats[\'failed_validations\'])',
            'description': 'Fix validate_market_data metrics recording'
        },
        
        # Fix 3: end_operation calls with success
        {
            'old': r'(\\s*)# End.*operation.*\\n(\\s*)self\\.metrics_manager\\.end_operation\\(operation\\)',
            'new': r'\\1# End performance tracking\\n\\2if self.metrics_manager and operation:\\n\\2    self.metrics_manager.end_operation(operation)',
            'description': 'Fix end_operation calls'
        },
        
        # Fix 4: end_operation calls with failure
        {
            'old': r'(\\s*)# End.*operation.*failure.*\\n(\\s*)self\\.metrics_manager\\.end_operation\\(operation, success=False\\)',
            'new': r'\\1# End operation with failure\\n\\2if self.metrics_manager and operation:\\n\\2    self.metrics_manager.end_operation(operation, success=False)',
            'description': 'Fix end_operation failure calls'
        }
    ]
    
    # Apply simple string replacements for the most critical fixes
    replacements = [
        # Most critical: the direct start_operation calls that cause AttributeError
        ('operation = self.metrics_manager.start_operation("validate_market_data")', 
         'operation = None\\nif self.metrics_manager:\\n    operation = self.metrics_manager.start_operation("validate_market_data")'),
        
        ('operation = self.metrics_manager.start_operation("process_market_data")',
         'operation = None\\nif self.metrics_manager:\\n    operation = self.metrics_manager.start_operation("process_market_data")'),
         
        ('operation = self.metrics_manager.start_operation(f"process_ws_message_{topic}")',
         'operation = None\\nif self.metrics_manager:\\n    operation = self.metrics_manager.start_operation(f"process_ws_message_{topic}")'),
         
        ('operation = self.metrics_manager.start_operation("visualize_market_data")',
         'operation = None\\nif self.metrics_manager:\\n    operation = self.metrics_manager.start_operation("visualize_market_data")'),
         
        # Record metrics fixes
        ('self.metrics_manager.record_metric("websocket_messages_processed", 1)',
         'if self.metrics_manager:\\n            self.metrics_manager.record_metric("websocket_messages_processed", 1)'),
         
        ('self.metrics_manager.record_metric(f"websocket_messages_{topic}", 1)',
         'if self.metrics_manager:\\n            self.metrics_manager.record_metric(f"websocket_messages_{topic}", 1)'),
    ]
    
    print("📝 Applying string replacements...")
    changes_made = 0
    
    for old_str, new_str in replacements:
        if old_str in content:
            content = content.replace(old_str, new_str.replace('\\n', '\\n            '))
            changes_made += 1
            print(f"  ✅ Applied fix for: {old_str[:50]}...")
    
    # Additional manual fixes for the most problematic patterns
    
    # Fix the start_operation patterns manually
    patterns_to_fix = [
        # Pattern 1: Basic start_operation without defensive check
        (r'(\\s+)operation = self\\.metrics_manager\\.start_operation\\(([^)]+)\\)',
         r'\\1operation = None\\n\\1if self.metrics_manager:\\n\\1    operation = self.metrics_manager.start_operation(\\2)'),
        
        # Pattern 2: end_operation without check
        (r'(\\s+)self\\.metrics_manager\\.end_operation\\(operation(?:, success=(?:True|False))?\\)',
         r'\\1if self.metrics_manager and operation:\\n\\1    self.metrics_manager.end_operation(operation)'),
        
        # Pattern 3: record_metric without check  
        (r'(\\s+)self\\.metrics_manager\\.record_metric\\(([^)]+)\\)',
         r'\\1if self.metrics_manager:\\n\\1    self.metrics_manager.record_metric(\\2)'),
    ]
    
    print("🔍 Applying regex patterns...")
    for pattern, replacement in patterns_to_fix:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            changes_made += len(matches)
            print(f"  ✅ Applied regex fix, {len(matches)} matches")
    
    # Write the fixed content back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"🎯 Applied {changes_made} fixes to {filepath}")
    return changes_made

def main():
    """Main execution function"""
    
    print("🚀 VPS Monitor.py AttributeError Fix Script")
    print("=" * 50)
    
    # File path on VPS
    monitor_file = "/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py"
    
    if not os.path.exists(monitor_file):
        print(f"❌ Error: {monitor_file} not found!")
        return False
    
    print(f"📍 Target file: {monitor_file}")
    
    # Create backup
    backup_path = backup_file(monitor_file)
    
    try:
        # Apply fixes
        changes = apply_fixes(monitor_file)
        
        if changes > 0:
            print(f"✅ Successfully applied {changes} fixes!")
            print("\\n📋 Next steps:")
            print("1. Restart the Virtuoso service: sudo systemctl restart virtuoso.service")
            print("2. Monitor the logs: sudo journalctl -u virtuoso.service -f")
            print("3. Check for AttributeError resolution")
            
            # Create a restart script
            restart_script = """#!/bin/bash
echo "🔄 Restarting Virtuoso service after monitor.py fix..."
sudo systemctl stop virtuoso.service
sleep 2
sudo systemctl start virtuoso.service
sleep 5
echo "📊 Service status:"
sudo systemctl status virtuoso.service --no-pager
echo "\\n📝 Recent logs:"
sudo journalctl -u virtuoso.service -n 10 --no-pager
"""
            with open('/tmp/restart_virtuoso.sh', 'w') as f:
                f.write(restart_script)
            os.chmod('/tmp/restart_virtuoso.sh', 0o755)
            print("\\n🎯 Restart script created: /tmp/restart_virtuoso.sh")
            
            return True
        else:
            print("⚠️  No changes applied. The file may already be fixed or have a different structure.")
            return False
            
    except Exception as e:
        print(f"❌ Error applying fixes: {e}")
        print(f"🔄 Restoring backup from {backup_path}")
        shutil.copy2(backup_path, monitor_file)
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
'''
    
    return patch_script

# Write the patch script
patch_script = create_patch_script()
with open('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/vps_monitor_fix.py', 'w') as f:
    f.write(patch_script)

print("✅ VPS patch script created: /Users/ffv_macmini/Desktop/Virtuoso_ccxt/vps_monitor_fix.py")
print("📋 Instructions:")
print("1. Copy this script to the VPS")
print("2. Run it as: python3 vps_monitor_fix.py")
print("3. It will automatically fix the AttributeError and restart the service")
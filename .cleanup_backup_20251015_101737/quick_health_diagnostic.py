#!/usr/bin/env python3
"""
Quick Health Check Diagnostic Script
Adds diagnostic logging to existing health check to identify warning triggers
"""

import os
import shutil
from datetime import datetime

def create_quick_patch():
    """Create a minimal patch that just adds diagnostic logging around the existing health check."""

    patch_script = '''
# Quick Health Diagnostic Patch
import re
import shutil
from datetime import datetime

def apply_quick_diagnostic_patch():
    """Apply minimal diagnostic patch to add detailed logging."""

    monitor_file = "/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py"
    backup_file = f"{monitor_file}.backup_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"Creating backup: {backup_file}")
    shutil.copy2(monitor_file, backup_file)

    # Read the file
    with open(monitor_file, 'r') as f:
        content = f.read()

    # Find the health check section and add diagnostic logging
    original_health_check = '''                # Check system health
                health_status = await self._check_system_health()
                if health_status['status'] != 'healthy':
                    self.logger.warning(f"System health check: {health_status['status']}")
                    await self._handle_health_issues(health_status)'''

    enhanced_health_check = '''                # Check system health with enhanced diagnostics
                health_status = await self._check_system_health()

                # DIAGNOSTIC LOGGING - Log detailed health status
                self.logger.debug(f"🔍 Health Check Result: {health_status}")

                if health_status.get('components'):
                    for component_name, component_data in health_status['components'].items():
                        if isinstance(component_data, dict):
                            comp_status = component_data.get('status', 'unknown')
                            comp_message = component_data.get('message', 'No message')
                            if comp_status != 'healthy':
                                self.logger.warning(f"⚠️  Component '{component_name}' status: {comp_status} - {comp_message}")
                            else:
                                self.logger.debug(f"✅ Component '{component_name}': {comp_status}")
                        else:
                            self.logger.debug(f"📊 Component '{component_name}': {component_data}")

                if health_status['status'] != 'healthy':
                    # Enhanced warning with specific details about what triggered it
                    warning_components = []
                    if health_status.get('components'):
                        for comp_name, comp_data in health_status['components'].items():
                            if isinstance(comp_data, dict) and comp_data.get('status') not in ['healthy', None]:
                                warning_components.append(f"{comp_name}:{comp_data.get('status')}")

                    warning_details = f" (triggered by: {', '.join(warning_components)})" if warning_components else ""
                    self.logger.warning(f"🚨 System health check: {health_status['status']}{warning_details}")

                    # Log full health status for debugging
                    import json
                    self.logger.warning(f"📊 Full health status: {json.dumps(health_status, indent=2, default=str)}")

                    await self._handle_health_issues(health_status)
                else:
                    self.logger.debug(f"✅ System health check: {health_status['status']}")'''

    # Replace the health check section
    if original_health_check in content:
        new_content = content.replace(original_health_check, enhanced_health_check)

        # Write the patched file
        with open(monitor_file, 'w') as f:
            f.write(new_content)

        print("✅ Quick diagnostic patch applied successfully!")
        print(f"📝 Original file backed up to: {backup_file}")
        print("🔄 Restart the trading service to see detailed health diagnostics")
        return True
    else:
        print("❌ Could not find the target health check code to patch")
        print("📝 File content around health check:")

        # Show context around health check
        lines = content.split('\\n')
        for i, line in enumerate(lines):
            if 'health_status = await self._check_system_health()' in line:
                start = max(0, i-5)
                end = min(len(lines), i+10)
                print(f"\\nLines {start}-{end}:")
                for j in range(start, end):
                    marker = " >>> " if j == i else "     "
                    print(f"{marker}{j:4d}: {lines[j]}")
                break
        return False

if __name__ == "__main__":
    success = apply_quick_diagnostic_patch()
    if success:
        print("\\n🎯 Next: Restart trading service and check logs for detailed health diagnostics")
    else:
        print("\\n❌ Manual intervention required - check the file structure")
'''

    return patch_script

# Save the quick patch
with open("/Users/ffv_macmini/Desktop/Virtuoso_ccxt/quick_health_diagnostic.py", "w") as f:
    f.write(create_quick_patch())

print("✅ Quick Health Diagnostic Script Created!")
print("This script will add detailed logging to identify exactly what triggers health warnings.")
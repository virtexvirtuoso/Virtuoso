#!/usr/bin/env python3
"""
Apply Health Check Diagnostics
Adds detailed logging around health checks to identify warning triggers
"""

import shutil
from datetime import datetime

def apply_diagnostics():
    """Apply diagnostic logging to monitor.py."""

    monitor_file = "/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py"
    backup_file = f"{monitor_file}.backup_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"Creating backup: {backup_file}")
    shutil.copy2(monitor_file, backup_file)

    # Read the file
    with open(monitor_file, 'r') as f:
        content = f.read()

    # Target section to replace
    target = '''                # Check system health
                health_status = await self._check_system_health()
                if health_status['status'] != 'healthy':
                    self.logger.warning(f"System health check: {health_status['status']}")
                    await self._handle_health_issues(health_status)'''

    # Replacement with diagnostics
    replacement = '''                # Check system health with enhanced diagnostics
                health_status = await self._check_system_health()

                # DIAGNOSTIC: Log detailed health status
                self.logger.debug(f"🔍 HEALTH CHECK: Full result = {health_status}")

                # DIAGNOSTIC: Check individual components
                if health_status.get('components'):
                    for comp_name, comp_data in health_status['components'].items():
                        if isinstance(comp_data, dict):
                            comp_status = comp_data.get('status', 'unknown')
                            comp_message = comp_data.get('message', 'No message')
                            if comp_status != 'healthy':
                                self.logger.warning(f"⚠️  DIAGNOSTIC: Component '{comp_name}' = {comp_status} ({comp_message})")
                            else:
                                self.logger.debug(f"✅ DIAGNOSTIC: Component '{comp_name}' = healthy")

                if health_status['status'] != 'healthy':
                    # Enhanced warning with component details
                    warning_components = []
                    if health_status.get('components'):
                        for comp_name, comp_data in health_status['components'].items():
                            if isinstance(comp_data, dict):
                                comp_status = comp_data.get('status', 'unknown')
                                if comp_status not in ['healthy', None]:
                                    warning_components.append(f"{comp_name}({comp_status})")

                    trigger_info = f" [Triggered by: {', '.join(warning_components)}]" if warning_components else " [Unknown trigger]"
                    self.logger.warning(f"🚨 DIAGNOSTIC: System health check: {health_status['status']}{trigger_info}")

                    # Log raw health data for analysis
                    import json
                    try:
                        health_json = json.dumps(health_status, indent=2, default=str)
                        self.logger.warning(f"📊 DIAGNOSTIC: Raw health data:\\n{health_json}")
                    except Exception as json_err:
                        self.logger.warning(f"📊 DIAGNOSTIC: Raw health data (non-JSON): {health_status}")

                    await self._handle_health_issues(health_status)
                else:
                    self.logger.debug(f"✅ DIAGNOSTIC: System health = {health_status['status']}")'''

    # Apply replacement
    if target in content:
        new_content = content.replace(target, replacement)

        # Write patched file
        with open(monitor_file, 'w') as f:
            f.write(new_content)

        print("✅ Health check diagnostics applied successfully!")
        print(f"📝 Original backed up to: {backup_file}")
        print("🔄 Restart service to activate enhanced health diagnostics")
        return True
    else:
        print("❌ Target health check code not found")

        # Show what we're looking for
        lines = content.split('\\n')
        for i, line in enumerate(lines):
            if 'health_status = await self._check_system_health()' in line:
                start = max(0, i-3)
                end = min(len(lines), i+8)
                print(f"\\nFound health check at line {i}, showing context:")
                for j in range(start, end):
                    prefix = " >>> " if j == i else "     "
                    print(f"{prefix}{j:4d}: {lines[j]}")
                break
        return False

if __name__ == "__main__":
    success = apply_diagnostics()
    if success:
        print("\\n🎯 Ready! Restart trading service to see detailed health diagnostics")
        print("📋 The logs will now show exactly what triggers health warnings")
    else:
        print("\\n❌ Could not apply patch - manual review needed")
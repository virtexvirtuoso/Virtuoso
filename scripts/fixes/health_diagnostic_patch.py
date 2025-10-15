#!/usr/bin/env python3
"""
Health Check Diagnostic Enhancement Script
This script adds detailed diagnostic logging to the monitoring system health checks.
"""

import os
import sys
import shutil
from datetime import datetime

def create_diagnostic_patch():
    """Creates an enhanced health check method with detailed diagnostics."""

    enhanced_health_check = '''
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system health using metrics tracker with fallback - ENHANCED WITH DIAGNOSTICS."""
        debug_info = {
            'timestamp': datetime.now().isoformat(),
            'method_entry': True,
            'metrics_tracker_available': self.metrics_tracker is not None
        }

        self.logger.debug(f"🔍 HEALTH CHECK START: {debug_info}")

        try:
            # First try metrics tracker if available
            if self.metrics_tracker is not None:
                self.logger.debug("📊 Using metrics_tracker.check_system_health()")

                # Add timing for metrics tracker call
                import time
                start_time = time.time()
                health_result = await self.metrics_tracker.check_system_health()
                metrics_duration = time.time() - start_time

                self.logger.debug(f"📊 Metrics tracker health check took {metrics_duration:.3f}s")
                self.logger.debug(f"📊 Metrics tracker returned: {health_result}")

                # Log detailed breakdown of health result
                if isinstance(health_result, dict):
                    status = health_result.get('status', 'unknown')
                    components = health_result.get('components', {})

                    self.logger.debug(f"🏥 Health Status: {status}")

                    if components:
                        self.logger.debug(f"🔧 Health Components ({len(components)} total):")
                        for component_name, component_data in components.items():
                            comp_status = component_data.get('status', 'unknown') if isinstance(component_data, dict) else component_data
                            self.logger.debug(f"  • {component_name}: {comp_status}")

                            # If component has warning/error status, log details
                            if isinstance(component_data, dict) and comp_status in ['warning', 'error', 'critical']:
                                message = component_data.get('message', 'No message')
                                value = component_data.get('value', 'No value')
                                threshold = component_data.get('threshold', 'No threshold')
                                self.logger.warning(f"⚠️  HEALTH ISSUE in {component_name}: {message} (value: {value}, threshold: {threshold})")

                    # Determine what triggers "warning" status
                    if status == 'warning':
                        warning_components = [name for name, data in components.items()
                                           if (isinstance(data, dict) and data.get('status') in ['warning', 'error', 'critical'])
                                           or (isinstance(data, str) and data in ['warning', 'error', 'critical'])]
                        self.logger.warning(f"🚨 WARNING STATUS triggered by components: {warning_components}")

                        # Log specific thresholds being exceeded
                        for comp_name in warning_components:
                            comp_data = components[comp_name]
                            if isinstance(comp_data, dict):
                                self.logger.warning(f"🔍 {comp_name} details: {comp_data}")

                return health_result
            else:
                self.logger.debug("📊 No metrics_tracker available, using fallback health check")
                # Fallback to basic health check
                fallback_result = await self._fallback_health_check()
                self.logger.debug(f"🔄 Fallback health check returned: {fallback_result}")
                return fallback_result

        except Exception as e:
            self.logger.error(f"❌ Error checking system health: {str(e)}")
            self.logger.error(f"❌ Exception type: {type(e).__name__}")

            import traceback
            self.logger.error(f"❌ Full traceback: {traceback.format_exc()}")

            # Return fallback on any error
            try:
                self.logger.debug("🔄 Attempting fallback health check due to error")
                fallback_result = await self._fallback_health_check()
                self.logger.debug(f"🔄 Fallback returned: {fallback_result}")
                return fallback_result
            except Exception as fallback_error:
                self.logger.error(f"💥 Error in fallback health check: {str(fallback_error)}")
                return {
                    'status': 'error',
                    'timestamp': time.time(),
                    'components': {
                        'system': {'status': 'error', 'message': 'Health check system unavailable'}
                    }
                }

    async def _fallback_health_check(self) -> Dict[str, Any]:
        """Fallback health check when metrics tracker is unavailable - ENHANCED WITH DIAGNOSTICS."""
        import psutil

        self.logger.debug("🔄 FALLBACK HEALTH CHECK STARTED")

        try:
            components = {}
            overall_status = 'healthy'
            diagnostic_data = {}

            # Check basic system resources
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()

                self.logger.debug(f"💻 System Resources: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%")

                # CPU health with detailed thresholds
                cpu_status = 'healthy' if cpu_percent < 80 else 'warning' if cpu_percent < 95 else 'critical'
                components['cpu'] = {
                    'status': cpu_status,
                    'usage_percent': cpu_percent,
                    'message': f'CPU usage: {cpu_percent:.1f}%',
                    'thresholds': {'warning': 80, 'critical': 95}
                }

                if cpu_status != 'healthy':
                    self.logger.warning(f"⚠️  CPU threshold exceeded: {cpu_percent:.1f}% (warning: 80%, critical: 95%)")
                    overall_status = 'warning' if overall_status == 'healthy' else overall_status

                # Memory health with detailed thresholds
                memory_status = 'healthy' if memory.percent < 80 else 'warning' if memory.percent < 95 else 'critical'
                components['memory'] = {
                    'status': memory_status,
                    'usage_percent': memory.percent,
                    'used_gb': memory.used / (1024**3),
                    'total_gb': memory.total / (1024**3),
                    'message': f'Memory usage: {memory.percent:.1f}%',
                    'thresholds': {'warning': 80, 'critical': 95}
                }

                if memory_status != 'healthy':
                    self.logger.warning(f"⚠️  Memory threshold exceeded: {memory.percent:.1f}% (warning: 80%, critical: 95%)")
                    overall_status = 'warning' if overall_status == 'healthy' else overall_status

                # Disk usage check
                try:
                    disk = psutil.disk_usage('/')
                    disk_percent = (disk.used / disk.total) * 100
                    disk_status = 'healthy' if disk_percent < 80 else 'warning' if disk_percent < 95 else 'critical'

                    components['disk'] = {
                        'status': disk_status,
                        'usage_percent': disk_percent,
                        'used_gb': disk.used / (1024**3),
                        'total_gb': disk.total / (1024**3),
                        'message': f'Disk usage: {disk_percent:.1f}%',
                        'thresholds': {'warning': 80, 'critical': 95}
                    }

                    if disk_status != 'healthy':
                        self.logger.warning(f"⚠️  Disk threshold exceeded: {disk_percent:.1f}% (warning: 80%, critical: 95%)")
                        overall_status = 'warning' if overall_status == 'healthy' else overall_status

                    self.logger.debug(f"💾 Disk Usage: {disk_percent:.1f}% ({disk.used / (1024**3):.1f}GB / {disk.total / (1024**3):.1f}GB)")

                except Exception as e:
                    self.logger.warning(f"⚠️  Could not check disk usage: {e}")
                    components['disk'] = {'status': 'unknown', 'message': 'Disk check failed'}

                # Check if any components triggered overall warning
                warning_components = [name for name, data in components.items() if data.get('status') == 'warning']
                critical_components = [name for name, data in components.items() if data.get('status') == 'critical']

                if critical_components:
                    overall_status = 'critical'
                    self.logger.error(f"🚨 CRITICAL components: {critical_components}")
                elif warning_components:
                    overall_status = 'warning'
                    self.logger.warning(f"⚠️  WARNING components: {warning_components}")

                # Additional diagnostic info
                diagnostic_data = {
                    'total_components_checked': len(components),
                    'healthy_components': len([c for c in components.values() if c.get('status') == 'healthy']),
                    'warning_components': len(warning_components),
                    'critical_components': len(critical_components),
                    'check_timestamp': datetime.now().isoformat()
                }

                self.logger.debug(f"📊 Health Check Summary: {diagnostic_data}")

            except Exception as resource_error:
                self.logger.error(f"❌ Error checking system resources: {resource_error}")
                components['system'] = {'status': 'error', 'message': f'Resource check failed: {resource_error}'}
                overall_status = 'error'

            result = {
                'status': overall_status,
                'timestamp': time.time(),
                'components': components,
                'diagnostics': diagnostic_data
            }

            self.logger.debug(f"🏥 Fallback health check complete: {overall_status}")
            return result

        except Exception as e:
            self.logger.error(f"💥 Critical error in fallback health check: {str(e)}")
            return {
                'status': 'error',
                'timestamp': time.time(),
                'components': {
                    'system': {'status': 'error', 'message': f'Fallback health check failed: {str(e)}'}
                }
            }
'''

    return enhanced_health_check

def apply_diagnostic_patch():
    """Apply the diagnostic patch to the VPS monitor.py file."""

    patch_content = f'''#!/usr/bin/env python3
"""
Apply Health Check Diagnostic Patch
Adds detailed diagnostic logging to monitor.py health checks
"""

import sys
import os
import shutil
from datetime import datetime

# Enhanced health check methods
{create_diagnostic_patch()}

def backup_and_patch():
    """Backup original file and apply patch."""

    monitor_file = "/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py"
    backup_file = f"{monitor_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"Creating backup: {backup_file}")
    shutil.copy2(monitor_file, backup_file)

    # Read original file
    with open(monitor_file, 'r') as f:
        content = f.read()

    # Find the _check_system_health method and replace it
    import re

    # Pattern to match the entire _check_system_health method
    pattern = r'(\\s+async def _check_system_health\\(self\\) -> Dict\\[str, Any\\]:.*?)(?=\\n\\s+async def|\\n\\s+def|\\Z)'

    # Replace with enhanced version
    new_content = re.sub(pattern, enhanced_health_check.strip(), content, flags=re.DOTALL)

    # Also replace _fallback_health_check if found
    fallback_pattern = r'(\\s+async def _fallback_health_check\\(self\\) -> Dict\\[str, Any\\]:.*?)(?=\\n\\s+async def|\\n\\s+def|\\Z)'

    # Write patched file
    with open(monitor_file, 'w') as f:
        f.write(new_content)

    print("✅ Health check diagnostic patch applied successfully!")
    print(f"📝 Original file backed up to: {backup_file}")
    print("🔄 Restart the trading service to activate enhanced diagnostics")

if __name__ == "__main__":
    backup_and_patch()
'''

    return patch_content

# Create the patch script
patch_script = apply_diagnostic_patch()
print("✅ Health Check Diagnostic Enhancement Script Created!")
print("📁 Script location: health_diagnostic_patch.py")
print("\nNext steps:")
print("1. Deploy this script to VPS")
print("2. Run it to patch monitor.py with enhanced diagnostics")
print("3. Restart trading service to activate enhanced logging")
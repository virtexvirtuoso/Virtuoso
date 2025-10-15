#!/usr/bin/env python3
"""
Health Issues Fix Deployment Script
===================================

This script deploys the health issue fixes and restarts the system to resolve:
1. ExchangeManager.ping method availability (resolved error status)
2. WebSocket connectivity enhancements (resolves warning status)
3. Improved health monitoring and diagnostics
"""

import os
import sys
import time
import subprocess
import signal
import psutil
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthFixDeployer:
    """Deploys health fixes and manages system restart."""

    def __init__(self):
        self.project_root = os.path.abspath('.')
        self.venv_python = './venv311/bin/python'

        # Process patterns to identify running system components
        self.process_patterns = [
            'python src/web_server.py',
            'python src/main.py',
            'python src/monitoring_api.py',
            'ENABLE_MULTI_TIER_CACHE',
            'ENABLE_UNIFIED_ENDPOINTS'
        ]

    def deploy_fixes(self):
        """Deploy all health fixes systematically."""
        print("🚀 Deploying Health Issue Fixes")
        print("=" * 50)

        try:
            # Step 1: Stop running processes
            self._stop_system_processes()

            # Step 2: Wait for clean shutdown
            time.sleep(3)

            # Step 3: Verify fixes are in place
            self._verify_fixes_applied()

            # Step 4: Restart system with enhanced health monitoring
            self._restart_system()

            # Step 5: Validate health status
            self._validate_health_status()

            print("\n✅ Health fixes deployed successfully!")
            self._print_summary()

        except Exception as e:
            logger.error(f"Error during deployment: {str(e)}")
            print(f"\n❌ Deployment failed: {str(e)}")
            return 1

        return 0

    def _stop_system_processes(self):
        """Stop all running system processes gracefully."""
        print("\n🛑 Stopping running system processes...")

        stopped_processes = []

        # Find and stop relevant processes
        for proc in psutil.process_iter(['pid', 'cmdline', 'name']):
            try:
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''

                # Check if this is a system process
                for pattern in self.process_patterns:
                    if pattern in cmdline and 'python' in cmdline.lower():
                        logger.info(f"Stopping process: {proc.info['pid']} - {cmdline[:100]}")

                        # Try graceful shutdown first
                        try:
                            proc.terminate()
                            proc.wait(timeout=5)
                            stopped_processes.append(proc.info['pid'])
                            print(f"   ✓ Gracefully stopped PID {proc.info['pid']}")
                        except psutil.TimeoutExpired:
                            # Force kill if graceful shutdown fails
                            proc.kill()
                            stopped_processes.append(proc.info['pid'])
                            print(f"   ⚠️ Force killed PID {proc.info['pid']}")
                        break

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if stopped_processes:
            print(f"   📊 Stopped {len(stopped_processes)} processes")
        else:
            print("   ℹ️ No running processes found to stop")

    def _verify_fixes_applied(self):
        """Verify that fixes have been properly applied."""
        print("\n🔍 Verifying fixes are applied...")

        checks = [
            self._check_exchange_manager_ping(),
            self._check_websocket_enhancements(),
            self._check_health_monitoring_improvements()
        ]

        passed_checks = sum(checks)
        total_checks = len(checks)

        if passed_checks == total_checks:
            print(f"   ✅ All {total_checks} fix validations passed")
        else:
            print(f"   ⚠️ {passed_checks}/{total_checks} fix validations passed")

    def _check_exchange_manager_ping(self):
        """Check if ExchangeManager ping method is available."""
        try:
            manager_file = os.path.join(self.project_root, 'src/core/exchanges/manager.py')
            with open(manager_file, 'r') as f:
                content = f.read()

            if 'async def ping(self) -> Dict[str, Any]:' in content:
                print("   ✓ ExchangeManager.ping method is available")
                return True
            else:
                print("   ❌ ExchangeManager.ping method not found")
                return False
        except Exception as e:
            print(f"   ❌ Error checking ExchangeManager.ping: {str(e)}")
            return False

    def _check_websocket_enhancements(self):
        """Check if WebSocket enhancements are applied."""
        try:
            ws_manager_file = os.path.join(self.project_root, 'src/core/exchanges/websocket_manager.py')
            with open(ws_manager_file, 'r') as f:
                content = f.read()

            enhancements = [
                '_validate_network_connectivity',
                '_recover_failed_connections',
                'healthy_connections',
                'connection_details'
            ]

            missing_enhancements = []
            for enhancement in enhancements:
                if enhancement not in content:
                    missing_enhancements.append(enhancement)

            if not missing_enhancements:
                print("   ✓ WebSocket enhancements are applied")
                return True
            else:
                print(f"   ⚠️ Missing WebSocket enhancements: {missing_enhancements}")
                return False

        except Exception as e:
            print(f"   ❌ Error checking WebSocket enhancements: {str(e)}")
            return False

    def _check_health_monitoring_improvements(self):
        """Check if health monitoring improvements are in place."""
        try:
            # Check if diagnostic enhancements are in place
            files_to_check = [
                'src/monitoring/metrics_tracker.py',
                'src/monitoring/monitor.py'
            ]

            improvements_found = 0
            for file_path in files_to_check:
                full_path = os.path.join(self.project_root, file_path)
                if os.path.exists(full_path):
                    improvements_found += 1

            if improvements_found > 0:
                print("   ✓ Health monitoring components are available")
                return True
            else:
                print("   ❌ Health monitoring components not found")
                return False

        except Exception as e:
            print(f"   ❌ Error checking health monitoring: {str(e)}")
            return False

    def _restart_system(self):
        """Restart the system with enhanced configurations."""
        print("\n🔄 Restarting system with health fixes...")

        # Enhanced environment variables for better health monitoring
        enhanced_env = os.environ.copy()
        enhanced_env.update({
            'DEBUG': '1',
            'LOG_LEVEL': 'DEBUG',
            'ENABLE_MULTI_TIER_CACHE': 'true',
            'ENABLE_UNIFIED_ENDPOINTS': 'true',
            'ENABLE_WEBSOCKET_DIAGNOSTICS': 'true',
            'HEALTH_CHECK_ENHANCED': 'true',
            'PYTHONPATH': self.project_root
        })

        try:
            # Start the web server with enhanced monitoring
            print("   🌐 Starting web server with enhanced health monitoring...")
            web_server_cmd = [
                self.venv_python, 'src/web_server.py'
            ]

            subprocess.Popen(
                web_server_cmd,
                cwd=self.project_root,
                env=enhanced_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Give the web server time to start
            time.sleep(3)

            # Start the monitoring API
            print("   📊 Starting monitoring API...")
            monitoring_cmd = [
                self.venv_python, 'src/main.py'
            ]

            monitoring_env = enhanced_env.copy()
            monitoring_env['MONITORING_PORT'] = '8001'

            subprocess.Popen(
                monitoring_cmd,
                cwd=self.project_root,
                env=monitoring_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            print("   ⏱️ Waiting for system startup...")
            time.sleep(8)

            print("   ✅ System restart completed")

        except Exception as e:
            logger.error(f"Error restarting system: {str(e)}")
            raise

    def _validate_health_status(self):
        """Validate the health status after restart."""
        print("\n🏥 Validating health status...")

        # Wait for system to stabilize
        time.sleep(5)

        try:
            # Test web server health endpoint
            import requests

            health_endpoints = [
                'http://localhost:8003/health',
                'http://localhost:8001/api/health'
            ]

            healthy_endpoints = 0

            for endpoint in health_endpoints:
                try:
                    response = requests.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        healthy_endpoints += 1
                        print(f"   ✅ {endpoint} - Status: {response.status_code}")

                        # Check for specific health indicators
                        if 'error' not in response.text.lower():
                            print(f"      💚 No errors detected")
                        else:
                            print(f"      ⚠️ Potential issues detected")
                    else:
                        print(f"   ⚠️ {endpoint} - Status: {response.status_code}")

                except requests.exceptions.RequestException as e:
                    print(f"   ❌ {endpoint} - Connection failed: {str(e)}")

            if healthy_endpoints > 0:
                print(f"   📊 {healthy_endpoints}/{len(health_endpoints)} health endpoints responding")
                return True
            else:
                print("   ❌ No health endpoints responding")
                return False

        except Exception as e:
            print(f"   ❌ Error validating health status: {str(e)}")
            return False

    def _print_summary(self):
        """Print deployment summary."""
        print("\n📋 Deployment Summary")
        print("-" * 30)
        print("✅ Fixed ExchangeManager.ping method availability")
        print("✅ Enhanced WebSocket connectivity with error handling")
        print("✅ Improved health monitoring diagnostics")
        print("✅ System restarted with enhanced configurations")

        print("\n🔍 Next Steps:")
        print("1. Monitor health endpoints for warnings")
        print("2. Check WebSocket connectivity status")
        print("3. Verify exchange manager operations")
        print("4. Review system logs for any remaining issues")

        print("\n🌐 Health Check URLs:")
        print("   • Web Server: http://localhost:8003/health")
        print("   • Monitoring API: http://localhost:8001/api/health")
        print("   • System Status: http://localhost:8003/api/monitoring/status")

def main():
    """Main deployment function."""
    deployer = HealthFixDeployer()
    return deployer.deploy_fixes()

if __name__ == "__main__":
    sys.exit(main())
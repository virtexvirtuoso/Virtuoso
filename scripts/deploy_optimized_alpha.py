#!/usr/bin/env python3
"""
Optimized Alpha Scanner Deployment Script
Automated safe rollout to production
"""

import os
import sys
import time
import json
import logging
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import yaml

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.monitoring.alpha_integration_manager import AlphaIntegrationManager, ScannerMode
from src.monitoring.alpha_performance_monitor import AlphaPerformanceMonitor

class OptimizedAlphaDeployment:
    """
    Manages the safe deployment of optimized alpha scanning to production.
    
    Features:
    - Pre-deployment validation
    - Gradual rollout with monitoring
    - Automatic rollback on issues
    - Performance tracking
    - Deployment reporting
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize deployment manager."""
        self.config_path = config_path
        self.config = self._load_config()
        
        # Deployment state
        self.deployment_id = f"alpha_deploy_{int(time.time())}"
        self.deployment_start_time = None
        self.deployment_log = []
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Components
        self.integration_manager = None
        self.performance_monitor = None
        
        self.logger.info(f"Deployment {self.deployment_id} initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup deployment logging."""
        logger = logging.getLogger('alpha_deployment')
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler
        log_file = f"logs/deployment_{self.deployment_id}.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def _log_deployment_event(self, event_type: str, message: str, data: Optional[Dict] = None):
        """Log deployment event."""
        event = {
            'timestamp': datetime.now(timezone.utc),
            'deployment_id': self.deployment_id,
            'event_type': event_type,
            'message': message,
            'data': data or {}
        }
        
        self.deployment_log.append(event)
        self.logger.info(f"[{event_type}] {message}")
    
    def validate_pre_deployment(self) -> bool:
        """Validate system before deployment."""
        self.logger.info("Starting pre-deployment validation...")
        
        validation_checks = [
            self._check_config_validity,
            self._check_dependencies,
            self._check_system_resources,
            self._check_file_structure,
            self._check_monitoring_setup
        ]
        
        for check in validation_checks:
            try:
                check_name = check.__name__.replace('_check_', '').replace('_validate_', '')
                self.logger.info(f"Running validation: {check_name}")
                
                if not check():
                    self._log_deployment_event('validation_failed', f"Validation failed: {check_name}")
                    return False
                
                self._log_deployment_event('validation_passed', f"Validation passed: {check_name}")
                
            except Exception as e:
                self.logger.error(f"Validation error in {check.__name__}: {str(e)}")
                self._log_deployment_event('validation_error', f"Validation error: {check.__name__}", {'error': str(e)})
                return False
        
        self._log_deployment_event('validation_complete', "All pre-deployment validations passed")
        return True
    
    def _check_config_validity(self) -> bool:
        """Check configuration validity."""
        required_sections = ['alpha_scanning', 'alpha_scanning_optimized']
        
        for section in required_sections:
            if section not in self.config:
                self.logger.error(f"Missing required config section: {section}")
                return False
        
        # Check optimized config structure
        optimized_config = self.config['alpha_scanning_optimized']
        required_keys = ['alpha_tiers', 'pattern_weights', 'value_scoring', 'filtering', 'throttling']
        
        for key in required_keys:
            if key not in optimized_config:
                self.logger.error(f"Missing required optimized config key: {key}")
                return False
        
        return True
    
    def _check_dependencies(self) -> bool:
        """Check required dependencies."""
        required_packages = ['numpy', 'pandas', 'yaml']
        
        for package in required_packages:
            try:
                __import__(package)
                self.logger.info(f"✓ Package {package} available")
            except ImportError:
                self.logger.error(f"Missing required package: {package}")
                return False
        
        # Check optional packages
        optional_packages = ['psutil']
        for package in optional_packages:
            try:
                __import__(package)
                self.logger.info(f"✓ Optional package {package} available")
            except ImportError:
                self.logger.warning(f"Optional package {package} not available")
        
        return True
    
    def _check_system_resources(self) -> bool:
        """Check system resources."""
        try:
            import psutil
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.logger.info(f"CPU usage: {cpu_percent}%")
            if cpu_percent > 80:
                self.logger.warning(f"High CPU usage: {cpu_percent}%")
                return False
            
            # Check memory usage
            memory = psutil.virtual_memory()
            self.logger.info(f"Memory usage: {memory.percent}%")
            if memory.percent > 95:
                self.logger.warning(f"Critical memory usage: {memory.percent}%")
                return False
            
            # Check disk space
            disk = psutil.disk_usage('/')
            self.logger.info(f"Disk usage: {disk.percent}%")
            if disk.percent > 90:
                self.logger.warning(f"Low disk space: {disk.percent}% used")
                return False
            
            return True
            
        except ImportError:
            self.logger.warning("psutil not available - skipping system resource check")
            return True
        except Exception as e:
            self.logger.error(f"Error checking system resources: {str(e)}")
            return False
    
    def _check_file_structure(self) -> bool:
        """Check required file structure."""
        required_files = [
            'src/monitoring/optimized_alpha_scanner.py',
            'src/monitoring/alpha_integration_manager.py',
            'config/alpha_optimization.yaml'
        ]
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                self.logger.error(f"Missing required file: {file_path}")
                return False
            self.logger.info(f"✓ Found required file: {file_path}")
        
        return True
    
    def _check_database_connectivity(self) -> bool:
        """Check database connectivity."""
        # This would implement actual database connectivity check
        # For now, return True as placeholder
        return True
    
    def _check_legacy_scanner_health(self) -> bool:
        """Check legacy scanner health."""
        try:
            # Initialize integration manager in legacy mode
            test_config = self.config.copy()
            test_config['alpha_scanning_optimized']['enabled'] = False
            
            test_manager = AlphaIntegrationManager(test_config)
            
            # Test legacy scanner
            if test_manager.legacy_scanner is None:
                self.logger.error("Legacy scanner failed to initialize")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Legacy scanner health check failed: {str(e)}")
            return False
    
    def _validate_optimized_scanner(self) -> bool:
        """Validate optimized scanner."""
        try:
            from src.monitoring.optimized_alpha_scanner import OptimizedAlphaScanner
            
            # Test initialization
            scanner = OptimizedAlphaScanner()
            
            # Test basic functionality
            test_data = {
                'ETHUSDT': {
                    'beta_change': 0.5,
                    'beta': 1.3,
                    'volume_spike': True
                }
            }
            
            # This should not raise an exception
            results = scanner.scan_for_alpha_opportunities(test_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Optimized scanner validation failed: {str(e)}")
            return False
    
    def _check_monitoring_setup(self) -> bool:
        """Check monitoring setup."""
        # Check log directories exist
        log_dirs = ['logs', 'reports', 'exports']
        for log_dir in log_dirs:
            if not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir)
                except Exception as e:
                    self.logger.error(f"Cannot create log directory {log_dir}: {str(e)}")
                    return False
        
        return True
    
    def test_integration(self) -> bool:
        """Test the integration with current system."""
        self.logger.info("Testing integration with current system...")
        
        try:
            from src.monitoring.alpha_integration_manager import AlphaIntegrationManager
            
            # Test with current config
            manager = AlphaIntegrationManager(self.config)
            
            # Test basic functionality
            test_data = {
                'ETHUSDT': {
                    'price': 2000,
                    'volume': 1000000,
                    'beta_change': 0.3,
                    'correlation': 0.8
                },
                'BTCUSDT': {
                    'price': 45000,
                    'volume': 2000000,
                    'beta_change': 0.0,
                    'correlation': 1.0
                }
            }
            
            # This should not raise an exception
            import asyncio
            
            async def test_scan():
                return await manager.scan_for_opportunities(test_data)
            
            # Run the test
            results = asyncio.run(test_scan())
            
            self.logger.info(f"✓ Integration test passed - returned {len(results)} results")
            self._log_deployment_event('integration_test_passed', f"Integration test successful", {'result_count': len(results)})
            
            return True
            
        except Exception as e:
            self.logger.error(f"Integration test failed: {str(e)}")
            self._log_deployment_event('integration_test_failed', "Integration test failed", {'error': str(e)})
            return False
    
    def deploy_parallel_mode(self) -> bool:
        """Deploy in parallel mode for testing."""
        self.logger.info("Deploying in parallel mode...")
        
        try:
            from src.monitoring.alpha_integration_manager import AlphaIntegrationManager, ScannerMode
            from src.monitoring.alpha_performance_monitor import AlphaPerformanceMonitor
            
            # Update config to enable parallel mode
            self.config['alpha_scanning']['enabled'] = True
            self.config['alpha_scanning_optimized']['enabled'] = True
            
            # Initialize integration manager
            self.integration_manager = AlphaIntegrationManager(self.config)
            
            if self.integration_manager.mode != ScannerMode.PARALLEL:
                self.logger.error("Failed to initialize parallel mode")
                return False
            
            # Initialize performance monitor
            self.performance_monitor = AlphaPerformanceMonitor()
            
            self._save_config()
            
            self._log_deployment_event('parallel_mode_deployed', "Parallel mode successfully deployed")
            return True
            
        except Exception as e:
            self.logger.error(f"Parallel mode deployment failed: {str(e)}")
            self._log_deployment_event('parallel_mode_failed', "Parallel mode deployment failed", {'error': str(e)})
            return False
    
    def start_gradual_rollout(self, initial_percentage: int = 10) -> bool:
        """Start gradual rollout."""
        self.logger.info(f"Starting gradual rollout at {initial_percentage}%...")
        
        try:
            from src.monitoring.alpha_integration_manager import AlphaIntegrationManager, ScannerMode
            
            # Initialize integration manager if not already done
            if not self.integration_manager:
                self.integration_manager = AlphaIntegrationManager(self.config)
            
            # Update integration manager to gradual rollout mode
            self.integration_manager.mode = ScannerMode.GRADUAL_ROLLOUT
            self.integration_manager.rollout_percentage = initial_percentage
            
            # Update config
            self.config['alpha_scanning']['enabled'] = True
            self.config['alpha_scanning_optimized']['enabled'] = True
            
            if 'rollout' not in self.config:
                self.config['rollout'] = {}
            
            self.config['rollout']['enabled'] = True
            self.config['rollout']['percentage'] = initial_percentage
            self.config['rollout']['mode'] = 'gradual'
            
            self._save_config()
            
            self._log_deployment_event(
                'gradual_rollout_started', 
                f"Gradual rollout started at {initial_percentage}%",
                {'initial_percentage': initial_percentage}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Gradual rollout start failed: {str(e)}")
            self._log_deployment_event('gradual_rollout_failed', "Gradual rollout start failed", {'error': str(e)})
            return False
    
    def monitor_deployment(self, duration_hours: int = 24) -> bool:
        """Monitor deployment for specified duration."""
        self.logger.info(f"Monitoring deployment for {duration_hours} hours...")
        
        if not self.performance_monitor:
            self.logger.error("Performance monitor not initialized")
            return False
        
        try:
            # Start performance monitoring
            import asyncio
            
            async def monitoring_task():
                await self.performance_monitor.start_monitoring()
            
            # Run monitoring for specified duration
            end_time = time.time() + (duration_hours * 3600)
            
            while time.time() < end_time:
                # Check for critical alerts
                dashboard = self.performance_monitor.get_performance_dashboard()
                recent_alerts = dashboard.get('recent_alerts', [])
                
                critical_alerts = [
                    alert for alert in recent_alerts 
                    if alert.get('severity') == 'critical'
                ]
                
                if critical_alerts:
                    self.logger.warning(f"Critical alerts detected: {len(critical_alerts)}")
                    self._log_deployment_event(
                        'critical_alerts_detected',
                        f"Critical alerts detected during monitoring",
                        {'alert_count': len(critical_alerts), 'alerts': critical_alerts}
                    )
                    
                    # Consider automatic rollback
                    if len(critical_alerts) >= 3:  # 3 or more critical alerts
                        self.logger.critical("Multiple critical alerts - triggering rollback")
                        return self.rollback_deployment()
                
                # Log progress
                if int(time.time()) % 3600 == 0:  # Every hour
                    self._log_deployment_event(
                        'monitoring_progress',
                        f"Monitoring in progress - {(end_time - time.time()) / 3600:.1f} hours remaining"
                    )
                
                time.sleep(60)  # Check every minute
            
            self._log_deployment_event('monitoring_complete', f"Monitoring completed successfully after {duration_hours} hours")
            return True
            
        except Exception as e:
            self.logger.error(f"Monitoring failed: {str(e)}")
            self._log_deployment_event('monitoring_failed', "Deployment monitoring failed", {'error': str(e)})
            return False
    
    def complete_rollout(self) -> bool:
        """Complete rollout to 100% optimized scanner."""
        self.logger.info("Completing rollout to 100% optimized scanner...")
        
        try:
            from src.monitoring.alpha_integration_manager import AlphaIntegrationManager, ScannerMode
            
            # Initialize integration manager if not already done
            if not self.integration_manager:
                self.integration_manager = AlphaIntegrationManager(self.config)
            
            # Switch to optimized only mode
            self.integration_manager.mode = ScannerMode.OPTIMIZED_ONLY
            
            # Update config file
            self.config['alpha_scanning']['enabled'] = False
            self.config['alpha_scanning_optimized']['enabled'] = True
            
            # Update rollout config
            if 'rollout' not in self.config:
                self.config['rollout'] = {}
            
            self.config['rollout']['enabled'] = True
            self.config['rollout']['percentage'] = 100
            self.config['rollout']['mode'] = 'complete'
            
            self._save_config()
            
            self._log_deployment_event('rollout_complete', "Rollout completed - 100% optimized scanner")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollout completion failed: {str(e)}")
            self._log_deployment_event('rollout_completion_failed', "Rollout completion failed", {'error': str(e)})
            return False
    
    def rollback_deployment(self) -> bool:
        """Rollback to legacy scanner."""
        self.logger.warning("Rolling back to legacy scanner...")
        
        try:
            # Force rollback
            if self.integration_manager:
                self.integration_manager.force_rollback()
            
            # Update config
            self.config['alpha_scanning']['enabled'] = True
            self.config['alpha_scanning_optimized']['enabled'] = False
            
            self._save_config()
            
            self._log_deployment_event('rollback_complete', "Rollback to legacy scanner completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            self._log_deployment_event('rollback_failed', "Rollback failed", {'error': str(e)})
            return False
    
    def _save_config(self):
        """Save updated configuration."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
        except Exception as e:
            self.logger.error(f"Failed to save config: {str(e)}")
    
    def generate_deployment_report(self) -> Dict[str, Any]:
        """Generate deployment report."""
        report = {
            'deployment_id': self.deployment_id,
            'start_time': self.deployment_start_time,
            'end_time': datetime.now(timezone.utc),
            'duration_hours': (datetime.now(timezone.utc) - self.deployment_start_time).total_seconds() / 3600 if self.deployment_start_time else 0,
            'deployment_log': self.deployment_log,
            'final_status': self._get_final_status(),
            'performance_summary': self._get_performance_summary(),
            'recommendations': self._get_deployment_recommendations()
        }
        
        return report
    
    def _get_final_status(self) -> str:
        """Get final deployment status."""
        if not self.deployment_log:
            return 'unknown'
        
        last_event = self.deployment_log[-1]
        
        if 'rollback' in last_event['event_type']:
            return 'rolled_back'
        elif 'complete' in last_event['event_type']:
            return 'completed'
        elif 'failed' in last_event['event_type']:
            return 'failed'
        else:
            return 'in_progress'
    
    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.performance_monitor:
            return {}
        
        return self.performance_monitor.get_performance_dashboard()
    
    def _get_deployment_recommendations(self) -> List[str]:
        """Get deployment recommendations."""
        recommendations = []
        
        final_status = self._get_final_status()
        
        if final_status == 'completed':
            recommendations.append("Deployment completed successfully - monitor performance for next 48 hours")
        elif final_status == 'rolled_back':
            recommendations.append("Deployment was rolled back - review logs and address issues before retry")
        elif final_status == 'failed':
            recommendations.append("Deployment failed - review validation checks and system requirements")
        
        return recommendations
    
    def save_deployment_report(self, filename: Optional[str] = None):
        """Save deployment report to file."""
        if not filename:
            filename = f"reports/deployment_report_{self.deployment_id}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        report = self.generate_deployment_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Deployment report saved to {filename}")

def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description='Deploy Optimized Alpha Scanner')
    parser.add_argument('--config', default='config/config.yaml', help='Configuration file path')
    parser.add_argument('--mode', choices=['validate', 'parallel', 'test', 'gradual', 'complete', 'rollback'], 
                       default='validate', help='Deployment mode')
    parser.add_argument('--monitor-hours', type=int, default=24, help='Monitoring duration in hours')
    parser.add_argument('--initial-percentage', type=int, default=10, help='Initial rollout percentage')
    
    args = parser.parse_args()
    
    # Initialize deployment
    deployment = OptimizedAlphaDeployment(args.config)
    deployment.deployment_start_time = datetime.now(timezone.utc)
    
    try:
        if args.mode == 'validate':
            print("Running pre-deployment validation...")
            if deployment.validate_pre_deployment():
                print("✅ All validations passed - ready for deployment")
                sys.exit(0)
            else:
                print("❌ Validation failed - check logs for details")
                sys.exit(1)
        
        elif args.mode == 'parallel':
            print("Deploying in parallel mode...")
            if not deployment.validate_pre_deployment():
                print("❌ Pre-deployment validation failed")
                sys.exit(1)
            
            if deployment.deploy_parallel_mode():
                print("✅ Parallel mode deployed successfully")
                print(f"Monitor performance for {args.monitor_hours} hours before proceeding")
                print("\nNext step: python scripts/deploy_optimized_alpha.py --mode test")
            else:
                print("❌ Parallel mode deployment failed")
                sys.exit(1)
        
        elif args.mode == 'test':
            print("🧪 Testing integration...")
            if deployment.test_integration():
                print("✅ Integration test passed successfully")
                print("System is ready for gradual rollout")
                print(f"\nNext step: python scripts/deploy_optimized_alpha.py --mode gradual --initial-percentage {args.initial_percentage}")
            else:
                print("❌ Integration test failed")
                sys.exit(1)
        
        elif args.mode == 'gradual':
            print(f"Starting gradual rollout at {args.initial_percentage}%...")
            if deployment.start_gradual_rollout(args.initial_percentage):
                print("✅ Gradual rollout started")
                if deployment.monitor_deployment(args.monitor_hours):
                    print("✅ Monitoring completed successfully")
                else:
                    print("⚠️ Monitoring detected issues")
            else:
                print("❌ Gradual rollout failed")
                sys.exit(1)
        
        elif args.mode == 'complete':
            print("Completing rollout to 100% optimized scanner...")
            if deployment.complete_rollout():
                print("✅ Rollout completed successfully")
            else:
                print("❌ Rollout completion failed")
                sys.exit(1)
        
        elif args.mode == 'rollback':
            print("Rolling back to legacy scanner...")
            if deployment.rollback_deployment():
                print("✅ Rollback completed successfully")
            else:
                print("❌ Rollback failed")
                sys.exit(1)
    
    finally:
        # Always generate deployment report
        deployment.save_deployment_report()
        print(f"📊 Deployment report saved for {deployment.deployment_id}")

if __name__ == '__main__':
    main() 
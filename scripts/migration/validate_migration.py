#!/usr/bin/env python3
"""
Migration Validation Script for Phase 5 Production Deployment

This script validates that the migration from monolithic monitor.py to 
service-based architecture was successful and all functionality is preserved.
"""

import asyncio
import logging
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Any, Tuple
import importlib.util
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validation tool for Phase 5 migration."""
    
    def __init__(self):
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'validations': {},
            'overall_status': 'PENDING',
            'errors': [],
            'warnings': []
        }
        
    def validate_file_structure(self) -> bool:
        """Validate that all required files exist in the correct structure."""
        logger.info("Validating file structure...")
        
        required_files = [
            'src/monitoring/monitor.py',
            'src/monitoring/monitor_legacy_backup.py',
            'src/monitoring/services/__init__.py',
            'src/monitoring/services/monitoring_orchestration_service.py',
            'src/monitoring/components/__init__.py',
            'src/monitoring/utilities/__init__.py'
        ]
        
        missing_files = []
        present_files = []
        
        for file_path in required_files:
            full_path = Path(file_path)
            if full_path.exists():
                present_files.append(file_path)
            else:
                missing_files.append(file_path)
        
        result = {
            'present_files': present_files,
            'missing_files': missing_files,
            'success': len(missing_files) == 0
        }
        
        if missing_files:
            self.validation_results['errors'].append(f"Missing required files: {missing_files}")
        
        self.validation_results['validations']['file_structure'] = result
        return result['success']
    
    def validate_monitor_size_reduction(self) -> bool:
        """Validate that the new monitor.py is significantly smaller."""
        logger.info("Validating monitor.py size reduction...")
        
        new_monitor_path = Path('src/monitoring/monitor.py')
        legacy_monitor_path = Path('src/monitoring/monitor_legacy_backup.py')
        
        if not new_monitor_path.exists():
            self.validation_results['errors'].append("New monitor.py not found")
            return False
        
        if not legacy_monitor_path.exists():
            self.validation_results['warnings'].append("Legacy monitor backup not found for comparison")
            return True  # Not critical
        
        try:
            # Count lines in each file
            with open(new_monitor_path, 'r') as f:
                new_lines = sum(1 for _ in f)
            
            with open(legacy_monitor_path, 'r') as f:
                legacy_lines = sum(1 for _ in f)
            
            reduction_percentage = ((legacy_lines - new_lines) / legacy_lines) * 100
            
            result = {
                'new_lines': new_lines,
                'legacy_lines': legacy_lines,
                'reduction_percentage': round(reduction_percentage, 2),
                'success': reduction_percentage > 50  # Expect at least 50% reduction
            }
            
            if reduction_percentage < 50:
                self.validation_results['errors'].append(
                    f"Insufficient size reduction: {reduction_percentage:.1f}% (expected >50%)"
                )
            
            self.validation_results['validations']['size_reduction'] = result
            return result['success']
            
        except Exception as e:
            self.validation_results['errors'].append(f"Failed to validate size reduction: {str(e)}")
            return False
    
    def validate_imports(self) -> bool:
        """Validate that all imports work correctly."""
        logger.info("Validating imports...")
        
        import_tests = [
            ('src.monitoring.monitor', 'MarketMonitor'),
            ('src.monitoring.services', 'MonitoringOrchestrationService'),
            ('src.monitoring.components', 'WebSocketProcessor'),
            ('src.monitoring.components', 'MarketDataProcessor'),
            ('src.monitoring.components', 'SignalProcessor'),
            ('src.monitoring.utilities', 'MarketDataValidator'),
            ('src.monitoring.utilities', 'TimestampUtility')
        ]
        
        successful_imports = []
        failed_imports = []
        
        for module_name, class_name in import_tests:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, class_name):
                    successful_imports.append(f"{module_name}.{class_name}")
                else:
                    failed_imports.append(f"{module_name}.{class_name} - class not found")
            except Exception as e:
                failed_imports.append(f"{module_name}.{class_name} - {str(e)}")
        
        result = {
            'successful_imports': successful_imports,
            'failed_imports': failed_imports,
            'success': len(failed_imports) == 0
        }
        
        if failed_imports:
            self.validation_results['errors'].extend([f"Import failure: {imp}" for imp in failed_imports])
        
        self.validation_results['validations']['imports'] = result
        return result['success']
    
    async def validate_monitor_initialization(self) -> bool:
        """Validate that the new MarketMonitor can be initialized."""
        logger.info("Validating monitor initialization...")
        
        try:
            from src.monitoring.monitor import MarketMonitor
            
            # Create basic config
            test_config = {
                'market_data': {'cache_ttl': 60},
                'signal_processing': {'enable_pdf_reports': False},
                'monitoring': {'cycle_interval': 10}
            }
            
            # Try to initialize
            monitor = MarketMonitor(config=test_config, logger=logger)
            
            # Check that key attributes exist
            required_attributes = [
                'orchestration_service',
                'websocket_processor',
                'market_data_processor',
                'signal_processor',
                'whale_activity_monitor',
                'manipulation_monitor'
            ]
            
            missing_attributes = []
            for attr in required_attributes:
                if not hasattr(monitor, attr):
                    missing_attributes.append(attr)
            
            result = {
                'initialization_successful': True,
                'missing_attributes': missing_attributes,
                'has_required_methods': hasattr(monitor, 'start') and hasattr(monitor, 'stop'),
                'success': len(missing_attributes) == 0 and hasattr(monitor, 'start')
            }
            
            if missing_attributes:
                self.validation_results['errors'].append(f"Missing attributes: {missing_attributes}")
            
            self.validation_results['validations']['monitor_initialization'] = result
            return result['success']
            
        except Exception as e:
            error_msg = f"Monitor initialization failed: {str(e)}"
            self.validation_results['errors'].append(error_msg)
            self.validation_results['validations']['monitor_initialization'] = {
                'success': False,
                'error': error_msg
            }
            return False
    
    async def validate_service_orchestration(self) -> bool:
        """Validate that the orchestration service works correctly."""
        logger.info("Validating service orchestration...")
        
        try:
            from src.monitoring.services import MonitoringOrchestrationService
            from src.monitoring.components import (
                WebSocketProcessor, MarketDataProcessor, SignalProcessor,
                WhaleActivityMonitor, ManipulationMonitor
            )
            from src.monitoring.utilities import MarketDataValidator
            from unittest.mock import Mock
            
            # Create mock dependencies
            mock_config = {'monitoring': {'cycle_interval': 10}}
            mock_logger = Mock()
            mock_alert_manager = Mock()
            mock_top_symbols_manager = Mock()
            
            # Initialize components
            validator = MarketDataValidator(logger=mock_logger)
            websocket_processor = WebSocketProcessor(config=mock_config, logger=mock_logger)
            market_data_processor = MarketDataProcessor(
                config={}, logger=mock_logger, market_data_manager=Mock(), validator=validator
            )
            signal_processor = SignalProcessor(
                config={}, logger=mock_logger, signal_generator=Mock(),
                alert_manager=mock_alert_manager, market_data_manager=Mock(),
                database_client=Mock()
            )
            whale_monitor = WhaleActivityMonitor(
                config=mock_config, logger=mock_logger, alert_manager=mock_alert_manager
            )
            manipulation_monitor = ManipulationMonitor(
                config=mock_config, logger=mock_logger, alert_manager=mock_alert_manager,
                manipulation_detector=Mock(), database_client=Mock()
            )
            
            # Initialize orchestration service
            orchestration_service = MonitoringOrchestrationService(
                websocket_processor=websocket_processor,
                market_data_processor=market_data_processor,
                signal_processor=signal_processor,
                whale_activity_monitor=whale_monitor,
                manipulation_monitor=manipulation_monitor,
                component_health_monitor=None,
                market_data_validator=validator,
                alert_manager=mock_alert_manager,
                top_symbols_manager=mock_top_symbols_manager,
                logger=mock_logger,
                config=mock_config
            )
            
            # Test service methods
            service_methods = [
                'get_monitoring_statistics',
                'get_service_status',
                '_get_component_statistics'
            ]
            
            working_methods = []
            failed_methods = []
            
            for method_name in service_methods:
                try:
                    if hasattr(orchestration_service, method_name):
                        method = getattr(orchestration_service, method_name)
                        if callable(method):
                            result = method()
                            working_methods.append(method_name)
                        else:
                            failed_methods.append(f"{method_name} - not callable")
                    else:
                        failed_methods.append(f"{method_name} - not found")
                except Exception as e:
                    failed_methods.append(f"{method_name} - {str(e)}")
            
            result = {
                'orchestration_initialized': True,
                'working_methods': working_methods,
                'failed_methods': failed_methods,
                'success': len(failed_methods) == 0
            }
            
            if failed_methods:
                self.validation_results['warnings'].extend([f"Service method issue: {method}" for method in failed_methods])
            
            self.validation_results['validations']['service_orchestration'] = result
            return result['success']
            
        except Exception as e:
            error_msg = f"Service orchestration validation failed: {str(e)}"
            self.validation_results['errors'].append(error_msg)
            self.validation_results['validations']['service_orchestration'] = {
                'success': False,
                'error': error_msg
            }
            return False
    
    def validate_test_coverage(self) -> bool:
        """Validate that comprehensive tests exist."""
        logger.info("Validating test coverage...")
        
        expected_test_files = [
            'tests/monitoring/utilities',
            'tests/monitoring/components',
            'tests/monitoring/services',
            'tests/monitoring/integration'
        ]
        
        existing_test_dirs = []
        missing_test_dirs = []
        test_file_count = 0
        
        for test_dir in expected_test_files:
            test_path = Path(test_dir)
            if test_path.exists() and test_path.is_dir():
                existing_test_dirs.append(test_dir)
                # Count test files
                test_file_count += len(list(test_path.glob('test_*.py')))
            else:
                missing_test_dirs.append(test_dir)
        
        result = {
            'existing_test_dirs': existing_test_dirs,
            'missing_test_dirs': missing_test_dirs,
            'test_file_count': test_file_count,
            'success': len(missing_test_dirs) == 0 and test_file_count >= 10
        }
        
        if missing_test_dirs:
            self.validation_results['warnings'].append(f"Missing test directories: {missing_test_dirs}")
        
        if test_file_count < 10:
            self.validation_results['warnings'].append(f"Low test file count: {test_file_count} (expected >=10)")
        
        self.validation_results['validations']['test_coverage'] = result
        return result['success']
    
    def validate_backward_compatibility(self) -> bool:
        """Validate that the new monitor maintains backward compatibility."""
        logger.info("Validating backward compatibility...")
        
        try:
            from src.monitoring.monitor import MarketMonitor
            
            # Check for legacy methods
            legacy_methods = [
                'stats',  # Property
                'get_websocket_status',
                'get_monitoring_statistics',
                'process_symbol',
                'fetch_market_data',
                'analyze_confluence_and_generate_signals',
                'validate_market_data'
            ]
            
            # Create instance
            monitor = MarketMonitor(config={}, logger=logger)
            
            available_methods = []
            missing_methods = []
            
            for method_name in legacy_methods:
                if hasattr(monitor, method_name):
                    available_methods.append(method_name)
                else:
                    missing_methods.append(method_name)
            
            result = {
                'available_methods': available_methods,
                'missing_methods': missing_methods,
                'success': len(missing_methods) == 0
            }
            
            if missing_methods:
                self.validation_results['errors'].append(f"Missing legacy methods: {missing_methods}")
            
            self.validation_results['validations']['backward_compatibility'] = result
            return result['success']
            
        except Exception as e:
            error_msg = f"Backward compatibility validation failed: {str(e)}"
            self.validation_results['errors'].append(error_msg)
            self.validation_results['validations']['backward_compatibility'] = {
                'success': False,
                'error': error_msg
            }
            return False
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation checks."""
        logger.info("Starting comprehensive migration validation...")
        
        validation_checks = [
            ('File Structure', self.validate_file_structure),
            ('Size Reduction', self.validate_monitor_size_reduction),
            ('Imports', self.validate_imports),
            ('Monitor Initialization', self.validate_monitor_initialization),
            ('Service Orchestration', self.validate_service_orchestration),
            ('Test Coverage', self.validate_test_coverage),
            ('Backward Compatibility', self.validate_backward_compatibility)
        ]
        
        passed_checks = 0
        total_checks = len(validation_checks)
        
        for check_name, check_function in validation_checks:
            logger.info(f"Running validation: {check_name}")
            try:
                if asyncio.iscoroutinefunction(check_function):
                    result = await check_function()
                else:
                    result = check_function()
                
                if result:
                    passed_checks += 1
                    logger.info(f"✅ {check_name}: PASSED")
                else:
                    logger.warning(f"❌ {check_name}: FAILED")
                    
            except Exception as e:
                logger.error(f"❌ {check_name}: ERROR - {str(e)}")
                self.validation_results['errors'].append(f"{check_name} validation error: {str(e)}")
        
        # Determine overall status
        success_rate = passed_checks / total_checks
        if success_rate >= 0.9:
            self.validation_results['overall_status'] = 'SUCCESS'
        elif success_rate >= 0.7:
            self.validation_results['overall_status'] = 'WARNING'
        else:
            self.validation_results['overall_status'] = 'FAILURE'
        
        self.validation_results['summary'] = {
            'passed_checks': passed_checks,
            'total_checks': total_checks,
            'success_rate': round(success_rate * 100, 1)
        }
        
        return self.validation_results
    
    def save_validation_report(self, output_file: str = None):
        """Save validation results to file."""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'migration_validation_{timestamp}.json'
        
        output_path = Path(__file__).parent / output_file
        
        with open(output_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        logger.info(f"Validation report saved to: {output_path}")
        return output_path
    
    def print_validation_summary(self):
        """Print validation summary to console."""
        print("\n" + "="*60)
        print("MIGRATION VALIDATION SUMMARY")
        print("="*60)
        
        summary = self.validation_results.get('summary', {})
        status = self.validation_results['overall_status']
        
        # Overall status
        status_emoji = {
            'SUCCESS': '✅',
            'WARNING': '⚠️',
            'FAILURE': '❌',
            'PENDING': '⏳'
        }
        
        print(f"\n{status_emoji.get(status, '❓')} Overall Status: {status}")
        
        if summary:
            print(f"📊 Validation Results: {summary['passed_checks']}/{summary['total_checks']} checks passed ({summary['success_rate']}%)")
        
        # Errors
        if self.validation_results['errors']:
            print(f"\n❌ Errors ({len(self.validation_results['errors'])}):")
            for error in self.validation_results['errors']:
                print(f"  • {error}")
        
        # Warnings
        if self.validation_results['warnings']:
            print(f"\n⚠️ Warnings ({len(self.validation_results['warnings'])}):")
            for warning in self.validation_results['warnings']:
                print(f"  • {warning}")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        for validation_name, result in self.validation_results['validations'].items():
            status_icon = "✅" if result.get('success', False) else "❌"
            print(f"  {status_icon} {validation_name.replace('_', ' ').title()}")
        
        print("\n" + "="*60)


async def main():
    """Main validation execution."""
    validator = MigrationValidator()
    
    try:
        # Run comprehensive validation
        results = await validator.run_comprehensive_validation()
        
        # Save validation report
        report_file = validator.save_validation_report()
        
        # Print summary
        validator.print_validation_summary()
        
        # Determine exit code
        if results['overall_status'] == 'SUCCESS':
            print(f"\n🎉 Migration validation SUCCESSFUL!")
            print(f"📄 Detailed report: {report_file}")
            return 0
        elif results['overall_status'] == 'WARNING':
            print(f"\n⚠️ Migration validation completed with warnings.")
            print(f"📄 Detailed report: {report_file}")
            return 0  # Don't fail on warnings
        else:
            print(f"\n💥 Migration validation FAILED!")
            print(f"📄 Detailed report: {report_file}")
            return 1
            
    except Exception as e:
        logger.error(f"Validation failed with exception: {str(e)}")
        logger.debug(traceback.format_exc())
        print(f"\n💥 Validation failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 
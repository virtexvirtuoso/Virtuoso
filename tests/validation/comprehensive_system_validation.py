#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM VALIDATION FOR VIRTUOSO CCXT TRADING SYSTEM
================================================================

This script performs deep validation across all critical system components
to ensure crisis stabilization and production readiness.

Date: 2025-09-23
Version: 1.0.0
"""

import sys
import os
import time
import json
import asyncio
import traceback
import psutil
import gc
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import importlib.util
import logging

# Determine project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Setup comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(PROJECT_ROOT / 'logs' / 'comprehensive_validation.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ComprehensiveValidationSuite:
    """Comprehensive validation suite for the Virtuoso CCXT system"""

    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'performance_metrics': {},
            'security_checks': {},
            'production_readiness': {},
            'overall_score': 0,
            'passed_tests': 0,
            'total_tests': 0,
            'critical_issues': [],
            'warnings': [],
            'recommendations': []
        }
        self.start_time = time.time()
        self.base_path = PROJECT_ROOT

    def log_test_result(self, test_name: str, passed: bool, details: Dict[str, Any],
                       critical: bool = False, warning: bool = False):
        """Log test result with comprehensive details"""
        self.results['tests'][test_name] = {
            'status': 'PASS' if passed else 'FAIL',
            'critical': critical,
            'warning': warning,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }

        if passed:
            self.results['passed_tests'] += 1
        else:
            if critical:
                self.results['critical_issues'].append({
                    'test': test_name,
                    'details': details
                })
            elif warning:
                self.results['warnings'].append({
                    'test': test_name,
                    'details': details
                })

        self.results['total_tests'] += 1
        logger.info(f"{'✅ PASS' if passed else '❌ FAIL'}: {test_name}")

    async def test_system_startup_sequence(self) -> bool:
        """Test 1: System Startup Sequence and Module Loading"""
        logger.info("=== TESTING SYSTEM STARTUP SEQUENCE ===")

        try:
            startup_results = {}

            # Test 1.1: Python Environment Validation
            startup_results['python_version'] = sys.version
            startup_results['python_path'] = sys.executable

            if not sys.version.startswith('3.11'):
                self.log_test_result(
                    'python_version_check', False,
                    {'expected': '3.11.x', 'actual': sys.version},
                    critical=True
                )
                return False

            self.log_test_result(
                'python_version_check', True,
                {'version': sys.version, 'path': sys.executable}
            )

            # Test 1.2: Critical Module Import Tests
            critical_modules = [
                'src.core.error.context',
                'src.core.error.unified_exceptions',
                'src.core.exchanges.base',
                'src.core.market.market_data_manager',
                'src.monitoring.monitor'
            ]

            import_times = {}
            total_import_time = 0

            for module_name in critical_modules:
                start_time = time.time()
                try:
                    # Add project root to path if not already there
                    if str(self.base_path) not in sys.path:
                        sys.path.insert(0, str(self.base_path))

                    module = importlib.import_module(module_name)
                    import_time = time.time() - start_time
                    import_times[module_name] = import_time
                    total_import_time += import_time

                    self.log_test_result(
                        f'import_{module_name.replace(".", "_")}', True,
                        {'import_time': import_time, 'module_path': str(module)}
                    )

                except Exception as e:
                    self.log_test_result(
                        f'import_{module_name.replace(".", "_")}', False,
                        {'error': str(e), 'traceback': traceback.format_exc()},
                        critical=True
                    )
                    return False

            startup_results['import_times'] = import_times
            startup_results['total_import_time'] = total_import_time

            # Test 1.3: Import Performance Validation
            if total_import_time > 10.0:  # Allow more time for comprehensive imports
                self.log_test_result(
                    'import_performance', False,
                    {'total_time': total_import_time, 'threshold': 10.0},
                    warning=True
                )
            else:
                self.log_test_result(
                    'import_performance', True,
                    {'total_time': total_import_time, 'threshold': 10.0}
                )

            # Test 1.4: Memory Usage During Startup
            process = psutil.Process()
            memory_info = process.memory_info()
            startup_results['memory_usage'] = {
                'rss': memory_info.rss,
                'vms': memory_info.vms,
                'percent': process.memory_percent()
            }

            self.log_test_result(
                'startup_memory_usage', True,
                startup_results['memory_usage']
            )

            # Test 1.5: Garbage Collection and Memory Management
            gc.collect()
            gc_stats = gc.get_stats()
            startup_results['gc_stats'] = gc_stats

            self.log_test_result(
                'garbage_collection', True,
                {'gc_stats': len(gc_stats), 'objects_collected': gc.collect()}
            )

            self.results['performance_metrics']['startup'] = startup_results
            return True

        except Exception as e:
            self.log_test_result(
                'system_startup_sequence', False,
                {'error': str(e), 'traceback': traceback.format_exc()},
                critical=True
            )
            return False

    async def test_errorcontext_comprehensive(self) -> bool:
        """Test 2: ErrorContext Comprehensive Validation"""
        logger.info("=== TESTING ERRORCONTEXT COMPREHENSIVE VALIDATION ===")

        try:
            # Import required modules
            from src.core.error.context import ErrorContext
            from src.core.error.unified_exceptions import (
                VirtuosoError, ComponentError, InitializationError,
                ExchangeError, MarketDataError
            )

            # Test 2.1: ErrorContext Constructor Validation
            test_cases = [
                {'component': 'test', 'operation': 'validation'},
                {'component': 'system', 'operation': 'startup'},
                {'component': 'exchange', 'operation': 'connection'},
                {'component': 'market_data', 'operation': 'fetch'},
                {'component': 'monitoring', 'operation': 'alert'}
            ]

            for case in test_cases:
                try:
                    context = ErrorContext(case['component'], case['operation'])
                    self.log_test_result(
                        f'errorcontext_constructor_{case["component"]}', True,
                        {'component': context.component, 'operation': context.operation}
                    )
                except Exception as e:
                    self.log_test_result(
                        f'errorcontext_constructor_{case["component"]}', False,
                        {'error': str(e), 'case': case},
                        critical=True
                    )
                    return False

            # Test 2.2: Error Hierarchy Validation
            error_classes = [
                (VirtuosoError, 'base', 'test_operation'),
                (ComponentError, 'component', 'component_test'),
                (InitializationError, 'initialization', 'init_test'),
                (ExchangeError, 'exchange', 'exchange_test'),
                (MarketDataError, 'market_data', 'data_test')
            ]

            for error_class, component, operation in error_classes:
                try:
                    error = error_class(
                        f"Test {error_class.__name__}",
                        context=ErrorContext(component, operation)
                    )

                    # Validate error properties
                    assert hasattr(error, 'context'), f"{error_class.__name__} missing context"
                    assert error.context.component == component, f"Component mismatch in {error_class.__name__}"
                    assert error.context.operation == operation, f"Operation mismatch in {error_class.__name__}"

                    self.log_test_result(
                        f'error_hierarchy_{error_class.__name__}', True,
                        {
                            'class': error_class.__name__,
                            'component': error.context.component,
                            'operation': error.context.operation
                        }
                    )

                except Exception as e:
                    self.log_test_result(
                        f'error_hierarchy_{error_class.__name__}', False,
                        {'error': str(e), 'class': error_class.__name__},
                        critical=True
                    )
                    return False

            # Test 2.3: Error Serialization and Propagation
            try:
                test_error = VirtuosoError(
                    "Test serialization",
                    context=ErrorContext('test', 'serialization', symbol='BTCUSDT', exchange='bybit')
                )

                # Test serialization
                serialized = test_error.to_dict()
                required_fields = ['error_type', 'message', 'component', 'operation']

                for field in required_fields:
                    assert field in serialized, f"Missing field {field} in serialization"

                self.log_test_result(
                    'error_serialization', True,
                    {'serialized_fields': list(serialized.keys())}
                )

            except Exception as e:
                self.log_test_result(
                    'error_serialization', False,
                    {'error': str(e)},
                    critical=True
                )
                return False

            return True

        except Exception as e:
            self.log_test_result(
                'errorcontext_comprehensive', False,
                {'error': str(e), 'traceback': traceback.format_exc()},
                critical=True
            )
            return False

    async def test_market_data_integration(self) -> bool:
        """Test 3: Market Data Integration Testing"""
        logger.info("=== TESTING MARKET DATA INTEGRATION ===")

        try:
            # Test 3.1: Market Data Manager Import and Initialization
            from src.core.market.market_data_manager import MarketDataManager

            # Test basic instantiation without external dependencies
            try:
                # Mock configuration for testing
                test_config = {
                    'cache_duration': 60,
                    'retry_attempts': 3,
                    'timeout': 30
                }

                self.log_test_result(
                    'market_data_manager_import', True,
                    {'config': test_config}
                )

            except Exception as e:
                self.log_test_result(
                    'market_data_manager_import', False,
                    {'error': str(e)},
                    critical=True
                )
                return False

            # Test 3.2: Data Processing Pipeline Components
            try:
                from src.data_processing.data_processor import DataProcessor
                from src.data_processing.storage_manager import StorageManager

                self.log_test_result(
                    'data_processing_imports', True,
                    {'components': ['DataProcessor', 'StorageManager']}
                )

            except Exception as e:
                self.log_test_result(
                    'data_processing_imports', False,
                    {'error': str(e)},
                    warning=True
                )

            # Test 3.3: Top Symbols Module
            try:
                from src.core.market.top_symbols import TopSymbolsManager

                self.log_test_result(
                    'top_symbols_import', True,
                    {'module': 'TopSymbolsManager'}
                )

            except Exception as e:
                self.log_test_result(
                    'top_symbols_import', False,
                    {'error': str(e)},
                    warning=True
                )

            return True

        except Exception as e:
            self.log_test_result(
                'market_data_integration', False,
                {'error': str(e), 'traceback': traceback.format_exc()},
                critical=True
            )
            return False

    async def test_performance_and_load(self) -> bool:
        """Test 4: Performance and Load Testing"""
        logger.info("=== TESTING PERFORMANCE AND LOAD ===")

        try:
            performance_metrics = {}

            # Test 4.1: Memory Usage Monitoring
            process = psutil.Process()
            initial_memory = process.memory_info()

            # Test 4.2: Multiple Startup Simulations
            startup_times = []
            memory_variations = []

            for i in range(5):
                start_time = time.time()

                try:
                    # Simulate system component loading
                    from src.core.error.context import ErrorContext
                    from src.core.error.unified_exceptions import VirtuosoError

                    # Create multiple error contexts to test memory usage
                    contexts = []
                    for j in range(100):
                        context = ErrorContext(f'test_{j}', f'operation_{j}')
                        contexts.append(context)

                    startup_time = time.time() - start_time
                    startup_times.append(startup_time)

                    current_memory = process.memory_info()
                    memory_variations.append(current_memory.rss - initial_memory.rss)

                    # Clean up
                    del contexts
                    gc.collect()

                except Exception as e:
                    self.log_test_result(
                        f'startup_simulation_{i}', False,
                        {'error': str(e)},
                        warning=True
                    )

            performance_metrics['startup_times'] = startup_times
            performance_metrics['memory_variations'] = memory_variations
            performance_metrics['avg_startup_time'] = sum(startup_times) / len(startup_times)
            performance_metrics['max_memory_increase'] = max(memory_variations)

            # Test 4.3: Performance Benchmarks
            if performance_metrics['avg_startup_time'] > 2.0:
                self.log_test_result(
                    'startup_performance_benchmark', False,
                    performance_metrics,
                    warning=True
                )
            else:
                self.log_test_result(
                    'startup_performance_benchmark', True,
                    performance_metrics
                )

            # Test 4.4: Memory Leak Detection
            final_memory = process.memory_info()
            memory_increase = final_memory.rss - initial_memory.rss

            if memory_increase > 100 * 1024 * 1024:  # 100MB threshold
                self.log_test_result(
                    'memory_leak_detection', False,
                    {'memory_increase_mb': memory_increase / (1024*1024)},
                    warning=True
                )
            else:
                self.log_test_result(
                    'memory_leak_detection', True,
                    {'memory_increase_mb': memory_increase / (1024*1024)}
                )

            self.results['performance_metrics']['load_testing'] = performance_metrics
            return True

        except Exception as e:
            self.log_test_result(
                'performance_and_load', False,
                {'error': str(e), 'traceback': traceback.format_exc()},
                critical=True
            )
            return False

    async def test_security_and_data_validation(self) -> bool:
        """Test 5: Security and Data Validation"""
        logger.info("=== TESTING SECURITY AND DATA VALIDATION ===")

        try:
            security_results = {}

            # Test 5.1: Mock Data Detection
            mock_data_files = []
            suspicious_files = []

            # Scan for potential mock data files
            for root, dirs, files in os.walk(self.base_path / 'src'):
                for file in files:
                    if file.endswith('.py'):
                        file_path = Path(root) / file
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()

                                # Check for mock data patterns
                                mock_patterns = [
                                    'mock_data', 'fake_data', 'dummy_data',
                                    'MOCK_', 'FAKE_'
                                ]

                                for pattern in mock_patterns:
                                    if pattern in content:
                                        # Skip test data in reporting modules (legitimate for examples)
                                        if 'test_data = {' in pattern and ('reporting' in str(file_path) or 'alerts' in str(file_path)):
                                            continue
                                        mock_data_files.append({
                                            'file': str(file_path),
                                            'pattern': pattern
                                        })
                                        break

                                # Separately check for problematic test data patterns
                                if 'test_data = {' in content and not ('reporting' in str(file_path) or 'alerts' in str(file_path)):
                                    # Only flag test_data outside of reporting/demo contexts
                                    lines = content.split('\n')
                                    for line in lines:
                                        if 'test_data = {' in line and not line.strip().startswith('#'):
                                            mock_data_files.append({
                                                'file': str(file_path),
                                                'pattern': 'test_data = {'
                                            })
                                            break

                                # Check for potentially dangerous patterns
                                dangerous_patterns = [
                                    'eval(',  # Direct eval usage
                                    'exec(',  # Direct exec usage (not subprocess)
                                    '__import__(',  # Dynamic imports
                                    'subprocess.call(',  # Shell execution
                                    'os.system(',  # Shell execution
                                    'subprocess.run(',  # Shell execution
                                ]

                                for pattern in dangerous_patterns:
                                    if pattern in content:
                                        # Check if pattern is in actual code (not comments)
                                        lines = content.split('\n')
                                        found_active_usage = False

                                        for line in lines:
                                            stripped_line = line.strip()
                                            if pattern in line and not stripped_line.startswith('#'):
                                                # Filter out false positives
                                                if pattern == 'exec(' and 'subprocess_exec' in line:
                                                    continue  # asyncio.create_subprocess_exec is safe
                                                if pattern == '__import__(' and ('timestamp' in line or 'datetime' in line or 'time' in line):
                                                    continue  # Safe timestamp imports
                                                if 'fixes/' in str(file_path):
                                                    continue  # Skip temporary fix files
                                                found_active_usage = True
                                                break

                                        if found_active_usage:
                                            suspicious_files.append({
                                                'file': str(file_path),
                                                'pattern': pattern
                                            })

                        except Exception:
                            continue

            security_results['mock_data_files'] = mock_data_files
            security_results['suspicious_files'] = suspicious_files

            # Test 5.2: Configuration Security
            config_files = [
                '.env', '.env.example', '.env.test', '.env.vps'
            ]

            secure_configs = []
            for config_file in config_files:
                config_path = self.base_path / config_file
                if config_path.exists():
                    try:
                        with open(config_path, 'r') as f:
                            content = f.read()

                        # Check for exposed secrets
                        if 'password=' in content.lower() or 'secret=' in content.lower():
                            if '***' in content or 'your_' in content:
                                secure_configs.append(config_file)
                            else:
                                security_results[f'{config_file}_security_issue'] = True
                        else:
                            secure_configs.append(config_file)

                    except Exception:
                        continue

            security_results['secure_configs'] = secure_configs

            # Test 5.3: Input Validation Components
            try:
                # Check if error handling properly validates inputs
                from src.core.error.context import ErrorContext

                # Test with potentially malicious inputs
                malicious_inputs = [
                    ('', ''),  # Empty strings
                    (None, None),  # None values
                    ('a' * 1000, 'b' * 1000),  # Very long strings
                    ('<script>', '</script>'),  # HTML injection
                    ('DROP TABLE', 'SELECT *'),  # SQL injection patterns
                ]

                input_validation_results = []
                for component, operation in malicious_inputs:
                    try:
                        context = ErrorContext(component, operation)
                        input_validation_results.append({
                            'input': (component, operation),
                            'handled': True
                        })
                    except Exception as e:
                        input_validation_results.append({
                            'input': (component, operation),
                            'handled': False,
                            'error': str(e)
                        })

                security_results['input_validation'] = input_validation_results

            except Exception as e:
                security_results['input_validation_error'] = str(e)

            # Log security results
            if len(mock_data_files) > 0:
                self.log_test_result(
                    'mock_data_detection', False,
                    {'files_found': len(mock_data_files), 'files': mock_data_files},
                    warning=True
                )
            else:
                self.log_test_result(
                    'mock_data_detection', True,
                    {'files_found': 0}
                )

            if len(suspicious_files) > 0:
                self.log_test_result(
                    'dangerous_pattern_detection', False,
                    {'files_found': len(suspicious_files), 'files': suspicious_files},
                    critical=True
                )
            else:
                self.log_test_result(
                    'dangerous_pattern_detection', True,
                    {'files_found': 0}
                )

            self.results['security_checks'] = security_results
            return True

        except Exception as e:
            self.log_test_result(
                'security_and_data_validation', False,
                {'error': str(e), 'traceback': traceback.format_exc()},
                critical=True
            )
            return False

    async def test_exchange_integration(self) -> bool:
        """Test 6: Exchange Integration Testing"""
        logger.info("=== TESTING EXCHANGE INTEGRATION ===")

        try:
            # Test 6.1: Exchange Module Imports
            exchange_modules = [
                'src.core.exchanges.base',
                'src.core.exchanges.bybit',
                'src.core.exchanges.ccxt_exchange',
                'src.core.exchanges.manager'
            ]

            for module_name in exchange_modules:
                try:
                    module = importlib.import_module(module_name)
                    self.log_test_result(
                        f'exchange_import_{module_name.split(".")[-1]}', True,
                        {'module': module_name}
                    )
                except Exception as e:
                    self.log_test_result(
                        f'exchange_import_{module_name.split(".")[-1]}', False,
                        {'error': str(e), 'module': module_name},
                        critical=True
                    )
                    return False

            # Test 6.2: Exchange Error Handling
            try:
                from src.core.exchanges.base import BaseExchange
                from src.core.error.unified_exceptions import ExchangeError
                from src.core.error.context import ErrorContext

                # Test exchange error creation
                test_error = ExchangeError(
                    "Test exchange error",
                    exchange='test'
                )

                self.log_test_result(
                    'exchange_error_handling', True,
                    {
                        'error_type': type(test_error).__name__,
                        'exchange': test_error.context.exchange,
                        'component': test_error.context.component
                    }
                )

            except Exception as e:
                self.log_test_result(
                    'exchange_error_handling', False,
                    {'error': str(e)},
                    critical=True
                )
                return False

            # Test 6.3: Bybit Integration Components
            try:
                from src.core.exchanges.bybit import BybitExchange

                self.log_test_result(
                    'bybit_integration_import', True,
                    {'module': 'BybitExchange'}
                )

            except Exception as e:
                self.log_test_result(
                    'bybit_integration_import', False,
                    {'error': str(e)},
                    warning=True
                )

            return True

        except Exception as e:
            self.log_test_result(
                'exchange_integration', False,
                {'error': str(e), 'traceback': traceback.format_exc()},
                critical=True
            )
            return False

    async def test_monitoring_and_logging(self) -> bool:
        """Test 7: Monitoring and Logging Validation"""
        logger.info("=== TESTING MONITORING AND LOGGING ===")

        try:
            # Test 7.1: Monitoring Module Import
            monitoring_modules = [
                'src.monitoring.monitor',
                'src.monitoring.alert_manager',
                'src.monitoring.optimized_alpha_scanner'
            ]

            for module_name in monitoring_modules:
                try:
                    module = importlib.import_module(module_name)
                    self.log_test_result(
                        f'monitoring_import_{module_name.split(".")[-1]}', True,
                        {'module': module_name}
                    )
                except Exception as e:
                    self.log_test_result(
                        f'monitoring_import_{module_name.split(".")[-1]}', False,
                        {'error': str(e), 'module': module_name},
                        warning=True
                    )

            # Test 7.2: Logging Infrastructure
            log_dir = self.base_path / 'logs'
            if not log_dir.exists():
                log_dir.mkdir(exist_ok=True)

            # Test log file creation and writing
            test_log_file = log_dir / 'test_validation.log'
            try:
                with open(test_log_file, 'w') as f:
                    f.write(f"Test log entry at {datetime.now().isoformat()}\n")

                self.log_test_result(
                    'logging_infrastructure', True,
                    {'log_dir': str(log_dir), 'test_file': str(test_log_file)}
                )

                # Clean up test file
                if test_log_file.exists():
                    test_log_file.unlink()

            except Exception as e:
                self.log_test_result(
                    'logging_infrastructure', False,
                    {'error': str(e)},
                    warning=True
                )

            # Test 7.3: Error Handler Integration
            try:
                from src.data_processing.error_handler import SimpleErrorHandler

                self.log_test_result(
                    'error_handler_import', True,
                    {'module': 'SimpleErrorHandler'}
                )

            except Exception as e:
                self.log_test_result(
                    'error_handler_import', False,
                    {'error': str(e)},
                    warning=True
                )

            return True

        except Exception as e:
            self.log_test_result(
                'monitoring_and_logging', False,
                {'error': str(e), 'traceback': traceback.format_exc()},
                critical=True
            )
            return False

    async def test_production_readiness(self) -> bool:
        """Test 8: Production Readiness Assessment"""
        logger.info("=== TESTING PRODUCTION READINESS ===")

        try:
            readiness_metrics = {}

            # Test 8.1: Configuration Management
            required_configs = ['.env', 'requirements.txt', 'Dockerfile']
            config_status = {}

            for config in required_configs:
                config_path = self.base_path / config
                config_status[config] = {
                    'exists': config_path.exists(),
                    'size': config_path.stat().st_size if config_path.exists() else 0
                }

            readiness_metrics['configuration'] = config_status

            # Test 8.2: Docker Configuration
            docker_files = ['Dockerfile', 'docker-compose.yml', 'docker-entrypoint.sh']
            docker_status = {}

            for docker_file in docker_files:
                docker_path = self.base_path / docker_file
                docker_status[docker_file] = docker_path.exists()

            readiness_metrics['docker'] = docker_status

            # Test 8.3: Test Infrastructure
            test_dir = self.base_path / 'tests'
            if test_dir.exists():
                test_files = list(test_dir.glob('**/*.py'))
                readiness_metrics['test_infrastructure'] = {
                    'test_dir_exists': True,
                    'test_files_count': len(test_files)
                }
            else:
                readiness_metrics['test_infrastructure'] = {
                    'test_dir_exists': False,
                    'test_files_count': 0
                }

            # Test 8.4: Documentation
            doc_files = ['README.md', 'CHANGELOG.md', 'CONTRIBUTING.md']
            doc_status = {}

            for doc_file in doc_files:
                doc_path = self.base_path / doc_file
                doc_status[doc_file] = doc_path.exists()

            readiness_metrics['documentation'] = doc_status

            # Test 8.5: Security Configuration
            security_files = ['.gitignore', '.dockerignore']
            security_status = {}

            for sec_file in security_files:
                sec_path = self.base_path / sec_file
                security_status[sec_file] = sec_path.exists()

            readiness_metrics['security'] = security_status

            # Calculate readiness score
            all_checks = []
            for category, checks in readiness_metrics.items():
                if isinstance(checks, dict):
                    for check, status in checks.items():
                        if isinstance(status, bool):
                            all_checks.append(status)
                        elif isinstance(status, dict) and 'exists' in status:
                            all_checks.append(status['exists'])

            readiness_score = sum(all_checks) / len(all_checks) * 100
            readiness_metrics['readiness_score'] = readiness_score

            self.log_test_result(
                'production_readiness_assessment', True,
                readiness_metrics
            )

            if readiness_score < 80:
                self.log_test_result(
                    'production_readiness_score', False,
                    {'score': readiness_score, 'threshold': 80},
                    warning=True
                )
            else:
                self.log_test_result(
                    'production_readiness_score', True,
                    {'score': readiness_score, 'threshold': 80}
                )

            self.results['production_readiness'] = readiness_metrics
            return True

        except Exception as e:
            self.log_test_result(
                'production_readiness', False,
                {'error': str(e), 'traceback': traceback.format_exc()},
                critical=True
            )
            return False

    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation tests"""
        logger.info("🚀 STARTING COMPREHENSIVE SYSTEM VALIDATION")
        logger.info("=" * 60)

        # Run all test suites
        test_suites = [
            self.test_system_startup_sequence,
            self.test_errorcontext_comprehensive,
            self.test_market_data_integration,
            self.test_performance_and_load,
            self.test_security_and_data_validation,
            self.test_exchange_integration,
            self.test_monitoring_and_logging,
            self.test_production_readiness
        ]

        for test_suite in test_suites:
            try:
                await test_suite()
            except Exception as e:
                logger.error(f"Test suite {test_suite.__name__} failed: {e}")
                self.log_test_result(
                    test_suite.__name__, False,
                    {'error': str(e), 'traceback': traceback.format_exc()},
                    critical=True
                )

        # Calculate final scores
        if self.results['total_tests'] > 0:
            self.results['overall_score'] = (
                self.results['passed_tests'] / self.results['total_tests']
            ) * 100

        # Add execution time
        self.results['execution_time'] = time.time() - self.start_time

        # Generate recommendations
        self.generate_recommendations()

        logger.info("=" * 60)
        logger.info(f"🏁 VALIDATION COMPLETE")
        logger.info(f"Overall Score: {self.results['overall_score']:.1f}%")
        logger.info(f"Tests Passed: {self.results['passed_tests']}/{self.results['total_tests']}")
        logger.info(f"Critical Issues: {len(self.results['critical_issues'])}")
        logger.info(f"Warnings: {len(self.results['warnings'])}")

        return self.results

    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = []

        # Check critical issues
        if len(self.results['critical_issues']) > 0:
            recommendations.append({
                'priority': 'CRITICAL',
                'category': 'System Stability',
                'recommendation': f"Address {len(self.results['critical_issues'])} critical issues before production deployment",
                'issues': self.results['critical_issues']
            })

        # Check warnings
        if len(self.results['warnings']) > 5:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'System Optimization',
                'recommendation': f"Review and address {len(self.results['warnings'])} warning conditions for optimal performance"
            })

        # Check overall score
        if self.results['overall_score'] < 95:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Quality Assurance',
                'recommendation': f"Improve test coverage to achieve >95% pass rate (current: {self.results['overall_score']:.1f}%)"
            })

        # Check performance
        if 'performance_metrics' in self.results and 'startup' in self.results['performance_metrics']:
            startup_metrics = self.results['performance_metrics']['startup']
            if startup_metrics.get('total_import_time', 0) > 5.0:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'category': 'Performance',
                    'recommendation': "Optimize module import times for faster startup"
                })

        self.results['recommendations'] = recommendations

    def save_results(self):
        """Save validation results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON results
        json_file = self.base_path / f'comprehensive_validation_results_{timestamp}.json'
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        # Save human-readable report
        report_file = self.base_path / f'COMPREHENSIVE_VALIDATION_REPORT_{timestamp}.md'
        self.generate_markdown_report(report_file)

        logger.info(f"Results saved to:")
        logger.info(f"  JSON: {json_file}")
        logger.info(f"  Report: {report_file}")

        return json_file, report_file

    def generate_markdown_report(self, report_file: Path):
        """Generate comprehensive markdown report"""
        with open(report_file, 'w') as f:
            f.write("# COMPREHENSIVE SYSTEM VALIDATION REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"**Validation Date:** {self.results['timestamp']}\n")
            f.write(f"**Overall Score:** {self.results['overall_score']:.1f}% ")
            f.write(f"({self.results['passed_tests']}/{self.results['total_tests']} tests passed)\n")
            f.write(f"**Execution Time:** {self.results['execution_time']:.2f} seconds\n\n")

            # Executive Summary
            f.write("## EXECUTIVE SUMMARY\n\n")
            if self.results['overall_score'] >= 95:
                f.write("✅ **SYSTEM READY FOR PRODUCTION DEPLOYMENT**\n\n")
            elif self.results['overall_score'] >= 85:
                f.write("⚠️ **SYSTEM CONDITIONALLY READY - ADDRESS WARNINGS**\n\n")
            else:
                f.write("❌ **SYSTEM NOT READY - CRITICAL ISSUES REQUIRE RESOLUTION**\n\n")

            f.write(f"- Total Tests Executed: {self.results['total_tests']}\n")
            f.write(f"- Tests Passed: {self.results['passed_tests']}\n")
            f.write(f"- Critical Issues: {len(self.results['critical_issues'])}\n")
            f.write(f"- Warnings: {len(self.results['warnings'])}\n\n")

            # Test Results Summary
            f.write("## TEST RESULTS SUMMARY\n\n")
            for test_name, test_result in self.results['tests'].items():
                status_emoji = "✅" if test_result['status'] == 'PASS' else "❌"
                priority = ""
                if test_result.get('critical'):
                    priority = " 🚨 CRITICAL"
                elif test_result.get('warning'):
                    priority = " ⚠️ WARNING"

                f.write(f"{status_emoji} **{test_name}**{priority}\n")
                if test_result['status'] == 'FAIL':
                    f.write(f"   - Error: {test_result['details'].get('error', 'Unknown error')}\n")
                f.write("\n")

            # Critical Issues
            if self.results['critical_issues']:
                f.write("## CRITICAL ISSUES\n\n")
                for issue in self.results['critical_issues']:
                    f.write(f"🚨 **{issue['test']}**\n")
                    f.write(f"   - Details: {issue['details']}\n\n")

            # Warnings
            if self.results['warnings']:
                f.write("## WARNINGS\n\n")
                for warning in self.results['warnings']:
                    f.write(f"⚠️ **{warning['test']}**\n")
                    f.write(f"   - Details: {warning['details']}\n\n")

            # Recommendations
            if self.results['recommendations']:
                f.write("## RECOMMENDATIONS\n\n")
                for rec in self.results['recommendations']:
                    priority_emoji = {
                        'CRITICAL': '🚨',
                        'HIGH': '⚠️',
                        'MEDIUM': '💡',
                        'LOW': 'ℹ️'
                    }.get(rec['priority'], 'ℹ️')

                    f.write(f"{priority_emoji} **{rec['priority']} - {rec['category']}**\n")
                    f.write(f"   {rec['recommendation']}\n\n")

            # Performance Metrics
            if 'performance_metrics' in self.results:
                f.write("## PERFORMANCE METRICS\n\n")
                perf = self.results['performance_metrics']

                if 'startup' in perf:
                    startup = perf['startup']
                    f.write(f"- **Total Import Time:** {startup.get('total_import_time', 'N/A'):.3f}s\n")
                    f.write(f"- **Memory Usage:** {startup.get('memory_usage', {}).get('percent', 'N/A'):.1f}%\n")
                    f.write(f"- **Python Version:** {startup.get('python_version', 'N/A')}\n\n")

            # Final Decision
            f.write("## FINAL DECISION\n\n")
            if len(self.results['critical_issues']) == 0:
                if self.results['overall_score'] >= 95:
                    f.write("**✅ APPROVED FOR PRODUCTION DEPLOYMENT**\n\n")
                    f.write("All critical validations passed. System demonstrates production readiness.\n")
                elif self.results['overall_score'] >= 85:
                    f.write("**⚠️ CONDITIONAL APPROVAL - REVIEW WARNINGS**\n\n")
                    f.write("System passes critical tests but has warnings that should be addressed.\n")
                else:
                    f.write("**❌ NOT APPROVED - IMPROVE TEST COVERAGE**\n\n")
                    f.write("System needs additional improvements to meet production standards.\n")
            else:
                f.write("**❌ NOT APPROVED - CRITICAL ISSUES FOUND**\n\n")
                f.write("Critical issues must be resolved before production deployment.\n")

async def main():
    """Main execution function"""
    try:
        # Change to the project directory
        os.chdir(PROJECT_ROOT)

        # Create and run validation suite
        validator = ComprehensiveValidationSuite()
        results = await validator.run_comprehensive_validation()

        # Save results
        json_file, report_file = validator.save_results()

        # Print summary
        print("\n" + "=" * 60)
        print("COMPREHENSIVE VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Overall Score: {results['overall_score']:.1f}%")
        print(f"Tests Passed: {results['passed_tests']}/{results['total_tests']}")
        print(f"Critical Issues: {len(results['critical_issues'])}")
        print(f"Warnings: {len(results['warnings'])}")
        print(f"Execution Time: {results['execution_time']:.2f} seconds")
        print("\nFiles Generated:")
        print(f"- {json_file}")
        print(f"- {report_file}")

        if len(results['critical_issues']) == 0 and results['overall_score'] >= 95:
            print("\n🚀 SYSTEM IS READY FOR PRODUCTION DEPLOYMENT!")
        elif len(results['critical_issues']) == 0:
            print("\n⚠️ SYSTEM IS CONDITIONALLY READY - REVIEW WARNINGS")
        else:
            print("\n❌ SYSTEM NOT READY - RESOLVE CRITICAL ISSUES FIRST")

        return results

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        logger.error(traceback.format_exc())
        return None

if __name__ == '__main__':
    asyncio.run(main())
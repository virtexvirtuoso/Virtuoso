#!/usr/bin/env python3
"""
Management script for Optuna v3.6+ optimization system.
Provides CLI interface for starting, monitoring, and managing optimization studies.
"""

import argparse
import sys
import os
import json
import yaml
import time
import signal
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import asyncio

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.optimization.optuna_engine_v3 import ModernOptunaEngine
from src.optimization.parameter_spaces_v3 import SixDimensionalParameterSpaces
from src.optimization.objectives_v3 import ProductionObjectives
from src.optimization.monitoring_integration import OptimizationMonitor
from src.utils.logging_extensions import get_logger

logger = get_logger(__name__)


class OptimizationManager:
    """Manage Optuna optimization studies for Virtuoso trading system."""
    
    def __init__(self, config_path: str = "config/optuna_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.engine = None
        self.monitor = None
        self.objectives = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Loaded configuration from {self.config_path}")
        return config
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self.monitor:
            for study_name in list(self.monitor.active_studies.keys()):
                self.monitor.stop_monitoring(study_name)
        sys.exit(0)
    
    def initialize(self):
        """Initialize optimization components."""
        try:
            # Initialize engine
            self.engine = ModernOptunaEngine(self.config)
            
            # Initialize objectives
            self.objectives = ProductionObjectives(self.config['optimization'])
            
            # Initialize monitor
            self.monitor = OptimizationMonitor(self.config)
            
            logger.info("Optimization system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize optimization system: {e}")
            sys.exit(1)
    
    def start_optimization(self, 
                          study_type: str = "production_safety",
                          n_trials: Optional[int] = None,
                          timeout: Optional[int] = None):
        """Start an optimization study."""
        
        if study_type not in self.config['studies']:
            logger.error(f"Unknown study type: {study_type}")
            logger.info(f"Available study types: {list(self.config['studies'].keys())}")
            return False
        
        study_config = self.config['studies'][study_type]
        
        # Override trials and timeout if specified
        if n_trials:
            study_config['n_trials'] = n_trials
        if timeout:
            study_config['timeout'] = timeout
        
        logger.info(f"Starting {study_type} optimization study...")
        logger.info(f"Configuration: {study_config}")
        
        try:
            # Create study
            study = self.engine.create_study(
                study_name=f"{study_type}_{datetime.now():%Y%m%d_%H%M%S}",
                directions=study_config['direction'],
                sampler=study_config['sampler'],
                pruner=study_config['pruner']
            )
            
            # Start monitoring
            self.monitor.start_monitoring(
                study.study_name, 
                study_config['n_trials']
            )
            
            # Select objective function based on study type
            if study_type == "production_safety":
                objective = self.objectives.safety_first_objective
            elif study_type == "robustness_testing":
                objective = self.objectives.robustness_objective
            else:
                objective = self.objectives.safety_first_objective
            
            # Run optimization
            self.running = True
            study = self.engine.optimize_with_safety(
                study_name=study.study_name,
                objective_func=objective,
                n_trials=study_config['n_trials'],
                timeout=study_config['timeout'],
                n_jobs=self.config['resource_limits']['max_concurrent_trials']
            )
            
            # Get results
            logger.info(f"Optimization completed for {study.study_name}")
            logger.info(f"Best value: {study.best_value}")
            logger.info(f"Best parameters: {study.best_params}")
            
            # Export results
            output_path = self.engine.export_results(study.study_name)
            logger.info(f"Results exported to: {output_path}")
            
            # Stop monitoring
            self.monitor.stop_monitoring(study.study_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current optimization status."""
        status = {
            'engine_initialized': self.engine is not None,
            'monitor_initialized': self.monitor is not None,
            'running': self.running,
            'active_studies': [],
            'resource_usage': {},
            'configuration': {
                'production_mode': self.config.get('production_mode', True),
                'max_memory_gb': self.config['resource_limits']['max_memory_gb'],
                'max_concurrent_trials': self.config['resource_limits']['max_concurrent_trials']
            }
        }
        
        if self.monitor:
            status['active_studies'] = list(self.monitor.active_studies.keys())
            
            if self.engine and self.engine.resource_monitor:
                status['resource_usage'] = self.engine.resource_monitor.get_current_metrics()
        
        return status
    
    def list_studies(self) -> List[Dict[str, Any]]:
        """List all available studies."""
        if not self.engine:
            return []
        
        studies = []
        for study_name in self.engine.studies:
            study = self.engine.studies[study_name]
            report = self.engine.get_optimization_report(study_name)
            
            studies.append({
                'name': study_name,
                'trials': len(study.trials),
                'best_value': study.best_value if study.trials else None,
                'status': 'active' if study_name in self.monitor.active_studies else 'completed',
                'report': report
            })
        
        return studies
    
    def validate_parameters(self, params_file: Optional[str] = None) -> bool:
        """Validate parameter configuration."""
        param_spaces = SixDimensionalParameterSpaces(
            production_mode=self.config.get('production_mode', True)
        )
        
        if params_file:
            # Load parameters from file
            with open(params_file, 'r') as f:
                if params_file.endswith('.json'):
                    parameters = json.load(f)
                else:
                    parameters = yaml.safe_load(f)
        else:
            # Use default safe parameters
            parameters = param_spaces.get_safe_parameters()
        
        # Validate
        is_valid, errors = param_spaces.validate_parameters(parameters)
        
        if is_valid:
            logger.info("✓ Parameters are valid for production")
            
            # Show parameter summary
            for category, params in parameters.items():
                logger.info(f"\n{category}:")
                for key, value in params.items():
                    logger.info(f"  {key}: {value}")
        else:
            logger.error("✗ Parameter validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
        
        return is_valid
    
    def run_diagnostics(self) -> Dict[str, Any]:
        """Run system diagnostics."""
        diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # Check Python version
        import sys
        diagnostics['checks']['python_version'] = {
            'status': 'pass' if sys.version_info >= (3, 11) else 'fail',
            'value': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        }
        
        # Check Optuna version
        try:
            import optuna
            version = optuna.__version__
            diagnostics['checks']['optuna_version'] = {
                'status': 'pass' if version >= '3.6.0' else 'fail',
                'value': version
            }
        except ImportError:
            diagnostics['checks']['optuna_version'] = {
                'status': 'fail',
                'value': 'not installed'
            }
        
        # Check cache connectivity
        try:
            import memcache
            mc = memcache.Client(['localhost:11211'])
            mc.set('test', 'test', time=1)
            diagnostics['checks']['memcached'] = {
                'status': 'pass',
                'value': 'connected'
            }
        except Exception as e:
            diagnostics['checks']['memcached'] = {
                'status': 'fail',
                'value': str(e)
            }
        
        # Check Redis connectivity
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379)
            r.ping()
            diagnostics['checks']['redis'] = {
                'status': 'pass',
                'value': 'connected'
            }
        except Exception as e:
            diagnostics['checks']['redis'] = {
                'status': 'warning',
                'value': str(e)
            }
        
        # Check resource availability
        import psutil
        memory = psutil.virtual_memory()
        diagnostics['checks']['memory'] = {
            'status': 'pass' if memory.available > 2 * 1024**3 else 'warning',
            'value': f"{memory.available / 1024**3:.2f}GB available"
        }
        
        cpu_count = psutil.cpu_count()
        diagnostics['checks']['cpu'] = {
            'status': 'pass' if cpu_count >= 2 else 'warning',
            'value': f"{cpu_count} cores"
        }
        
        # Check configuration
        diagnostics['checks']['configuration'] = {
            'status': 'pass' if self.config else 'fail',
            'value': 'loaded' if self.config else 'not found'
        }
        
        # Check storage
        storage_path = Path("data/optuna")
        diagnostics['checks']['storage'] = {
            'status': 'pass' if storage_path.exists() else 'warning',
            'value': str(storage_path.absolute())
        }
        
        return diagnostics
    
    def benchmark(self, n_trials: int = 10) -> Dict[str, Any]:
        """Run optimization benchmark."""
        logger.info(f"Running benchmark with {n_trials} trials...")
        
        benchmark_results = {
            'n_trials': n_trials,
            'start_time': datetime.now().isoformat(),
            'results': []
        }
        
        # Create test study
        study = self.engine.create_study(
            study_name=f"benchmark_{datetime.now():%Y%m%d_%H%M%S}",
            directions='maximize',
            sampler='TPE',
            pruner='MedianPruner'
        )
        
        # Simple test objective
        def test_objective(trial):
            x = trial.suggest_float('x', -10, 10)
            y = trial.suggest_float('y', -10, 10)
            return -(x**2 + y**2)  # Simple sphere function
        
        start = time.time()
        
        try:
            study = self.engine.optimize_with_safety(
                study_name=study.study_name,
                objective_func=test_objective,
                n_trials=n_trials,
                timeout=300,
                n_jobs=1
            )
            
            elapsed = time.time() - start
            
            benchmark_results['elapsed_seconds'] = elapsed
            benchmark_results['trials_per_second'] = n_trials / elapsed
            benchmark_results['best_value'] = study.best_value
            benchmark_results['best_params'] = study.best_params
            benchmark_results['status'] = 'success'
            
            logger.info(f"Benchmark completed: {n_trials} trials in {elapsed:.2f}s")
            logger.info(f"Performance: {benchmark_results['trials_per_second']:.2f} trials/second")
            
        except Exception as e:
            benchmark_results['status'] = 'failed'
            benchmark_results['error'] = str(e)
            logger.error(f"Benchmark failed: {e}")
        
        return benchmark_results


def main():
    """Main entry point for optimization management."""
    parser = argparse.ArgumentParser(
        description="Manage Optuna optimization for Virtuoso trading system"
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/optuna_config.yaml',
        help='Path to configuration file'
    )
    
    # Commands
    parser.add_argument(
        '--start',
        action='store_true',
        help='Start optimization study'
    )
    
    parser.add_argument(
        '--study-type',
        type=str,
        default='production_safety',
        help='Type of study to run'
    )
    
    parser.add_argument(
        '--n-trials',
        type=int,
        help='Number of trials to run'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        help='Timeout in seconds'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show optimization status'
    )
    
    parser.add_argument(
        '--list-studies',
        action='store_true',
        help='List all studies'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate parameter configuration'
    )
    
    parser.add_argument(
        '--validate-file',
        type=str,
        help='Parameter file to validate'
    )
    
    parser.add_argument(
        '--diagnostics',
        action='store_true',
        help='Run system diagnostics'
    )
    
    parser.add_argument(
        '--benchmark',
        action='store_true',
        help='Run performance benchmark'
    )
    
    parser.add_argument(
        '--benchmark-trials',
        type=int,
        default=10,
        help='Number of trials for benchmark'
    )
    
    args = parser.parse_args()
    
    # Create manager
    manager = OptimizationManager(config_path=args.config)
    
    # Run diagnostics first if requested
    if args.diagnostics:
        print("\n=== System Diagnostics ===")
        diagnostics = manager.run_diagnostics()
        
        all_pass = True
        for check, result in diagnostics['checks'].items():
            status_symbol = "✓" if result['status'] == 'pass' else "✗" if result['status'] == 'fail' else "⚠"
            print(f"{status_symbol} {check}: {result['value']}")
            if result['status'] == 'fail':
                all_pass = False
        
        if not all_pass:
            print("\n⚠ Some checks failed. Please resolve issues before running optimization.")
            sys.exit(1)
        else:
            print("\n✓ All checks passed")
    
    # Initialize if needed for other commands
    if args.start or args.status or args.list_studies or args.benchmark:
        manager.initialize()
    
    # Execute command
    if args.start:
        success = manager.start_optimization(
            study_type=args.study_type,
            n_trials=args.n_trials,
            timeout=args.timeout
        )
        sys.exit(0 if success else 1)
    
    elif args.status:
        status = manager.get_status()
        print("\n=== Optimization Status ===")
        print(json.dumps(status, indent=2))
    
    elif args.list_studies:
        studies = manager.list_studies()
        print("\n=== Available Studies ===")
        for study in studies:
            print(f"\n{study['name']}:")
            print(f"  Status: {study['status']}")
            print(f"  Trials: {study['trials']}")
            print(f"  Best Value: {study['best_value']}")
    
    elif args.validate:
        manager.validate_parameters(args.validate_file)
    
    elif args.benchmark:
        results = manager.benchmark(args.benchmark_trials)
        print("\n=== Benchmark Results ===")
        print(json.dumps(results, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
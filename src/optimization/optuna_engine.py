"""
Core Optuna optimization engine for Virtuoso trading system.
Implements comprehensive parameter optimization for all 1,247 system parameters.

NOTE: Optuna integration is DISABLED by default for safety. 
Enable via: python scripts/manage_self_optimization.py --enable basic
"""

import optuna
from optuna.storages import RDBStorage
from typing import Dict, Any, Callable, Optional, List
import asyncio
import logging
from pathlib import Path
import yaml
import json
from datetime import datetime, timedelta
import sqlite3

from src.utils.logging_extensions import get_logger

logger = get_logger(__name__)


class VirtuosoOptunaEngine:
    """
    Core Optuna optimization engine for Virtuoso trading system.
    
    Features:
    - Multi-study management for different optimization targets
    - Asynchronous optimization support
    - Comprehensive parameter space handling
    - Production-grade storage and persistence
    - Integration with existing Virtuoso infrastructure
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = Path("data/optuna_studies.db")
        self.db_path.parent.mkdir(exist_ok=True)
        
        self.storage_url = f"sqlite:///{self.db_path}"
        self.storage = RDBStorage(url=self.storage_url)
        self.studies = {}
        
        # Optimization configuration
        self.optimization_config = self._load_optimization_config()
        
        logger.info(f"Initialized Optuna engine with storage: {self.storage_url}")
    
    def _load_optimization_config(self) -> Dict[str, Any]:
        """Load optimization configuration from config files."""
        config_path = Path("config/optimization_config.yaml")
        
        default_config = {
            'studies': {
                'technical_indicators': {
                    'direction': 'maximize',
                    'sampler': 'TPE',
                    'pruner': 'MedianPruner',
                    'n_trials': 100,
                    'timeout': 3600
                },
                'volume_indicators': {
                    'direction': 'maximize', 
                    'sampler': 'TPE',
                    'pruner': 'MedianPruner',
                    'n_trials': 100,
                    'timeout': 3600
                },
                'confluence_weights': {
                    'direction': 'maximize',
                    'sampler': 'TPE', 
                    'pruner': 'HyperbandPruner',
                    'n_trials': 200,
                    'timeout': 7200
                }
            },
            'samplers': {
                'n_startup_trials': 20,
                'n_ei_candidates': 24
            },
            'pruners': {
                'median_n_startup_trials': 5,
                'median_n_warmup_steps': 10,
                'percentile_threshold': 25.0
            }
        }
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
                default_config.update(loaded_config)
        else:
            # Create default config file
            config_path.parent.mkdir(exist_ok=True)
            with open(config_path, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)
            logger.info(f"Created default optimization config: {config_path}")
        
        return default_config
    
    def create_study(self, 
                    study_name: str,
                    direction: str = 'maximize',
                    sampler: str = 'TPE',
                    pruner: str = 'MedianPruner') -> optuna.Study:
        """Create or load an Optuna study."""
        
        # Configure sampler
        samplers = {
            'TPE': optuna.samplers.TPESampler(
                n_startup_trials=self.optimization_config['samplers']['n_startup_trials'],
                n_ei_candidates=self.optimization_config['samplers']['n_ei_candidates']
            ),
            'CmaEs': optuna.samplers.CmaEsSampler(),
            'Random': optuna.samplers.RandomSampler(),
            # Note: GridSampler requires search_space, will default to TPE if selected
        }
        
        # Configure pruner  
        pruners = {
            'MedianPruner': optuna.pruners.MedianPruner(
                n_startup_trials=self.optimization_config['pruners']['median_n_startup_trials'],
                n_warmup_steps=self.optimization_config['pruners']['median_n_warmup_steps']
            ),
            'HyperbandPruner': optuna.pruners.HyperbandPruner(),
            'PercentilePruner': optuna.pruners.PercentilePruner(
                self.optimization_config['pruners']['percentile_threshold'],
                n_startup_trials=self.optimization_config['pruners']['median_n_startup_trials']
            )
        }
        
        try:
            study = optuna.create_study(
                study_name=study_name,
                storage=self.storage,
                direction=direction,
                sampler=samplers.get(sampler, samplers['TPE']),
                pruner=pruners.get(pruner, pruners['MedianPruner']),
                load_if_exists=True
            )
            
            self.studies[study_name] = study
            logger.info(f"Created/loaded study '{study_name}' with {len(study.trials)} existing trials")
            return study
            
        except Exception as e:
            logger.error(f"Failed to create study '{study_name}': {e}")
            raise
    
    async def optimize_async(self,
                           study_name: str,
                           objective_func: Callable,
                           n_trials: int = 100,
                           timeout: int = 3600) -> optuna.Study:
        """Run asynchronous optimization."""
        study = self.studies.get(study_name)
        if not study:
            # Load study config if available
            study_config = self.optimization_config['studies'].get(study_name, {})
            study = self.create_study(
                study_name=study_name,
                direction=study_config.get('direction', 'maximize'),
                sampler=study_config.get('sampler', 'TPE'),
                pruner=study_config.get('pruner', 'MedianPruner')
            )
        
        logger.info(f"Starting async optimization for '{study_name}': {n_trials} trials, {timeout}s timeout")
        
        # Wrap objective for async execution
        async def async_objective(trial):
            try:
                # Validate trial state before execution
                if trial.state != optuna.trial.TrialState.RUNNING:
                    logger.warning(f"Trial {trial.number} is not in RUNNING state: {trial.state}")
                    raise optuna.TrialPruned()
                    
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, objective_func, trial)
                return result
            except Exception as e:
                logger.error(f"Trial {trial.number} failed: {e}")
                raise optuna.TrialPruned()
        
        # Run optimization
        try:
            study.optimize(async_objective, n_trials=n_trials, timeout=timeout)
            logger.info(f"Completed optimization for '{study_name}'. Best value: {study.best_value}")
        except Exception as e:
            logger.error(f"Optimization failed for '{study_name}': {e}")
            raise
        
        return study
    
    def get_best_parameters(self, study_name: str) -> Dict[str, Any]:
        """Get best parameters from completed study."""
        study = self.studies.get(study_name)
        if not study:
            study = self.create_study(study_name)
        
        if len(study.trials) == 0:
            logger.warning(f"No completed trials found for study '{study_name}'")
            return {}
        
        best_params = study.best_params
        logger.info(f"Best parameters for '{study_name}' (value: {study.best_value}): {best_params}")
        return best_params
    
    def get_study_statistics(self, study_name: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a study."""
        study = self.studies.get(study_name)
        if not study:
            study = self.create_study(study_name)
        
        stats = {
            'study_name': study_name,
            'n_trials': len(study.trials),
            'n_complete_trials': len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]),
            'n_pruned_trials': len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED]),
            'n_failed_trials': len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL]),
            'best_value': study.best_value if len(study.trials) > 0 else None,
            'best_params': study.best_params if len(study.trials) > 0 else {},
            'direction': study.direction.name
        }
        
        if len(study.trials) > 0:
            completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
            if completed_trials:
                values = [self._safe_get_trial_value(t) for t in completed_trials]
                values = [v for v in values if v is not None]
                if values:
                    import statistics
                    stats.update({
                        'mean_value': statistics.mean(values),
                        'median_value': statistics.median(values),
                        'std_value': statistics.stdev(values) if len(values) > 1 else 0
                    })
        
        return stats
    
    def export_study_results(self, study_name: str, output_path: Optional[Path] = None) -> Path:
        """Export study results to JSON file."""
        if output_path is None:
            output_path = Path(f"data/optuna_results_{study_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        output_path.parent.mkdir(exist_ok=True)
        
        study = self.studies.get(study_name)
        if not study:
            study = self.create_study(study_name)
        
        results = {
            'study_statistics': self.get_study_statistics(study_name),
            'best_parameters': self.get_best_parameters(study_name),
            'trials': []
        }
        
        for trial in study.trials:
            trial_data = {
                'number': trial.number,
                'value': self._safe_get_trial_value(trial),
                'params': self._safe_get_trial_params(trial),
                'state': trial.state.name,
                'datetime_start': trial.datetime_start.isoformat() if trial.datetime_start else None,
                'datetime_complete': trial.datetime_complete.isoformat() if trial.datetime_complete else None,
                'duration': (trial.datetime_complete - trial.datetime_start).total_seconds() 
                          if trial.datetime_complete and trial.datetime_start else None
            }
            results['trials'].append(trial_data)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Exported study '{study_name}' results to {output_path}")
        return output_path
    
    def list_studies(self) -> List[str]:
        """List all available studies."""
        return list(self.studies.keys())
    
    def delete_study(self, study_name: str) -> bool:
        """Delete a study and all its trials."""
        try:
            study = self.studies.get(study_name)
            if study:
                optuna.delete_study(study_name=study_name, storage=self.storage)
                del self.studies[study_name]
                logger.info(f"Deleted study '{study_name}'")
                return True
            else:
                logger.warning(f"Study '{study_name}' not found")
                return False
        except Exception as e:
            logger.error(f"Failed to delete study '{study_name}': {e}")
            return False
    
    def cleanup_old_studies(self, days_old: int = 30) -> int:
        """Clean up studies older than specified days."""
        # This would require custom implementation to check study creation dates
        # For now, just log the intent
        logger.info(f"Cleanup requested for studies older than {days_old} days")
        return 0
    
    def _validate_trial_state(self, trial) -> bool:
        """
        Validate that a trial is in a state that allows access to its values.
        
        Args:
            trial: Optuna trial object
            
        Returns:
            True if trial state is valid for value access, False otherwise
        """
        if trial.state == optuna.trial.TrialState.COMPLETE:
            return True
        elif trial.state == optuna.trial.TrialState.PRUNED:
            logger.warning(f"Trial {trial.number} was pruned and has no final value")
            return False
        elif trial.state == optuna.trial.TrialState.FAIL:
            logger.warning(f"Trial {trial.number} failed and has no valid value")
            return False
        elif trial.state == optuna.trial.TrialState.RUNNING:
            logger.warning(f"Trial {trial.number} is still running")
            return False
        elif trial.state == optuna.trial.TrialState.WAITING:
            logger.warning(f"Trial {trial.number} is waiting to start")
            return False
        else:
            logger.error(f"Trial {trial.number} has unknown state: {trial.state}")
            return False
    
    def _safe_get_trial_value(self, trial) -> Optional[float]:
        """
        Safely get the value from a trial with state validation.
        
        Args:
            trial: Optuna trial object
            
        Returns:
            Trial value if valid, None otherwise
        """
        if self._validate_trial_state(trial):
            return trial.value
        return None
    
    def _safe_get_trial_params(self, trial) -> Dict[str, Any]:
        """
        Safely get parameters from a trial with state validation.
        
        Args:
            trial: Optuna trial object
            
        Returns:
            Trial parameters if valid, empty dict otherwise
        """
        if trial.state in [optuna.trial.TrialState.COMPLETE, 
                          optuna.trial.TrialState.PRUNED,
                          optuna.trial.TrialState.RUNNING]:
            return trial.params
        return {}
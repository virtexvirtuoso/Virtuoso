#!/usr/bin/env python3
"""
Simple test to verify Optuna v3.6+ implementation works.
Tests basic parameter optimization without complex trading objectives.
"""

import sys
import os
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

import optuna
import yaml
from pathlib import Path

def simple_objective(trial):
    """Simple quadratic objective for testing."""
    x = trial.suggest_float('x', -10, 10)
    y = trial.suggest_float('y', -10, 10)
    return -(x - 2)**2 - (y + 5)**2

def test_optuna_integration():
    """Test basic Optuna integration."""
    print("🧪 Testing Optuna v3.6+ integration...")
    
    # Load configuration
    config_path = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/optuna_config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Create simple study
    storage_url = config.get('storage', {}).get('url', 'sqlite:///data/optuna/test_studies.db')
    
    try:
        study = optuna.create_study(
            study_name="simple_test",
            storage=storage_url,
            direction="maximize",
            load_if_exists=True
        )
        
        print(f"✓ Study created: {study.study_name}")
        
        # Run optimization
        study.optimize(simple_objective, n_trials=5, timeout=30)
        
        print(f"✓ Optimization completed!")
        print(f"  - Best value: {study.best_value:.4f}")
        print(f"  - Best params: {study.best_params}")
        print(f"  - Number of trials: {len(study.trials)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_optuna_integration()
    sys.exit(0 if success else 1)
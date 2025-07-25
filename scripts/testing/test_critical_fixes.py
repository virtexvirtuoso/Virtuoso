#!/usr/bin/env python3
"""
Test script for critical fixes implemented in the codebase.
Tests the following fixes:
1. Numba prange race conditions
2. Mutable default arguments
3. Float validation for mplfinance
4. Trial state validation in Optuna
"""

import sys
import os
import asyncio
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logging_extensions import get_logger

logger = get_logger(__name__)

def test_numba_jit_fixes():
    """Test that Numba JIT functions work without race conditions."""
    logger.info("Testing Numba JIT fixes...")
    
    try:
        from src.indicators.price_structure_jit import fast_sr_detection
        from src.indicators.orderflow_jit import fast_cvd_calculation
        
        # Generate test data
        n = 1000
        prices = 100 + np.cumsum(np.random.randn(n) * 0.1)
        highs = prices * 1.01
        lows = prices * 0.99
        volumes = np.random.rand(n) * 1000
        close_prices = prices
        lookback_periods = np.array([10, 20, 50])
        sides = np.random.choice([-1, 0, 1], size=n)
        
        # Test price structure detection (no prange)
        logger.info("Testing fast_sr_detection...")
        support_levels, resistance_levels, level_strengths = fast_sr_detection(
            highs, lows, volumes, close_prices, lookback_periods
        )
        assert support_levels.shape == (n, len(lookback_periods))
        assert not np.any(np.isnan(support_levels))
        logger.info("✅ fast_sr_detection passed")
        
        # Test CVD calculation (no prange issues)
        logger.info("Testing fast_cvd_calculation...")
        cvd_total, buy_volume, sell_volume = fast_cvd_calculation(prices, volumes, sides)
        assert not np.isnan(cvd_total)
        assert buy_volume >= 0
        assert sell_volume >= 0
        logger.info("✅ fast_cvd_calculation passed")
        
        logger.info("✅ All Numba JIT tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Numba JIT test failed: {e}")
        return False

async def test_mutable_defaults_fix():
    """Test that mutable default arguments are fixed."""
    logger.info("Testing mutable default arguments fix...")
    
    try:
        from src.core.exchanges.bybit import BybitExchange
        
        # Test that params default is None in the method signature
        import inspect
        fetch_trades_sig = inspect.signature(BybitExchange.fetch_trades)
        params_default = fetch_trades_sig.parameters['params'].default
        
        assert params_default is None, "params should default to None, not {}"
        logger.info("✅ Mutable default arguments test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Mutable defaults test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mplfinance_float_validation():
    """Test float validation for mplfinance."""
    logger.info("Testing mplfinance float validation...")
    
    try:
        # Check if the float validation code exists in the files
        report_gen_path = Path('src/monitoring/report_generator.py')
        pdf_gen_path = Path('src/core/reporting/pdf_generator.py')
        
        # Read the files and check for float validation code
        validation_found = {'report_gen': False, 'pdf_gen': False}
        
        with open(report_gen_path, 'r') as f:
            content = f.read()
            if 'pd.to_numeric' in content and 'errors=\'coerce\'' in content:
                validation_found['report_gen'] = True
                logger.info("✅ Found float validation in report_generator.py")
        
        with open(pdf_gen_path, 'r') as f:
            content = f.read()
            if 'pd.to_numeric' in content and 'errors=\'coerce\'' in content:
                validation_found['pdf_gen'] = True
                logger.info("✅ Found float validation in pdf_generator.py")
        
        # Both files should have float validation
        assert validation_found['report_gen'], "Float validation not found in report_generator.py"
        assert validation_found['pdf_gen'], "Float validation not found in pdf_generator.py"
        
        logger.info("✅ All mplfinance float validation tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ mplfinance float validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_optuna_trial_validation():
    """Test Optuna trial state validation."""
    logger.info("Testing Optuna trial state validation...")
    
    try:
        from src.optimization.optuna_engine import VirtuosoOptunaEngine
        import optuna
        
        # Create engine instance
        engine = VirtuosoOptunaEngine({'optimization': {'enabled': True}})
        
        # Check that safe methods exist
        assert hasattr(engine, '_validate_trial_state')
        assert hasattr(engine, '_safe_get_trial_value')
        assert hasattr(engine, '_safe_get_trial_params')
        
        # Create a mock trial for testing
        class MockTrial:
            def __init__(self, state, number=1, value=None, params=None):
                self.state = state
                self.number = number
                self.value = value
                self.params = params or {}
        
        # Test different trial states
        complete_trial = MockTrial(optuna.trial.TrialState.COMPLETE, value=0.8, params={'x': 1})
        pruned_trial = MockTrial(optuna.trial.TrialState.PRUNED)
        failed_trial = MockTrial(optuna.trial.TrialState.FAIL)
        
        # Test validation
        assert engine._validate_trial_state(complete_trial) == True
        assert engine._validate_trial_state(pruned_trial) == False
        assert engine._validate_trial_state(failed_trial) == False
        
        # Test safe value access
        assert engine._safe_get_trial_value(complete_trial) == 0.8
        assert engine._safe_get_trial_value(pruned_trial) is None
        assert engine._safe_get_trial_value(failed_trial) is None
        
        # Test safe params access
        assert engine._safe_get_trial_params(complete_trial) == {'x': 1}
        assert engine._safe_get_trial_params(pruned_trial) == {}
        assert engine._safe_get_trial_params(failed_trial) == {}
        
        logger.info("✅ All Optuna trial validation tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Optuna trial validation test failed: {e}")
        return False

async def main():
    """Run all tests."""
    logger.info("Starting critical fixes tests...")
    
    results = {
        'numba_jit': test_numba_jit_fixes(),
        'mutable_defaults': await test_mutable_defaults_fix(),
        'mplfinance_validation': test_mplfinance_float_validation(),
        'optuna_validation': test_optuna_trial_validation()
    }
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("="*50)
    
    if all_passed:
        print("🎉 All critical fixes tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Please check the logs above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
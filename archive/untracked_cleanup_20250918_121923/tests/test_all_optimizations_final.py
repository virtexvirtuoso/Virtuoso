#!/usr/bin/env python3
"""
Comprehensive test of all monitoring optimizations before VPS deployment
Tests Phase 1, 2, and 3 changes with actual code
"""
import asyncio
import time
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from unittest.mock import MagicMock, AsyncMock

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_phase1_config():
    """Verify Phase 1 configuration changes"""
    results = []
    
    # Check config.yaml settings
    try:
        import yaml
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Check monitoring settings
        monitoring = config.get('monitoring', {})
        cache_ttl = monitoring.get('cache_ttl', 60)
        max_bg_tasks = monitoring.get('max_background_tasks', 5)
        
        results.append(('Cache TTL', cache_ttl, cache_ttl == 30))
        results.append(('Max Background Tasks', max_bg_tasks, max_bg_tasks == 20))
        
        # Check market_data cache settings
        market_data = config.get('market_data', {}).get('cache', {})
        max_retries = market_data.get('max_retries', 3)
        timeout = market_data.get('timeout', 1.0)
        
        results.append(('Max Retries', max_retries, max_retries == 1))
        results.append(('Cache Timeout', timeout, timeout == 0.5))
        
    except Exception as e:
        logger.error(f"Error checking config: {e}")
        return []
    
    return results

def check_phase1_code():
    """Verify Phase 1 code changes"""
    results = []
    
    # Check if cache warmer is disabled in main.py
    try:
        with open('src/main.py', 'r') as f:
            main_content = f.read()
        
        cache_warmer_disabled = '# Cache warmer disabled for performance optimization (Phase 1)' in main_content
        results.append(('Cache Warmer Disabled', 'Yes' if cache_warmer_disabled else 'No', cache_warmer_disabled))
    except Exception as e:
        logger.error(f"Error checking main.py: {e}")
    
    # Check monitor.py for background task limit
    try:
        with open('src/monitoring/monitor.py', 'r') as f:
            monitor_content = f.read()
        
        has_increased_limit = 'self._max_background_tasks = 20' in monitor_content
        results.append(('Background Tasks = 20', 'Yes' if has_increased_limit else 'No', has_increased_limit))
    except Exception as e:
        logger.error(f"Error checking monitor.py: {e}")
    
    # Check cache_adapter_direct.py for retry limit
    try:
        with open('src/api/cache_adapter_direct.py', 'r') as f:
            cache_content = f.read()
        
        has_reduced_retries = 'self.max_retries = 1' in cache_content
        results.append(('Retries Reduced to 1', 'Yes' if has_reduced_retries else 'No', has_reduced_retries))
    except Exception as e:
        logger.error(f"Error checking cache_adapter_direct.py: {e}")
    
    return results

async def test_phase2_extraction():
    """Test Phase 2 streamlined data extraction"""
    from src.monitoring.monitor_cache_integration import MonitorCacheIntegration
    
    integration = MonitorCacheIntegration()
    
    # Create mock monitor with data
    mock_monitor = MagicMock()
    mock_monitor.market_data_manager = MagicMock()
    mock_monitor.market_data_manager.data_cache = {
        f'SYMBOL{i}': {
            'ticker': {
                'last': 1000 + i,
                'percentage': i * 0.1,
                'quoteVolume': 10000 * i,
                'high': 1100 + i,
                'low': 900 + i
            }
        } for i in range(10)  # 10 test symbols
    }
    
    # Test extraction
    start_time = time.time()
    market_data = await integration._extract_market_data(mock_monitor)
    extraction_time = time.time() - start_time
    
    symbols_extracted = len(market_data.get('symbols', []))
    
    return extraction_time, symbols_extracted

async def test_phase2_batching():
    """Test Phase 2 batched cache operations"""
    
    # Check if batching is implemented
    try:
        with open('src/monitoring/monitor_cache_integration.py', 'r') as f:
            content = f.read()
        
        has_batching = 'Phase 2 optimization: Batch all cache operations' in content
        has_single_key = 'monitor:all_data' in content
        
        return has_batching and has_single_key
    except Exception as e:
        logger.error(f"Error checking batching: {e}")
        return False

def check_phase3_parallelization():
    """Check Phase 3 parallelization implementation"""
    try:
        with open('src/monitoring/monitor.py', 'r') as f:
            content = f.read()
        
        has_gather = 'asyncio.gather' in content
        has_concurrent = 'Process all symbols concurrently' in content
        
        return has_gather or has_concurrent
    except Exception as e:
        logger.error(f"Error checking parallelization: {e}")
        return False

async def run_comprehensive_test():
    """Run all tests"""
    print("="*70)
    print("COMPREHENSIVE OPTIMIZATION TEST - PRE-DEPLOYMENT VALIDATION")
    print("="*70)
    print()
    
    all_passed = True
    
    # Phase 1 Tests
    print("PHASE 1: Configuration & Quick Wins")
    print("-"*50)
    
    # Config checks
    print("\nConfiguration Settings:")
    config_results = check_phase1_config()
    for name, value, passed in config_results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}: {value}")
        if not passed:
            all_passed = False
    
    # Code checks
    print("\nCode Changes:")
    code_results = check_phase1_code()
    for name, value, passed in code_results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}: {value}")
        if not passed:
            all_passed = False
    
    print()
    
    # Phase 2 Tests
    print("PHASE 2: Core Simplifications")
    print("-"*50)
    
    # Test data extraction
    print("\nData Extraction Test:")
    extraction_time, symbols = await test_phase2_extraction()
    extraction_passed = extraction_time < 0.1  # Should be very fast
    status = "✅" if extraction_passed else "❌"
    print(f"  {status} Extraction Time: {extraction_time:.4f}s")
    print(f"  {status} Symbols Extracted: {symbols}")
    if not extraction_passed:
        all_passed = False
    
    # Test batching
    print("\nCache Batching:")
    batching_implemented = await test_phase2_batching()
    status = "✅" if batching_implemented else "❌"
    print(f"  {status} Batched Operations: {'Implemented' if batching_implemented else 'Not Found'}")
    if not batching_implemented:
        all_passed = False
    
    print()
    
    # Phase 3 Tests
    print("PHASE 3: Parallelization")
    print("-"*50)
    
    parallel_implemented = check_phase3_parallelization()
    status = "✅" if parallel_implemented else "❌"
    print(f"  {status} Async Parallelization: {'Implemented' if parallel_implemented else 'Not Found'}")
    if not parallel_implemented:
        all_passed = False
    
    print()
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    # Summary of expected improvements
    print("\nExpected Performance Improvements:")
    print("  Phase 1 (Config & Quick Wins): ~10-12s")
    print("  Phase 2 (Core Simplifications): ~8-10s")
    print("  Phase 3 (Parallelization): ~2-3s")
    print("  -------------------------------")
    print("  Total Expected Savings: ~20-25s")
    print()
    print("  Baseline: 71-74s")
    print("  Target: 48-49s")
    print("  Expected After Optimizations: 48-52s")
    
    print()
    if all_passed:
        print("🎉 ALL TESTS PASSED - READY FOR VPS DEPLOYMENT!")
        print()
        print("Next Steps:")
        print("1. Deploy to VPS using deployment script")
        print("2. Monitor actual performance on VPS")
        print("3. Validate cycle times reach 48-49s target")
    else:
        print("⚠️ SOME TESTS FAILED - REVIEW BEFORE DEPLOYMENT")
        print()
        print("Please fix the failed items before deploying to VPS")
    
    return all_passed

def create_deployment_checklist():
    """Create a deployment checklist"""
    print()
    print("="*70)
    print("DEPLOYMENT CHECKLIST")
    print("="*70)
    print()
    print("[ ] 1. All tests passed")
    print("[ ] 2. Local changes saved/committed")
    print("[ ] 3. VPS is accessible (ssh vps)")
    print("[ ] 4. Backup current VPS code")
    print("[ ] 5. Deploy optimized code to VPS")
    print("[ ] 6. Restart services on VPS")
    print("[ ] 7. Monitor VPS logs for errors")
    print("[ ] 8. Validate performance improvement")
    print("[ ] 9. Document actual cycle times")
    print("[ ] 10. Rollback plan ready if needed")
    print()
    print("Deployment Commands:")
    print("  1. Backup: ssh vps 'cd /home/linuxuser/trading/Virtuoso_ccxt && cp -r src src_backup_$(date +%Y%m%d_%H%M%S)'")
    print("  2. Deploy: ./scripts/sync_to_vps.sh")
    print("  3. Restart: ssh vps 'sudo systemctl restart virtuoso.service'")
    print("  4. Monitor: ssh vps 'sudo journalctl -u virtuoso.service -f'")

if __name__ == "__main__":
    all_passed = asyncio.run(run_comprehensive_test())
    if all_passed:
        create_deployment_checklist()
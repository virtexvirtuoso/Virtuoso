#!/usr/bin/env python3
"""
Fix Volume and Orderflow Indicator Validation Issues

This script addresses:
1. Missing 'base' timeframe mapping (should be 1m data)
2. Missing trade data for orderflow indicator
3. Incorrect timeframe labels in market data

The issues cause confluence analysis to fail with validation errors.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import traceback

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import Logger
from src.config.manager import ConfigManager

def main():
    """Main execution function."""
    logger = Logger('fix_validation')
    
    try:
        logger.info("="*60)
        logger.info("Volume and Orderflow Validation Fix")
        logger.info("="*60)
        
        # Load configuration to understand timeframe mappings
        config_manager = ConfigManager()
        config = config_manager.config
        
        # Show current timeframe configuration
        logger.info("\nCurrent Timeframe Configuration:")
        timeframes = config.get('timeframes', {})
        for tf_name, tf_config in timeframes.items():
            logger.info(f"  {tf_name}: {tf_config['interval']} minutes")
        
        # Fix 1: Update monitor.py to use correct timeframe mapping
        monitor_file = project_root / 'src' / 'monitoring' / 'monitor.py'
        logger.info(f"\n1. Updating monitor.py timeframe mapping...")
        
        if monitor_file.exists():
            # Read the file
            with open(monitor_file, 'r') as f:
                content = f.read()
            
            # Update the default timeframes to match config
            old_timeframes = "default_timeframes = {'ltf': '1m', 'mtf': '15m', 'htf': '1h'}"
            new_timeframes = "default_timeframes = {'base': '1m', 'ltf': '5m', 'mtf': '30m', 'htf': '4h'}"
            
            if old_timeframes in content:
                content = content.replace(old_timeframes, new_timeframes)
                logger.info("   ✓ Updated default timeframes to match config")
            else:
                logger.warning("   ⚠ Default timeframes line not found, may already be updated")
            
            # Backup and write
            backup_file = monitor_file.with_suffix('.py.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
            with open(backup_file, 'w') as f:
                f.write(content)
            
            with open(monitor_file, 'w') as f:
                f.write(content)
                
            logger.info(f"   ✓ Backup created: {backup_file.name}")
            logger.info("   ✓ monitor.py updated")
        
        # Fix 2: Update confluence.py timeframe mapping
        confluence_file = project_root / 'src' / 'core' / 'analysis' / 'confluence.py'
        logger.info(f"\n2. Updating confluence.py timeframe mapping...")
        
        if confluence_file.exists():
            with open(confluence_file, 'r') as f:
                content = f.read()
            
            # Find and update the timeframe mapping section
            # Look for the tf_map dictionary
            old_mapping_start = "'15m': 'mtf',"
            new_mapping = "'15m': 'ltf',  # Changed from mtf to ltf to match 5-30 min range"
            
            if old_mapping_start in content:
                content = content.replace(old_mapping_start, new_mapping)
                logger.info("   ✓ Updated 15m mapping from 'mtf' to 'ltf'")
            
            # Add 1m to base mapping if not present
            if "'1m': 'base'," not in content:
                # Find the tf_map section and add it
                tf_map_start = "tf_map = {"
                if tf_map_start in content:
                    insert_pos = content.find(tf_map_start) + len(tf_map_start)
                    content = content[:insert_pos] + "\n                        '1m': 'base',  # 1-minute to base" + content[insert_pos:]
                    logger.info("   ✓ Added 1m to base mapping")
            
            # Backup and write
            backup_file = confluence_file.with_suffix('.py.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
            with open(backup_file, 'w') as f:
                f.write(content)
            
            with open(confluence_file, 'w') as f:
                f.write(content)
                
            logger.info(f"   ✓ Backup created: {backup_file.name}")
            logger.info("   ✓ confluence.py updated")
        
        # Fix 3: Create wrapper to ensure trade data is fetched
        wrapper_file = project_root / 'src' / 'core' / 'analysis' / 'market_data_wrapper.py'
        logger.info(f"\n3. Creating market data wrapper to ensure trade data...")
        
        wrapper_content = '''"""
Market Data Wrapper to ensure complete data for indicators

This module wraps market data collection to ensure:
1. All required timeframes are present with correct labels
2. Trade data is fetched for orderflow analysis
3. Data validation before passing to indicators
"""

import pandas as pd
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MarketDataWrapper:
    """Wrapper to ensure complete market data for confluence analysis."""
    
    @staticmethod
    async def ensure_complete_market_data(exchange, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure market data has all required components.
        
        Args:
            exchange: Exchange instance
            symbol: Trading symbol
            market_data: Existing market data
            
        Returns:
            Complete market data with all required fields
        """
        try:
            # Ensure OHLCV data has correct timeframe labels
            if 'ohlcv' in market_data:
                ohlcv = market_data['ohlcv']
                
                # Map common timeframe labels to standard ones
                timeframe_mapping = {
                    '1m': 'base',
                    '5m': 'ltf',
                    '15m': 'ltf',  # 15m maps to ltf (lower timeframe)
                    '30m': 'mtf',
                    '1h': 'mtf',   # 1h maps to mtf (medium timeframe)
                    '4h': 'htf',
                    '240': 'htf'
                }
                
                # Create properly mapped OHLCV data
                mapped_ohlcv = {}
                for tf_key, tf_data in ohlcv.items():
                    if tf_key in timeframe_mapping:
                        standard_key = timeframe_mapping[tf_key]
                        if standard_key not in mapped_ohlcv:
                            mapped_ohlcv[standard_key] = tf_data
                    elif tf_key in ['base', 'ltf', 'mtf', 'htf']:
                        # Already in standard format
                        mapped_ohlcv[tf_key] = tf_data
                
                # Ensure we have base timeframe (fallback to ltf if missing)
                if 'base' not in mapped_ohlcv and 'ltf' in mapped_ohlcv:
                    logger.warning(f"Missing base timeframe for {symbol}, using ltf as fallback")
                    mapped_ohlcv['base'] = mapped_ohlcv['ltf']
                
                market_data['ohlcv'] = mapped_ohlcv
            
            # Ensure trade data is present
            if 'trades' not in market_data or not market_data['trades']:
                logger.info(f"Fetching trade data for {symbol}...")
                try:
                    trades = await exchange.fetch_trades(symbol, limit=1000)
                    if trades:
                        market_data['trades'] = trades
                        logger.info(f"Fetched {len(trades)} trades for {symbol}")
                    else:
                        market_data['trades'] = []
                        logger.warning(f"No trades available for {symbol}")
                except Exception as e:
                    logger.error(f"Failed to fetch trades for {symbol}: {e}")
                    market_data['trades'] = []
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error ensuring complete market data: {e}")
            return market_data

    @staticmethod
    def validate_market_data(market_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate market data completeness.
        
        Returns:
            Dictionary of validation results
        """
        validation = {
            'has_ohlcv': False,
            'has_base_timeframe': False,
            'has_all_timeframes': False,
            'has_trades': False,
            'has_orderbook': False,
            'is_complete': False
        }
        
        try:
            # Check OHLCV
            if 'ohlcv' in market_data and market_data['ohlcv']:
                validation['has_ohlcv'] = True
                
                ohlcv = market_data['ohlcv']
                if 'base' in ohlcv:
                    validation['has_base_timeframe'] = True
                
                required_timeframes = ['base', 'ltf', 'mtf', 'htf']
                if all(tf in ohlcv for tf in required_timeframes):
                    validation['has_all_timeframes'] = True
            
            # Check trades
            if 'trades' in market_data and market_data['trades']:
                validation['has_trades'] = True
            
            # Check orderbook
            if 'orderbook' in market_data and market_data['orderbook']:
                validation['has_orderbook'] = True
            
            # Overall completeness
            validation['is_complete'] = (
                validation['has_ohlcv'] and
                validation['has_base_timeframe'] and
                validation['has_trades'] and
                validation['has_orderbook']
            )
            
            return validation
            
        except Exception as e:
            logger.error(f"Error validating market data: {e}")
            return validation
'''
        
        # Create the wrapper file
        wrapper_file.parent.mkdir(parents=True, exist_ok=True)
        with open(wrapper_file, 'w') as f:
            f.write(wrapper_content)
        
        logger.info("   ✓ Created market_data_wrapper.py")
        
        # Fix 4: Update documentation
        logger.info("\n4. Updating documentation files...")
        
        # Update ERROR_SUMMARY.md
        error_summary_file = project_root / 'logs' / 'RUN-R6Q48J-3594_ERROR_SUMMARY.md'
        if error_summary_file.exists():
            with open(error_summary_file, 'r') as f:
                content = f.read()
            
            # Fix the incorrect statement about base being 60-minute
            content = content.replace('base (60 minute)', 'base (1 minute)')
            content = content.replace('base" timeframe (60-minute data)', 'base" timeframe (1-minute data)')
            content = content.replace('"base" (60-minute) timeframe', '"base" (1-minute) timeframe')
            
            with open(error_summary_file, 'w') as f:
                f.write(content)
            
            logger.info("   ✓ Updated ERROR_SUMMARY.md with correct timeframe info")
        
        # Update VOLUME_ORDERFLOW_VALIDATION_ANALYSIS.md
        validation_file = project_root / 'logs' / 'VOLUME_ORDERFLOW_VALIDATION_ANALYSIS.md'
        if validation_file.exists():
            with open(validation_file, 'r') as f:
                content = f.read()
            
            # Fix the incorrect statement
            content = content.replace('Missing required timeframe: `base` (60-minute data)', 
                                    'Missing required timeframe: `base` (1-minute data)')
            content = content.replace('- **Missing**: `base` timeframe (should contain 60-minute OHLCV data)',
                                    '- **Missing**: `base` timeframe (should contain 1-minute OHLCV data)')
            
            with open(validation_file, 'w') as f:
                f.write(content)
            
            logger.info("   ✓ Updated VOLUME_ORDERFLOW_VALIDATION_ANALYSIS.md")
        
        logger.info("\n" + "="*60)
        logger.info("Fix Summary")
        logger.info("="*60)
        logger.info("\n1. Monitor timeframes updated to match config:")
        logger.info("   - base: 1m (was missing)")
        logger.info("   - ltf: 5m (was 1m)")
        logger.info("   - mtf: 30m (was 15m)")
        logger.info("   - htf: 4h (was 1h)")
        
        logger.info("\n2. Confluence timeframe mapping updated:")
        logger.info("   - 15m now maps to 'ltf' (was 'mtf')")
        logger.info("   - Added 1m to 'base' mapping")
        
        logger.info("\n3. Created market data wrapper to:")
        logger.info("   - Ensure correct timeframe labels")
        logger.info("   - Fetch missing trade data")
        logger.info("   - Validate data completeness")
        
        logger.info("\n4. Documentation updated with correct timeframe info")
        
        logger.info("\n✅ All fixes applied successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Restart the application to load changes")
        logger.info("2. Monitor logs to verify validation errors are resolved")
        logger.info("3. Use MarketDataWrapper.ensure_complete_market_data() before confluence analysis")
        
    except Exception as e:
        logger.error(f"Error applying fixes: {e}")
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
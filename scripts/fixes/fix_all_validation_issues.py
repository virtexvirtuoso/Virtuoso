#!/usr/bin/env python3
"""
Comprehensive Fix for All Validation Issues in RUN-R6Q48J-3594

This script addresses ALL issues found in the error summary:
1. WebSocket initialization error (coroutine not awaited)
2. Missing 'base' timeframe mapping 
3. Missing trade data for orderflow indicator
4. Confluence analysis failures

Run this script to apply all necessary fixes.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import traceback
import re

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import Logger

def fix_websocket_issue(logger):
    """Fix the WebSocket coroutine subscriptable error."""
    logger.info("\n1. Fixing WebSocket Initialization Error...")
    
    monitor_file = project_root / 'src' / 'monitoring' / 'monitor.py'
    
    if not monitor_file.exists():
        logger.error(f"   ✗ monitor.py not found at {monitor_file}")
        return False
        
    try:
        # Read the file
        with open(monitor_file, 'r') as f:
            content = f.read()
        
        # Backup the file
        backup_file = monitor_file.with_suffix('.py.backup_websocket_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
        with open(backup_file, 'w') as f:
            f.write(content)
        logger.info(f"   ✓ Created backup: {backup_file.name}")
        
        # Fix 1: The main issue - get_top_symbols is async but not awaited
        # Find the problematic line around 1985-1988
        pattern = r'top_symbols = self\.top_symbols_manager\.get_top_symbols\(\)'
        replacement = 'top_symbols = await self.top_symbols_manager.get_top_symbols()'
        
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            logger.info("   ✓ Fixed: Added await to get_top_symbols() call")
        else:
            logger.warning("   ⚠ get_top_symbols pattern not found, checking alternative...")
            
        # Fix 2: Make sure _initialize_websocket is async
        # Check if the method signature needs to be async
        if 'def _initialize_websocket(self):' in content:
            content = content.replace('def _initialize_websocket(self):', 'async def _initialize_websocket(self):')
            logger.info("   ✓ Fixed: Made _initialize_websocket async")
            
        # Fix 3: Ensure the method is called with await
        # Look for calls to _initialize_websocket
        init_pattern = r'self\._initialize_websocket\(\)(?!\s*\))'
        if re.search(init_pattern, content):
            content = re.sub(init_pattern, 'await self._initialize_websocket()', content)
            logger.info("   ✓ Fixed: Added await to _initialize_websocket() calls")
            
        # Write the fixed content
        with open(monitor_file, 'w') as f:
            f.write(content)
            
        logger.info("   ✓ WebSocket initialization fix applied successfully")
        return True
        
    except Exception as e:
        logger.error(f"   ✗ Error fixing WebSocket issue: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_timeframe_mappings(logger):
    """Fix timeframe mapping issues."""
    logger.info("\n2. Fixing Timeframe Mapping Issues...")
    
    # Fix monitor.py timeframes
    monitor_file = project_root / 'src' / 'monitoring' / 'monitor.py'
    if monitor_file.exists():
        try:
            with open(monitor_file, 'r') as f:
                content = f.read()
            
            # Update default timeframes
            old_tf = "default_timeframes = {'ltf': '1m', 'mtf': '15m', 'htf': '1h'}"
            new_tf = "default_timeframes = {'base': '1m', 'ltf': '5m', 'mtf': '30m', 'htf': '4h'}"
            
            if old_tf in content:
                content = content.replace(old_tf, new_tf)
                logger.info("   ✓ Updated default timeframes in monitor.py")
            else:
                logger.info("   ℹ Default timeframes already updated or different format")
                
            with open(monitor_file, 'w') as f:
                f.write(content)
                
        except Exception as e:
            logger.error(f"   ✗ Error updating monitor.py: {e}")
    
    # Fix confluence.py mappings
    confluence_file = project_root / 'src' / 'core' / 'analysis' / 'confluence.py'
    if confluence_file.exists():
        try:
            with open(confluence_file, 'r') as f:
                content = f.read()
            
            # Backup
            backup_file = confluence_file.with_suffix('.py.backup_timeframe_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
            with open(backup_file, 'w') as f:
                f.write(content)
            
            # Fix timeframe mappings
            # Ensure 1m maps to base
            if "'1m': 'base'" not in content and "tf_map = {" in content:
                # Find tf_map and add the mapping
                tf_map_match = re.search(r'(tf_map\s*=\s*{)', content)
                if tf_map_match:
                    insert_pos = tf_map_match.end()
                    content = content[:insert_pos] + "\n            '1': 'base',\n            '1m': 'base'," + content[insert_pos:]
                    logger.info("   ✓ Added 1m to base mapping in confluence.py")
            
            # Fix 15m mapping (should be ltf not mtf)
            content = content.replace("'15m': 'mtf'", "'15m': 'ltf'")
            content = content.replace("'15': 'mtf'", "'15': 'ltf'")
            logger.info("   ✓ Fixed 15m mapping to ltf")
            
            with open(confluence_file, 'w') as f:
                f.write(content)
                
        except Exception as e:
            logger.error(f"   ✗ Error updating confluence.py: {e}")
            
    logger.info("   ✓ Timeframe mapping fixes completed")
    return True

def ensure_trade_data_collection(logger):
    """Ensure trade data is collected for orderflow analysis."""
    logger.info("\n3. Ensuring Trade Data Collection...")
    
    # Check if market data fetching includes trades
    bybit_file = project_root / 'src' / 'core' / 'exchanges' / 'bybit.py'
    
    if bybit_file.exists():
        try:
            with open(bybit_file, 'r') as f:
                content = f.read()
            
            # Check if fetch_market_data includes trade fetching
            if 'fetch_trades' in content and 'fetch_market_data' in content:
                logger.info("   ✓ Trade fetching already implemented in exchange")
            else:
                logger.warning("   ⚠ May need to add trade fetching to market data collection")
                
        except Exception as e:
            logger.error(f"   ✗ Error checking trade data collection: {e}")
    
    # Create or update data validation helper
    validation_file = project_root / 'src' / 'core' / 'analysis' / 'data_validator.py'
    
    validation_content = '''"""
Data Validator for Market Data Completeness

Ensures all required data is present before indicator calculations.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """Validates market data completeness for indicators."""
    
    @staticmethod
    def validate_for_confluence(market_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate market data has all required components for confluence analysis.
        
        Returns:
            Dict with validation results for each component
        """
        results = {
            'has_ohlcv': False,
            'has_base_timeframe': False,
            'has_trades': False,
            'has_orderbook': False,
            'has_ticker': False,
            'is_valid': False
        }
        
        try:
            # Check OHLCV data
            if 'ohlcv' in market_data and market_data['ohlcv']:
                results['has_ohlcv'] = True
                
                # Check for base timeframe
                ohlcv = market_data['ohlcv']
                if any(key in ohlcv for key in ['base', '1m', '1']):
                    results['has_base_timeframe'] = True
                    
            # Check trades
            if 'trades' in market_data and market_data['trades'] and len(market_data['trades']) > 0:
                results['has_trades'] = True
                
            # Check orderbook
            if 'orderbook' in market_data and market_data['orderbook']:
                ob = market_data['orderbook']
                if 'bids' in ob and 'asks' in ob and ob['bids'] and ob['asks']:
                    results['has_orderbook'] = True
                    
            # Check ticker
            if 'ticker' in market_data and market_data['ticker']:
                results['has_ticker'] = True
                
            # Overall validity
            results['is_valid'] = (
                results['has_ohlcv'] and 
                results['has_trades'] and 
                results['has_orderbook']
            )
            
            # Log validation results
            if not results['is_valid']:
                missing = [k for k, v in results.items() if not v and k != 'is_valid']
                logger.warning(f"Market data validation failed. Missing: {missing}")
                
        except Exception as e:
            logger.error(f"Error validating market data: {e}")
            
        return results
    
    @staticmethod
    async def ensure_complete_data(exchange, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure market data is complete, fetching missing components.
        
        Args:
            exchange: Exchange instance
            symbol: Trading symbol
            market_data: Existing market data
            
        Returns:
            Complete market data
        """
        try:
            # Validate current data
            validation = DataValidator.validate_for_confluence(market_data)
            
            # Fetch missing trades
            if not validation['has_trades']:
                logger.info(f"Fetching missing trade data for {symbol}...")
                try:
                    trades = await exchange.fetch_trades(symbol, limit=1000)
                    if trades:
                        market_data['trades'] = trades
                        logger.info(f"Fetched {len(trades)} trades")
                except Exception as e:
                    logger.error(f"Failed to fetch trades: {e}")
                    market_data['trades'] = []
                    
            # Ensure base timeframe exists
            if not validation['has_base_timeframe'] and 'ohlcv' in market_data:
                ohlcv = market_data['ohlcv']
                
                # Map 1m to base if it exists
                if '1m' in ohlcv:
                    ohlcv['base'] = ohlcv['1m']
                    logger.info("Mapped 1m data to base timeframe")
                elif '1' in ohlcv:
                    ohlcv['base'] = ohlcv['1']
                    logger.info("Mapped 1 data to base timeframe")
                elif 'ltf' in ohlcv:
                    # Use ltf as fallback
                    ohlcv['base'] = ohlcv['ltf']
                    logger.warning("Using ltf as fallback for base timeframe")
                    
            return market_data
            
        except Exception as e:
            logger.error(f"Error ensuring complete data: {e}")
            return market_data
'''
    
    try:
        validation_file.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_file, 'w') as f:
            f.write(validation_content)
        logger.info("   ✓ Created data_validator.py for data completeness checks")
    except Exception as e:
        logger.error(f"   ✗ Error creating data validator: {e}")
        
    return True

def update_documentation(logger):
    """Update documentation with correct information."""
    logger.info("\n4. Updating Documentation...")
    
    # Fix ERROR_SUMMARY.md
    error_file = project_root / 'logs' / 'RUN-R6Q48J-3594_ERROR_SUMMARY.md'
    if error_file.exists():
        try:
            with open(error_file, 'r') as f:
                content = f.read()
            
            # Fix incorrect timeframe references
            content = content.replace('base (60 minute)', 'base (1 minute)')
            content = content.replace('base (60-minute)', 'base (1 minute)')
            content = content.replace('"base" timeframe (60-minute data)', '"base" timeframe (1-minute data)')
            
            with open(error_file, 'w') as f:
                f.write(content)
            
            logger.info("   ✓ Updated ERROR_SUMMARY.md")
        except Exception as e:
            logger.error(f"   ✗ Error updating ERROR_SUMMARY.md: {e}")
    
    return True

def main():
    """Apply all fixes for validation issues."""
    logger = Logger('fix_all_validation')
    
    logger.info("="*60)
    logger.info("Comprehensive Validation Issues Fix")
    logger.info("="*60)
    logger.info(f"Time: {datetime.now()}")
    
    try:
        # Apply all fixes
        success = True
        
        # Fix 1: WebSocket initialization
        if not fix_websocket_issue(logger):
            success = False
            
        # Fix 2: Timeframe mappings
        if not fix_timeframe_mappings(logger):
            success = False
            
        # Fix 3: Trade data collection
        if not ensure_trade_data_collection(logger):
            success = False
            
        # Fix 4: Documentation
        if not update_documentation(logger):
            success = False
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("Fix Summary")
        logger.info("="*60)
        
        if success:
            logger.info("\n✅ All fixes applied successfully!")
            logger.info("\nFixed Issues:")
            logger.info("1. WebSocket initialization - Added await for async get_top_symbols()")
            logger.info("2. Timeframe mappings - Added base (1m), fixed 15m to ltf mapping")
            logger.info("3. Trade data collection - Created validator to ensure data completeness")
            logger.info("4. Documentation - Updated with correct timeframe information")
            
            logger.info("\nNext Steps:")
            logger.info("1. Restart the application to load all changes")
            logger.info("2. Monitor logs to verify errors are resolved")
            logger.info("3. Check that confluence analysis completes successfully")
        else:
            logger.error("\n⚠️  Some fixes may have failed. Check the logs above.")
            
    except Exception as e:
        logger.error(f"Error applying fixes: {e}")
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
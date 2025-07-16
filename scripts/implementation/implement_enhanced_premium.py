#!/usr/bin/env python3
"""
Enhanced Futures Premium Implementation Script

This script implements the enhanced futures premium calculation into the market reporter.
It includes safety measures, backup creation, and gradual rollout capabilities.

Usage:
    python scripts/implementation/implement_enhanced_premium.py --backup --test
"""

import os
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

def create_backup(file_path: str) -> str:
    """Create a backup of the original file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    
    shutil.copy2(file_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return backup_path

def add_enhanced_imports(file_content: str) -> str:
    """Add required imports for enhanced premium calculation."""
    # Find existing imports section
    lines = file_content.split('\n')
    
    # Look for imports section
    import_end_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            import_end_idx = i
        elif line.strip() and not line.strip().startswith('#') and import_end_idx > 0:
            break
    
    # Add new imports
    new_imports = [
        "import aiohttp",
        "from datetime import timedelta"
    ]
    
    # Check if imports already exist
    existing_content = '\n'.join(lines)
    imports_to_add = []
    
    for imp in new_imports:
        if imp not in existing_content:
            imports_to_add.append(imp)
    
    if imports_to_add:
        # Insert new imports after existing ones
        lines.insert(import_end_idx + 1, '\n# Enhanced premium calculation imports')
        for imp in reversed(imports_to_add):
            lines.insert(import_end_idx + 2, imp)
        
        print(f"✅ Added imports: {', '.join(imports_to_add)}")
    
    return '\n'.join(lines)

def add_enhanced_mixin(file_content: str) -> str:
    """Add the enhanced futures premium mixin to the file."""
    
    # Enhanced mixin code
    mixin_code = '''
class EnhancedFuturesPremiumMixin:
    """Enhanced futures premium calculation mixin for MarketReporter."""
    
    def _init_enhanced_premium(self):
        """Initialize enhanced premium calculation capabilities."""
        self._aiohttp_session = None
        self._premium_api_base_url = getattr(self, 'premium_api_base_url', "https://api.bybit.com")
        self._enable_enhanced_premium = getattr(self, 'enable_enhanced_premium', True)
        self._enable_premium_validation = getattr(self, 'enable_premium_validation', True)
        self._premium_calculation_stats = {
            'improved_success': 0,
            'improved_failures': 0,
            'fallback_usage': 0,
            'validation_matches': 0,
            'validation_mismatches': 0
        }
    
    async def _get_aiohttp_session(self) -> 'aiohttp.ClientSession':
        """Get or create aiohttp session for direct API calls."""
        if self._aiohttp_session is None:
            self._aiohttp_session = aiohttp.ClientSession()
        return self._aiohttp_session
    
    async def _close_aiohttp_session(self):
        """Close aiohttp session on cleanup."""
        if self._aiohttp_session:
            await self._aiohttp_session.close()
            self._aiohttp_session = None
    
    async def _calculate_single_premium_enhanced(self, symbol: str, all_markets: Dict = None) -> Optional[Dict[str, Any]]:
        """Enhanced single premium calculation with improved API usage."""
        if not getattr(self, '_enable_enhanced_premium', True):
            return await self._calculate_single_premium_original(symbol, all_markets)
        
        start_time = time.time()
        
        try:
            # Extract base coin
            base_coin = self._extract_base_coin_enhanced(symbol)
            if not base_coin:
                self.logger.warning(f"Could not extract base coin from symbol: {symbol}")
                self._premium_calculation_stats['improved_failures'] += 1
                return await self._fallback_to_original_method(symbol, all_markets)
            
            self.logger.debug(f"Enhanced premium calculation for {symbol} (base: {base_coin})")
            
            # Get perpetual data using enhanced method
            perpetual_data = await self._get_perpetual_data_enhanced(base_coin)
            if not perpetual_data:
                self.logger.warning(f"No perpetual data found via enhanced method for {base_coin}")
                self._premium_calculation_stats['improved_failures'] += 1
                return await self._fallback_to_original_method(symbol, all_markets)
            
            # Extract pricing data
            mark_price = float(perpetual_data.get('markPrice', 0))
            index_price = float(perpetual_data.get('indexPrice', 0))
            
            if mark_price <= 0 or index_price <= 0:
                self.logger.warning(f"Invalid pricing data for {base_coin}: mark={mark_price}, index={index_price}")
                self._premium_calculation_stats['improved_failures'] += 1
                return await self._fallback_to_original_method(symbol, all_markets)
            
            # Calculate perpetual premium
            perpetual_premium = ((mark_price - index_price) / index_price) * 100
            
            # Get quarterly contracts (simplified for initial implementation)
            quarterly_data = []
            quarterly_futures_count = 0
            
            # Validate with Bybit's premium index (if enabled)
            validation_data = None
            if getattr(self, '_enable_premium_validation', True):
                validation_data = await self._validate_with_bybit_premium_index(base_coin)
                if validation_data:
                    bybit_premium = validation_data.get('bybit_premium_index', 0) * 100
                    if abs(perpetual_premium - bybit_premium) < 0.05:  # 5 basis points tolerance
                        self._premium_calculation_stats['validation_matches'] += 1
                    else:
                        self._premium_calculation_stats['validation_mismatches'] += 1
                        self.logger.warning(f"Premium validation mismatch for {base_coin}: "
                                          f"calculated={perpetual_premium:.4f}%, bybit={bybit_premium:.4f}%")
            
            # Compile result (backward compatible)
            result = {
                'premium': f"{perpetual_premium:.4f}%",
                'premium_value': perpetual_premium,
                'premium_type': "📈 Contango" if perpetual_premium > 0 else "📉 Backwardation",
                'mark_price': mark_price,
                'index_price': index_price,
                'last_price': float(perpetual_data.get('lastPrice', mark_price)),
                'funding_rate': perpetual_data.get('fundingRate', 0),
                'timestamp': int(datetime.now().timestamp() * 1000),
                'quarterly_futures_count': quarterly_futures_count,
                'futures_price': 0,
                'futures_basis': "0.00%",
                'futures_contracts': quarterly_data,
                'weekly_futures_count': 0,
                'data_source': 'enhanced_api_v5',
                'data_quality': 'high',
                'calculation_method': 'enhanced_perpetual_vs_index',
                'processing_time_ms': round((time.time() - start_time) * 1000, 2),
                'bybit_validation': validation_data,
                'validation_status': 'validated' if validation_data else 'not_validated'
            }
            
            self._premium_calculation_stats['improved_success'] += 1
            self.logger.debug(f"Enhanced premium calculation successful for {symbol}: {perpetual_premium:.4f}%")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in enhanced premium calculation for {symbol}: {e}")
            self._premium_calculation_stats['improved_failures'] += 1
            return await self._fallback_to_original_method(symbol, all_markets)
    
    def _extract_base_coin_enhanced(self, symbol: str) -> Optional[str]:
        """Enhanced base coin extraction."""
        try:
            if '/' in symbol:
                return symbol.split('/')[0].upper()
            elif symbol.endswith('USDT'):
                return symbol.replace('USDT', '').upper()
            elif ':' in symbol:
                return symbol.split(':')[0].replace('USDT', '').upper()
            else:
                return symbol.upper()
        except Exception:
            return None
    
    async def _get_perpetual_data_enhanced(self, base_coin: str) -> Optional[Dict[str, Any]]:
        """Get perpetual contract data using enhanced API method."""
        session = await self._get_aiohttp_session()
        
        try:
            perpetual_symbol = f"{base_coin}USDT"
            ticker_url = f"{self._premium_api_base_url}/v5/market/tickers"
            params = {'category': 'linear', 'symbol': perpetual_symbol}
            
            async with session.get(ticker_url, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        ticker_list = data.get('result', {}).get('list', [])
                        if ticker_list:
                            return ticker_list[0]
                        
        except Exception as e:
            self.logger.error(f"Error getting enhanced perpetual data for {base_coin}: {e}")
        
        return None
    
    async def _validate_with_bybit_premium_index(self, base_coin: str) -> Optional[Dict[str, Any]]:
        """Validate calculations using Bybit's own premium index data."""
        session = await self._get_aiohttp_session()
        
        try:
            symbol = f"{base_coin}USDT"
            url = f"{self._premium_api_base_url}/v5/market/premium-index-price-kline"
            params = {'category': 'linear', 'symbol': symbol, 'interval': '1', 'limit': 1}
            
            async with session.get(url, params=params, timeout=3) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        kline_data = data.get('result', {}).get('list', [])
                        if kline_data:
                            latest = kline_data[0]
                            return {
                                'bybit_premium_index': float(latest[4]),
                                'timestamp': int(latest[0]),
                                'source': 'premium_index_kline',
                                'validation_method': 'enhanced'
                            }
                            
        except Exception as e:
            self.logger.debug(f"Could not validate with Bybit premium index for {base_coin}: {e}")
        
        return None
    
    async def _fallback_to_original_method(self, symbol: str, all_markets: Dict = None) -> Optional[Dict[str, Any]]:
        """Fallback to the original _calculate_single_premium method."""
        self._premium_calculation_stats['fallback_usage'] += 1
        self.logger.info(f"Falling back to original premium calculation method for {symbol}")
        
        try:
            return await self._calculate_single_premium_original(symbol, all_markets)
        except Exception as e:
            self.logger.error(f"Error in fallback premium calculation for {symbol}: {e}")
            return None
    
    def get_premium_calculation_stats(self) -> Dict[str, Any]:
        """Get statistics about premium calculation performance."""
        total_attempts = (self._premium_calculation_stats['improved_success'] + 
                         self._premium_calculation_stats['improved_failures'])
        
        return {
            'enhanced_method': {
                'success_count': self._premium_calculation_stats['improved_success'],
                'failure_count': self._premium_calculation_stats['improved_failures'],
                'success_rate': (self._premium_calculation_stats['improved_success'] / max(total_attempts, 1)) * 100,
                'total_attempts': total_attempts
            },
            'fallback_usage': {
                'count': self._premium_calculation_stats['fallback_usage'],
                'percentage': (self._premium_calculation_stats['fallback_usage'] / max(total_attempts, 1)) * 100
            },
            'validation': {
                'matches': self._premium_calculation_stats['validation_matches'],
                'mismatches': self._premium_calculation_stats['validation_mismatches'],
                'match_rate': (self._premium_calculation_stats['validation_matches'] / 
                              max(self._premium_calculation_stats['validation_matches'] + 
                                  self._premium_calculation_stats['validation_mismatches'], 1)) * 100
            }
        }

'''
    
    # Find the right place to insert the mixin (before the MarketReporter class)
    lines = file_content.split('\n')
    
    # Find MarketReporter class definition
    market_reporter_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('class MarketReporter'):
            market_reporter_idx = i
            break
    
    if market_reporter_idx == -1:
        raise ValueError("Could not find MarketReporter class definition")
    
    # Insert mixin before MarketReporter class
    lines.insert(market_reporter_idx, mixin_code)
    lines.insert(market_reporter_idx, '')
    
    print("✅ Added EnhancedFuturesPremiumMixin class")
    return '\n'.join(lines)

def modify_market_reporter_class(file_content: str) -> str:
    """Modify the MarketReporter class to inherit from the mixin."""
    
    # Replace class definition
    updated_content = file_content.replace(
        'class MarketReporter:',
        'class MarketReporter(EnhancedFuturesPremiumMixin):'
    )
    
    # Add enhanced premium initialization to __init__
    # Find the __init__ method
    lines = updated_content.split('\n')
    
    init_start = -1
    for i, line in enumerate(lines):
        if '__init__' in line and 'def ' in line:
            init_start = i
            break
    
    if init_start != -1:
        # Find the end of existing initialization
        indent_level = 0
        init_end = init_start
        for i in range(init_start + 1, len(lines)):
            line = lines[i]
            if line.strip():
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= 8 and not line.strip().startswith('#'):
                    init_end = i
                    break
            init_end = i
        
        # Add enhanced premium initialization
        enhancement_init = [
            '',
            '        # Initialize enhanced premium calculation',
            '        self._init_enhanced_premium()',
            '        self.enable_enhanced_premium = True  # Feature flag',
            '        self.enable_premium_validation = True  # Validation flag',
            '        self.premium_api_base_url = "https://api.bybit.com"  # Configurable'
        ]
        
        # Insert at the end of __init__
        for line in reversed(enhancement_init):
            lines.insert(init_end, line)
        
        print("✅ Added enhanced premium initialization to __init__")
    
    return '\n'.join(lines)

def rename_original_method(file_content: str) -> str:
    """Rename the original _calculate_single_premium method to preserve it as fallback."""
    
    # Find the original method
    lines = file_content.split('\n')
    
    method_start = -1
    for i, line in enumerate(lines):
        if 'async def _calculate_single_premium(self, symbol: str, all_markets: Dict)' in line:
            method_start = i
            break
    
    if method_start == -1:
        raise ValueError("Could not find original _calculate_single_premium method")
    
    # Rename the method
    lines[method_start] = lines[method_start].replace(
        'async def _calculate_single_premium(self, symbol: str, all_markets: Dict)',
        'async def _calculate_single_premium_original(self, symbol: str, all_markets: Dict)'
    )
    
    print("✅ Renamed original method to _calculate_single_premium_original")
    return '\n'.join(lines)

def add_new_premium_method(file_content: str) -> str:
    """Add the new enhanced premium calculation method."""
    
    new_method = '''
    async def _calculate_single_premium(self, symbol: str, all_markets: Dict) -> Optional[Dict[str, Any]]:
        """Calculate futures premium with enhanced capabilities and fallback."""
        return await self._calculate_single_premium_enhanced(symbol, all_markets)
'''
    
    # Find where to insert the new method (after the original renamed method)
    lines = file_content.split('\n')
    
    original_method_end = -1
    for i, line in enumerate(lines):
        if 'async def _calculate_single_premium_original' in line:
            # Find the end of this method
            method_start = i
            indent_level = len(line) - len(line.lstrip())
            
            for j in range(method_start + 1, len(lines)):
                current_line = lines[j]
                if current_line.strip():
                    current_indent = len(current_line) - len(current_line.lstrip())
                    if current_indent <= indent_level and current_line.strip().startswith('async def '):
                        original_method_end = j
                        break
                elif j == len(lines) - 1:
                    original_method_end = j
            break
    
    if original_method_end != -1:
        lines.insert(original_method_end, new_method)
        print("✅ Added new enhanced _calculate_single_premium method")
    
    return '\n'.join(lines)

def add_performance_monitoring(file_content: str) -> str:
    """Add performance monitoring for the enhanced premium calculation."""
    
    # Find the _log_performance_metrics method
    lines = file_content.split('\n')
    
    perf_method_start = -1
    for i, line in enumerate(lines):
        if 'async def _log_performance_metrics(self)' in line:
            perf_method_start = i
            break
    
    if perf_method_start != -1:
        # Find the end of the method
        method_end = perf_method_start
        indent_level = len(lines[perf_method_start]) - len(lines[perf_method_start].lstrip())
        
        for j in range(perf_method_start + 1, len(lines)):
            current_line = lines[j]
            if current_line.strip():
                current_indent = len(current_line) - len(current_line.lstrip())
                if current_indent <= indent_level and (current_line.strip().startswith('async def ') or current_line.strip().startswith('def ')):
                    method_end = j
                    break
            elif j == len(lines) - 1:
                method_end = j
        
        # Add premium performance logging
        premium_logging = [
            '',
            '        # Log enhanced premium calculation performance',
            '        if hasattr(self, "_premium_calculation_stats"):',
            '            stats = self.get_premium_calculation_stats()',
            '            self.logger.info("=== Enhanced Premium Calculation Performance ===")',
            '            self.logger.info(f"Enhanced method success rate: {stats[\'enhanced_method\'][\'success_rate\']:.1f}%")',
            '            self.logger.info(f"Fallback usage: {stats[\'fallback_usage\'][\'percentage\']:.1f}%")',
            '            self.logger.info(f"Validation match rate: {stats[\'validation\'][\'match_rate\']:.1f}%")'
        ]
        
        # Insert before the method end
        for line in reversed(premium_logging):
            lines.insert(method_end - 1, line)
        
        print("✅ Added enhanced premium performance monitoring")
    
    return '\n'.join(lines)

def implement_enhanced_premium(market_reporter_path: str, create_backup_flag: bool = True, test_mode: bool = False):
    """Implement enhanced premium calculation in the market reporter."""
    
    print("🚀 Starting Enhanced Futures Premium Implementation")
    print("=" * 60)
    
    # Check if file exists
    if not os.path.exists(market_reporter_path):
        raise FileNotFoundError(f"Market reporter not found: {market_reporter_path}")
    
    # Create backup
    backup_path = None
    if create_backup_flag:
        backup_path = create_backup(market_reporter_path)
    
    try:
        # Read current file
        with open(market_reporter_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📖 Read {len(content)} characters from {market_reporter_path}")
        
        # Apply modifications step by step
        print("\n🔧 Applying Modifications:")
        
        # Step 1: Add imports
        content = add_enhanced_imports(content)
        
        # Step 2: Add enhanced mixin
        content = add_enhanced_mixin(content)
        
        # Step 3: Modify MarketReporter class to inherit from mixin
        content = modify_market_reporter_class(content)
        
        # Step 4: Rename original method
        content = rename_original_method(content)
        
        # Step 5: Add new enhanced method
        content = add_new_premium_method(content)
        
        # Step 6: Add performance monitoring
        content = add_performance_monitoring(content)
        
        if test_mode:
            # In test mode, write to a test file
            test_path = market_reporter_path.replace('.py', '_enhanced_test.py')
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Enhanced version written to test file: {test_path}")
            print("🧪 Test mode: Original file unchanged")
        else:
            # Write the modified content back
            with open(market_reporter_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Enhanced premium calculation implemented in {market_reporter_path}")
        
        print("\n🎉 Implementation Complete!")
        print("\n📊 Next Steps:")
        print("1. Test the enhanced implementation")
        print("2. Monitor performance metrics in logs")  
        print("3. Verify premium data for major symbols")
        print("4. Check validation rates against Bybit's calculations")
        
        if backup_path:
            print(f"5. Backup available at: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during implementation: {e}")
        
        # Restore from backup if it exists
        if backup_path and os.path.exists(backup_path) and not test_mode:
            print(f"🔄 Restoring from backup: {backup_path}")
            shutil.copy2(backup_path, market_reporter_path)
            print("✅ Original file restored")
        
        raise e

def main():
    """Main implementation function."""
    parser = argparse.ArgumentParser(description='Implement Enhanced Futures Premium Calculation')
    parser.add_argument('--backup', action='store_true', default=True, 
                       help='Create backup of original file (default: True)')
    parser.add_argument('--no-backup', action='store_true', 
                       help='Skip creating backup')
    parser.add_argument('--test', action='store_true', 
                       help='Test mode: write to separate file without modifying original')
    parser.add_argument('--file', type=str, 
                       default='src/monitoring/market_reporter.py',
                       help='Path to market reporter file')
    
    args = parser.parse_args()
    
    # Determine backup flag
    create_backup_flag = args.backup and not args.no_backup
    
    try:
        implement_enhanced_premium(
            market_reporter_path=args.file,
            create_backup_flag=create_backup_flag,
            test_mode=args.test
        )
        
        print("\n🚀 Ready to test enhanced futures premium calculation!")
        
    except Exception as e:
        print(f"\n💥 Implementation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
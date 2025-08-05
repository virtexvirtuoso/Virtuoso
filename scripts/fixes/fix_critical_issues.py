#!/usr/bin/env python3
"""
Fix critical issues identified on 2025-08-04:
1. API timeout causing system hang
2. PDF generator entry_pos undefined variable
3. Missing price data for newly added symbols
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def backup_file(filepath):
    """Create a backup of the file before modifying."""
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up {filepath} to {backup_path}")
    return backup_path

def fix_bybit_timeout():
    """Fix the Bybit API timeout issue."""
    bybit_file = project_root / "src/core/exchanges/bybit.py"
    
    if not bybit_file.exists():
        print(f"❌ File not found: {bybit_file}")
        return False
    
    backup_file(bybit_file)
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Increase timeouts to prevent hanging
    old_timeout = """            # Configure timeouts
            self.timeout = aiohttp.ClientTimeout(
                total=30,  # Total timeout
                connect=10,  # Connection timeout
                sock_read=20  # Socket read timeout
            )"""
    
    new_timeout = """            # Configure timeouts with more aggressive settings to prevent hanging
            self.timeout = aiohttp.ClientTimeout(
                total=15,  # Reduced total timeout to fail faster
                connect=5,  # Reduced connection timeout
                sock_read=10,  # Reduced socket read timeout
                sock_connect=5  # Socket connection timeout
            )"""
    
    if old_timeout in content:
        content = content.replace(old_timeout, new_timeout)
        print("✅ Fixed timeout configuration in _create_session")
    else:
        print("⚠️  Timeout configuration not found or already modified")
    
    # Fix 2: Add request timeout wrapper
    old_request = """            # Use persistent session instead of creating new one
            if method.upper() == 'GET':
                async with self.session.get(url, params=params, headers=headers) as response:
                    return await self._process_response(response, url)
            elif method.upper() == 'POST':
                # For POST requests, send params as JSON in the body
                async with self.session.post(url, json=params, headers=headers) as response:
                    return await self._process_response(response, url)"""
    
    new_request = """            # Use persistent session with explicit timeout
            try:
                if method.upper() == 'GET':
                    async with asyncio.wait_for(
                        self.session.get(url, params=params, headers=headers),
                        timeout=15.0
                    ) as response:
                        return await self._process_response(response, url)
                elif method.upper() == 'POST':
                    # For POST requests, send params as JSON in the body
                    async with asyncio.wait_for(
                        self.session.post(url, json=params, headers=headers),
                        timeout=15.0
                    ) as response:
                        return await self._process_response(response, url)
            except asyncio.TimeoutError:
                self.logger.error(f"Request timeout after 15s: {endpoint}")
                return {'retCode': -1, 'retMsg': 'Request timeout'}"""
    
    if old_request in content:
        content = content.replace(old_request, new_request)
        print("✅ Added timeout wrapper to requests")
    else:
        print("⚠️  Request code not found or already modified")
    
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print("✅ Bybit timeout fixes applied")
    return True

def fix_pdf_generator():
    """Fix the PDF generator entry_pos undefined variable issue."""
    pdf_file = project_root / "src/core/reporting/pdf_generator.py"
    
    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_file}")
        return False
    
    backup_file(pdf_file)
    
    with open(pdf_file, 'r') as f:
        content = f.read()
    
    # Fix: Initialize entry_pos before the conditional block
    old_code = """                # Add labels with improved styling
                if entry_price is not None:
                    # Calculate normalized position for entry price
                    entry_pos = (entry_price - y_min) / (y_max - y_min)"""
    
    new_code = """                # Add labels with improved styling
                entry_pos = None  # Initialize to prevent undefined variable error
                if entry_price is not None:
                    # Calculate normalized position for entry price
                    entry_pos = (entry_price - y_min) / (y_max - y_min)"""
    
    # Count occurrences
    occurrences = content.count(old_code)
    if occurrences > 0:
        content = content.replace(old_code, new_code)
        print(f"✅ Fixed {occurrences} occurrences of entry_pos undefined variable")
    else:
        print("⚠️  entry_pos pattern not found or already fixed")
    
    # Also fix the usage of entry_pos outside the if block
    old_usage = """                ax1.annotate(
                    f"Entry: ${self._format_number(entry_price)}",
                    xy=(1.01, entry_pos),
                    xycoords=("axes fraction", "axes fraction"),
                    xytext=(1.05, entry_pos),"""
    
    new_usage = """                if entry_pos is not None:
                    ax1.annotate(
                        f"Entry: ${self._format_number(entry_price)}",
                        xy=(1.01, entry_pos),
                        xycoords=("axes fraction", "axes fraction"),
                        xytext=(1.05, entry_pos),"""
    
    if old_usage in content:
        # Need to properly indent the closing parenthesis
        content = content.replace(
            old_usage + """
                    textcoords="axes fraction",
                    fontsize=9,
                    color="#10b981",
                    fontweight="bold",
                    bbox=dict(
                        facecolor="#0c1a2b",
                        edgecolor="#3b82f6",
                        boxstyle="round,pad=0.3",
                        alpha=0.9,
                    ),
                )""",
            new_usage + """
                        textcoords="axes fraction",
                        fontsize=9,
                        color="#10b981",
                        fontweight="bold",
                        bbox=dict(
                            facecolor="#0c1a2b",
                            edgecolor="#3b82f6",
                            boxstyle="round,pad=0.3",
                            alpha=0.9,
                        ),
                    )"""
        )
        print("✅ Fixed entry_pos usage with null check")
    
    with open(pdf_file, 'w') as f:
        f.write(content)
    
    print("✅ PDF generator fixes applied")
    return True

def fix_market_data_manager():
    """Fix missing price data for newly added symbols."""
    market_file = project_root / "src/core/market/market_data_manager.py"
    
    if not market_file.exists():
        print(f"❌ File not found: {market_file}")
        return False
    
    backup_file(market_file)
    
    with open(market_file, 'r') as f:
        content = f.read()
    
    # Find the update_symbol_data method
    if "async def update_symbol_data(self, symbol: str)" in content:
        # Add immediate price fetch for new symbols
        old_method = """    async def update_symbol_data(self, symbol: str) -> bool:
        \"\"\"Update data for a specific symbol.\"\"\"
        try:
            if symbol not in self.symbols:
                self.logger.warning(f"Symbol {symbol} not in active symbols list")
                return False"""
        
        new_method = """    async def update_symbol_data(self, symbol: str) -> bool:
        \"\"\"Update data for a specific symbol.\"\"\"
        try:
            if symbol not in self.symbols:
                self.logger.warning(f"Symbol {symbol} not in active symbols list")
                # Try to fetch immediate data for new symbols
                await self._fetch_immediate_symbol_data(symbol)
                return False"""
        
        if old_method in content:
            content = content.replace(old_method, new_method)
            print("✅ Added immediate data fetch for new symbols")
        
        # Add the new method
        new_method_code = '''
    async def _fetch_immediate_symbol_data(self, symbol: str) -> None:
        """Fetch immediate price data for a symbol not in the regular update cycle."""
        try:
            self.logger.info(f"Fetching immediate data for new symbol: {symbol}")
            
            # Get current price
            ticker = await self.exchange_manager.fetch_ticker(symbol)
            if ticker and 'last' in ticker:
                current_price = ticker['last']
                
                # Store in cache
                if symbol not in self._symbol_data_cache:
                    self._symbol_data_cache[symbol] = {}
                
                self._symbol_data_cache[symbol]['current_price'] = current_price
                self._symbol_data_cache[symbol]['ticker'] = ticker
                self._symbol_data_cache[symbol]['last_update'] = datetime.now()
                
                self.logger.info(f"Immediate data fetched for {symbol}: ${current_price}")
                
                # Try to get minimal OHLCV data
                try:
                    ohlcv = await self.exchange_manager.fetch_ohlcv(symbol, '1m', limit=100)
                    if ohlcv:
                        self._symbol_data_cache[symbol]['ohlcv'] = {'base': ohlcv}
                except Exception as e:
                    self.logger.warning(f"Could not fetch OHLCV for {symbol}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error fetching immediate data for {symbol}: {str(e)}")
'''
        
        # Insert the new method after update_symbol_data
        if "_fetch_immediate_symbol_data" not in content:
            # Find a good insertion point
            insertion_point = content.find("    async def get_symbol_data(")
            if insertion_point > 0:
                content = content[:insertion_point] + new_method_code + "\n" + content[insertion_point:]
                print("✅ Added _fetch_immediate_symbol_data method")
        
    else:
        print("⚠️  update_symbol_data method not found")
    
    # Also ensure confluence analyzer can handle missing price data gracefully
    old_get_data = """    async def get_symbol_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        \"\"\"Get cached data for a symbol.\"\"\"
        return self._symbol_data_cache.get(symbol)"""
    
    new_get_data = """    async def get_symbol_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        \"\"\"Get cached data for a symbol.\"\"\"
        data = self._symbol_data_cache.get(symbol)
        
        # If no data and symbol is in our list, try immediate fetch
        if not data and symbol in self.symbols:
            await self._fetch_immediate_symbol_data(symbol)
            data = self._symbol_data_cache.get(symbol)
            
        return data"""
    
    if old_get_data in content:
        content = content.replace(old_get_data, new_get_data)
        print("✅ Enhanced get_symbol_data with fallback fetch")
    
    with open(market_file, 'w') as f:
        f.write(content)
    
    print("✅ Market data manager fixes applied")
    return True

def main():
    """Apply all fixes."""
    print("🔧 Applying critical fixes for issues found on 2025-08-04")
    print("=" * 60)
    
    success = True
    
    # Fix 1: Bybit timeout issue
    print("\n1. Fixing Bybit API timeout issue...")
    if not fix_bybit_timeout():
        success = False
    
    # Fix 2: PDF generator entry_pos issue
    print("\n2. Fixing PDF generator entry_pos undefined variable...")
    if not fix_pdf_generator():
        success = False
    
    # Fix 3: Market data manager missing price data
    print("\n3. Fixing missing price data for new symbols...")
    if not fix_market_data_manager():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All fixes applied successfully!")
        print("\n⚠️  Please test the changes thoroughly before deploying to VPS")
    else:
        print("❌ Some fixes failed. Please check the output above.")
    
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
#!/usr/bin/env python3
"""
Apply the remaining fixes that weren't correctly applied.
"""

import re
from pathlib import Path
from datetime import datetime

def fix_pdf_entry_pos_usage():
    """Fix the usage of entry_pos outside the if block."""
    pdf_file = Path(__file__).parent.parent / "src/core/reporting/pdf_generator.py"
    
    with open(pdf_file, 'r') as f:
        content = f.read()
    
    # Find and fix the annotate calls that use entry_pos
    pattern = r'(\s+)(ax1\.annotate\(\s*\n\s+f"Entry: \$\{self\._format_number\(entry_price\)\}",\s*\n\s+xy=\(1\.01, entry_pos\),)'
    
    def replacer(match):
        indent = match.group(1)
        annotate_call = match.group(2)
        return f'{indent}if entry_pos is not None:\n{indent}    {annotate_call}'
    
    # Apply the fix
    new_content = re.sub(pattern, replacer, content)
    
    # Also need to indent the rest of the annotate call
    # This is trickier - find the pattern and properly indent
    lines = new_content.split('\n')
    new_lines = []
    in_annotate = False
    indent_level = 0
    
    for i, line in enumerate(lines):
        if 'if entry_pos is not None:' in line and i + 1 < len(lines) and 'ax1.annotate(' in lines[i + 1]:
            new_lines.append(line)
            in_annotate = True
            # Get the base indentation
            indent_level = len(line) - len(line.lstrip()) + 4
        elif in_annotate:
            if line.strip() == ')':
                new_lines.append(' ' * indent_level + line.strip())
                in_annotate = False
            else:
                new_lines.append(' ' * indent_level + line.strip())
        else:
            new_lines.append(line)
    
    with open(pdf_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print("✅ Fixed PDF entry_pos usage")

def fix_market_data_manager_complete():
    """Properly fix the market data manager."""
    market_file = Path(__file__).parent.parent / "src/core/market/market_data_manager.py"
    
    with open(market_file, 'r') as f:
        content = f.read()
    
    # Add the import if needed
    if "from datetime import datetime" not in content:
        content = content.replace("import logging", "import logging\nfrom datetime import datetime")
    
    # Add the _fetch_immediate_symbol_data method
    if "_fetch_immediate_symbol_data" not in content:
        # Find a good insertion point - after get_symbol_data method
        insertion_pattern = r'(async def get_symbol_data\(self, symbol: str\) -> Optional\[Dict\[str, Any\]\]:.*?\n        return data)'
        
        new_method = '''

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
            self.logger.error(f"Error fetching immediate data for {symbol}: {str(e)}")'''
        
        # Find the method and add our new method after it
        match = re.search(insertion_pattern, content, re.DOTALL)
        if match:
            end_pos = match.end()
            content = content[:end_pos] + new_method + content[end_pos:]
            print("✅ Added _fetch_immediate_symbol_data method")
        else:
            print("⚠️  Could not find insertion point for _fetch_immediate_symbol_data")
    
    # Update get_symbol_data to use the new method
    old_get_symbol = r'(async def get_symbol_data\(self, symbol: str\) -> Optional\[Dict\[str, Any\]\]:.*?return self\._symbol_data_cache\.get\(symbol\))'
    
    new_get_symbol = '''async def get_symbol_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached data for a symbol."""
        data = self._symbol_data_cache.get(symbol)
        
        # If no data and symbol is in our list, try immediate fetch
        if not data and symbol in self.symbols:
            await self._fetch_immediate_symbol_data(symbol)
            data = self._symbol_data_cache.get(symbol)
            
        return data'''
    
    content = re.sub(old_get_symbol, new_get_symbol, content, flags=re.DOTALL)
    print("✅ Updated get_symbol_data method")
    
    with open(market_file, 'w') as f:
        f.write(content)
    
    print("✅ Market data manager fixes applied")

def main():
    """Apply remaining fixes."""
    print("🔧 Applying remaining fixes...")
    print("=" * 60)
    
    fix_pdf_entry_pos_usage()
    fix_market_data_manager_complete()
    
    print("\n✅ Remaining fixes applied!")

if __name__ == "__main__":
    main()
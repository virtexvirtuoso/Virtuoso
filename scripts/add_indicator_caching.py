#!/usr/bin/env python3
"""
Script to add comprehensive caching to TechnicalIndicators class
This will modify the calculate method to use cached versions of all indicator calculations
"""

import re

def add_cached_methods_to_technical_indicators():
    """Add cached wrapper methods for all technical indicator calculations"""
    
    # Read the current file
    with open('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/indicators/technical_indicators.py', 'r') as f:
        content = f.read()
    
    # Find the calculate method and modify it to use await for cached calls
    # First, we need to make all the score calculations async
    
    # Pattern to find the timeframe score calculations
    pattern = r"(\s+)(base_scores|ltf_scores|mtf_scores|htf_scores) = \{([^}]+)\}"
    
    def replace_with_await(match):
        indent = match.group(1)
        var_name = match.group(2)
        content = match.group(3)
        
        # Extract timeframe from variable name
        timeframe_map = {
            'base_scores': 'base',
            'ltf_scores': 'ltf',
            'mtf_scores': 'mtf',
            'htf_scores': 'htf'
        }
        timeframe = timeframe_map[var_name]
        
        # Replace each calculation with await version
        lines = content.strip().split('\n')
        new_lines = []
        for line in lines:
            # Extract the component name and method call
            if ':' in line:
                component_part, call_part = line.split(':', 1)
                component = component_part.strip().strip("'\"")
                
                # Check which indicator it is
                if 'rsi' in component:
                    new_call = f" await self._calculate_rsi_score_cached({timeframe}_ohlcv, '{timeframe}', symbol)"
                elif 'macd' in component:
                    new_call = f" await self._calculate_macd_score_cached({timeframe}_ohlcv, '{timeframe}', symbol)"
                elif 'ao' in component:
                    new_call = f" await self._calculate_ao_score_cached({timeframe}_ohlcv, '{timeframe}', symbol)"
                elif 'williams_r' in component:
                    new_call = f" await self._calculate_williams_r_score_cached({timeframe}_ohlcv, '{timeframe}', symbol)"
                elif 'atr' in component:
                    new_call = f" await self._calculate_atr_score_cached({timeframe}_ohlcv, '{timeframe}', symbol)"
                elif 'cci' in component:
                    new_call = f" await self._calculate_cci_score_cached({timeframe}_ohlcv, '{timeframe}', symbol)"
                else:
                    new_call = call_part.rstrip(',')
                
                new_line = f"            '{component}':{new_call},"
                new_lines.append(new_line)
        
        return f"{indent}{var_name} = {{\n" + '\n'.join(new_lines).rstrip(',') + f"\n{indent}}}"
    
    # Apply the replacement
    modified = re.sub(pattern, replace_with_await, content)
    
    # Now add the cached wrapper methods for MACD, AO, Williams R, ATR, and CCI
    # Find the position after the RSI cached method we already added
    insert_pos = modified.find("    def _calculate_rsi_score(self, df: pd.DataFrame")
    if insert_pos > 0:
        # Find the start of this method definition
        method_start = modified.rfind("    async def _calculate_rsi_score_cached", 0, insert_pos)
        
        # Create the new cached methods
        cached_methods = """
    async def _calculate_macd_score_cached(self, df: pd.DataFrame, timeframe: str = 'base', symbol: str = None) -> float:
        \"\"\"Calculate MACD score with caching support.\"\"\"
        if not self.enable_caching or not self.cache or not symbol:
            return self._calculate_macd_score(df, timeframe)
        
        def compute():
            return self._calculate_macd_score(df, timeframe)
        
        return await self.cache.get_indicator(
            indicator_type='technical',
            symbol=symbol,
            component=f'macd_{timeframe}',
            params=self.macd_params,
            compute_func=lambda: asyncio.create_task(asyncio.to_thread(compute))
        )
    
    async def _calculate_ao_score_cached(self, df: pd.DataFrame, timeframe: str = 'base', symbol: str = None) -> float:
        \"\"\"Calculate AO score with caching support.\"\"\"
        if not self.enable_caching or not self.cache or not symbol:
            return self._calculate_ao_score(df, timeframe)
        
        def compute():
            return self._calculate_ao_score(df, timeframe)
        
        return await self.cache.get_indicator(
            indicator_type='technical',
            symbol=symbol,
            component=f'ao_{timeframe}',
            params={'fast': self.ao_fast, 'slow': self.ao_slow},
            compute_func=lambda: asyncio.create_task(asyncio.to_thread(compute))
        )
    
    async def _calculate_williams_r_score_cached(self, df: pd.DataFrame, timeframe: str = 'base', symbol: str = None) -> float:
        \"\"\"Calculate Williams %R score with caching support.\"\"\"
        if not self.enable_caching or not self.cache or not symbol:
            return self._calculate_williams_r_score(df, timeframe)
        
        def compute():
            return self._calculate_williams_r_score(df, timeframe)
        
        return await self.cache.get_indicator(
            indicator_type='technical',
            symbol=symbol,
            component=f'williams_r_{timeframe}',
            params={'period': self.williams_period},
            compute_func=lambda: asyncio.create_task(asyncio.to_thread(compute))
        )
    
    async def _calculate_atr_score_cached(self, df: pd.DataFrame, timeframe: str = 'base', symbol: str = None) -> float:
        \"\"\"Calculate ATR score with caching support.\"\"\"
        if not self.enable_caching or not self.cache or not symbol:
            return self._calculate_atr_score(df, timeframe)
        
        def compute():
            return self._calculate_atr_score(df, timeframe)
        
        return await self.cache.get_indicator(
            indicator_type='technical',
            symbol=symbol,
            component=f'atr_{timeframe}',
            params={'period': self.atr_period},
            compute_func=lambda: asyncio.create_task(asyncio.to_thread(compute))
        )
    
    async def _calculate_cci_score_cached(self, df: pd.DataFrame, timeframe: str = 'base', symbol: str = None) -> float:
        \"\"\"Calculate CCI score with caching support.\"\"\"
        if not self.enable_caching or not self.cache or not symbol:
            return self._calculate_cci_score(df, timeframe)
        
        def compute():
            return self._calculate_cci_score(df, timeframe)
        
        return await self.cache.get_indicator(
            indicator_type='technical',
            symbol=symbol,
            component=f'cci_{timeframe}',
            params={'period': self.cci_period},
            compute_func=lambda: asyncio.create_task(asyncio.to_thread(compute))
        )
"""
        
        # Insert the cached methods before the _calculate_rsi_score method
        modified = modified[:insert_pos] + cached_methods + "\n" + modified[insert_pos:]
    
    # Write the modified content back
    with open('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/indicators/technical_indicators.py', 'w') as f:
        f.write(modified)
    
    print("✅ Successfully added caching to TechnicalIndicators")
    print("Added cached methods for: RSI, MACD, AO, Williams %R, ATR, CCI")
    print("Modified calculate method to use async/await for cached calls")

if __name__ == "__main__":
    add_cached_methods_to_technical_indicators()
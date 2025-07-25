# Deprecated Pandas/NumPy Operations Audit

Date: 2025-07-24

## Summary of Findings

After a comprehensive search of the `src/` directory for deprecated pandas and numpy operations, I found the following issues that need attention:

### 1. ✅ DataFrame.append() - NOT FOUND
- **Status**: No usage of deprecated `DataFrame.append()` found
- **Note**: All list appends found are for regular Python lists, not DataFrames

### 2. ✅ .ix indexer - NOT FOUND
- **Status**: No usage of removed `.ix` indexer found

### 3. ✅ DataFrame.from_items() - NOT FOUND
- **Status**: No usage of removed `from_items()` method found

### 4. ✅ Series.get_value()/set_value() - NOT FOUND
- **Status**: No usage of deprecated pandas methods found
- **Note**: Found methods named `get_value` in config classes, but these are custom methods, not pandas

### 5. ✅ pd.np usage - NOT FOUND
- **Status**: No usage of deprecated `pd.np` found

### 6. ⚠️ inplace parameter usage - FOUND
- **Status**: Multiple occurrences found that need attention
- **Files affected**:
  - `/src/data_acquisition/bybit_data_fetcher.py` (line 101)
  - `/src/data_processing/data_processor.py` (lines 1164, 1349)
  - `/src/main.py` (lines 1553, 1561)
  - Multiple backup files also contain inplace usage

**Example**:
```python
df.set_index('timestamp', inplace=True)  # Should be: df = df.set_index('timestamp')
df.dropna(subset=numeric_columns, inplace=True)  # Should be: df = df.dropna(subset=numeric_columns)
```

### 7. ⚠️ .values usage - FOUND
- **Status**: Multiple occurrences found
- **Files affected**:
  - `/src/indicators/base_indicator.py` (lines 1658-1660, 1778)
  
**Problematic usage**:
```python
returns_aligned = returns.iloc[-min_length:].values  # Should use .to_numpy()
volatility_aligned = volatility.iloc[-min_length:].values
volume_ratio_aligned = volume_ratio.iloc[-min_length:].values
prices = data['close'].values
```

**Note**: Most `.values` usage found is on dictionaries (e.g., `dict.values()`), which is fine.

### 8. ✅ datetime64[ns] timezone issues - PROPERLY HANDLED
- **Status**: Timezone operations found are using proper methods
- **Note**: Usage of `tz_localize('UTC')` is the correct way to handle timezone-naive timestamps

### 9. ⚠️ Deprecated aggregation dict syntax - POTENTIAL ISSUE
- **Status**: Found usage that might be problematic in future pandas versions
- **File**: `/src/indicators/price_structure_indicators.py` (line 1119)

**Current usage**:
```python
grouped = df.groupby('price_row').agg({
    'volume': 'sum',
    'close': ['first', 'last']  # Mixed scalar/list syntax may be deprecated
})
```

### 10. ✅ Old-style string formatting - NOT A PANDAS ISSUE
- **Status**: Found % formatting in general Python code, but no pandas-specific string formatting issues

## Recommendations

1. **High Priority - inplace parameter**:
   - Replace all `inplace=True` usage with assignment pattern
   - This is being phased out and will cause issues in future pandas versions

2. **Medium Priority - .values usage**:
   - Replace `.values` with `.to_numpy()` for explicit numpy array conversion
   - This provides better type safety and clarity

3. **Low Priority - Aggregation syntax**:
   - Monitor the mixed scalar/list aggregation syntax
   - Consider using named aggregation for clarity

## Code Changes Needed

### 1. Fix inplace usage:
```python
# Before
df.set_index('timestamp', inplace=True)

# After
df = df.set_index('timestamp')
```

### 2. Fix .values usage:
```python
# Before
returns_aligned = returns.iloc[-min_length:].values

# After
returns_aligned = returns.iloc[-min_length:].to_numpy()
```

### 3. Consider updating aggregation syntax:
```python
# Current
grouped = df.groupby('price_row').agg({
    'volume': 'sum',
    'close': ['first', 'last']
})

# Future-proof alternative
grouped = df.groupby('price_row').agg(
    volume_sum=('volume', 'sum'),
    close_first=('close', 'first'),
    close_last=('close', 'last')
)
```

## Files Requiring Updates

1. `/src/data_acquisition/bybit_data_fetcher.py`
2. `/src/data_processing/data_processor.py`
3. `/src/main.py`
4. `/src/indicators/base_indicator.py`
5. `/src/indicators/price_structure_indicators.py`

## Conclusion

The codebase is generally well-maintained with respect to deprecated pandas/numpy operations. The main issues are:
- Use of `inplace=True` parameter (being phased out)
- Use of `.values` instead of `.to_numpy()` (clarity/type safety issue)
- Potential future issue with mixed aggregation syntax

These issues are relatively minor and can be fixed with straightforward replacements.
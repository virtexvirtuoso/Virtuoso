# Unique Error Patterns Analysis - Last 30 Days

## Overview
Analysis of log files from the last 30 days to identify unique error patterns in the Virtuoso CCXT system.

## Error Types Found

### 1. AttributeError
**Files:** bitcoin_beta_7day_report.log, market_reporter.log

#### Patterns:
- **'dict' object has no attribute 'symbols'**
  - File: bitcoin_beta_7day_report.log
  - Context: Exchange manager cleanup
  
- **'MarketReporter' object has no attribute 'generate_report'**
  - File: market_reporter.log
  - Frequency: Multiple occurrences
  - Context: Market report generation
  
- **'LiveWhaleTest' object has no attribute 'get_current_price'**
  - File: market_reporter.log
  - Context: Whale activity testing
  - Affected exchanges: Both Bybit and Binance

### 2. TypeError
**Files:** bitcoin_beta_7day_report.log, enhanced_scoring_bybit_live_test.log, market_reporter.log, pdf_generator.log

#### Patterns:
- **BybitExchange._fetch_ohlcv() got an unexpected keyword argument 'limit'**
  - File: enhanced_scoring_bybit_live_test.log
  - Frequency: Multiple occurrences
  - Context: Fetching OHLCV data for various symbols (BTCUSDT, ETHUSDT, BNBUSDT)
  
- **'Expect data.index as DatetimeIndex'**
  - File: pdf_generator.log
  - Context: Data validation for PDF generation
  
- **argument of type 'bool' is not iterable**
  - File: market_reporter.log
  - Context: PDF generation setup when checking report['html']
  
- **object MagicMock can't be used in 'await' expression**
  - File: market_reporter.log
  - Context: Sending Discord webhook messages during testing

### 3. ValueError
**Files:** market_reporter.log, pdf_generator.log

#### Patterns:
- **Missing required subsection 'enabled' in exchanges**
  - File: market_reporter.log
  - Context: Configuration validation

### 4. KeyError
**Files:** market_reporter.log

#### Patterns:
- **'exchanges'**
  - File: market_reporter.log
  - Context: BybitExchange fetch_markets fix

### 5. IndexError
- No IndexError patterns found in the last 30 days

### 6. Pandas/Numpy Related Errors
- No direct pandas/numpy error patterns found

### 7. Division by Zero Errors
**Files:** market_reporter.log, pdf_generator.log

#### Patterns:
- **ZeroDivisionError: float division by zero**
  - File: market_reporter.log
  - Context: Alert manager error sending
  - Location: src/monitoring/alert_manager.py line 654

### 8. NaN/Infinity Related Issues
While many files contain NaN/infinity references, no specific error patterns were found related to NaN handling.

### 9. Type Conversion Failures
**Files:** market_reporter.log

#### Patterns:
- **could not convert string to float: 'invalid'**
  - File: market_reporter.log
  - Context: Signal frequency tracker
  - Associated with: 'NoneType' object has no attribute 'get'

### 10. Missing Data Handling Errors
**Files:** market_reporter.log

#### Patterns:
- **'NoneType' object has no attribute 'get'**
  - File: market_reporter.log
  - Context: Signal frequency tracker
  - Often appears alongside type conversion errors

## Summary

The most common error patterns are:
1. **Method/Attribute Missing Errors**: Several components trying to access non-existent methods or attributes
2. **Type Mismatches**: Boolean values where iterables expected, unexpected keyword arguments
3. **Configuration Issues**: Missing required configuration sections
4. **Division by Zero**: Occurring in alert calculations
5. **Type Conversion**: Invalid string to float conversions with signal tracking

## Recommendations

1. **Add attribute checks** before accessing object methods
2. **Validate configuration** completeness on startup
3. **Add zero-division guards** in mathematical calculations
4. **Improve type validation** for signal tracking inputs
5. **Update method signatures** to match expected parameters (e.g., _fetch_ohlcv)
6. **Replace MagicMock objects** with proper async implementations in tests
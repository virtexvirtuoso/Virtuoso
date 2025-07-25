# DI Service Initialization Fixes Summary

## Issues Found and Fixed

### 1. ConfluenceAnalyzer - Missing Config Parameter
**Error**: `'NoneType' object is not subscriptable`
**Fix**: Created factory function with config parameter

### 2. ConfluenceAnalyzer - Missing 'timeframes' Key
**Error**: `Could not create confluence analyzer: 'timeframes'`
**Fix**: Added default timeframes configuration in factory

### 3. AlphaScannerEngine - Missing Dependencies
**Issue**: Requires ExchangeManager and config
**Fix**: Created factory function to inject both dependencies

### 4. LiquidationDetectionEngine - Missing ExchangeManager
**Issue**: Requires ExchangeManager parameter
**Fix**: Created factory function to inject ExchangeManager

### 5. All Indicator Services - Missing Config
**Issue**: All indicators (Technical, Volume, Price Structure, Orderbook, Orderflow, Sentiment) require config
**Fix**: Created generic factory function for all indicators with default timeframes

## Services Fixed

1. **ConfluenceAnalyzer**
   - Added factory with config injection
   - Added default timeframes structure
   - Added fallback config in exception handler

2. **AlphaScannerEngine**
   - Added factory with ExchangeManager injection
   - Added config injection

3. **LiquidationDetectionEngine**
   - Added factory with ExchangeManager injection
   - Database URL parameter is optional (set to None)

4. **All Indicator Services**
   - TechnicalIndicators
   - VolumeIndicators
   - PriceStructureIndicators
   - OrderbookIndicators
   - OrderflowIndicators
   - SentimentIndicators
   - All now use factory functions with config injection

## Default Configuration Structure

When config is missing, the following defaults are provided:

```python
{
    'timeframes': {
        'base': {
            'interval': 1,
            'required': 1000,
            'validation': {
                'max_gap': 60,
                'min_candles': 100
            },
            'weight': 0.4
        },
        'ltf': {
            'interval': 5,
            'required': 200,
            'validation': {
                'max_gap': 300,
                'min_candles': 50
            },
            'weight': 0.3
        },
        'mtf': {
            'interval': 30,
            'required': 200,
            'validation': {
                'max_gap': 1800,
                'min_candles': 50
            },
            'weight': 0.2
        },
        'htf': {
            'interval': 240,
            'required': 200,
            'validation': {
                'max_gap': 14400,
                'min_candles': 50
            },
            'weight': 0.1
        }
    }
}
```

## Services Checked and Found OK

The following services were checked and don't need fixes:
- InterpretationGenerator (uses optional dependencies)
- WebSocketManager (config passed but not requiring specific structure)
- LiquidationDataCollector (uses ExchangeManager, not config)
- AlertManager (already has factory with config injection)
- MetricsManager (already has factory with dependencies)
- MarketReporter (already has factory with dependencies)
- MarketMonitor (already has factory with dependencies)

## Files Modified

- `/src/core/di/registration.py` - All factory functions added/updated

## Result

All services that require dependencies are now properly registered with factory functions. The application should start without DI resolution errors.
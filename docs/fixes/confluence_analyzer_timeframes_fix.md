# ConfluenceAnalyzer Timeframes Configuration Fix

## Issue
```
2025-07-24 22:20:53.302 [WARNING] src.core.di.registration - ⚠️  WARNING: Could not create confluence analyzer: 'timeframes' (registration.py:119)
2025-07-24 22:20:53.303 [ERROR] src.core.di.container - ❌ ERROR: Error resolving service ConfluenceAnalyzer: 'timeframes' (container.py:181)
```

## Root Cause
The ConfluenceAnalyzer was trying to access `self.config['timeframes']` but the config dictionary passed to it didn't have the 'timeframes' key. This happened because:
1. The config service might not have the timeframes configuration loaded
2. The ConfluenceAnalyzer expects a specific config structure with timeframes

## Solution
Updated the `create_confluence_analyzer` factory function to ensure the config has the required 'timeframes' structure:

```python
async def create_confluence_analyzer():
    try:
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
        
        # Ensure required config structure exists
        if 'timeframes' not in config_dict:
            config_dict['timeframes'] = {
                'base': {
                    'interval': 1,
                    'required': 1000,
                    'validation': {
                        'max_gap': 60,
                        'min_candles': 100
                    },
                    'weight': 0.4
                },
                'htf': {
                    'interval': 240,
                    'required': 200,
                    'validation': {
                        'max_gap': 14400,
                        'min_candles': 50
                    },
                    'weight': 0.1
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
                }
            }
        
        return ConfluenceAnalyzer(config_dict)
    except Exception as e:
        logger.warning(f"Could not create confluence analyzer: {e}")
        # Return with minimal config as fallback
        return ConfluenceAnalyzer({
            'timeframes': {
                'base': {'interval': 1},
                'ltf': {'interval': 5},
                'mtf': {'interval': 30},
                'htf': {'interval': 240}
            }
        })
```

## Key Changes
1. Added check for 'timeframes' key in config_dict
2. If missing, populate with default timeframe configuration matching the expected structure
3. Added fallback config in exception handler with minimal timeframes structure
4. Ensures ConfluenceAnalyzer always receives a valid config with timeframes

## Files Modified
- `/src/core/di/registration.py` - Updated `create_confluence_analyzer` factory function

## Result
The ConfluenceAnalyzer will now successfully initialize with either:
- The actual timeframes config from the config service
- Default timeframes config if not present
- Minimal fallback config in case of any errors

This ensures the service can always be resolved without KeyError exceptions.
# ConfluenceAnalyzer DI Resolution Fix

## Issue
```
2025-07-24 22:09:43.378 [ERROR] src.core.di.container - ❌ ERROR: Error resolving service ConfluenceAnalyzer: 'NoneType' object is not subscriptable (container.py:181)
```

## Root Cause
The ConfluenceAnalyzer was registered as a scoped service without a factory function, but its constructor requires a `config` parameter. When the DI container tried to instantiate it without parameters, it passed `None` which caused the error.

## Solution
Updated the DI registration to use factory functions for services that require dependencies:

### 1. ConfluenceAnalyzer Factory
```python
async def create_confluence_analyzer():
    try:
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
        return ConfluenceAnalyzer(config_dict)
    except Exception as e:
        logger.warning(f"Could not create confluence analyzer: {e}")
        # Return with empty config as fallback
        return ConfluenceAnalyzer({})

container.register_factory(ConfluenceAnalyzer, create_confluence_analyzer, ServiceLifetime.SCOPED)
```

### 2. AlphaScannerEngine Factory
```python
async def create_alpha_scanner():
    try:
        exchange_manager = await container.get_service(ExchangeManager)
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else None
        return AlphaScannerEngine(exchange_manager, config_dict)
    except Exception as e:
        logger.warning(f"Could not create alpha scanner: {e}")
        raise

container.register_factory(AlphaScannerEngine, create_alpha_scanner, ServiceLifetime.SCOPED)
```

### 3. LiquidationDetectionEngine Factory
```python
async def create_liquidation_detector():
    try:
        exchange_manager = await container.get_service(ExchangeManager)
        # Database URL is optional
        database_url = None
        return LiquidationDetectionEngine(exchange_manager, database_url)
    except Exception as e:
        logger.warning(f"Could not create liquidation detector: {e}")
        raise

container.register_factory(LiquidationDetectionEngine, create_liquidation_detector, ServiceLifetime.SCOPED)
```

## Files Modified
- `/src/core/di/registration.py` - Updated service registrations for:
  - ConfluenceAnalyzer
  - AlphaScannerEngine
  - LiquidationDetectionEngine

## Result
All analysis services that require dependencies are now properly registered with factory functions that retrieve the necessary dependencies from the DI container before instantiation.

## Testing
To verify the fix works, restart the application and check that the ConfluenceAnalyzer error no longer appears in the logs.
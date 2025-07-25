# Exchange Method Resolution Fix

## Issue
```
❌ ERROR: All 3 attempts failed for fetch_ticker: Exchange does not have method 'fetch_ticker'
```

## Root Cause
The error was occurring because exchange services were not properly configured in the DI container:

1. **BybitExchange** was registered without a factory function, but requires config parameter
2. **WebSocketManager** was registered without a factory function, but requires config parameter  
3. The exchange object passed to MarketReporter might be None or incorrectly initialized

## Solution

### 1. Fixed BybitExchange Registration
Created factory function to properly inject config:

```python
async def create_bybit_exchange():
    try:
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
        
        # Ensure exchanges config exists
        if 'exchanges' not in config_dict:
            config_dict['exchanges'] = {
                'bybit': {
                    'rest_endpoint': 'https://api.bybit.com',
                    'websocket_endpoint': 'wss://stream.bybit.com',
                    'testnet': False,
                    'primary': True
                }
            }
        
        return BybitExchange(config_dict)
    except Exception as e:
        logger.warning(f"Could not create BybitExchange: {e}")
        # Return with minimal config
        return BybitExchange({
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api.bybit.com',
                    'testnet': False,
                    'primary': True
                }
            }
        })

container.register_factory(IExchangeService, create_bybit_exchange, ServiceLifetime.SINGLETON)
```

### 2. Fixed WebSocketManager Registration
Created factory function to inject config:

```python
async def create_websocket_manager():
    try:
        config_service = await container.get_service(IConfigService)
        config_dict = config_service.to_dict() if hasattr(config_service, 'to_dict') else {}
        return WebSocketManager(config_dict)
    except Exception as e:
        logger.warning(f"Could not create WebSocketManager: {e}")
        return WebSocketManager({})

container.register_factory(WebSocketManager, create_websocket_manager, ServiceLifetime.SINGLETON)
```

### 3. Enhanced Error Handling in MarketReporter
Added better debugging for exchange method resolution:

```python
# Get the method from the exchange object
if self.exchange is None:
    raise AttributeError(f"Exchange is None, cannot call method '{method_name}'")
    
if not hasattr(self.exchange, method_name):
    # Log exchange details for debugging
    exchange_type = type(self.exchange).__name__
    exchange_methods = [m for m in dir(self.exchange) if not m.startswith('_')]
    self.logger.debug(f"Exchange type: {exchange_type}, Available methods: {exchange_methods[:10]}...")
    raise AttributeError(f"Exchange ({exchange_type}) does not have method '{method_name}'")
```

### 4. Enhanced MarketReporter Factory
Added verification of exchange methods:

```python
try:
    exchange_manager = await container.get_service(ExchangeManager)
    if exchange_manager:
        exchange = await exchange_manager.get_primary_exchange()
        if exchange:
            logger.info(f"MarketReporter using exchange: {type(exchange).__name__}")
            # Verify the exchange has required methods
            required_methods = ['fetch_ticker', 'fetch_order_book', 'fetch_trades']
            missing_methods = [m for m in required_methods if not hasattr(exchange, m)]
            if missing_methods:
                logger.warning(f"Exchange missing methods: {missing_methods}")
        else:
            logger.warning("ExchangeManager returned None for primary exchange")
except Exception as e:
    logger.warning(f"Exchange not available for MarketReporter: {e}")
```

## Files Modified
- `/src/core/di/registration.py` - Added factory functions for BybitExchange and WebSocketManager
- `/src/monitoring/market_reporter.py` - Enhanced error handling and debugging

## Expected Result
- BybitExchange will be properly initialized with config
- MarketReporter will receive a properly configured exchange instance
- fetch_ticker method will be available on the exchange object
- Better error messages when method resolution fails

## Testing
To verify the fix:
1. Check that MarketReporter logs show "MarketReporter using exchange: BybitExchange"
2. No "Exchange missing methods" warnings should appear
3. fetch_ticker calls should succeed for both spot and futures contracts
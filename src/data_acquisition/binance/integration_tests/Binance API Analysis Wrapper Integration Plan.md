
# Binance API Analysis Wrapper Integration Plan

## 1. Project Goals & Scope

### What This Wrapper Will Support
- **Public Market Data**: OHLCV candlestick data, orderbook data, recent trades, 24h ticker statistics
- **Spot Market Analysis**: Focus on spot trading pairs for analytical purposes
- **Futures Market Data**: Open interest, funding rates, and futures-specific sentiment indicators
- **Volume & Liquidity Metrics**: Real-time volume, turnover, market depth analysis
- **Sentiment Proxies**: Funding rates, open interest changes, large transaction monitoring
- **Multi-timeframe Analysis**: Support for all existing Virtuoso timeframes (1m, 5m, 30m, 4h)

### What Is Out of Scope
- **Order Execution**: No trading functionality, purely analytical data source
- **Account Management**: No wallet, balance, or position management
- **Margin Trading Controls**: No leverage or margin-related operations
- **Private Endpoints**: No access to user-specific data
- **Real-time Trading Signals**: This wrapper provides data input, not trading decisions

## 2. Configuration Strategy

### Environment Variables (.env)
```bash
# Binance API Configuration (Optional - for higher rate limits)
BINANCE_API_KEY=your_optional_api_key
BINANCE_API_SECRET=your_optional_secret

# Binance Data Source Toggle
ENABLE_BINANCE_DATA=true
BINANCE_AS_PRIMARY=false
```

### Configuration Updates (config/config.yaml)

**Add to exchanges section:**
```yaml
exchanges:
  # Existing Bybit config...
  bybit:
    # ... existing configuration ...
  
  # New Binance configuration
  binance:
    enabled: ${ENABLE_BINANCE_DATA:false}  # Default disabled
    primary: ${BINANCE_AS_PRIMARY:false}   # Default not primary
    data_only: true                        # Analysis only, no trading
    use_ccxt: true                         # Use CCXT for standardization
    
    # API credentials (optional for higher rate limits)
    api_credentials:
      api_key: ${BINANCE_API_KEY:}         # Optional API key
      api_secret: ${BINANCE_API_SECRET:}   # Optional API secret
    
    # Rate limiting settings (public API limits)
    rate_limits:
      requests_per_minute: 1200            # Weight-based limit
      requests_per_second: 10              # Conservative limit
      weight_per_minute: 6000              # Binance weight system
    
    # Endpoint configuration
    rest_endpoint: https://api.binance.com
    testnet_endpoint: https://testnet.binance.vision
    testnet: false
    
    # WebSocket configuration
    websocket:
      public: wss://stream.binance.com:9443/ws
      testnet_public: wss://testnet.binance.vision/ws
      keep_alive: true
      ping_interval: 30
      reconnect_attempts: 3
    
    # Market types to support
    market_types:
      - spot                               # Spot trading pairs
      - futures                            # USDT-M futures
    
    # Data fetching preferences
    data_preferences:
      preferred_quote_currencies: ["USDT", "BTC", "ETH"]
      exclude_symbols: []
      min_24h_volume: 1000000              # Minimum 24h volume
```

### Schema Validation Updates
Update `src/core/config/config_manager.py` validation to include Binance exchange requirements.

## 3. Architecture Integration

### Integration with Atomic Data Fetching Framework
The Binance wrapper will implement the existing `BaseExchange` interface, ensuring seamless integration with:

- **ExchangeManager**: Add Binance as a secondary data source alongside Bybit
- **MarketDataManager**: Automatic failover and data aggregation capabilities
- **DataProcessor**: Existing OHLCV processing and technical analysis pipeline
- **ValidationService**: Existing data quality checks and validation rules

### Market Prism Analysis Stack Integration
- **Data Input Layer**: Binance feeds into the same `market_data` dictionary structure
- **Indicator Layer**: Existing technical indicators automatically process Binance data
- **Confluence Layer**: Binance data contributes to existing confluence scoring
- **Output Layer**: No changes needed to alerting or reporting systems

### Co-existence Strategy
```python
# Data source priority configuration
data_sources:
  primary: "bybit"                         # Keep Bybit as primary
  secondary: ["binance"]                   # Binance as backup/verification
  aggregation_mode: "primary_with_fallback" # Use primary, fallback to secondary
  cross_validation: true                   # Compare data across exchanges
```

## 4. Required Binance Endpoints

### Spot Market Endpoints
| Endpoint | Purpose | Rate Limit Weight |
|----------|---------|-------------------|
| `/api/v3/ticker/24hr` | 24h price change statistics | 1-40 |
| `/api/v3/klines` | OHLCV candlestick data | 1 |
| `/api/v3/depth` | Order book data | 1-50 |
| `/api/v3/trades` | Recent trades list | 1 |
| `/api/v3/avgPrice` | Current average price | 1 |
| `/api/v3/exchangeInfo` | Exchange trading rules | 10 |

### Futures Market Endpoints (USDT-M)
| Endpoint | Purpose | Rate Limit Weight |
|----------|---------|-------------------|
| `/fapi/v1/ticker/24hr` | 24h futures statistics | 1-40 |
| `/fapi/v1/klines` | Futures OHLCV data | 1 |
| `/fapi/v1/depth` | Futures order book | 1-50 |
| `/fapi/v1/openInterest` | Open interest data | 1 |
| `/fapi/v1/fundingRate` | Funding rate history | 1 |
| `/fapi/v1/premiumIndex` | Mark price and funding rate | 1 |

### Considerations
- **Spot vs Futures**: Implement market type detection for appropriate endpoint selection
- **Rate Limiting**: Use Binance's weight-based system rather than request counting
- **Testnet Support**: Full testnet endpoint support for development/testing

## 5. Design & Structure

### Module Structure
```
src/data_acquisition/binance/
├── __init__.py                   # Package initialization
├── client.py                     # BinanceClient (REST API wrapper)
├── data_fetcher.py              # BinanceDataFetcher (main data acquisition)
├── websocket_handler.py         # WebSocket implementation
├── rate_limiter.py              # Binance-specific rate limiting
├── endpoints.py                 # Endpoint definitions and constants
└── exceptions.py                # Binance-specific exceptions

src/core/exchanges/
├── binance.py                   # BinanceExchange (BaseExchange implementation)
└── # existing files...
```

### Class Architecture

#### Core Classes
```python
# BinanceExchange - Main interface
class BinanceExchange(BaseExchange):
    """Binance exchange implementation using CCXT with custom enhancements"""

# BinanceClient - REST API wrapper  
class BinanceClient:
    """Handles REST API communication with proper rate limiting"""

# BinanceDataFetcher - Data acquisition coordinator
class BinanceDataFetcher:
    """Coordinates data fetching across spot and futures markets"""
```

### CCXT vs Direct Implementation Decision

**Recommendation: Hybrid Approach**
- **Primary**: Use CCXT for standardized data formats and basic API calls
- **Enhancement**: Custom implementations for Binance-specific features (funding rates, advanced orderbook analysis)
- **Rationale**: 
  - CCXT provides battle-tested standardization and error handling
  - Custom code handles Binance-specific analytics requirements
  - Easier maintenance and upgrades
  - Better compliance with Virtuoso's existing CCXT patterns

## 6. Efficiency & Reliability

### Rate Limiting Strategy
```python
class BinanceRateLimiter:
    def __init__(self):
        self.weight_limits = {
            'spot': {'per_minute': 6000, 'per_second': 100},
            'futures': {'per_minute': 2400, 'per_second': 50}
        }
        self.current_weights = defaultdict(int)
        self.last_reset = time.time()
```

### Error Handling & Retry Logic
- **HTTP 429 (Rate Limit)**: Exponential backoff with weight tracking
- **HTTP 4xx**: Log and skip (data quality issue)
- **HTTP 5xx**: Retry with linear backoff (max 3 attempts)
- **Network Errors**: Circuit breaker pattern with health checks
- **Data Validation**: Cross-reference with existing data validation framework

### Caching Strategy
```python
# Leverage existing cache infrastructure
cache_config = {
    'ticker': {'ttl': 5, 'enabled': True},      # 5 seconds
    'orderbook': {'ttl': 1, 'enabled': True},   # 1 second  
    'klines': {'ttl': 60, 'enabled': True},     # 1 minute
    'funding': {'ttl': 300, 'enabled': True},   # 5 minutes
}
```

### Fallback Handling
- **Primary Source**: Continue using Bybit as primary
- **Data Validation**: Cross-validate critical metrics between exchanges
- **Failover Logic**: Automatic fallback if Binance data quality drops
- **Health Monitoring**: Continuous monitoring of data freshness and accuracy

## 7. Testing Strategy

### Unit Tests
```python
# tests/data_acquisition/binance/
test_binance_client.py           # REST API client tests
test_binance_data_fetcher.py     # Data fetching logic tests  
test_binance_rate_limiter.py     # Rate limiting tests
test_binance_websocket.py        # WebSocket handler tests

# tests/core/exchanges/
test_binance_exchange.py         # Exchange integration tests
```

### Mock Data Strategy
- **Location**: `tests/fixtures/binance/`
- **Scope**: Representative samples of all supported endpoints
- **Realism**: Based on actual Binance API responses
- **Scenarios**: Normal operation, rate limits, errors, edge cases

### Integration Tests
```python
# tests/integration/binance/
test_binance_data_flow.py        # End-to-end data flow
test_binance_market_analysis.py  # Integration with analysis framework
test_binance_failover.py         # Failover and fallback scenarios
```

### Edge Cases Coverage
- Rate limit boundary conditions
- Malformed API responses
- Network interruption scenarios
- Market closure/maintenance periods
- Symbol delisting/addition events

## 8. Documentation Plan

### Technical Documentation
- **`docs/integration/binance_integration.md`**: Complete integration guide
- **`docs/api/binance_wrapper.md`**: API reference and usage examples
- **`src/data_acquisition/binance/README.md`**: Quick start guide for developers

### Code Documentation
- **Comprehensive docstrings**: All public methods with type hints
- **Configuration examples**: Sample configuration blocks
- **Error scenarios**: Documented error conditions and handling

### Junior Developer Onboarding
- **Setup Guide**: Step-by-step Binance API key setup (optional)
- **Testing Guide**: How to run tests with mock data
- **Troubleshooting**: Common issues and solutions
- **Code Examples**: Basic usage patterns and integration examples

## 9. Milestones & Timeline

### Week 1: Foundation (Days 1-5)

#### Milestone 1: Core Infrastructure (Days 1-2)
- [ ] Create `BinanceClient` with basic REST API capabilities
- [ ] Implement `BinanceRateLimiter` with weight-based limiting  
- [ ] Set up configuration schema and validation
- [ ] Create basic error handling and logging framework

#### Milestone 2: Data Fetching (Days 3-4)
- [ ] Implement `BinanceDataFetcher` for OHLCV and ticker data
- [ ] Add orderbook and trades data fetching
- [ ] Create data standardization layer for Virtuoso compatibility
- [ ] Implement basic caching mechanism

#### Milestone 3: Exchange Integration (Day 5)
- [ ] Create `BinanceExchange` class inheriting from `BaseExchange`
- [ ] Integrate with `ExchangeFactory` and `ExchangeManager`
- [ ] Update configuration management to support Binance

### Week 2: Enhancement and Testing (Days 6-10)

#### Milestone 4: Advanced Features (Days 6-7)
- [ ] Add futures market support (open interest, funding rates)
- [ ] Implement WebSocket data streaming (stretch goal)
- [ ] Add cross-exchange data validation
- [ ] Enhance error handling and circuit breaker patterns

#### Milestone 5: Testing & Validation (Days 8-9)
- [ ] Create comprehensive unit test suite with mock data
- [ ] Implement integration tests with existing analysis framework
- [ ] Add performance and reliability testing
- [ ] Validate data quality and consistency

#### Milestone 6: Documentation & Deployment (Day 10)
- [ ] Complete technical documentation
- [ ] Create junior developer onboarding materials
- [ ] Perform final integration testing
- [ ] Prepare deployment checklist and monitoring setup

### Priority Levels
- **High Priority**: Core OHLCV data, basic orderbook, exchange integration
- **Medium Priority**: Advanced analytics, WebSocket support, comprehensive testing
- **Stretch Goals**: Real-time streaming, advanced sentiment indicators, performance optimization

## Implementation Notes

### Risk Mitigation
- **Gradual Rollout**: Deploy as secondary data source initially
- **Monitoring**: Comprehensive logging and alerting for data quality
- **Rollback Plan**: Easy configuration to disable Binance integration
- **Rate Limit Safety**: Conservative limits with buffer zones

### Performance Considerations
- **Async-First Design**: All API calls use asyncio for non-blocking operation
- **Batch Operations**: Group requests where possible to minimize API calls
- **Smart Caching**: Cache frequently accessed, slowly changing data
- **Resource Management**: Proper connection pooling and cleanup

This plan provides a comprehensive roadmap for integrating Binance as an analytical data source while maintaining the reliability and architecture integrity of the Virtuoso trading system. The implementation prioritizes seamless integration with existing patterns and provides clear guidance for junior developers to contribute effectively.

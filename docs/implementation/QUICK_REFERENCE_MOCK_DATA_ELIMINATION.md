# Quick Reference: Mock Data Elimination
## Developer Implementation Guide

---

## 🎯 **QUICK IDENTIFICATION CHECKLIST**

### **Red Flags - Mock Data Patterns:**
```python
# ❌ REMOVE THESE PATTERNS:
import random
random.uniform(0, 100)          # Random scores
fake_data = {...}               # Hardcoded data structures  
mock_symbols = [...]            # Hardcoded symbol lists
price = 100000 if 'BTC'...      # Hardcoded price fallbacks
"data_source": "mock"           # Mock data indicators
```

### **Green Patterns - Real Data Usage:**
```python
# ✅ REPLACE WITH THESE PATTERNS:
await exchange.fetch_ticker()    # Real exchange data
market_data = await monitor._get_market_data()  # Real monitoring
confluence_result = await analyzer.analyze()   # Real analysis
"data_source": "real_exchange"  # Real data indicators
```

---

## 📋 **CRITICAL FILES TO UPDATE**

| **File** | **Problem** | **Solution** |
|----------|-------------|--------------|
| `src/api/routes/whale_activity.py:89` | Mock whale data generation | Connect to MarketMonitor._last_whale_activity |
| `src/web_server.py:170` | Hardcoded symbol prices | Use ExchangeManager.fetch_ticker() |
| `src/dashboard/dashboard_integration.py:619` | Fallback fake prices | Use real exchange data or return empty |
| `src/trade_execution/trade_executor.py:234` | Random signal scores | Connect to ConfluenceAnalyzer |
| `src/core/reporting/pdf_generator.py:4483` | Simulated OHLCV data | Use exchange.fetch_ohlcv() |

---

## 🔧 **CODE REPLACEMENT TEMPLATES**

### **Template 1: Replace Mock API Data**
```python
# ❌ OLD (Mock):
def get_data():
    return {"price": 50000, "volume": 1000000}

# ✅ NEW (Real):
async def get_data(symbol: str):
    try:
        exchange = await get_primary_exchange()
        ticker = await exchange.fetch_ticker(symbol)
        return {
            "price": ticker.get('last', 0),
            "volume": ticker.get('baseVolume', 0),
            "data_source": "real_exchange"
        }
    except Exception as e:
        logger.error(f"Real data unavailable: {e}")
        return {"error": "data_unavailable"}
```

### **Template 2: Replace Random Scores**
```python
# ❌ OLD (Random):
score = random.uniform(0, 100)

# ✅ NEW (Real Analysis):
async def get_real_score(symbol: str, market_data: dict):
    try:
        analyzer = ConfluenceAnalyzer()
        result = await analyzer.analyze_confluence(symbol, market_data)
        return result.get('score', 50.0)  # Default neutral
    except:
        return 50.0  # Neutral fallback, not random
```

### **Template 3: Replace Fallback Data**
```python
# ❌ OLD (Fake Fallback):
if not real_data:
    return {"price": 50000, "data_source": "mock"}

# ✅ NEW (Proper Error):
if not real_data:
    return {
        "error": "data_unavailable", 
        "message": "Real market data temporarily unavailable",
        "retry_after": 60
    }
```

### **Template 4: Advanced Error Handling**
```python
# ✅ Comprehensive Error Handling with Circuit Breaker
class DataSourceCircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call_with_circuit_breaker(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure > self.timeout:
                self.state = "HALF_OPEN"
            else:
                return {
                    "error": "circuit_breaker_open",
                    "message": "Data source temporarily disabled",
                    "retry_after": self.timeout - (time.time() - self.last_failure)
                }
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            return {
                "error": "data_source_failure",
                "message": f"Data source error: {str(e)}",
                "circuit_state": self.state,
                "retry_after": 30 if self.state != "OPEN" else self.timeout
            }
```

### **Template 5: Edge Case Handling**
```python
# ✅ Handle Market Closure and Low Liquidity
async def get_market_data_with_context(symbol: str):
    try:
        exchange = await get_primary_exchange()
        ticker = await exchange.fetch_ticker(symbol)
        
        # Check for edge cases
        if ticker.get('last') is None:
            return {
                "error": "no_recent_trades",
                "message": f"No recent price data for {symbol}",
                "last_known_price": await get_cached_price(symbol),
                "data_age_minutes": await get_data_age(symbol)
            }
        
        volume_24h = ticker.get('baseVolume', 0)
        if volume_24h < 1000:  # Low liquidity threshold
            return {
                "warning": "low_liquidity",
                "price": ticker['last'],
                "volume_24h": volume_24h,
                "message": "Low liquidity - price may be stale",
                "data_source": "real_exchange_low_liquidity"
            }
        
        # Market closure detection
        if await is_market_closed(symbol):
            return {
                "warning": "market_closed",
                "price": ticker['last'],
                "message": "Market is closed - showing last available price",
                "market_next_open": await get_next_market_open(symbol)
            }
        
        return {
            "price": ticker['last'],
            "volume": volume_24h,
            "data_source": "real_exchange",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except NetworkError as e:
        return {
            "error": "network_error",
            "message": "Network connectivity issue",
            "retry_after": 15,
            "fallback_available": await has_cached_data(symbol)
        }
    except RateLimitExceeded as e:
        return {
            "error": "rate_limit_exceeded",
            "message": "Exchange rate limit reached",
            "retry_after": e.retry_after or 60,
            "cached_data": await get_cached_data(symbol)
        }
```

---

## ⚡ **TESTING COMMANDS**

### **Quick Data Source Verification:**
```bash
# Check for mock data in responses
curl localhost:8000/api/whale-activity | grep -i mock

# Verify real exchange connection
curl localhost:8000/api/top-symbols | jq '.source'

# Test production mode (should fail on mock data)
ENVIRONMENT=production python -m pytest tests/test_real_data.py
```

### **Environment Setup:**
```bash
# Development (allows real data)
export ENVIRONMENT=development
export ENABLE_MOCK_DATA=false

# Production (strict real data only) 
export ENVIRONMENT=production
export ENABLE_MOCK_DATA=false
export REQUIRE_REAL_EXCHANGE=true
```

---

## 🚨 **VALIDATION CHECKLIST**

Before committing changes:

- [ ] **No `random.uniform()` or `random.random()` calls**
- [ ] **No hardcoded price/volume values**  
- [ ] **All data includes `data_source` metadata**
- [ ] **Proper error handling for data unavailability**
- [ ] **Exchange connections tested and working**
- [ ] **APIs return empty/error instead of fake data**
- [ ] **Tests pass with `ENVIRONMENT=production`**

---

## 🔍 **REAL DATA SOURCES AVAILABLE**

### **Exchange Data (Primary):**
- `ExchangeManager.get_primary_exchange()` - *Connection: 5-10s timeout*
- `exchange.fetch_ticker(symbol)` - *Refresh: 1-5s, Cache: 5s TTL*
- `exchange.fetch_ohlcv(symbol, timeframe, limit)` - *Refresh: 15-60s, Cache: 30s TTL*
- `exchange.fetch_trades(symbol, limit)` - *Refresh: 1-3s, Cache: 3s TTL*
- `exchange.fetch_order_book(symbol, limit)` - *Refresh: 0.5-1s, Cache: 1s TTL*

### **Market Analysis (Secondary):**
- `MarketMonitor._get_market_data(symbol)` - *Refresh: 30s, Cache: 60s TTL*
- `MarketMonitor._last_whale_activity[symbol]` - *Refresh: 30s, Cache: 300s TTL*
- `ConfluenceAnalyzer.analyze_confluence()` - *Refresh: 60s, Cache: 120s TTL*
- `MarketReporter._process_whale_activity()` - *Refresh: 60s, Cache: 180s TTL*

### **WebSocket Streams (Real-time):**
- `WebSocketHandler.subscribe_to_ticker()` - *Update: Real-time, Buffer: 100ms*
- `WebSocketHandler.subscribe_to_trades()` - *Update: Real-time, Buffer: 50ms*
- Bybit WebSocket channels for live data - *Latency: 10-50ms*

### **Data Refresh Rate Guidelines:**
| **Data Type** | **Refresh Rate** | **Cache TTL** | **Priority** |
|---------------|------------------|---------------|--------------|
| **Price Tickers** | 1-5 seconds | 5 seconds | Critical |
| **Order Books** | 0.5-1 seconds | 1 second | Critical |
| **Trade History** | 1-3 seconds | 3 seconds | High |
| **OHLCV Candles** | 15-60 seconds | 30 seconds | Medium |
| **Whale Activity** | 30 seconds | 300 seconds | Medium |
| **Confluence Scores** | 60 seconds | 120 seconds | Low |
| **Volume Analysis** | 30 seconds | 60 seconds | Medium |

---

## ⚠️ **PRODUCTION DEPLOYMENT CHECKLIST**

### **Pre-Deploy:**
1. Set `ENVIRONMENT=production` 
2. Verify exchange API connections
3. Test all endpoints return real data
4. Confirm no mock data patterns remain

### **Post-Deploy:**
1. Monitor data source metrics
2. Check API response data_source fields
3. Verify error handling works correctly
4. Monitor system performance with real data

---

*Keep this guide handy during implementation for quick reference and validation.* 
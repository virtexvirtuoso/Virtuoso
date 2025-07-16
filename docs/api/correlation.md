# Signal Correlation Matrix API

The Signal Correlation Matrix API provides comprehensive analysis of signal correlations and matrix data matching your dashboard display. This API enables real-time correlation analysis between different signal types and assets.

## Overview

The correlation API offers:
- **Signal Confluence Matrix**: Live matrix data matching your dashboard
- **Signal Correlations**: How different signals correlate with each other
- **Asset Correlations**: How assets correlate based on signal patterns
- **Heatmap Data**: Formatted data for correlation visualizations
- **Real-time Updates**: Live matrix data with performance metrics

## Endpoints

### 1. Signal Confluence Matrix

```http
GET /api/correlation/matrix
```

Returns the signal confluence matrix data matching your dashboard display.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbols` | List[str] | All assets | List of symbols to include |
| `timeframe` | str | "1h" | Timeframe for analysis |
| `include_correlations` | bool | true | Include correlation calculations |

#### Response

```json
{
  "matrix_data": {
    "BTCUSDT": {
      "momentum": {
        "score": 75.2,
        "direction": "bullish",
        "strength": "strong"
      },
      "technical": {
        "score": 68.5,
        "direction": "bullish", 
        "strength": "medium"
      },
      "volume": {
        "score": 82.1,
        "direction": "bullish",
        "strength": "strong"
      },
      "orderflow": {
        "score": 71.3,
        "direction": "bullish",
        "strength": "medium"
      },
      "orderbook": {
        "score": 79.4,
        "direction": "bullish",
        "strength": "strong"
      },
      "sentiment": {
        "score": 65.7,
        "direction": "bullish",
        "strength": "medium"
      },
      "price_action": {
        "score": 73.8,
        "direction": "bullish",
        "strength": "medium"
      },
      "beta_exp": {
        "score": 77.2,
        "direction": "bullish",
        "strength": "strong"
      },
      "confluence": {
        "score": 74.6,
        "direction": "bullish",
        "strength": "medium"
      },
      "whale_act": {
        "score": 69.3,
        "direction": "bullish",
        "strength": "medium"
      },
      "liquidation": {
        "score": 45.2,
        "direction": "neutral",
        "strength": "weak"
      },
      "composite_score": 73.8
    }
  },
  "correlations": {
    "signal_correlations": {
      "momentum": {
        "technical": 0.75,
        "volume": 0.68,
        "orderflow": 0.82
      }
    },
    "asset_correlations": {
      "BTCUSDT": {
        "ETHUSDT": 0.85,
        "ADAUSDT": 0.72
      }
    }
  },
  "metadata": {
    "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
    "signal_types": ["momentum", "technical", "volume", ...],
    "timeframe": "1h",
    "timestamp": "2024-01-15T10:30:00Z",
    "total_symbols": 10,
    "total_signals": 11
  }
}
```

### 2. Signal Correlations

```http
GET /api/correlation/signal-correlations
```

Calculate correlations between different signal types.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbols` | List[str] | All assets | Symbols to analyze |
| `timeframe` | str | "1h" | Analysis timeframe |
| `lookback_periods` | int | 100 | Historical periods to analyze |

#### Response

```json
{
  "signal_correlations": {
    "momentum": {
      "momentum": 1.0,
      "technical": 0.75,
      "volume": 0.68,
      "orderflow": 0.82,
      "orderbook": 0.71,
      "sentiment": 0.64,
      "price_action": 0.78,
      "beta_exp": 0.85,
      "confluence": 0.92,
      "whale_act": 0.56,
      "liquidation": -0.23
    },
    "technical": {
      "momentum": 0.75,
      "technical": 1.0,
      "volume": 0.82,
      "orderflow": 0.67,
      "orderbook": 0.73,
      "sentiment": 0.58,
      "price_action": 0.89,
      "beta_exp": 0.71,
      "confluence": 0.88,
      "whale_act": 0.52,
      "liquidation": -0.31
    }
  },
  "statistics": {
    "signal_correlation_stats": {
      "mean_correlation": 0.72,
      "max_correlation": 0.92,
      "min_correlation": -0.31,
      "std_correlation": 0.18
    }
  },
  "metadata": {
    "symbols": ["BTCUSDT", "ETHUSDT", ...],
    "timeframe": "1h",
    "lookback_periods": 100,
    "calculation_time": "2024-01-15T10:30:00Z",
    "data_points": 1500
  }
}
```

### 3. Asset Correlations

```http
GET /api/correlation/asset-correlations
```

Calculate correlations between assets based on signal patterns.

#### Response

```json
{
  "asset_correlations": {
    "BTCUSDT": {
      "BTCUSDT": 1.0,
      "ETHUSDT": 0.85,
      "ADAUSDT": 0.72,
      "DOTUSDT": 0.68,
      "AVAXUSDT": 0.71,
      "NEARUSDT": 0.65,
      "SOLUSDT": 0.78,
      "ALGOUSDT": 0.61,
      "ATOMUSDT": 0.69,
      "FTMUSDT": 0.74
    }
  },
  "statistics": {
    "mean_correlation": 0.71,
    "max_correlation": 0.85,
    "min_correlation": 0.61,
    "std_correlation": 0.07
  },
  "metadata": {
    "symbols": ["BTCUSDT", "ETHUSDT", ...],
    "timeframe": "1h",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### 4. Heatmap Data

```http
GET /api/correlation/heatmap-data
```

Get correlation data formatted for heatmap visualization.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `correlation_type` | str | "signals" | "signals" or "assets" |
| `symbols` | List[str] | All assets | Symbols to include |
| `timeframe` | str | "1h" | Analysis timeframe |

#### Response

```json
{
  "correlation_matrix": [
    [1.0, 0.75, 0.68, 0.82, 0.71, 0.64, 0.78, 0.85, 0.92, 0.56, -0.23],
    [0.75, 1.0, 0.82, 0.67, 0.73, 0.58, 0.89, 0.71, 0.88, 0.52, -0.31],
    [0.68, 0.82, 1.0, 0.71, 0.79, 0.61, 0.85, 0.73, 0.86, 0.49, -0.28]
  ],
  "labels": [
    "momentum", "technical", "volume", "orderflow", 
    "orderbook", "sentiment", "price_action", "beta_exp", 
    "confluence", "whale_act", "liquidation"
  ],
  "correlation_type": "signals",
  "statistics": {
    "signal_correlation_stats": {
      "mean_correlation": 0.72,
      "max_correlation": 0.92,
      "min_correlation": -0.31,
      "std_correlation": 0.18
    }
  },
  "metadata": {
    "dimensions": "11x11",
    "timeframe": "1h",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### 5. Live Matrix

```http
GET /api/correlation/live-matrix
```

Get live signal matrix data with real-time updates and performance metrics.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbols` | List[str] | All assets | Symbols to include |
| `refresh_interval` | int | 30 | Refresh interval in seconds |

#### Response

```json
{
  "live_matrix": {
    "BTCUSDT": {
      "momentum": {"score": 75.2, "direction": "bullish", "strength": "strong"},
      "technical": {"score": 68.5, "direction": "bullish", "strength": "medium"},
      "composite_score": 73.8
    }
  },
  "performance_metrics": {
    "accuracy": "94%",
    "latency": "12ms",
    "signals_pnl": "$12.4K",
    "active_count": 156,
    "win_rate": "8.7%",
    "sharpe": "2.3x"
  },
  "real_time_status": {
    "is_live": true,
    "last_update": "2024-01-15T10:30:00Z",
    "refresh_interval": 30,
    "data_freshness": "excellent"
  },
  "signal_types": [
    "momentum", "technical", "volume", "orderflow",
    "orderbook", "sentiment", "price_action", "beta_exp",
    "confluence", "whale_act", "liquidation"
  ],
  "metadata": {
    "symbols": ["BTCUSDT", "ETHUSDT", ...],
    "timeframe": "1h",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Signal Types

The API analyzes the following signal types:

| Signal Type | Description | Range |
|-------------|-------------|-------|
| `momentum` | Momentum indicators and trend strength | 0-100 |
| `technical` | Technical analysis indicators | 0-100 |
| `volume` | Volume-based indicators | 0-100 |
| `orderflow` | Order flow analysis | 0-100 |
| `orderbook` | Order book analysis | 0-100 |
| `sentiment` | Market sentiment indicators | 0-100 |
| `price_action` | Price action patterns | 0-100 |
| `beta_exp` | Beta exposure analysis | 0-100 |
| `confluence` | Confluence score | 0-100 |
| `whale_act` | Whale activity indicators | 0-100 |
| `liquidation` | Liquidation risk analysis | 0-100 |

## Signal Directions

| Direction | Description | Score Range |
|-----------|-------------|-------------|
| `bullish` | Positive signal | 60-100 |
| `bearish` | Negative signal | 0-40 |
| `neutral` | Neutral signal | 40-60 |

## Signal Strength

| Strength | Description | Score Range |
|----------|-------------|-------------|
| `strong` | High confidence | 70-100 or 0-30 |
| `medium` | Medium confidence | 30-70 |
| `weak` | Low confidence | 45-55 |

## Example Usage

### Python

```python
import aiohttp
import asyncio

async def get_live_matrix():
    """Get live signal matrix data."""
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8000/api/correlation/live-matrix") as response:
            data = await response.json()
            
            # Process matrix data
            live_matrix = data["live_matrix"]
            for symbol, signals in live_matrix.items():
                print(f"{symbol}: Composite Score = {signals['composite_score']}")
                
                # Show individual signals
                for signal_type, signal_data in signals.items():
                    if signal_type != "composite_score":
                        score = signal_data["score"]
                        direction = signal_data["direction"]
                        print(f"  {signal_type}: {score} ({direction})")

# Run the example
asyncio.run(get_live_matrix())
```

### JavaScript

```javascript
// Fetch live matrix data
async function getLiveMatrix() {
    try {
        const response = await fetch('/api/correlation/live-matrix');
        const data = await response.json();
        
        // Update dashboard matrix
        updateSignalMatrix(data.live_matrix);
        
        // Update performance metrics
        updatePerformanceMetrics(data.performance_metrics);
        
    } catch (error) {
        console.error('Error fetching live matrix:', error);
    }
}

// Update every 30 seconds
setInterval(getLiveMatrix, 30000);
```

### cURL

```bash
# Get signal confluence matrix
curl "http://localhost:8000/api/correlation/matrix?symbols=BTCUSDT,ETHUSDT&timeframe=1h"

# Get signal correlations
curl "http://localhost:8000/api/correlation/signal-correlations?lookback_periods=200"

# Get heatmap data for assets
curl "http://localhost:8000/api/correlation/heatmap-data?correlation_type=assets"

# Get live matrix with custom refresh interval
curl "http://localhost:8000/api/correlation/live-matrix?refresh_interval=60"
```

## Integration with Dashboard

The correlation API is automatically integrated with your dashboard. The matrix data is fetched and displayed in real-time:

```javascript
// Dashboard integration (already implemented)
async function fetchCorrelationData() {
    const response = await fetch('/api/correlation/live-matrix');
    return await response.json();
}

// The dashboard will automatically use correlation data if available
// and fall back to other signal sources if needed
```

## Performance Considerations

- **Caching**: Correlation calculations are cached for performance
- **Rate Limiting**: API calls are rate-limited to prevent overload
- **Data Freshness**: Matrix data is updated every 30 seconds by default
- **Fallback**: API provides fallback data when live sources are unavailable

## Error Handling

The API provides comprehensive error handling:

```json
{
  "error": "Error message",
  "detail": "Detailed error description",
  "timestamp": "2024-01-15T10:30:00Z",
  "endpoint": "/api/correlation/matrix"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid parameters)
- `404`: Endpoint not found
- `429`: Rate limit exceeded
- `500`: Internal server error 
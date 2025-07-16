# Liquidation Intelligence API Documentation

## Overview

The Liquidation Intelligence API provides real-time detection and analysis of liquidation events across cryptocurrency markets. It monitors unusual trading patterns, leverage ratios, and market stress indicators to identify potential forced liquidations and cascade risks.

**Base URL**: `/api/liquidation`

## Key Features

- **Real-time Liquidation Detection**: Identify liquidation events as they occur
- **Market Stress Monitoring**: Assess overall market stress levels
- **Cascade Risk Analysis**: Detect potential cascade liquidation events
- **Leverage Metrics**: Monitor funding rates and leverage indicators
- **Historical Analysis**: Track liquidation patterns over time
- **Risk Assessment**: Evaluate liquidation probability for specific symbols

---

## Authentication

All endpoints require valid API authentication. Include your API key in the request headers:

```
Authorization: Bearer YOUR_API_KEY
```

---

## Endpoints

### 1. Detect Liquidation Events

Performs real-time analysis to detect liquidation events across specified markets.

**Endpoint**: `POST /api/liquidation/detect`

**Request Body**:
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT"],
  "exchanges": ["binance", "bybit"],
  "sensitivity": 0.7,
  "lookback_minutes": 60
}
```

**Parameters**:
- `symbols` (required): Array of trading pairs to analyze
- `exchanges` (optional): Target exchanges (defaults to all available)
- `sensitivity` (0-1): Detection sensitivity level (default: 0.7)
- `lookback_minutes` (5-1440): Analysis time window (default: 60)

**Response**:
```json
{
  "detected_events": [
    {
      "event_id": "liq_001",
      "symbol": "BTCUSDT",
      "exchange": "binance",
      "timestamp": "2024-01-15T10:30:00Z",
      "liquidation_type": "long_liquidation",
      "severity": "high",
      "confidence_score": 0.85,
      "trigger_price": 45000.0,
      "price_impact": -3.5,
      "volume_spike_ratio": 4.2,
      "suspected_triggers": ["funding_rate_stress", "volume_spike"]
    }
  ],
  "market_stress": {
    "overall_stress_level": "high",
    "stress_score": 75.0,
    "warning_signals": ["Extreme funding rates detected"],
    "recommended_actions": ["Reduce leverage", "Monitor closely"]
  },
  "cascade_alerts": [],
  "analysis_timestamp": "2024-01-15T10:30:00Z",
  "detection_duration_ms": 1250
}
```

---

### 2. Get Active Liquidation Alerts

Retrieves currently active liquidation alerts across monitored markets.

**Endpoint**: `GET /api/liquidation/alerts`

**Query Parameters**:
- `min_severity`: Minimum alert severity (low/medium/high/critical)
- `max_age_minutes`: Maximum age of alerts in minutes (default: 60)
- `limit`: Maximum number of alerts to return (default: 20)
- `exchanges`: Comma-separated list of exchanges to filter

**Example Request**:
```
GET /api/liquidation/alerts?min_severity=medium&limit=10
```

**Response**:
```json
[
  {
    "event_id": "liq_002",
    "symbol": "ETHUSDT",
    "exchange": "bybit",
    "timestamp": "2024-01-15T10:25:00Z",
    "liquidation_type": "cascade_event",
    "severity": "critical",
    "confidence_score": 0.92,
    "trigger_price": 2850.0,
    "price_impact": -8.2,
    "volume_spike_ratio": 12.5
  }
]
```

---

### 3. Market Stress Indicators

Provides real-time market stress assessment across multiple indicators.

**Endpoint**: `GET /api/liquidation/stress-indicators`

**Query Parameters**:
- `symbols`: Specific symbols to analyze (optional)
- `exchanges`: Target exchanges (optional)

**Response**:
```json
{
  "overall_stress_level": "elevated",
  "stress_score": 65.0,
  "volatility_stress": 70.0,
  "funding_rate_stress": 60.0,
  "liquidity_stress": 55.0,
  "correlation_stress": 45.0,
  "leverage_stress": 80.0,
  "active_risk_factors": ["elevated_volatility", "funding_rate_stress"],
  "warning_signals": [
    "Volatility significantly above normal levels",
    "Extreme funding rates indicate high leverage"
  ],
  "recommended_actions": [
    "Reduce position sizes and increase stop-loss buffers",
    "Monitor for potential cascade liquidations"
  ]
}
```

---

### 4. Cascade Risk Assessment

Analyzes potential cascade liquidation risks across correlated markets.

**Endpoint**: `GET /api/liquidation/cascade-risk`

**Query Parameters**:
- `symbols`: Symbols to analyze for cascade risk (optional)
- `exchanges`: Target exchanges (optional)
- `min_probability`: Minimum cascade probability threshold (0-1, default: 0.5)

**Response**:
```json
[
  {
    "alert_id": "cascade_001",
    "severity": "high",
    "initiating_symbol": "BTCUSDT",
    "affected_symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
    "cascade_probability": 0.75,
    "estimated_total_liquidations": 100000000.0,
    "duration_estimate_minutes": 45,
    "immediate_actions": [
      "Reduce leverage across correlated positions",
      "Set tight stop-losses"
    ],
    "monitoring_priorities": ["BTCUSDT", "ETHUSDT"]
  }
]
```

---

### 5. Symbol Risk Assessment

Provides detailed liquidation risk analysis for a specific trading pair.

**Endpoint**: `GET /api/liquidation/risk/{symbol}`

**Path Parameters**:
- `symbol`: Trading pair symbol (e.g., BTCUSDT)

**Query Parameters**:
- `exchange`: Specific exchange to analyze (optional)
- `time_horizon_minutes`: Risk assessment timeframe (default: 60)

**Example Request**:
```
GET /api/liquidation/risk/BTCUSDT?time_horizon_minutes=120
```

**Response**:
```json
{
  "symbol": "BTCUSDT",
  "exchange": "binance",
  "liquidation_probability": 0.35,
  "risk_level": "medium",
  "time_horizon_minutes": 120,
  "funding_rate_pressure": 45.0,
  "liquidity_risk": 30.0,
  "technical_weakness": 55.0,
  "support_levels": [44000.0, 43500.0, 43000.0],
  "resistance_levels": [46000.0, 46500.0, 47000.0],
  "current_price": 45000.0,
  "price_distance_to_risk": 2.2,
  "similar_events_count": 3
}
```

---

### 6. Leverage Metrics

Retrieves detailed leverage and funding rate metrics for a symbol.

**Endpoint**: `GET /api/liquidation/leverage-metrics/{symbol}`

**Path Parameters**:
- `symbol`: Trading pair symbol

**Query Parameters**:
- `exchange`: Specific exchange (optional)

**Response**:
```json
{
  "symbol": "BTCUSDT",
  "exchange": "binance",
  "funding_rate": 0.005,
  "funding_rate_8h_avg": 0.0048,
  "funding_rate_24h_avg": 0.0045,
  "open_interest": 1000000000,
  "open_interest_24h_change": -2.5,
  "long_short_ratio": 1.15,
  "estimated_avg_leverage": 3.2,
  "max_leverage_available": 125,
  "leverage_stress_score": 60.0
}
```

---

### 7. Setup Real-time Monitoring

Configures continuous liquidation monitoring with webhook alerts.

**Endpoint**: `POST /api/liquidation/monitor`

**Request Body**:
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT"],
  "exchanges": ["binance"],
  "sensitivity_level": 0.8,
  "alert_threshold": "medium",
  "webhook_url": "https://your-webhook-endpoint.com"
}
```

**Response**:
```json
{
  "monitor_id": "monitor_1642248600",
  "status": "monitoring_started",
  "message": "Monitoring 2 symbols for liquidation events"
}
```

---

### 8. Stop Monitoring

Stops active liquidation monitoring.

**Endpoint**: `DELETE /api/liquidation/monitor/{monitor_id}`

**Response**:
```json
{
  "monitor_id": "monitor_1642248600",
  "status": "monitoring_stopped",
  "message": "Liquidation monitoring has been stopped"
}
```

---

### 9. Historical Liquidation Events

Retrieves historical liquidation events for a symbol.

**Endpoint**: `GET /api/liquidation/history/{symbol}`

**Query Parameters**:
- `exchange`: Specific exchange (optional)
- `days_back`: Number of days of history (1-30, default: 7)
- `limit`: Maximum number of events (1-200, default: 50)

**Response**:
```json
[
  {
    "event_id": "liq_hist_001",
    "symbol": "BTCUSDT",
    "timestamp": "2024-01-14T15:30:00Z",
    "liquidation_type": "long_liquidation",
    "severity": "high",
    "trigger_price": 44500.0,
    "price_impact": -4.2
  }
]
```

---

## Data Models

### LiquidationEvent

| Field | Type | Description |
|-------|------|-------------|
| event_id | string | Unique event identifier |
| symbol | string | Trading pair symbol |
| exchange | string | Exchange identifier |
| timestamp | datetime | Event timestamp |
| liquidation_type | enum | Type of liquidation (long_liquidation, short_liquidation, cascade_event, flash_crash) |
| severity | enum | Severity level (low, medium, high, critical) |
| confidence_score | float | Detection confidence (0-1) |
| trigger_price | float | Price at liquidation trigger |
| price_impact | float | Price impact percentage |
| volume_spike_ratio | float | Volume spike vs normal |

### MarketStressIndicator

| Field | Type | Description |
|-------|------|-------------|
| overall_stress_level | enum | Overall stress (calm, elevated, high, extreme) |
| stress_score | float | Quantified stress level (0-100) |
| volatility_stress | float | Volatility stress component |
| funding_rate_stress | float | Funding rate stress component |
| liquidity_stress | float | Liquidity stress component |
| active_risk_factors | array | Currently active risk factors |
| warning_signals | array | Warning messages |
| recommended_actions | array | Recommended risk mitigation actions |

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error description",
  "error_code": "LIQUIDATION_DETECTION_FAILED",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `INSUFFICIENT_DATA` | Not enough market data for analysis |
| `INVALID_SYMBOL` | Unsupported trading pair |
| `EXCHANGE_UNAVAILABLE` | Target exchange not accessible |
| `RATE_LIMIT_EXCEEDED` | API rate limit exceeded |
| `ANALYSIS_TIMEOUT` | Analysis took too long to complete |

---

## Rate Limits

- **Detection endpoints**: 10 requests per minute
- **Query endpoints**: 60 requests per minute
- **Monitoring endpoints**: 5 requests per minute

---

## WebSocket Integration

Real-time liquidation alerts can be streamed via WebSocket:

```javascript
const ws = new WebSocket('wss://api.example.com/ws/liquidation');

ws.onmessage = function(event) {
    const alert = JSON.parse(event.data);
    console.log('Liquidation alert:', alert);
};
```

---

## Implementation Examples

### Python Example

```python
import requests

# Detect liquidation events
response = requests.post('https://api.example.com/api/liquidation/detect', 
    json={
        'symbols': ['BTCUSDT', 'ETHUSDT'],
        'sensitivity': 0.7,
        'lookback_minutes': 60
    },
    headers={'Authorization': 'Bearer YOUR_API_KEY'}
)

events = response.json()['detected_events']
for event in events:
    print(f"Liquidation detected: {event['symbol']} - {event['severity']}")
```

### JavaScript Example

```javascript
const response = await fetch('/api/liquidation/stress-indicators');
const stress = await response.json();

if (stress.stress_score > 70) {
    console.warn('High market stress detected:', stress.warning_signals);
}
```

---

## Best Practices

1. **Sensitivity Tuning**: Start with default sensitivity (0.7) and adjust based on false positive rate
2. **Monitoring Setup**: Use webhooks for real-time alerts rather than polling
3. **Risk Management**: Combine liquidation signals with other risk indicators
4. **Rate Limiting**: Implement client-side rate limiting to avoid API limits
5. **Error Handling**: Always handle network errors and API failures gracefully

---

## Support

For API support or feature requests, please contact the development team or create an issue in the project repository. 
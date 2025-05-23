# Virtuoso Trading System

   ██╗   ██╗██╗██████╗ ████████╗██╗   ██╗ ██████╗ ███████╗ ██████╗ 
    ██║   ██║██║██╔══██╗╚══██╔══╝██║   ██║██╔═══██╗██╔════╝██╔═══██╗
    ██║   ██║██║██████╔╝   ██║   ██║   ██║██║   ██║███████╗██║   ██║
    ╚██╗ ██╔╝██║██╔══██╗   ██║   ██║   ██║██║   ██║╚════██║██║   ██║
     ╚████╔╝ ██║██║  ██║   ██║   ╚██████╔╝╚██████╔╝███████║╚██████╔╝
      ╚═══╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝ ╚═════╝ 
                                                                     
     ██████╗██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗              
    ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗             
    ██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║             
    ██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║             
    ╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝             
     ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝              
                                                                     
                      🚀 Advanced Signal Analytics 🚀      

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/fil0s/Virtuoso/python-tests.yml?branch=main&style=flat-square)
![License](https://img.shields.io/github/license/fil0s/Virtuoso?style=flat-square)
![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11-blue?style=flat-square)

## Table of Contents
- [Overview](#overview)
- [The Market Prism Concept](#the-market-prism-concept)
- [Getting Started](#getting-started)
- [Development](#development)
- [Documentation](#documentation)
- [Advanced System Features](#advanced-system-features)
  - [Atomic Data Fetching](#1-atomic-data-fetching)
  - [Enhanced Divergence Visualization](#2-enhanced-divergence-visualization)
  - [Advanced Open Interest Analysis](#3-advanced-open-interest-analysis)
  - [Real-time Market Monitoring](#4-real-time-market-monitoring)
  - [Machine Learning Signal Validation](#5-machine-learning-signal-validation)
  - [Signals API](#6-signals-api)
- [System Architecture](#system-architecture)
- [System Requirements](#system-requirements)
- [Quick Start Guide](#quick-start-guide)
- [API Endpoints Reference](#api-endpoints-reference)
- [Performance Optimization](#performance-optimization)
- [Contributing](#contributing)
- [License](#license)
- [Recent Fixes](#recent-fixes)

## Overview

Virtuoso is an advanced cryptocurrency trading system that combines real-time market analysis, multi-factor signal generation, and automated trading execution. The system leverages machine learning and statistical analysis to identify high-probability trading opportunities across multiple timeframes.

## The Market Prism Concept

Virtuoso approaches market analysis like a prism refracting light - taking in raw market data and decomposing it into six distinct analytical dimensions that combine to form a complete trading signal:

```
Raw Market Data (Spectrum) → Market Prism → Trading Signals (Light)
```

### The Six Faces of Market Analysis:

1. **Technical** 
   - Reveals the fastest-moving market forces
   - Captures immediate price action and directional strength
   - Identifies acceleration and deceleration patterns

2. **Volume**
   - Shows the depth and intensity of market moves
   - Measures participation and conviction
   - Validates price action with volume confirmation

3. **Orderflow**
   - Reveals the flow and pressure of trading activity
   - Tracks institutional activity and market maker behavior
   - Identifies significant accumulation/distribution

4. **Orderbook**
   - Shows the market's structural foundation
   - Maps supply and demand dynamics
   - Reveals potential support and resistance levels

5. **Price Structure**
   - Illuminates market participant positioning
   - Tracks aggregate trader behavior
   - Identifies potential squeeze points

6. **Sentiment**
   - Captures the market's emotional state
   - Measures market psychology and bias
   - Identifies extreme sentiment conditions

Just as a prism reveals the hidden spectrum within white light, Virtuoso's market prism reveals the underlying forces driving price action. The system combines these six dimensions into a coherent trading signal, with each component weighted according to its predictive power and market conditions.

---

## Getting Started

### Prerequisites

- Python 3.9+ 
- Git

### Installation

**Option 1: Standard Setup**

```bash
# Clone the repository
git clone https://github.com/fil0s/Virtuoso.git
cd Virtuoso

# Setup development environment
make setup
```

**Option 2: Docker Setup**

```bash
# Clone the repository
git clone https://github.com/fil0s/Virtuoso.git
cd Virtuoso

# Setup with Docker
make docker-setup
```

### Configuration

1. Copy the example environment file: `cp config/.env.example .env`
2. Edit the `.env` file with your specific configuration

---

## Development

### Running Tests

```bash
# Run all tests
make test

# Run tests in Docker
make docker-test
```

### Code Style

This project uses pre-commit hooks to enforce code style standards:

```bash
# Install pre-commit hooks
pre-commit install

# Run linting checks
make lint

# Format code
make format
```

---

## Documentation

Detailed documentation is available in the `docs/` directory:

- [API Documentation](docs/api/)
  - [API Overview](docs/api/index.md)
  - [Market Data API](docs/api/market.md)
  - [Trading API](docs/api/trading.md)
  - [System API](docs/api/system.md)
  - [Signals API](docs/api/signals.md)
  - [WebSocket API](docs/api/websocket.md)
  - [Authentication](docs/api/authentication.md)
- [User Guides](docs/guides/)
- [Development Guidelines](docs/development/)
- [Architecture Documentation](docs/architecture/)

---

## Advanced System Features

### 1. Atomic Data Fetching

Virtuoso implements an advanced atomic data fetching mechanism that ensures data consistency across different market metrics. This feature is critical for accurate market analysis as it prevents temporal misalignment between different data types.

#### Key Benefits of Atomic Fetching:

- **Data Consistency**: All market data (OHLCV, orderbook, trades, etc.) is fetched within the same time window, ensuring analytical coherence
- **Reduced Latency**: Parallel API requests optimize data retrieval speed
- **Error Resilience**: Comprehensive error handling with automatic retry mechanisms
- **Rate Limit Compliance**: Built-in rate limit awareness to prevent exchange API restrictions
- **Performance Monitoring**: Detailed metrics on fetch success rates and timing

#### Complete Metadata Structure:

Each atomic fetch operation captures a comprehensive set of metadata:

- **Symbol**: Trading pair identifier (e.g., "BTCUSDT")
- **Fetch Timestamps**:
  - Request start timestamp (ms precision)
  - Component-specific timestamps (for each data type)
  - Request completion timestamp
  - Duration (ms) for total fetch and component-level operations
  - Data age indicators (time since last update)
- **Data Components**:
  - **Ticker**: 
    - Latest price
    - 24h high/low
    - Bid/ask prices and sizes
    - 24h volume (base and quote)
    - 24h price change and percentage
    - Last price timestamp
  - **Orderbook**: 
    - Complete order book with depth (up to L2/L3 depending on exchange)
    - Aggregated volumes at price levels
    - Bid/ask imbalance ratios
    - Timestamp of orderbook snapshot
    - Sequence number (for order matching)
  - **Klines/OHLCV**: For multiple timeframes with full data for each:
    - Base (1m): Open, High, Low, Close, Volume
    - LTF (5m): Open, High, Low, Close, Volume
    - MTF (30m): Open, High, Low, Close, Volume
    - HTF (240m/4h): Open, High, Low, Close, Volume
    - Timestamp for each candle
  - **Trades**: 
    - Recent market trades with complete data:
      - Price
      - Size/amount
      - Side (buy/sell)
      - Cost (price * size)
      - Timestamp
      - Trade ID
      - Liquidation flag (when available)
  - **Long/Short Ratio**: 
    - Long vs short position distribution
    - Account ratio
    - Position ratio
    - Buy/sell volume ratio
  - **Open Interest**: 
    - Current open interest values
    - Historical open interest data when available
    - Open interest by timeframe
    - Timestamp of each data point
  - **Risk Limits**: 
    - Exchange-specific position limit data
    - Leverage tiers
    - Maintenance margin requirements
    - Position size limits
- **Performance Metrics**:
  - Component fetch timing (ms) for each data type
  - Success/error rates (overall and by component)
  - API rate limit usage and remaining quota
  - Data freshness indicators (age of data in ms)
  - Fetch efficiency scores
  - Queue time and processing time separation
  - Resource utilization during fetch
- **Error Metadata**:
  - Component-specific error tracking
  - Retry attempt counts and history
  - Exception details with stack traces
  - Error classification (network, rate limit, data parsing)
  - Recovery actions taken
  - Fallback data usage indicators

#### Implementation Details:

```python
async def _fetch_symbol_data_atomically(self, symbol: str) -> Dict[str, Any]:
    """
    Fetch all required data types for a symbol atomically to ensure data consistency
    across different market metrics. This prevents temporal misalignment issues.
    
    Args:
        symbol: Trading pair to fetch data for
        
    Returns:
        Dictionary containing all market data types
    """
    start_time = time.time()
    market_data = {}
    
    # Create tasks for parallel execution
    tasks = [
        self._fetch_ohlcv(symbol),
        self._fetch_orderbook(symbol),
        self._fetch_trades(symbol),
        self._fetch_ticker(symbol),
        self._fetch_funding_rate(symbol) if self._is_perpetual(symbol) else None
    ]
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*[t for t in tasks if t is not None], 
                                  return_exceptions=True)
    
    # Process results and handle any exceptions
    # ...
    
    end_time = time.time()
    logger.debug(f"Atomic fetch for {symbol} completed in {int((end_time - start_time) * 1000)}ms")
    return market_data
```

#### Performance Metrics:

- **Typical Fetch Time**: 150-300ms for complete market data
- **Success Rate**: >99.5% under normal network conditions
- **Data Freshness**: All data points within 500ms time window

### 2. Enhanced Divergence Visualization

Virtuoso includes sophisticated divergence visualization capabilities across all indicator classes, providing clear insights into how timeframe divergences affect trading signals.

#### Key Features:

- **Visual Divergence Tracking**: Color-coded indication of divergence impact on component scores
- **Detailed Contribution Breakdown**: Explicit display of divergence bonuses in score calculations
- **Cross-Indicator Consistency**: Standardized visualization across all indicator types
- **Real-time Adjustment Tracking**: Continuous monitoring of divergence effects on signals

#### Example Output:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ XRPUSDT Technical Score Contribution Breakdown                          │
├────────────────┬────────┬───────┬────────┬────────┬─────────────────────┤
│ COMPONENT      │ SCORE  │ WEIGHT │ IMPACT │ DIV    │ GAUGE              │
├────────────────┼────────┼───────┼────────┼────────┼─────────────────────┤
│ ao             │ 55.78  │ 0.20  │   11.2 │ +6.0   │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
│ macd           │ 59.93  │ 0.15  │    9.0 │ +4.0   │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │
│ rsi            │ 43.90  │ 0.20  │    8.8 │ 0.0    │ ▒▒▒▒▒▒▒▒▒▒▒▒▒      │
│ williams_r     │ 48.52  │ 0.15  │    7.3 │ -3.0   │ ▒▒▒▒▒▒▒▒▒▒▒▒       │
│ cci            │ 38.05  │ 0.15  │    5.7 │ 0.0    │ ░░░░░░░░░░         │
│ atr            │ 27.20  │ 0.15  │    4.1 │ 0.0    │ ░░░░░░             │
├────────────────┴────────┴───────┴────────┴────────┼─────────────────────┤
│ FINAL SCORE    │ 46.10  │       │        │ +7.0   │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒     │
└────────────────┴────────┴───────┴────────┴────────┴─────────────────────┘
* DIV column shows timeframe divergence adjustments
```

#### Implementation:

The system implements a standardized divergence visualization framework that works across all indicator types:

```python
def _apply_divergence_bonuses(self, component_scores, divergences):
    """
    Apply divergence bonuses to component scores with enhanced visualization
    
    Args:
        component_scores: Dictionary of component scores
        divergences: Dictionary of divergence data by component
        
    Returns:
        Dictionary of adjusted scores with divergence information
    """
    adjusted_scores = {}
    
    for component, score in component_scores.items():
        # Get divergence bonus if available
        div_bonus = divergences.get(component, {}).get('bonus', 0)
        
        # Apply the bonus
        adjusted_score = score + div_bonus
        adjusted_score = np.clip(adjusted_score, 0, 100)
        
        # Store the adjusted score with divergence information
        adjusted_scores[component] = {
            'score': adjusted_score,
            'raw_score': score,
            'divergence_bonus': div_bonus,
            'divergence_type': divergences.get(component, {}).get('type', 'none')
        }
    
    return adjusted_scores
```

### 3. Advanced Open Interest Analysis

Virtuoso incorporates sophisticated open interest (OI) analysis to track institutional positioning and market structure. This feature provides critical insights into market participant behavior and potential price movements.

#### Key Components:

- **OI Delta Tracking**: Monitors changes in open interest relative to price movement
- **OI Divergence Detection**: Identifies divergences between price action and open interest
- **Funding Rate Integration**: Correlates OI with funding rates to detect market imbalances
- **Position Concentration Analysis**: Detects significant position buildups and potential liquidation cascades
- **Multi-timeframe OI Structure**: Analyzes OI patterns across different timeframes

#### Implementation:

```python
class OpenInterestAnalyzer:
    """
    Analyzes open interest data to detect institutional positioning and market structure
    """
    
    def analyze_oi_structure(self, symbol, oi_data, price_data):
        """
        Analyze open interest structure and its relationship with price
        
        Args:
            symbol: Trading pair
            oi_data: Open interest time series
            price_data: Price time series
            
        Returns:
            Dictionary containing OI analysis results
        """
        # Calculate OI delta (change in OI)
        oi_delta = self._calculate_oi_delta(oi_data)
        
        # Analyze OI-price relationship
        oi_price_correlation = self._analyze_oi_price_correlation(oi_delta, price_data)
        
        # Detect OI divergences
        divergences = self._detect_oi_divergences(oi_data, price_data)
        
        # Analyze OI structure across timeframes
        timeframe_structure = self._analyze_timeframe_structure(symbol, oi_data)
        
        return {
            'oi_delta': oi_delta,
            'oi_price_correlation': oi_price_correlation,
            'divergences': divergences,
            'timeframe_structure': timeframe_structure,
            'score': self._calculate_oi_score(oi_delta, oi_price_correlation, divergences)
        }
```

#### Interpretation Guidelines:

- **Rising OI + Rising Price**: Strong bullish trend confirmation
- **Rising OI + Falling Price**: Strong bearish trend confirmation
- **Falling OI + Rising Price**: Weak bullish trend, potential reversal
- **Falling OI + Falling Price**: Weak bearish trend, potential reversal
- **OI Divergence**: Early warning of potential trend reversal

### 4. Real-time Market Monitoring

Virtuoso features a comprehensive real-time market monitoring system that continuously tracks market conditions and generates alerts for significant events.

#### Key Features:

- **Multi-Exchange Monitoring**: Simultaneous tracking across multiple exchanges
- **Custom Alert Conditions**: Configurable alert triggers based on market conditions
- **Liquidation Tracking**: Real-time detection of significant liquidation events
- **Volatility Monitoring**: Alerts for unusual volatility spikes
- **Volume Anomaly Detection**: Identification of abnormal trading volume
- **Sentiment Shifts**: Detection of rapid changes in market sentiment

### 5. Machine Learning Signal Validation

Virtuoso incorporates advanced machine learning models to validate trading signals and enhance prediction accuracy.

#### Key Features:

- **Pattern Recognition**: Sophisticated pattern recognition for market structure analysis
- **False Signal Filtering**: ML-based filtering of potential false signals
- **Regime Classification**: Automatic market regime detection and classification
- **Signal Strength Prediction**: ML-enhanced prediction of signal strength and reliability
- **Adaptive Learning**: Continuous model improvement based on market feedback

### 6. Signals API

Virtuoso provides a comprehensive REST API for retrieving trading signals, which can be integrated with trading platforms, dashboards, or custom applications.

#### Available Endpoints:

- **/api/signals/latest**: Retrieves the latest signals across all symbols (default limit: 5, max: 20)
- **/api/signals/symbol/{symbol}**: Gets signals for a specific symbol (default limit: 10, max: 100)
- **/api/signals**: Retrieves all signals with pagination and filtering options (by symbol, signal type, date range, minimum score)
- **/api/signals/file/{filename}**: Gets a specific signal by its filename

#### Signal Structure:

Each signal includes comprehensive metadata and analysis:

```json
{
  "symbol": "BTCUSDT",           // Trading pair
  "signal": "BULLISH",           // BULLISH, BEARISH, or NEUTRAL
  "score": 75.4,                 // Confluence score (0-100)
  "reliability": 0.85,           // Signal reliability score (0-1)
  "price": 55000.0,              // Price at signal generation
  "timestamp": 1678234567000,    // UTC timestamp
  "components": {                // Component scores
    "price_action": {
      "score": 80,
      "impact": 4.0,
      "interpretation": "Strong bullish price action"
    },
    "momentum": {
      "score": 70,
      "impact": 3.0
    },
    "technical": { /*...*/ },
    "volume": { /*...*/ },
    "orderbook": { /*...*/ },
    "orderflow": { /*...*/ },
    "sentiment": { /*...*/ },
    "price_structure": { /*...*/ }
  },
  "entry_price": 54800.0,        // Recommended entry level
  "stop_loss": 53500.0,          // Suggested stop loss
  "targets": {                   // Price targets
    "target1": { "price": 57500.0 },
    "target2": { "price": 60000.0 }
  },
  "insights": [                  // Key market observations
    "Volume increasing with price breakout",
    "Multi-timeframe momentum alignment"
  ],
  "actionable_insights": [       // Specific trading recommendations
    "Consider entry on retest of 54800 level",
    "Scale out at first target (57500)"
  ]
}
```

#### Implementation:

Signals are stored as JSON files in the `reports/json` directory and served through FastAPI endpoints. The system provides extensive filtering and pagination capabilities for efficient data retrieval:

```python
@router.get("/", response_model=SignalList)
async def get_all_signals(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    symbol: Optional[str] = None,
    signal_type: Optional[str] = None,
    min_score: Optional[float] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """
    Get paginated list of signals with filtering options
    """
    # Implementation with filters, pagination, and sorting
```

For quick testing and development, a standalone test script (`test_signals_api.py`) is provided that creates a minimal FastAPI app with only the signals router:

```python
# Run with: python test_signals_api.py
from fastapi import FastAPI
import uvicorn
from src.api.routes.signals import router as signals_router

app = FastAPI(title="Signals API Test")
app.include_router(signals_router, tags=["signals"])

if __name__ == "__main__":
    # Opens browser to the API docs automatically
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

This script automatically creates sample signals if none exist and opens the Swagger UI documentation in your browser, making it easy to explore and test the API endpoints.

#### Signal Reports and Visualizations

In addition to JSON data, Virtuoso generates comprehensive PDF reports and charts for each trading signal:

- **PDF Reports**: Detailed analysis documents containing signal data, market context, component breakdowns, and trading recommendations
- **Chart Images**: Technical charts with entry/exit levels, targets, and key indicators visualized

These files are automatically generated alongside JSON signals and stored in organized directories:
- JSON files: `reports/json/`
- PDF reports: `reports/pdfs/`
- Chart images: `reports/charts/`

The report generation system includes:

1. **Candlestick Charts with Annotations**:
   - Entry and exit levels
   - Stop-loss visualization
   - Target price levels 
   - Color-coded zones for risk/reward

2. **Component Breakdowns**:
   - Visual representation of each analysis component
   - Score contribution charts
   - Pattern identification graphics

3. **PDF Organization**:
   - Signal summary
   - Market context
   - Trading recommendations
   - Risk management guidelines

File naming follows a consistent pattern: `{SYMBOL}_{TIMESTAMP}_{TYPE}.{EXTENSION}` for easy reference and retrieval.

#### Accessing PDF Reports and Charts

The Signals API provides access to PDF reports and chart images through dedicated endpoints:

- **/api/signals/file/{filename}/pdf**: Retrieves the PDF report associated with a specific signal
- **/api/signals/file/{filename}/chart**: Gets the chart image associated with a signal

Each signal in the API response includes references to its associated files:

```json
{
  "symbol": "BTCUSDT",
  "signal": "BULLISH",
  "score": 78.5,
  // ... other signal data ...
  "file_references": {
    "json": "/reports/json/BTCUSDT_20230401_123045_data.json",
    "pdf": "/reports/pdfs/BTCUSDT_20230401_123045_report.pdf",
    "chart": "/reports/charts/BTCUSDT_20230401_123045_chart.png"
  }
}
```

For integration with external systems, Base64-encoded versions of PDFs and charts can be requested:

```
GET /api/signals/file/{filename}/pdf?format=base64
```

This makes it easy to embed reports and visualizations directly into web applications, trading platforms, or notification systems.

The signals API serves as the core output interface for the Virtuoso trading system, allowing seamless integration with downstream applications and trading interfaces.

---

## System Architecture

For a detailed system architecture diagram and component descriptions, see [System Architecture Documentation](docs/architecture/system_architecture.md).


### Data Flow
```
Market Data → Analysis → Trading
├── L1: Raw Data
│   ├── Trade data
│   ├── Order book
│   └── Market info
│
├── L2: Processed Data
│   ├── OHLCV aggregation
│   ├── Volume profiles
│   └── Order flow metrics
│
├── L3: Indicator Layer
│   ├── Technical indicators
│   ├── Custom metrics
│   └── Market context
│
├── L4: Signal Layer
│   ├── Pattern detection
│   ├── Trend analysis
│   └── Entry/exit signals
│
└── L5: Execution Layer
    ├── Position sizing
    ├── Order generation
    └── Risk checks
```

### System Components
1. **Data Layer**
   - Market data processing
   - Data validation
   - Storage management
   - Cache optimization

2. **Analysis Engine**
   - Indicator calculation
   - Pattern recognition
   - Signal generation
   - Risk assessment

3. **Execution Engine**
   - Order management
   - Position sizing
   - Risk controls
   - Performance monitoring

---

## System Requirements

### Hardware Requirements
- CPU: 8+ cores recommended
- RAM: 16GB minimum, 32GB+ recommended
- Storage: 500GB+ SSD
- Network: Low-latency connection

### Software Requirements
- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- TA-Lib
- Required Python packages:
  * NumPy
  * Pandas
  * Scikit-learn
  * FastAPI
  * CCXT
  * Pydantic
  * SQLAlchemy

### Exchange Requirements
- API access with required permissions
- Rate limit considerations
- Data feed subscriptions
- Account verification levels

---

## Quick Start Guide

### 1. Initial Setup
```bash
# Clone repository
git clone https://github.com/fil0s/Virtuoso.git
cd virtuoso

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
```

### 2. Configuration
```yaml
# config/config.yaml
system:
  environment: production
  log_level: INFO
  debug_mode: false
  
exchanges:
  - name: binance
    type: spot
    api_key: ${BINANCE_API_KEY}
    api_secret: ${BINANCE_API_SECRET}
    testnet: false
    
  - name: bybit
    type: futures
    api_key: ${BYBIT_API_KEY}
    api_secret: ${BYBIT_API_SECRET}
    testnet: false

trading:
  max_positions: 10
  base_position_size: 0.01
  max_leverage: 3.0
  
risk:
  max_drawdown: 0.15
  position_heat: 0.25
  correlation_limit: 0.7
```

### 3. Start Services
```bash
# Start Redis
redis-server

# Start PostgreSQL
sudo service postgresql start

# Start API server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Verify Installation
```bash
# Run tests
pytest tests/

# Check API health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

---

## API Endpoints Reference

Virtuoso provides a comprehensive suite of REST API endpoints and WebSocket connections for integrating with trading platforms, dashboards, or custom applications.

### Signals API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/signals/latest` | GET | Get the latest signals across all symbols |
| `/api/signals/symbol/{symbol}` | GET | Get signals for a specific symbol |
| `/api/signals` | GET | Get all signals with filtering and pagination |
| `/api/signals/{filename}` | GET | Get a specific signal by its filename |

### Market Data API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/market/exchanges` | GET | List all available exchanges |
| `/api/market/{exchange_id}/{symbol}/data` | GET | Get market data for a symbol from a specific exchange |
| `/api/market/{exchange_id}/{symbol}/orderbook` | GET | Get orderbook data for a symbol |
| `/api/market/{exchange_id}/{symbol}/trades` | GET | Get recent trades for a symbol |
| `/api/market/compare/{symbol}` | GET | Compare market data across all exchanges for a symbol |
| `/api/market/{exchange_id}/{symbol}/analysis` | GET | Get technical analysis for a symbol |

### System API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/system/status` | GET | Get overall system status including CPU, memory, disk usage and exchange status |
| `/api/system/config` | GET | Get system configuration (excluding sensitive data) |
| `/api/system/exchanges/status` | GET | Get detailed status for each exchange |
| `/api/system/performance` | GET | Get system performance metrics |

### Trading API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trading/{exchange_id}/order` | POST | Place a new order on a specific exchange |
| `/api/trading/{exchange_id}/orders` | GET | Get orders from a specific exchange |
| `/api/trading/{exchange_id}/positions` | GET | Get open positions from a specific exchange |
| `/api/trading/{exchange_id}/position/update` | POST | Update position parameters (stop loss, take profit) |
| `/api/trading/portfolio/summary` | GET | Get portfolio summary across all exchanges |

### WebSocket API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ws/{client_id}` | WebSocket connection for real-time data |

#### WebSocket Message Types

- `subscribe` - Subscribe to real-time updates for a symbol
- `unsubscribe` - Unsubscribe from updates for a symbol
- `market_update` - Real-time market data and analysis updates (sent from server to client)

For detailed API documentation including request parameters, response formats, and example usage, see the [API Documentation](docs/api/) section.

---

## Performance Optimization

### 1. Data Processing
- Efficient data structures
  * NumPy arrays for calculations
  * Pandas for analysis
  * Redis for caching

### 2. Calculation Optimization
- Vectorized operations
- Parallel processing
- GPU acceleration
- Caching strategies

### 3. Network Optimization
- WebSocket connection management
- Request batching
- Rate limit optimization
- Connection pooling

### 4. Database Optimization
- Index optimization
- Query performance
- Connection pooling
- Data partitioning

---

## Contributing

We welcome contributions! Please see [Contributing Guidelines](.github/CONTRIBUTING.md) for more information.

## License

This project is licensed under the [LICENSE](LICENSE) - see the LICENSE file for details.

---

**Note**: Additional detailed documentation is available in the `docs/` directory, including API specifications, component details, and advanced usage guides.

## Recent Fixes

### Fixed Validation Rules Registration
- Added proper `add_rule` method to both sync and async `ValidationService` classes
- The method now correctly handles data type and rule registration
- Improved error logging for validation failures

### Fixed Open Interest History Fetching
- Implemented comprehensive `fetch_open_interest_history` method in CCXTExchange class
- Added caching mechanism to prevent excessive API calls
- Implemented exchange-specific handling (especially for Bybit)
- Added fallback mechanism to create synthetic data when exchange doesn't support history

### Fixed Logging Issues
- Fixed 'Logger' object has no attribute 'trace' error in momentum indicators
- Added safe initialization of trace logging level (5) in indicator package
- Improved trace method implementation to follow Python logging standards
- Added conditional addition to prevent duplicate trace method registration

### Enhanced Data Collection
- Improved data collection for trade history and orderbook depth
- Added better error handling for insufficient data scenarios
- Implemented synthetic data generation for missing open interest history
- Improved exchange integration for more reliable data fetching

All fixes have been designed to maintain backward compatibility while improving reliability and data quality.

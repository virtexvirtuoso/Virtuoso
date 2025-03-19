# Market Monitoring System

This directory contains a comprehensive monitoring system for cryptocurrency market data, designed to provide robust tracking, validation, and health monitoring capabilities.

## 🔍 Key Components

### 1. MarketMonitor

The `MarketMonitor` class is responsible for fetching and validating market data from cryptocurrency exchanges.

**Features:**
- Fetches OHLCV (candlestick), orderbook, and trades data
- Applies retry logic with exponential backoff
- Implements rate limiting to avoid API throttling
- Validates data quality and freshness
- Tracks performance metrics and memory usage
- Provides detailed debugging and visualization tools

### 2. MetricsManager

The `MetricsManager` tracks various performance metrics related to API calls, data fetching, and system resources.

**Features:**
- Tracks operation durations
- Monitors API call success/failure rates
- Records memory usage and detects leaks
- Provides comprehensive metrics reporting
- Enables trend analysis over time

### 3. HealthMonitor

The `HealthMonitor` tracks system and API health, providing alerts when issues are detected.

**Features:**
- Monitors CPU, memory, and disk usage
- Tracks API availability and response times
- Generates alerts for critical conditions
- Maintains historical health data
- Provides health status reporting

## 📊 Visualization Capabilities

The system includes visualization tools for market data analysis:
- Candlestick charts for OHLCV data
- Depth charts for orderbooks
- Trade activity visualization
- Visualizations can be saved as PNG files or returned as base64-encoded strings

## 🚨 Alerting System

The alerting system can detect and report various issues:
- System resource thresholds exceeded
- API availability problems
- Data quality issues
- Response time degradation

Alerts can be handled via callbacks for integration with notification systems (Slack, email, etc.)

## 🔄 Validation System

The validation system ensures data quality by checking:
- Data completeness (minimum number of candles, orderbook levels, trades)
- Data freshness (maximum age for each data type)
- Data structure and integrity

## 🚀 Getting Started

### Installation

Ensure you have installed all required dependencies:

```bash
pip install ccxt pandas numpy matplotlib psutil
```

### Basic Usage

```python
import asyncio
import ccxt.async_support as ccxt
from src.monitoring.metrics_manager import MetricsManager
from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.monitor import MarketMonitor

async def main():
    # Initialize components
    metrics_manager = MetricsManager()
    health_monitor = HealthMonitor(metrics_manager=metrics_manager)
    await health_monitor.start_monitoring()
    
    # Initialize exchange
    exchange = ccxt.binance({'enableRateLimit': True})
    
    # Initialize market monitor
    market_monitor = MarketMonitor(
        exchange=exchange,
        symbol='BTC/USDT',
        metrics_manager=metrics_manager,
        health_monitor=health_monitor
    )
    
    # Fetch market data
    market_data = await market_monitor.fetch_market_data()
    
    # Clean up
    await exchange.close()
    await health_monitor.stop_monitoring()

# Run the main function
asyncio.run(main())
```

See the `examples/market_monitor_example.py` for a complete working example.

## ⚙️ Configuration Options

The system supports various configuration options:

### MarketMonitor Configuration

```python
market_monitor = MarketMonitor(
    exchange=exchange,
    symbol='BTC/USDT',
    timeframes={'ltf': '1m', 'mtf': '15m', 'htf': '1h'},
    validation_config={
        'max_ohlcv_age_seconds': 300,
        'min_ohlcv_candles': 20,
        'max_orderbook_age_seconds': 60,
        'min_orderbook_levels': 5,
        'max_trades_age_seconds': 300,
        'min_trades_count': 5
    },
    rate_limit_config={
        'enabled': True,
        'max_requests_per_second': 5,
        'timeout_seconds': 10
    },
    retry_config={
        'max_retries': 3,
        'retry_delay_seconds': 2,
        'retry_exponential_backoff': True
    },
    debug_config={
        'log_raw_responses': False,
        'verbose_validation': True,
        'save_visualizations': True,
        'visualization_dir': 'visualizations'
    }
)
```

### HealthMonitor Configuration

```python
health_monitor = HealthMonitor(
    metrics_manager=metrics_manager,
    alert_callback=alert_callback_function,
    config={
        'check_interval_seconds': 60,
        'cpu_warning_threshold': 80,
        'cpu_critical_threshold': 95,
        'memory_warning_threshold': 80,
        'memory_critical_threshold': 95,
        'disk_warning_threshold': 80,
        'disk_critical_threshold': 95,
        'alert_log_path': 'logs/alerts.json'
    }
)
```

## 📈 Advanced Features

### Memory Leak Detection

The system can detect potential memory leaks by analyzing memory snapshots:

```python
# Get memory leak report
report = metrics_manager.generate_memory_report()
```

### API Health Analysis

Get detailed information about API health:

```python
# Get API health summary
api_health = health_monitor.get_api_health_summary()
```

### Health Metrics Dashboard

Convert health metrics to a DataFrame for analysis and visualization:

```python
# Get health metrics as DataFrame
health_df = health_monitor.get_health_metrics_df()
```

## 🔗 Integration with Other Systems

The monitoring system is designed to be modular and easily integrated with other systems:

- **Exchanges**: Works with any exchange supported by CCXT
- **Alert Systems**: Customizable alert callbacks for integration with notification systems
- **Data Storage**: Metrics and health data can be exported for long-term storage and analysis
- **Visualization Tools**: Generated visualizations can be saved or served via web interfaces 
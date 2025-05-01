# Virtuoso Trading System - Repository Update Guide

This document provides instructions for updating the Virtuoso Trading System to the latest version, including the newly added features and enhancements.

## What's New

The latest update includes several significant enhancements:

1. **New Signals API**: A complete RESTful API for retrieving trading signals
2. **Enhanced Signal Generation**: Improved multi-component analysis
3. **PDF Report Generation**: Support for generating PDF reports with annotated charts
4. **Chart Image Generation**: Automated creation of chart images with entry/exit levels
5. **Confluence Analysis Log Images**: Integration of confluence breakdown logs into PDF reports
6. **Dynamic Symbol Trading**: Automatic symbol management based on incoming signals
7. **Improved Market Interpretations**: Enhanced analysis for all market components
8. **Discord Alert Formatting**: Improved formatting for better readability
9. **Environment Variable Management**: Streamlined setup for InfluxDB credentials

## Update Instructions

### 1. Clone/Pull Latest Code

If you're setting up a new instance:

```bash
git clone https://github.com/fil0s/Virtuoso.git
cd Virtuoso
```

If you're updating an existing instance:

```bash
cd Virtuoso
git pull origin main
```

### 2. Update Dependencies

The latest version includes new dependencies for PDF generation and additional functionality:

```bash
# Activate your virtual environment
source venv/bin/activate  # On Unix/MacOS
# OR
venv\Scripts\activate     # On Windows

# Update dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

If you're setting up a new instance, copy the example environment file:

```bash
cp config/.env.example .env
```

Edit the `.env` file to configure your API keys and system settings.

For InfluxDB configuration, you can use the new environment management script:

```bash
# Set up InfluxDB environment variables
bash set_influxdb_env.sh
```

### 4. Create Required Directories

Ensure the report directories exist:

```bash
mkdir -p reports/json
mkdir -p reports/pdf
mkdir -p reports/charts
mkdir -p reports/session_reports
```

### 5. Test the Installation

Run the test suite to verify everything is working correctly:

```bash
make test
# OR
pytest -c config/ci/pytest.ini
```

## New Features Overview

### Signals API

The new Signals API provides comprehensive endpoints for retrieving trading signals:

- `/api/signals/latest` - Get latest signals with configurable limits
- `/api/signals/symbol/{symbol}` - Get signals for specific symbols
- `/api/signals` - Get paginated list of signals with extensive filtering options
- `/api/signals/file/{filename}` - Get specific signal by filename

#### Example Usage:

```python
import requests

# Get the latest 5 signals
response = requests.get("http://your-server/api/signals/latest?limit=5")
latest_signals = response.json()

# Get signals for a specific symbol
symbol = "BTCUSDT"
response = requests.get(f"http://your-server/api/signals/symbol/{symbol}")
symbol_signals = response.json()

# Get signals with filtering
params = {
    "symbol": "ETHUSDT",
    "signal_type": "BULLISH",
    "min_score": 75,
    "page": 1,
    "size": 10
}
response = requests.get("http://your-server/api/signals", params=params)
filtered_signals = response.json()
```

### PDF Report Generation

The system now supports generating PDF reports with annotated charts for trading signals. These reports include:

- Entry and exit levels
- Price targets
- Risk-to-reward ratios
- Component score breakdowns
- Market condition analysis
- Confluence analysis log images
- Detailed market interpretations

Reports are stored in the `reports/pdf` directory and can be accessed through the API.

### Chart Image Generation

The system automatically generates chart images with technical analysis annotations, including:

- Entry points
- Stop-loss levels
- Take-profit targets
- Key support and resistance levels
- Indicator signals

These charts are included in the PDF reports and can be accessed separately through the API.

### Dynamic Symbol Trading

The system now supports dynamic symbol management based on incoming signals:

- Automatically adds new trading symbols when signals are received
- Executes trades based on signal recommendations
- Monitors active positions for each symbol
- Manages risk parameters dynamically

This feature allows the system to respond to opportunities across a wider range of markets without manual configuration.

### Enhanced Market Interpretations

Market analysis components have been significantly improved:

- **Sentiment Analysis**: Detailed market psychology insights and extreme sentiment conditions
- **Technical Analysis**: Improved pattern recognition and directional strength indicators
- **Orderbook Analysis**: Enhanced supply/demand dynamics and liquidity zone identification
- **Volume Analysis**: Better metrics for participation and conviction
- **Price Structure Analysis**: Detailed market positioning and potential squeeze points
- **Orderflow Analysis**: Advanced tracking of institutional activity and market maker behavior

These enhancements provide more detailed and actionable insights in alerts and reports.

## Configuration Options

### Signal Generation

You can configure the signal generation parameters in the config file:

```yaml
# config/config.yaml
signals:
  min_score: 65
  reliability_threshold: 75
  timeframes: ["1m", "5m", "15m", "1h", "4h", "1d"]
  component_weights:
    technical: 0.4
    volume: 0.2
    orderflow: 0.15
    orderbook: 0.15
    sentiment: 0.1
  report_generation:
    generate_pdf: true
    generate_charts: true
    store_json: true
    include_confluence_image: true
```

### API Rate Limiting

The Signals API includes rate limiting to prevent abuse. You can configure these limits in the config file:

```yaml
# config/config.yaml
api:
  rate_limit:
    default: 100  # requests per minute
    signals: 60   # requests per minute for signal endpoints
```

### Discord Alert Configuration

The Discord alert formatting can be configured in the config file:

```yaml
# config/config.yaml
alerts:
  discord:
    enable: true
    include_details: true
    format: "enhanced"  # "basic" or "enhanced"
    include_images: true
```

## Troubleshooting

### Common Issues

1. **PDF Generation Fails**: Ensure that all required dependencies for PDF generation are installed. You may need additional system libraries depending on your OS.

2. **Missing Data**: If signals aren't appearing, check that the market data fetching is configured correctly and that your exchange API keys have the necessary permissions.

3. **API Access Issues**: Verify that the API server is running and that you're using the correct endpoints and authentication.

4. **InfluxDB Connection Problems**: If you're experiencing issues with InfluxDB connectivity, run the `set_influxdb_env.sh` script to ensure your environment variables are correctly set.

5. **Reliability Score Discrepancies**: If you notice inconsistencies in reliability scores between logs and alerts, ensure you have the latest version which includes fixes for this issue.

### Logs

Check the logs for detailed error information:

```bash
cat logs/virtuoso.log
```

## Additional Resources

- [API Documentation](docs/api/)
- [Development Guidelines](docs/development/)
- [Architecture Documentation](docs/architecture/)

## Support

For additional support, please open an issue on the GitHub repository or contact the development team. 
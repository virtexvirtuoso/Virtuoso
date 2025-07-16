# Bitcoin Beta Analysis Report

## Overview

The Bitcoin Beta Analysis Report is a sophisticated quantitative trading tool that analyzes correlations between Bitcoin and other cryptocurrencies across multiple timeframes. This report provides traders with actionable insights into how different assets move relative to Bitcoin, helping inform portfolio construction and risk management decisions.

## Features

### 🔍 Multi-Timeframe Analysis
- **4H (High Timeframe)**: ~90 days of data for long-term trends
- **30M (Medium Timeframe)**: ~15 days of data for medium-term patterns  
- **5M (Low Timeframe)**: ~3 days of data for short-term movements
- **1M (Base Timeframe)**: ~8 hours of data for real-time analysis

### 📊 Statistical Measures for Traders
- **Beta Coefficient**: How much an asset moves relative to Bitcoin
- **Correlation (R)**: Strength of relationship (-1 to +1)
- **R-squared**: Percentage of price movements explained by Bitcoin
- **Volatility Ratio**: Asset volatility compared to Bitcoin volatility
- **Alpha**: Excess returns independent of Bitcoin movements
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Worst peak-to-trough decline
- **Rolling Beta**: Recent 30-period correlation trends

### 📈 Professional Charts
- **Normalized Performance Chart**: All prices start at 100 to show relative performance
- **Beta Comparison**: Side-by-side beta coefficients across timeframes
- **Correlation Heatmap**: Visual correlation matrix across timeframes
- **Bitcoin in orange** with other assets in distinct colors

### 🤖 Dynamic Symbol Selection
- Uses current symbols being analyzed by the system
- Automatically includes BTCUSDT as reference asset
- Supports up to 10 symbols for readability

### ⏰ Automated Scheduling
- Runs every 6 hours starting at 00:00 UTC
- Schedule: 00:00, 06:00, 12:00, 18:00 UTC daily
- Manual generation available via API

## Understanding Beta

### What is Beta?
Beta measures how much an asset's price moves relative to Bitcoin's price movements:

- **β = 1.0**: Asset moves exactly with Bitcoin
- **β > 1.0**: Asset is more volatile than Bitcoin (amplifies movements)
- **β < 1.0**: Asset is less volatile than Bitcoin (dampens movements)
- **β = 0.0**: Asset has no correlation with Bitcoin

### Trading Applications

#### Portfolio Construction
- **High Beta Assets (β > 1.2)**: Use for amplified Bitcoin exposure
- **Medium Beta Assets (0.8 < β < 1.2)**: Core portfolio holdings
- **Low Beta Assets (β < 0.8)**: Diversification and risk reduction

#### Risk Management
- **Monitor correlation breakdown**: When β drops significantly across timeframes
- **Hedge positions**: Use low-beta assets to offset high-beta exposure
- **Position sizing**: Adjust based on beta to maintain target volatility

#### Market Timing
- **Rising correlations**: May indicate risk-on market conditions
- **Diverging assets**: Potential alpha opportunities
- **Cross-timeframe analysis**: Identify changing market regimes

## File Structure

```
src/reports/
├── bitcoin_beta_report.py      # Main report generator
├── bitcoin_beta_scheduler.py   # Automated scheduling
└── __init__.py

scripts/
├── run_bitcoin_beta_report.py  # Manual execution script
└── test_bitcoin_beta.py        # Test suite with mock data

exports/bitcoin_beta_reports/   # Generated reports
├── bitcoin_beta_report_YYYYMMDD_HHMMSS.pdf
├── performance_chart_*.png
├── beta_comparison_*.png
└── correlation_heatmap_*.png
```

## API Endpoints

### Get Status
```bash
GET /api/bitcoin-beta/status
```

Returns scheduler status and feature information.

### Generate Report Manually
```bash
POST /api/bitcoin-beta/generate
```

Triggers immediate report generation and returns file path.

## Usage

### Manual Generation
```bash
# Run the manual script
python scripts/run_bitcoin_beta_report.py

# Or use the API
curl -X POST http://localhost:8000/api/bitcoin-beta/generate
```

### Integration with Main System
```python
from src.reports.bitcoin_beta_scheduler import initialize_beta_scheduler

# Initialize during system startup
beta_scheduler = await initialize_beta_scheduler(
    exchange_manager=exchange_manager,
    top_symbols_manager=top_symbols_manager,
    config=config,
    alert_manager=alert_manager  # Optional
)
```

### Testing
```bash
# Run test suite with mock data
python scripts/test_bitcoin_beta.py
```

## Configuration

The report uses existing system configuration:

```yaml
# config/config.yaml
market:
  symbols:
    static_symbols:
      - BTCUSDT
      - ETHUSDT
      - SOLUSDT
      - AVAXUSDT
      - XRPUSDT
    max_symbols: 15
    use_static_list: false  # Uses dynamic symbols when false
```

## Output Example

### PDF Report Sections
1. **Executive Summary**: Overview of analysis methodology
2. **Beta Summary Table**: Key statistics for 4H timeframe
3. **Charts**: 
   - Normalized price performance
   - Beta comparison across timeframes
   - Correlation heatmap
4. **Key Trading Insights**: Automated analysis highlights

### Sample Insights
- "SOL shows the highest beta (1.45), making it most sensitive to Bitcoin movements"
- "XRP shows the lowest beta (0.67), offering potential diversification benefits"  
- "ETH has the strongest correlation with Bitcoin (0.89)"
- "AVAX is 1.3x more volatile than Bitcoin"

## Dependencies

```python
# Core dependencies
numpy>=1.21.0
pandas>=1.3.0
matplotlib>=3.5.0
reportlab>=3.6.0
schedule>=1.1.0

# Existing system components
exchange_manager
top_symbols_manager
config_manager
```

## Performance Considerations

### Data Requirements
- **4H timeframe**: 540 candles (~90 days)
- **30M timeframe**: 720 candles (~15 days)
- **5M timeframe**: 864 candles (~3 days)
- **1M timeframe**: 480 candles (~8 hours)

### Optimization
- Rate limiting: 0.1s between symbol requests
- Minimum data validation: 50 candles per timeframe
- Statistical significance: 30+ aligned data points for beta calculation
- Chart caching: Temporary files cleaned after PDF generation

### Resource Usage
- Memory: ~50MB during generation
- Disk: ~500KB per PDF report
- Network: ~20 API calls per report
- CPU: ~30 seconds generation time

## Troubleshooting

### Common Issues

#### Insufficient Data
```
WARNING: Insufficient Bitcoin data for htf
```
**Solution**: Ensure exchange connectivity and sufficient historical data availability.

#### Symbol Mismatch
```
ERROR: No dynamic symbols found, using fallback list
```
**Solution**: Check top_symbols_manager initialization and exchange connectivity.

#### Chart Generation Errors
```
ERROR: Error creating performance chart
```
**Solution**: Verify matplotlib backend and file permissions in exports directory.

### Logging
Set log level for detailed debugging:
```python
logging.getLogger('src.reports.bitcoin_beta_report').setLevel(logging.DEBUG)
```

## Future Enhancements

### Planned Features
- **Rolling beta charts**: Visualize how correlations change over time
- **Sector analysis**: Group similar assets (DeFi, Layer 1, etc.)
- **Risk metrics**: VaR, CVaR, and other risk measures
- **Alert thresholds**: Notify when correlations break down
- **Multiple base assets**: Analysis vs ETH, stablecoins, etc.

### Performance Improvements
- **Parallel data fetching**: Reduce generation time
- **Data caching**: Store processed data between runs
- **Incremental updates**: Only fetch new data since last run
- **Chart templates**: Pre-styled chart configurations

## License

This feature is part of the Virtuoso Trading System and follows the same licensing terms.

## Support

For issues or questions:
1. Check logs for error details
2. Run test suite to verify functionality
3. Review API responses for additional context
4. Consult system documentation for integration guidance 
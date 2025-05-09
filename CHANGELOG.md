# Changelog

All notable changes to the Virtuoso Trading System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New Signals API endpoints for retrieving trading signals
  - `/api/signals/latest` - Get latest signals with configurable limits
  - `/api/signals/symbol/{symbol}` - Get signals for specific symbols
  - `/api/signals` - Get paginated list of signals with extensive filtering options
  - `/api/signals/file/{filename}` - Get specific signal by filename
- PDF report generation for trading signals with annotated charts
- Chart image generation with entry/exit levels and price targets
- Base64 encoding option for PDF and chart attachments in API responses
- Simplified Signals API testing functionality
- Confluence analysis log image integration in PDF reports
- Dynamic trading symbol management based on incoming signals
- Signal monitoring system in DemoTradingRunner for automated trade execution
- Environment variable management script for InfluxDB credentials
- Advanced diagnostic tools for troubleshooting system components
- Comprehensive system integrity verification

### Enhanced
- README.md updated with comprehensive Signals API documentation
- Improved signal generation with multi-component analysis
- Added file organization structure for reports (JSON, PDF, charts)
- Enhanced market interpretations in trading alerts with more detailed insights
- Improved Discord alert formatting for better readability
- Enhanced interpretation methods for all market components:
  - Sentiment analysis with detailed market psychology insights
  - Technical analysis with pattern recognition improvements
  - Orderbook analysis with supply/demand dynamics
  - Volume analysis with participation and conviction metrics
  - Price structure analysis with market positioning details
  - Orderflow analysis with institutional activity tracking
- Improved OHLCV data handling in MarketMonitor:
  - Added fallback mechanism for missing OHLCV data
  - Enhanced data refresh capability for specific components
  - Implemented proper error handling and logging for data fetching
- Enhanced PDF report generation with better template management
- Improved ReportManager integration in SignalGenerator for consistent PDF generation
- Optimized directory structure for report storage and organization

### Fixed
- JSON serialization for datetime objects in signal responses
- Error handling for missing files in the signals directory
- Directory creation logic for reports folder structure
- Signal contributor impact calculation to prevent inflated values
- Reliability score display discrepancy between logs and alerts
- Consistency in market interpretations between different components
- Missing OHLCV data in market analysis by implementing proper data fetching and caching
- PDF attachment issues in webhook alerts by improving path handling and file verification
- Signal PDF generation failures by ensuring proper initialization of ReportManager
- OHLCV cache handling in MarketMonitor
- Missing required directories for report generation
- Template directory path resolution for report generation
- File permission issues for generated reports and charts

## [1.0.0] - 2023-06-01

### Added
- Initial release of Virtuoso Trading System
- Real-time market data processing from multiple exchanges
- Multi-factor signal generation using Market Prism methodology
- Comprehensive market monitoring system
- Confluence-based trading signals
- Basic API framework for system monitoring and control

### Technical Features
- Atomic data fetching for consistent market analysis
- Enhanced divergence visualization
- Advanced open interest analysis
- Machine learning signal validation
- Real-time market monitoring

## [0.9.0] - 2023-03-15

### Added
- Beta release for internal testing
- Core market data processing functionality
- Basic signal generation framework
- Initial exchange integrations (Binance, Bybit)
- Development environment setup

### Technical
- Data processing pipeline
- Technical indicator framework
- Configuration system
- Logging infrastructure 
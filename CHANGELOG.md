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
- Test script (`test_signals_api.py`) for simplified Signals API testing

### Enhanced
- README.md updated with comprehensive Signals API documentation
- Improved signal generation with multi-component analysis
- Added file organization structure for reports (JSON, PDF, charts)

### Fixed
- JSON serialization for datetime objects in signal responses
- Error handling for missing files in the signals directory
- Directory creation logic for reports folder structure

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
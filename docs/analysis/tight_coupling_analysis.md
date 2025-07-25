# Tight Coupling Analysis Report
Generated on: 2025-07-24 15:51:45.690566

## Overall Coupling Statistics
Total cross-module dependencies: 312

## Module Coupling Matrix
| From Module | To Module | Dependency Count |
|-------------|-----------|------------------|
| analysis | api | 1 |
| analysis | config | 1 |
| analysis | core | 6 |
| analysis | data_storage | 1 |
| analysis | indicators | 21 |
| analysis | utils | 1 |
| analysis | validation | 1 |
| api | analysis | 6 |
| api | config | 1 |
| api | core | 15 |
| api | dashboard | 3 |
| api | data_storage | 1 |
| api | monitoring | 5 |
| api | reports | 1 |
| api | validation | 1 |
| core | analysis | 4 |
| core | config | 1 |
| core | data_acquisition | 1 |
| core | data_processing | 3 |
| core | data_storage | 2 |
| core | monitoring | 9 |
| core | utils | 3 |
| core | validation | 3 |
| dashboard | core | 2 |
| dashboard | monitoring | 3 |
| dashboard | signal_generation | 1 |
| data_acquisition | core | 3 |
| data_acquisition | validation | 1 |
| data_processing | core | 8 |
| data_processing | data | 1 |
| data_processing | validation | 3 |
| data_storage | core | 1 |
| demo_trading_runner | analysis | 1 |
| demo_trading_runner | core | 1 |
| demo_trading_runner | monitoring | 2 |
| demo_trading_runner | signal_generation | 1 |
| demo_trading_runner | trade_execution | 2 |
| examples | analysis | 1 |
| examples | core | 1 |
| fixes | core | 2 |
| fixes | monitoring | 3 |
| fixes | signal_generation | 3 |
| indicators | analysis | 20 |
| indicators | config | 3 |
| indicators | core | 9 |
| indicators | utils | 15 |
| indicators | validation | 2 |
| integrated_server | analysis | 2 |
| integrated_server | config | 1 |
| integrated_server | core | 4 |
| integrated_server | dashboard | 1 |
| integrated_server | data_storage | 1 |
| integrated_server | monitoring | 5 |
| integrated_server | signal_generation | 1 |
| integrated_server | utils | 1 |
| integrated_server | validation | 1 |
| integrated_server | web_server | 1 |
| main | analysis | 3 |
| main | api | 2 |
| main | config | 4 |
| main | core | 8 |
| main | dashboard | 1 |
| main | data_storage | 1 |
| main | monitoring | 6 |
| main | reports | 1 |
| main | signal_generation | 1 |
| main | utils | 2 |
| main | validation | 1 |
| monitoring | analysis | 2 |
| monitoring | config | 2 |
| monitoring | core | 28 |
| monitoring | indicators | 2 |
| monitoring | models | 1 |
| monitoring | reports | 4 |
| monitoring | signal_generation | 2 |
| monitoring | utils | 7 |
| monitoring | validation | 3 |
| optimization | utils | 4 |
| signal_generation | analysis | 1 |
| signal_generation | core | 2 |
| signal_generation | data_processing | 1 |
| signal_generation | indicators | 6 |
| signal_generation | models | 1 |
| signal_generation | monitoring | 1 |
| signal_generation | utils | 3 |
| trade_execution | analysis | 1 |
| trade_execution | data_acquisition | 1 |
| trade_execution | indicators | 6 |
| trade_execution | monitoring | 1 |
| trade_execution | validation | 1 |
| utils | core | 1 |
| web_server | api | 1 |
| web_server | config | 1 |
| web_server | dashboard | 1 |

## Bidirectional Dependencies: 9

### core ↔ data_storage
- core → data_storage: 2 dependencies
- data_storage → core: 1 dependencies
- **Coupling Strength**: 3

### core ↔ analysis
- core → analysis: 4 dependencies
- analysis → core: 6 dependencies
- **Coupling Strength**: 10

### core ↔ monitoring
- core → monitoring: 9 dependencies
- monitoring → core: 28 dependencies
- **Coupling Strength**: 37

### core ↔ utils
- core → utils: 3 dependencies
- utils → core: 1 dependencies
- **Coupling Strength**: 4

### core ↔ data_processing
- core → data_processing: 3 dependencies
- data_processing → core: 8 dependencies
- **Coupling Strength**: 11

### core ↔ data_acquisition
- core → data_acquisition: 1 dependencies
- data_acquisition → core: 3 dependencies
- **Coupling Strength**: 4

### analysis ↔ api
- analysis → api: 1 dependencies
- api → analysis: 6 dependencies
- **Coupling Strength**: 7

### analysis ↔ indicators
- analysis → indicators: 21 dependencies
- indicators → analysis: 20 dependencies
- **Coupling Strength**: 41

### signal_generation ↔ monitoring
- signal_generation → monitoring: 1 dependencies
- monitoring → signal_generation: 2 dependencies
- **Coupling Strength**: 3

## Core-Monitoring Coupling Detailed Analysis

### Core → Monitoring Dependencies
Total: 9 dependencies

**trading_components_adapter.py:**
  - Line 36: `src.monitoring.metrics_manager` (MetricsManager)
  - Line 37: `src.monitoring.alert_manager` (AlertManager)
  - Line 38: `src.monitoring.market_reporter` (MarketReporter)
  - Line 39: `src.monitoring.monitor` (MarketMonitor)

**pdf_generator.py:**
  - Line 36: `src.monitoring.error_tracker` (track_error, ErrorCategory)
  - Line 2031: `src.monitoring.visualizers.confluence_visualizer` (()

**startup_validator.py:**
  - Line 13: `src.monitoring.alert_manager` (AlertManager)
  - Line 14: `src.monitoring.metrics_manager` (MetricsManager)
  - Line 15: `src.monitoring.monitor` (MarketMonitor)

### Monitoring → Core Dependencies
Total: 28 dependencies

**monitor.py:**
  - Line 52: `src.core.formatting` (AnalysisFormatter, format_analysis_result, LogFormatter)
  - Line 55: `src.core.interpretation.interpretation_manager` (InterpretationManager)
  - Line 80: `src.core.error.models` (ErrorContext, ErrorSeverity)
  - Line 81: `src.core.market.top_symbols` (TopSymbolsManager)
  - Line 83: `src.core.market.market_data_manager` (MarketDataManager  # Import the new MarketDataManager)
  - Line 84: `src.core.exchanges.websocket_manager` (WebSocketManager  # Import WebSocketManager)
  - Line 1401: `src.core.models.liquidation` (LiquidationEvent, LiquidationType, LiquidationSeverity)
  - Line 2542: `src.core.formatting` (LogFormatter)

**alert_manager.py:**
  - Line 80: `src.core.reporting.report_manager` (ReportManager)
  - Line 91: `src.core.interpretation.interpretation_manager` (InterpretationManager)
  - Line 362: `src.core.reporting.pdf_generator` (ReportGenerator)

**market_reporter_enhanced_test.py:**
  - Line 21: `src.core.reporting.report_manager` (ReportManager)
  - Line 22: `src.core.reporting.pdf_generator` (ReportGenerator)

**monitor_original.py:**
  - Line 52: `src.core.formatting` (AnalysisFormatter, format_analysis_result, LogFormatter)
  - Line 77: `src.core.error.models` (ErrorContext, ErrorSeverity)
  - Line 78: `src.core.market.top_symbols` (TopSymbolsManager)
  - Line 80: `src.core.market.market_data_manager` (MarketDataManager  # Import the new MarketDataManager)
  - Line 81: `src.core.exchanges.websocket_manager` (WebSocketManager  # Import WebSocketManager)
  - Line 2744: `src.core.formatting` (LogFormatter)

**enhanced_market_report.py:**
  - Line 25: `src.core.market.top_symbols` (TopSymbolsManager)
  - Line 28: `src.core.exchanges.manager` (ExchangeManager)
  - Line 29: `src.core.exchanges.bybit` (BybitExchange)
  - Line 266: `src.core.container` (Container)

**market_reporter.py:**
  - Line 40: `src.core.reporting.report_manager` (ReportManager)
  - Line 41: `src.core.reporting.pdf_generator` (ReportGenerator)

**liquidation_monitor.py:**
  - Line 26: `src.core.market.market_data_manager` (MarketDataManager)
  - Line 28: `src.core.config.config_manager` (ConfigManager)
  - Line 29: `src.core.exchanges.manager` (ExchangeManager)


## Modules with Highest Coupling
- **core**: 117 total dependencies
- **monitoring**: 86 total dependencies
- **indicators**: 84 total dependencies
- **analysis**: 73 total dependencies
- **utils**: 37 total dependencies
- **api**: 37 total dependencies
- **main**: 30 total dependencies
- **signal_generation**: 24 total dependencies
- **integrated_server**: 18 total dependencies
- **data_processing**: 16 total dependencies


## Detailed Recommendations

### 1. Break Core-Monitoring Circular Dependency
**Problem**: Core and monitoring modules have bidirectional dependencies
**Solutions**:
- Create `src/interfaces/` module for shared contracts
- Move `AlertManager` and `MetricsManager` to `src/services/`
- Use dependency injection for core services in monitoring
- Implement observer pattern for notifications

### 2. Resolve Indicators-Analysis Circular Dependency
**Problem**: OrderflowIndicators imports DataValidator from confluence
**Solutions**:
- Move `DataValidator` to `src/utils/validation/`
- Create abstract base validator that both modules can inherit
- Use composition instead of inheritance for validation

### 3. Implement Dependency Injection Container
**Create**: `src/container/dependency_container.py`
**Benefits**: Centralized dependency management, easier testing, loose coupling

### 4. Create Shared Interfaces Module
**Create**: `src/interfaces/` with abstract base classes
**Move**: Common interfaces used by multiple modules
**Result**: Reduced coupling through abstraction

### 5. Event-Driven Architecture
**Create**: `src/events/` module with event bus
**Replace**: Direct method calls with event publishing/subscribing
**Benefits**: Loose coupling, better scalability
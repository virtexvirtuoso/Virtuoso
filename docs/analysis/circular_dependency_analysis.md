# Circular Dependency Analysis Report
Generated on: 2025-07-24 15:50:15.453004
Total modules analyzed: 320

## Direct Cycles Found: 1

### Cycle 1:
indicators.orderflow_indicators -> analysis.core.confluence -> indicators.orderflow_indicators

## Strongly Connected Components: 1

### SCC 1 (2 modules):
  - analysis.core.confluence
  - indicators.orderflow_indicators
  Interconnections:
    analysis.core.confluence -> indicators.orderflow_indicators
    indicators.orderflow_indicators -> analysis.core.confluence

## Module Coupling Analysis
Cross-module dependencies by major components:

### analysis:
  - indicators: 21 dependencies
  - core: 6 dependencies
  - api: 1 dependencies

### api:
  - core: 15 dependencies
  - analysis: 6 dependencies
  - monitoring: 5 dependencies

### core:
  - monitoring: 9 dependencies
  - analysis: 4 dependencies

### indicators:
  - analysis: 14 dependencies
  - core: 9 dependencies

### monitoring:
  - core: 26 dependencies
  - signal_generation: 2 dependencies
  - indicators: 2 dependencies
  - analysis: 2 dependencies

### signal_generation:
  - indicators: 6 dependencies
  - core: 2 dependencies
  - analysis: 1 dependencies
  - monitoring: 1 dependencies

## Core-Monitoring Circular Dependency Analysis
  core.trading_components_adapter imports from monitoring: monitoring.monitor, monitoring.market_reporter, monitoring.metrics_manager, monitoring.alert_manager
  core.reporting.pdf_generator imports from monitoring: monitoring.visualizers.confluence_visualizer, monitoring.error_tracker
  core.validation.startup_validator imports from monitoring: monitoring.monitor, monitoring.metrics_manager, monitoring.alert_manager
  monitoring.monitor imports from core: core.exchanges.websocket_manager, core.market.market_data_manager, core.interpretation.interpretation_manager, core.error.models, core.models.liquidation, core.formatting, core.market.top_symbols
  monitoring.alert_manager imports from core: core.reporting.pdf_generator, core.interpretation.interpretation_manager, core.reporting.report_manager
  monitoring.market_reporter_enhanced_test imports from core: core.reporting.pdf_generator, core.reporting.report_manager
  monitoring.monitor_original imports from core: core.exchanges.websocket_manager, core.market.market_data_manager, core.error.models, core.formatting, core.market.top_symbols
  monitoring.enhanced_market_report imports from core: core.exchanges.bybit, core.exchanges.manager, core.market.top_symbols, core.container
  monitoring.market_reporter imports from core: core.reporting.report_manager, core.reporting.pdf_generator
  monitoring.liquidation_monitor imports from core: core.exchanges.manager, core.config.config_manager, core.market.market_data_manager
Core -> Monitoring dependencies: 9
Monitoring -> Core dependencies: 26
⚠️  CIRCULAR DEPENDENCY DETECTED between core and monitoring modules!

## Recommendations for Breaking Circular Dependencies

### Immediate Actions:
1. **Dependency Injection**: Use dependency injection instead of direct imports
2. **Interface Abstraction**: Create abstract base classes/interfaces
3. **Event-Driven Architecture**: Use events/signals instead of direct calls
4. **Factory Pattern**: Use factories to create dependencies at runtime
5. **Configuration-Based Wiring**: Wire dependencies through configuration

### Specific Strategies:
- Move shared interfaces to a separate 'interfaces' module
- Create a 'common' module for shared utilities
- Use lazy imports (import inside functions when needed)
- Implement observer pattern for notifications
- Create a service locator or registry pattern
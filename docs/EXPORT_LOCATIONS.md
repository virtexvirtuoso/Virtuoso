# Virtuoso Export and Output Locations

This document lists the primary directories where the Virtuoso application saves generated files such as reports, data exports, visualizations, logs, and temporary files.

Note: Some paths might be configurable. Check the relevant configuration files (`config/*.yaml`, `.env`) for specific settings.

## Reports

Generated reports in various formats.

*   `reports/charts/`: Chart images generated during analysis or reporting.
*   `reports/diagnostics/`: Output files from diagnostic runs (e.g., `diagnostic_report_*.txt`, `diagnostic_report_*.html`).
*   `reports/html/`: HTML versions of reports. May contain subdirectories based on symbol (e.g., `btc/usdt/`).
*   `reports/json/`: JSON versions of reports. May contain subdirectories based on symbol (e.g., `btc/usdt/`).
*   `reports/pdf/`: PDF versions of reports. May contain subdirectories based on symbol (e.g., `btc/usdt/`).
*   `reports/session_reports/`: Reports specific to trading sessions.

## Data Exports

Structured data exported from the application.

*   `exports/alerts/`: Data related to triggered alerts.
*   `exports/buy_BTC/`: (Purpose might need clarification) Potentially exports related to specific BTC buy operations.
*   `exports/component_data/`: Data exported from individual analysis components. May contain subdirectories based on symbol (e.g., `BTC/USDT/`).
*   `exports/confluence_visualizations/`: Output files from the confluence visualizer (e.g., `confluence_radar_chart.png`, `confluence_3d_visualization.html`).
*   `exports/market_reports/json/`: JSON-formatted market reports (possibly a duplicate or alternative location to `reports/json/`).
*   `exports/signal_data/`: Data related to generated trading signals.

## Logs

Application logs for monitoring and debugging.

*   `logs/`: Main application log files (e.g., `virtuoso.log`, `market_reporter.log`, `monitor.log`).
*   `logs/alerts/`: Logs specifically related to the alerting system.
*   `logs/archive_*/`: Archived logs from previous application runs.
*   `logs/diagnostics/`: Logs generated during diagnostic runs (e.g., `diagnostics.log`).
*   `logs/reports/`: Logs related to the report generation process.
*   `logs/tests/`: Logs generated specifically during test runs (e.g., `test_pdf_attachment.log`).

## Cache

Cached data for performance optimization.

*   `cache/`: General application-level cache files.
*   `src/indicators/cache/`: Cache files specific to indicator calculations.

## Temporary Files

Temporary files generated during runtime.

*   `temp/`: Miscellaneous temporary files (e.g., `monitor.py.temp`, `extra_params.txt`, `wkhtmltox.pkg`). 
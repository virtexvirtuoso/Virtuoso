# PDF Generation Fix for Market Reports

This file shows the exact changes needed in the `monitor.py` file around line 3240 to implement PDF generation for market reports.

## Current code:

```python
# Use report_manager to generate PDF
pdf_success, pdf_path, _ = await self.market_reporter.report_manager.generate_and_attach_report(
    signal_data=market_pdf_data,
    output_path=pdf_path,
    signal_type='market_report'
)

self.logger.debug(f"PDF generation success: {pdf_success}, path: {pdf_path}")
else:
    self.logger.warning("No PDF generator or report manager available, skipping PDF generation")
```

## Updated code:

```python
# Check if PDF path exists
pdf_path = None
try:
    # Generate HTML and PDF if market_reporter has PDF functionality
    if hasattr(self.market_reporter, 'generate_market_pdf_report') and callable(getattr(self.market_reporter, 'generate_market_pdf_report')):
        # Use the updated market_reporter's PDF generation functionality
        pdf_path = await self.market_reporter.generate_market_pdf_report(report_data)
        self.logger.debug(f"PDF generation success: {bool(pdf_path)}, path: {pdf_path}")
    elif hasattr(self.market_reporter, 'report_manager') and self.market_reporter.report_manager:
        # Use report_manager to generate PDF
        pdf_success, pdf_path, _ = await self.market_reporter.report_manager.generate_and_attach_report(
            signal_data=market_pdf_data,
            output_path=pdf_path,
            signal_type='market_report'
        )
        
        self.logger.debug(f"PDF generation success: {pdf_success}, path: {pdf_path}")
    else:
        self.logger.warning("No PDF generator or report manager available, skipping PDF generation")
except Exception as pdf_error:
    self.logger.error(f"Error generating PDF report: {str(pdf_error)}")
    self.logger.debug(traceback.format_exc())
```

## Making the Change:

1. Find the section in `monitor.py` around line 3241 where it checks if the report manager is available
2. Replace that section with the updated code above
3. This will:
   - First check if the `generate_market_pdf_report` method is available on market_reporter
   - Fall back to the original report_manager approach if not
   - Handle exceptions during PDF generation properly 
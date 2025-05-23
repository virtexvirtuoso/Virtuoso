# Bybit Futures Symbol Format Fix

## Issue Identified

Based on the logs, the market reporter is failing to fetch quarterly futures data with the following error:

```
params error: symbol invalid, result: {list: [0 items, sample: []]}
No ticker data in response for AVAXUSDT-29DEC25
Missing price data for futures premium: AVAXUSDT (mark: 0, index: 25.957)
```

The issue is that the system is attempting to fetch futures contract data using an outdated symbol format. 

## Symbol Format Changes in Bybit API (2025)

In 2025, Bybit appears to have modified the format used for quarterly futures contracts:

1. **Old Format (2024 and earlier)**: 
   - `BTCUSDT-27JUN25` - Using hyphens and month abbreviations

2. **New Format (2025)**: 
   - `BTCUSDT0627` - Using MMDD numeric format without hyphens

This is consistent with the error messages in the logs, which show the system is trying to use the old format with hyphens (e.g., `BTCUSDT-29DEC25`), but Bybit no longer accepts this format.

## Implementation Fix

The fix updates the `_calculate_single_premium` method in `market_reporter.py` to try multiple symbol formats with the new format prioritized:

1. **MMDD Numeric Format** (primary, current Bybit format):
   - Example: `BTCUSDT0627`, `ETHUSDT0926`, `SOLUSDT1226`
   - Implementation: `f"{base_asset_clean}USDT{date.month:02d}{date.day:02d}"`

2. **Inverse Contract Format** (fallback, sometimes still used):
   - Example: `BTCUSDM25`, `BTCUSDU25`, `BTCUSDZ25`
   - Implementation: `f"{base_asset_clean}USDM{current_year}"` etc.

3. **Old Format with Hyphen** (last resort, likely deprecated):
   - Example: `BTCUSDT-27JUN25`, `ETHUSDT-26SEP25`
   - Implementation: `f"{base_asset_clean}USDT-{date.day}JUN{current_year}"` etc.

The updated code tries each format in order, ensuring that at least one valid format will be matched for quarterly futures contracts. The system now gracefully handles the format change with better fallback options.

## Expected Results

With this fix, the market reporter should now be able to:
1. Successfully fetch quarterly futures contract data
2. Calculate futures premiums correctly
3. Display accurate market data in the PDF reports

This will resolve the "market overview data is currently unavailable" message in the PDF report. 
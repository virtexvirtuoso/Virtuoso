# Bybit Futures Symbol Format Fix

## Issue Identified

Based on log analysis, the market reporter was failing to fetch quarterly futures data with errors like:

```
params error: symbol invalid, result: {list: [0 items, sample: []]}
No ticker data in response for AVAXUSDT-29DEC25
Missing price data for futures premium: AVAXUSDT (mark: 0, index: 25.957)
```

The system was attempting to fetch futures contract data using symbol formats that were not recognized by the Bybit API.

## Root Cause

After extensive testing of the Bybit API, we identified two key issues:

1. **Wrong Category**: The system was looking for quarterly futures in the "linear" category, but Bybit's futures contracts are in the "inverse" category.
2. **Wrong Symbol Format**: The system was using the format `{asset}USDT-{day}{MON}{year}` (e.g., BTCUSDT-29DEC25), but Bybit uses `{asset}USD{code}{year}` (e.g., BTCUSDM25) for its inverse futures.

Additionally, not all assets have futures contracts. Our testing confirmed:
- BTC has M25 (June) and U25 (September) contracts
- ETH has M25 (June) and U25 (September) contracts
- SOL, XRP, and AVAX do not have futures contracts at this time

## Implementation Details

We implemented a more resilient approach:

1. Added support for both "linear" and "inverse" contract categories
2. Try multiple symbol formats for each contract, including:
   - Standard format: `{asset}USDT-{day}{MON}{year}` (e.g., BTCUSDT-27JUN25)
   - MMDD numeric format: `{asset}USDT{mm}{dd}` (e.g., BTCUSDT0627)
   - Linear month code: `{asset}USDT{code}{year}` (e.g., BTCUSDTM25)
   - **Inverse month code**: `{asset}USD{code}{year}` (e.g., BTCUSDM25) ← This is the working format!
3. Added direct API calls that allow specifying the contract category
4. Improved the basis calculation formula for inverse contracts
5. Enhanced date parsing to extract the month and expiry information from various symbol formats

## Benefits

1. **Resilience**: The system can now adapt to different symbol formats and categories without requiring code changes
2. **Adaptability**: If Bybit changes their symbol format or adds contracts for other assets, the system will automatically find them
3. **Backward Compatibility**: Still supports older symbol formats for compatibility with historical data
4. **Improved Math**: Handles the inverse contract calculation correctly

## Next Steps

1. Monitor the market reports to ensure they consistently fetch futures data
2. Consider caching the successful symbol formats for each asset to reduce API calls
3. Add automated tests to verify symbol format calculations
4. Add specific checks to handle other exchanges' futures formats when needed 
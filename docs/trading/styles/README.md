# Trading Styles Documentation

This directory contains comprehensive guides for different trading styles supported by the Virtuoso Trading System.

## Quick Links

### Trading Style Guides
- **[Trading Styles Comparison](TRADING_STYLES_COMPARISON.md)** - Side-by-side comparison of all 4 trading styles
- **[Aggressive Day Trading Guide](AGGRESSIVE_DAY_TRADING_GUIDE.md)** - Deep dive into aggressive day trading (CURRENT)
- **[Day Trading Parameters](DAY_TRADING_PARAMETERS.md)** - Configuration parameters for day trading

## Trading Styles Overview

| Style | Stop Loss | Holding Time | Trades/Day | Win Rate | Best For |
|-------|-----------|--------------|------------|----------|----------|
| **Scalping** | 1.27% | 15min-2h | 3-10 | 60-70% | Full-time traders |
| **Aggressive Day** ✅ | 2.22% | 1-4h | 2-5 | 55-65% | Active part-time traders |
| **Day Trading** | 2.54% | 4h-1day | 1-3 | 45-55% | Passive traders |
| **Swing Trading** | 10.0% | 1-7 days | 0.2-1 | 40-50% | Patient investors |

## Current Configuration

The system is currently configured for **Aggressive Day Trading**:
- Short stop: 1.75%
- Long stop: 1.4%
- Target 1: Typically hit in 1-2 hours
- Trades: 2-5 per day

## Related Documentation

- Deployment: [Aggressive Day Trading Deployment](../../deployment/AGGRESSIVE_DAY_TRADING_DEPLOYMENT.md)
- Validation: [Validation Report](../../validation/AGGRESSIVE_DAY_TRADING_VALIDATION_REPORT.md)
- Fixes: [Day Trading Fixes Summary](../DAY_TRADING_FIXES_SUMMARY.md)

---

**Last Updated**: 2025-10-30

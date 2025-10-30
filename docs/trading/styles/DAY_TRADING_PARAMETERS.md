# Day Trading Parameters - Quick Reference

## Current Configuration (Day Trading)

### Stop Loss Ranges

| Signal Type | Base | Min (0.8x) | Max (1.3x) | Use Case |
|------------|------|------------|------------|----------|
| **LONG** | 1.5% | 1.2% | 1.95% | High to Low Confidence |
| **SHORT** | 2.0% | 1.6% | 2.6% | High to Low Confidence |

### Target Ranges (R:R Based)

| Target | R:R Ratio | Typical % (SHORT) | Position Size |
|--------|-----------|-------------------|---------------|
| **T1** | 1.5:1 | 3.0 - 4.0% | 50% |
| **T2** | 2.5:1 | 5.0 - 6.5% | 30% |
| **T3** | 4.0:1 | 8.0 - 10.5% | 20% |

### Confidence Scaling

| Confluence Score | Confidence Level | Stop Multiplier | Example (SHORT 2.0%) |
|------------------|------------------|-----------------|----------------------|
| 85-100 | Very High | 0.8x | 1.6% |
| 70-84 | High | 0.9x | 1.8% |
| 50-69 | Medium | 1.1x | 2.2% |
| 35-49 | Low | 1.3x | 2.6% |
| 0-34 | Very Low | 1.3x | 2.6% |

*Note: For SHORT signals, LOWER scores = HIGHER confidence*

---

## Example Calculations

### BTCUSDT SHORT @ $107,982

**Scenario 1: High Confidence (Score 32.76)**
```
Entry: $107,982
Stop:  $110,720 (2.54% above)
T1:    $103,874 (3.80% down) - 50%
T2:    $101,136 (6.34% down) - 30%
T3:    $97,028  (10.14% down) - 20%
```

**Scenario 2: Low Confidence (Score 50)**
```
Entry: $107,982
Stop:  $110,789 (2.60% above)
T1:    $103,771 (3.90% down) - 50%
T2:    $100,965 (6.50% down) - 30%
T3:    $96,753  (10.40% down) - 20%
```

### ETHUSDT LONG @ $2,500

**Scenario 1: High Confidence (Score 85)**
```
Entry: $2,500.00
Stop:  $2,470.00 (1.20% below)
T1:    $2,545.00 (1.80% up) - 50%
T2:    $2,575.00 (3.00% up) - 30%
T3:    $2,620.00 (4.80% up) - 20%
```

**Scenario 2: Low Confidence (Score 50)**
```
Entry: $2,500.00
Stop:  $2,451.25 (1.95% below)
T1:    $2,573.13 (2.93% up) - 50%
T2:    $2,621.88 (4.88% up) - 30%
T3:    $2,695.00 (7.80% up) - 20%
```

---

## Comparison: Day Trading vs Swing Trading

| Parameter | Day Trading | Swing Trading | Difference |
|-----------|-------------|---------------|------------|
| **Long Stop** | 1.5% | 4.5% | 3x tighter |
| **Short Stop** | 2.0% | 5.0% | 2.5x tighter |
| **Max Multiplier** | 1.3x | 2.0x | 35% reduction |
| **Typical Stop** | 1.6-2.6% | 3.15-10% | 75% tighter |
| **Typical Target 1** | 2-4% | 4.7-15% | 60% tighter |
| **Typical Target 3** | 6-10% | 12.6-40% | 70% tighter |
| **Timeframe** | Intraday | Multi-day | - |

---

## When to Use Each Style

### Day Trading (Current Config)
- ✅ Intraday moves only
- ✅ Close all positions before market close
- ✅ High volume, high liquidity pairs
- ✅ Tight stop loss acceptable
- ✅ Quick profit taking

### Swing Trading (Old Config)
- ✅ Multi-day to multi-week holds
- ✅ Can withstand intraday volatility
- ✅ Lower frequency trades
- ✅ Wider stops for breathing room
- ✅ Larger profit targets

---

## Risk Management Rules

### Position Sizing

```
Risk per trade = Account × Risk% × (1 / Stop%)

Example:
Account: $10,000
Risk: 1% per trade
Stop: 2% on entry

Position Size = $10,000 × 0.01 × (1 / 0.02)
             = $100 × 50
             = $5,000 (50% of account)
```

### Exit Strategy

1. **Stop Loss Hit**: Exit entire position immediately
2. **Target 1**: Close 50%, move stop to breakeven
3. **Target 2**: Close 30%, let remaining 20% run
4. **Target 3**: Close final 20%

### Maximum Daily Loss

```
Max Daily Loss = 3% of account

If 3 consecutive stop losses:
3 × 1% = 3% → STOP TRADING FOR THE DAY
```

---

## Configuration Location

**File**: `config/config.yaml`
**Lines**: 1193-1210

```yaml
risk:
  risk_free_rate: 0.02
  risk_limits:
    max_drawdown: 0.25
    max_leverage: 3.0
    max_position_size: 0.1
  # Day trading configuration
  long_stop_percentage: 1.5
  short_stop_percentage: 2.0
  min_stop_multiplier: 0.8
  max_stop_multiplier: 1.3
```

---

## Common Scenarios

### Bitcoin Day Trading

**Typical Moves**:
- Low volatility: 1-3% intraday
- Medium volatility: 3-6% intraday
- High volatility: 6-10% intraday

**Recommended Stops**:
- Tight: 1.5-2.0% (high confidence)
- Normal: 2.0-2.5% (medium confidence)
- Wide: 2.5-3.0% (low confidence or high volatility)

### Altcoin Day Trading

**Typical Moves**:
- Low volatility: 3-5% intraday
- Medium volatility: 5-10% intraday
- High volatility: 10-20% intraday

**Recommended Stops**:
- Consider 1.5-2x Bitcoin stops for altcoins
- LONG: 2.5-3.0%
- SHORT: 3.0-4.0%

---

## Monitoring & Adjustments

### Weekly Review

Check if stops/targets are:
1. Being hit too frequently (stops too tight)
2. Never being hit (stops too wide)
3. Profitable overall (positive expectancy)

### Adjustment Guidelines

If **stop loss hit rate > 70%**:
- Increase min/max multipliers by 0.1
- Or increase base percentages by 0.5%

If **stop loss hit rate < 30%**:
- Decrease min/max multipliers by 0.1
- Or decrease base percentages by 0.5%

Target: **40-60% win rate** with positive R:R

---

## Validation Checklist

Before each trade, verify:

- [ ] Confluence score displayed correctly
- [ ] Stop loss within expected range (1.6-2.6%)
- [ ] Target 1 achievable intraday (2-4%)
- [ ] Risk:Reward ratio at least 1.5:1
- [ ] Position size within risk tolerance
- [ ] Sufficient liquidity for entry/exit

---

**Last Updated**: 2025-10-30
**Configuration**: Day Trading Mode
**Status**: ✅ Active

# CONFLUENCE: Market Prism Signal Architecture

This document is the canonical specification for Virtuoso's confluence (Market Prism) system. It defines components, data flow, scoring, thresholds, risk integration, API exposure, validation, and operations. All contributors should treat this as the single source of truth for design and behavior.

---

## 1) Purpose and Scope

- **Objective**: Convert heterogeneous market signals into a unified, calibrated score on [0,100], mapped to actionable trade decisions with explicit risk constraints.
- **Coverage**: Technical, Volume, Orderflow, Orderbook, Price Structure, Sentiment; aggregation, normalization, thresholds, execution hooks, and dashboards.

---

## 2) Component Model

### Primary Dimensions

Six primary dimensions produce normalized scores [0,100]:
- **Technical** (e.g., RSI/MACD/AO/ATR) - Momentum and trend indicators
- **Volume** (e.g., ADL/MFI/CMF) - Volume-weighted price movement
- **Orderflow** (e.g., CVD/trade imbalance/liquidations context) - Trade-level flow analysis
- **Orderbook** (e.g., OIR, depth imbalance, absorption) - Limit order book dynamics
- **Price Structure** (e.g., range/EQ, order blocks, swing structure) - Market structure and levels
- **Sentiment** (e.g., funding, long/short, fear/greed) - Market participant positioning

### Quality Metrics Derivation

From the six component scores, the system derives quality metrics that feed into the Hybrid Quality Adjustment Formula (Section 4):

**Consensus** (Agreement Level):
```python
signal_variance = np.var(normalized_component_scores)
consensus = np.exp(-signal_variance * 2)  # Range: 0-1
```
- High consensus (>0.8): Components agree on direction
- Low consensus (<0.5): Components show conflicting signals

**Confidence** (Combined Quality):
```python
confidence = abs(weighted_sum) * consensus  # Range: 0-1
```
- Combines signal strength with agreement level
- Used as primary quality gate for amplification

**Disagreement** (Signal Variance):
```python
disagreement = np.var(normalized_component_scores)  # Range: 0-~1
```
- Direct measure of component dispersion
- Lower is better (tighter clustering = better quality)

These quality metrics determine whether signals are **amplified** (high quality) or **dampened** (low quality) in the final score.

### Normalization Utilities

- `src/indicators/base_indicator.py` -> weighted component score helpers
- `src/utils/indicators.py` -> rolling window normalization to [1,100]
- `src/core/scoring/unified_scoring_framework.py` -> transformation modes and caching

### Key References

```183:206:src/core/analysis/integrated_analysis.py
    def _calculate_confluence_score(self, component_results: List[Dict[str, Any]]) -> float:
        # Weighted sum with alignment factor, clipped to [0,100]
```

---

## 3) Scoring & Aggregation

### Two-Stage Scoring Process

The confluence system uses a two-stage process to generate trading signals:

1. **Stage 1: Base Score Calculation**
   - Weighted aggregation of component scores (0-100)
   - Default equal or configured weights with fallback to equal on missing config
   - Alignment penalty via score dispersion to avoid false consensus
   - Clipping and NaN guards return neutral 50 on failure
   - Result: **Base Score** (raw directional signal strength)

2. **Stage 2: Quality Adjustment**
   - Apply Hybrid Quality Adjustment Formula (see Section 4)
   - Modulate base score based on quality metrics (consensus, confidence, disagreement)
   - High quality -> amplify signal (up to 15%)
   - Low quality -> dampen signal toward neutral
   - Result: **Quality-Adjusted Score** (USE THIS FOR TRADING)

**Important**: The base score represents raw indicator consensus. The quality-adjusted score incorporates signal reliability and is the authoritative value for trading decisions, risk calculations, and threshold evaluation.

### Implementation Details

Signal generator weighted fallback:
```633:647:src/signal_generation/signal_generator.py
                # Weighted average of component scores with default equal weights
```

Unified framework ensures deterministic transforms and bounds:
```139:174:src/core/scoring/unified_scoring_framework.py
            # AUTO/TRADITIONAL/ENHANCED/HYBRID modes, cache, bounds, debug
```

---

## 4) Quality Adjustment (Hybrid Formula)

**Version**: 2.1 (Hybrid Quality-Adjusted Scores)

The confluence system applies a **Hybrid Quality Adjustment Formula** that modulates the base confluence score based on quality metrics, creating a quality-adjusted score used for trading decisions.

### Quality Metrics

Three key metrics evaluate signal quality:

- **Consensus** (0-1): Agreement level between indicators, calculated as `exp(-variance * 2)`
  - High consensus (>0.8) indicates indicators are aligned
  - Low consensus (<0.5) indicates conflicting signals

- **Confidence** (0-1): Combined signal strength and agreement, `abs(weighted_sum) * consensus`
  - Captures both direction certainty and indicator alignment
  - Used as primary quality gate for amplification

- **Disagreement**: Signal variance across indicators (lower is better)
  - Measures dispersion in component scores
  - Inverse of consensus quality

### Hybrid Adjustment Logic

The system uses two adjustment paths based on quality thresholds:

**Path 1: High-Quality Amplification** (confidence > 0.7 AND consensus > 0.8)
- Amplifies strong, aligned signals away from neutral (50)
- Maximum amplification: 15% beyond base score
- Formula: `adjusted_score = 50 + (deviation * amplification_factor)`
- Where: `amplification_factor = 1 + ((confidence - 0.7) * 0.15 / 0.3)`

**Path 2: Low/Medium-Quality Dampening** (default path)
- Dampens weak or conflicting signals toward neutral (50)
- Reduces risk from low-quality setups
- Formula: `adjusted_score = 50 + (deviation * confidence)`

#### How the Formula Works (Simple Explanation)

The formula uses **signed arithmetic** to automatically handle both bearish and bullish signals:

```
Step 1: deviation = base_score - 50
  - Bearish signals (< 50): deviation is NEGATIVE
  - Bullish signals (> 50): deviation is POSITIVE

Step 2: adjusted_score = 50 + (deviation * adjustment_factor)
  - When multiplying by a fraction (dampening):
    - Negative * fraction = smaller negative (closer to 0)
    - Positive * fraction = smaller positive (closer to 0)
  - Result moves score TOWARD neutral (50)

  - When multiplying by >1 (amplification):
    - Negative * >1 = larger negative (away from 0)
    - Positive * >1 = larger positive (away from 0)
  - Result moves score AWAY from neutral (50)
```

**Example - Bearish Dampening:**
```
Base: 45.65 -> deviation = 45.65 - 50 = -4.35
Dampen: 50 + (-4.35 * 0.073) = 50 + (-0.318) = 49.68
Result: Moved UP toward neutral (positive quality impact: +4.03)
```

**Example - Bullish Dampening:**
```
Base: 58.00 -> deviation = 58.00 - 50 = +8.00
Dampen: 50 + (+8.00 * 0.073) = 50 + (+0.584) = 50.58
Result: Moved DOWN toward neutral (negative quality impact: -7.42)
```

The **sign of the deviation** automatically determines the adjustment direction—no conditional logic needed!

### Quality Impact Convention

Quality Impact shows how much the adjustment changed the score:
- **Positive (+)**: Score moved UP on 0-100 scale (toward 100)
- **Negative (−)**: Score moved DOWN on 0-100 scale (toward 0)

Formula: `quality_impact = adjusted_score - base_score`

**Interpretation Context** (0=extreme bearish, 50=neutral, 100=extreme bullish):

For **Bearish Signals** (base < 50):
- Negative impact = amplified bearishness (moved closer to 0)  HIGH QUALITY
- Positive impact = dampened toward neutral (moved toward 50)

For **Bullish Signals** (base > 50):
- Positive impact = amplified bullishness (moved closer to 100)  HIGH QUALITY
- Negative impact = dampened toward neutral (moved toward 50)

### Display Format

The system displays adjustment information with context:
```
Base Score: 56.41 (before quality adjustment)
Overall Score: 50.79 (quality-adjusted, use for trading)
Quality Impact: −5.63 points (moderate dampening (low quality signal))
```

Or for high-quality signals:
```
Base Score: 80.00 (before quality adjustment)
Overall Score: 83.00 (quality-adjusted, use for trading)
Quality Impact: +3.00 points (moderate amplification (high quality signal))
```

### Configuration & Thresholds

Default quality thresholds (in `src/core/analysis/confluence.py`):
- `QUALITY_THRESHOLD_CONFIDENCE = 0.7`
- `QUALITY_THRESHOLD_CONSENSUS = 0.8`
- `MAX_AMPLIFICATION = 0.15` (15%)

### Key Implementation Files

- Score calculation: `src/core/analysis/confluence.py:1900-1932`
- Display formatting: `src/core/formatting/formatter.py:2327-2351`
- Signal processing: `src/monitoring/signal_processor.py:206-219`
- Metrics tracking: `src/monitoring/quality_metrics_tracker.py`

### Mathematical Symmetry

The formula is perfectly symmetric for bearish/bullish signals:
- Uses `deviation = base_score - 50` which is negative for bearish, positive for bullish
- Amplification multiplies the deviation, preserving direction
- Bearish amplification: 20 -> 17 (moved toward 0)
- Bullish amplification: 80 -> 83 (moved toward 100)

### Quality Metrics Tracking

Quality metrics are logged for performance analysis:
- Logged to: `logs/quality_metrics/quality_metrics_YYYYMMDD.jsonl`
- Tracks: consensus, confidence, disagreement, filter status, signal outcomes
- Enables threshold optimization and filter effectiveness analysis

See `QUALITY_ADJUSTMENT_FORMULA_ANALYSIS.md` for comprehensive design rationale and examples.

---

## 5) Thresholds and Decisions

**Trading thresholds are applied to the quality-adjusted score:**

- **Buy threshold**: 70 (default) - Generate BUY signal when quality-adjusted score >= 70
- **Sell threshold**: 30 (default) - Generate SELL signal when quality-adjusted score <= 30
- **Neutral band**: (30, 70) - No trade signal in this range

**Important**: All thresholds evaluate the **quality-adjusted score**, not the base score. This ensures trading decisions incorporate both directional signal strength AND signal reliability.

### Threshold Application Example

```
Base Score: 75 (strong bullish)
Quality-Adjusted Score: 68 (dampened due to low confidence)
Decision: NEUTRAL (68 < 70 buy threshold)  Protected from low-quality signal
```

```
Base Score: 72 (moderately bullish)
Quality-Adjusted Score: 76 (amplified due to high quality)
Decision: BUY (76 >= 70 buy threshold)  Captured high-quality opportunity
```

### Strategy Implementation

Strategy example:
```171:181:src/trade_execution/confluence_trading_strategy.py
            if score >= self.long_threshold: action = 'buy'
            elif score <= self.short_threshold: action = 'sell'
```

**Note**: The `score` variable in strategy code refers to the quality-adjusted score.

Signal API uses thresholds consistently across all dashboards and routes.

---

## 6) Risk Integration

**All risk calculations use the quality-adjusted confluence score** to ensure position sizing and stop-loss levels reflect both directional strength and signal reliability.

### Risk Components

Risk config and calculators:
- `config/config.yaml` -> `risk`, `risk_management` (stop-loss/take-profit, multipliers)
- `src/core/risk/stop_loss_calculator.py` -> confidence-based sizing tied to confluence
- `src/risk/risk_manager.py` -> position sizing, SL/TP computation, portfolio limits

Score-aware SL example in executor:
```962:986:src/trade_execution/trade_executor.py
        # min/max stop around base, scaled by confluence and side
```

### Risk Calculation Guidelines

- **Position sizing**: Based on quality-adjusted score, not base score
  - Higher quality-adjusted confluence -> larger position size (within limits)
  - Dampened scores -> smaller positions (automatic risk reduction)
  - Amplified scores -> larger positions (capitalize on quality opportunities)

- **Stop-loss placement**:
  - Higher quality-adjusted confluence => wider initial SL within max multiplier
  - Quality-adjusted score determines SL distance from entry
  - Base score not used for risk calculations

- **Quality metrics overlay** (optional):
  - Confidence < 0.3 -> Consider additional position size reduction
  - Consensus < 0.5 -> Tighter stops due to indicator disagreement
  - Disagreement > 0.3 -> Flag for manual review or skip trade

- **Risk limits** (always enforced):
  - Max position size per symbol
  - Max leverage
  - Max portfolio drawdown
  - Default risk:reward >= 2:1 unless config overrides

### Example Risk Calculation

```
Base Score: 80 (strong bullish)
Quality-Adjusted Score: 83 (amplified, high quality)
Position Size: Calculated from 83, not 80
Stop Loss: Wider SL based on 83 (high confidence in trade)
Result: Larger position with appropriate SL for quality setup 
```

```
Base Score: 75 (strong bullish)
Quality-Adjusted Score: 62 (dampened, low quality)
Position Size: Calculated from 62, not 75
Stop Loss: Tighter SL based on 62 (lower confidence)
Result: Smaller position, protected from low-quality signal 
```

---

## 7) Data Flow and Realtime

Acquisition -> Indicators -> Confluence -> Signals/Alerts -> Dashboard:
- Realtime ingest: `src/core/streaming/realtime_pipeline.py`
- Indicator processing: `src/enhanced_real_data_server.py` (`TechnicalIndicatorProcessor`)
- Trading signals generation: `EnhancedDataManager.get_trading_signals()`
- Web/API exposure: FastAPI routes in `src/api/routes/*` and `src/real_data_web_server.py`

Realtime pipeline watches for:
```48:63:src/core/streaming/realtime_pipeline.py
    'confluence_scores', 'signals', 'alerts' with change thresholds
```

---

## 8) API and Dashboard Exposure

Primary endpoints (selection):
- `GET /dashboard/signals` -> `src/api/routes/dashboard.py`
- `GET /dashboard-unified/signals` -> `src/api/routes/dashboard_unified.py`
- `GET /api/signals/latest` -> `src/main.py.vps_fixed`
- Confluence breakdown routes: `src/api/routes/confluence_breakdown.py`

Dashboard integration builders:
```66:89:src/dashboard/integration_service.py
    # Builds 11-component confluence signal payloads for UI
```

---

## 9) Configuration Knobs

`config/config.yaml` (key excerpts):
- `confluence.thresholds.buy/sell`
- `risk`: `long_stop_percentage`, `short_stop_percentage`, `min_stop_multiplier`, `max_stop_multiplier`
- `risk_management.default_stop_loss`, `confidence_scaling`
- `timeframes` with weights and validation

All thresholds must be centrally read by strategies and services; avoid hard-coding.

---

## 10) Validation & Metrics

### Validation Principles

- **Deterministic tests** on aggregation/normalization boundaries
- **Backtests** stratified by regime; report Sharpe/Sortino/MaxDD/HitRate
- **Live sanity checks**:
  - Score monotonicity vs. component moves
  - Threshold adherence
  - Quality adjustment behavior (amplification/dampening frequency)
- **Quality metrics validation**:
  - Consensus/confidence/disagreement distributions
  - Amplification vs dampening frequency (target: 5-15% amplified)
  - Quality impact correlation with signal outcomes

### Test Artifacts

- Validation reports under `docs/validation/` and top-level reports
- Tests: `tests/` incl. confluence/integration and mock isolation
- Quality metrics logs: `logs/quality_metrics/quality_metrics_YYYYMMDD.jsonl`

### Operational Metrics

**Performance Metrics:**
- Response times for `/signals` endpoints (<2ms target in `dashboard_unified` path)
- Streaming freshness (<= 3s for confluence updates)
- Error rates for analyzer and indicator paths

**Quality Metrics Tracking:**
- **Distribution monitoring**:
  - Mean/median confidence across all signals
  - Mean/median consensus across all signals
  - Amplification frequency (% of signals amplified)
  - Dampening frequency (% of signals dampened)

- **Quality impact analysis**:
  - Correlation between confidence and signal outcomes
  - Win rate for amplified vs dampened signals
  - Average quality impact magnitude
  - Quality metrics by symbol/timeframe

- **Threshold effectiveness**:
  - Signals filtered by low quality (% filtered)
  - Filter reasons distribution
  - Performance comparison: filtered vs passed signals

**Target Ranges (for tuning):**
```
Amplification Frequency: 5-15% of signals
  - If >20%: Thresholds too low (amplifying too often)
  - If <5%: Thresholds too high (missing opportunities)

Mean Confidence: 0.4-0.7
  - If <0.3: Consider indicator diversity issues
  - If >0.8: May indicate over-fitted indicators

Consensus Distribution:
  - High (>0.8): 10-20% of signals
  - Medium (0.5-0.8): 50-70% of signals
  - Low (<0.5): 10-30% of signals
```

### Quality Metrics Access

Retrieve quality statistics via `QualityMetricsTracker`:
```python
tracker = QualityMetricsTracker()
stats = tracker.get_statistics(hours=24, symbol='BTCUSDT')
effectiveness = tracker.get_filter_effectiveness(hours=24)
```

---

## 11) Known Fallbacks/Mocks and Migration Plan

Replace any neutral or mock fallbacks with real data sources:
- Whale activity routes may still include placeholders; ensure integration with real detection pipeline.
- Trade executor confluence fallback must route to real `ConfluenceAnalyzer` with actual market data.
- PDF generator should avoid simulated data; pull from canonical signal objects.
- Dashboard symbol lists and integration fallbacks must be sourced from cache/exchange discovery.

Action items:
1. Audit all TODO fallbacks returning neutral 50 and replace with analyzer calls
2. Wire Bybit-only live tests for data (user preference)
3. Validate each endpoint returns production-proven fields; no mock keys in production paths

---

## 12) Execution Hooks

Trading strategy:
- `src/trade_execution/confluence_trading_strategy.py` drives periodic evaluation
- Executor: `src/trade_execution/trade_executor.py` maps score -> action, size, SL/TP, alerts

Rules:
- Never execute with missing analyzer; return neutral and skip
- Enforce risk gates before order placement
- Emit alerts with score and risk context

---

## 13) Operational Runbook

### Health Checks

**System Health:**
- Health of data sources (exchange connectivity, websockets, cache)
- Config parity between services; thresholds consistent
- Latency SLOs for `/signals`, streaming freshness, cache hit rates

**Quality System Health:**
- Quality metrics logging active (check `logs/quality_metrics/`)
- Amplification frequency within target range (5-15%)
- Mean confidence within expected range (0.4-0.7)
- Quality adjustment appearing in logs with contextual descriptions

### Incident Patterns

**Core System Issues:**
- **Score collapse to 50 across board** => Upstream analyzer failure or stale inputs
  - Check: Component scores all returning neutral
  - Fix: Restart data acquisition, verify exchange connectivity

- **Divergence between UI and API** => Cache invalidation or stale websocket clients
  - Check: Compare `/api/signals/latest` with dashboard display
  - Fix: Clear cache, reconnect websockets

**Quality System Issues:**

- **Quality metrics consistently low (confidence < 0.3 for majority of signals)**
  - Symptom: Most signals heavily dampened, few trades generated
  - Possible causes:
    - Indicators showing high disagreement (check component scores)
    - Market regime change (choppy/sideways market)
    - Indicator configuration mismatch
  - Investigation:
    - Check `disagreement` values (if >0.3, indicators conflicting)
    - Review indicator parameter settings
    - Check if low quality is symbol-specific or system-wide
  - Resolution:
    - If market regime: This is expected behavior (protecting capital)
    - If configuration: Review indicator timeframes and parameters
    - If symbol-specific: May need symbol-specific tuning

- **Base vs adjusted scores diverging heavily (>15 points consistently)**
  - Symptom: Base score 75, adjusted score 55 (20-point dampening)
  - Possible causes:
    - Quality thresholds too strict
    - Indicators genuinely conflicting (system working correctly)
  - Investigation:
    - Check consensus/confidence values in logs
    - Review component score distributions
    - Compare win rates for heavily dampened signals
  - Resolution:
    - If protecting from losses: System working correctly
    - If missing opportunities: Consider threshold adjustment

- **Amplification too frequent (>20% of signals)**
  - Symptom: Most signals being amplified
  - Possible causes:
    - Quality thresholds set too low (confidence < 0.7, consensus < 0.8)
    - Indicators too correlated (artificially high consensus)
  - Investigation:
    - Check current threshold values
    - Review indicator independence
    - Analyze amplified signal outcomes
  - Resolution:
    - Increase thresholds: `QUALITY_THRESHOLD_CONFIDENCE = 0.75`
    - Review indicator diversity

- **Amplification too rare (<5% of signals)**
  - Symptom: Very few signals being amplified despite strong setups
  - Possible causes:
    - Quality thresholds set too high
    - Indicators genuinely not aligning
  - Investigation:
    - Check how close signals are to threshold (e.g., confidence = 0.68 vs 0.7)
    - Review quality metrics distribution
  - Resolution:
    - Lower thresholds: `QUALITY_THRESHOLD_CONFIDENCE = 0.65`
    - Verify this doesn't compromise signal quality

- **Quality Impact showing generic descriptions ("adjustment" instead of "dampening")**
  - Symptom: Logs show "moderate adjustment" instead of "moderate dampening (low quality signal)"
  - Root cause: `adjustment_type` field missing from response dictionary
  - Investigation:
    - Check if `adjustment_type` present in confluence response
    - Verify formatter receiving the field
  - Resolution:
    - Ensure `src/core/analysis/confluence.py` includes adjustment_type in return dict
    - Verify `src/monitoring/signal_processor.py` passes it to formatter

- **Duplicate quality impact logs**
  - Symptom: Same quality impact appears twice with different descriptions
  - Root cause: Multiple logging points (confluence analyzer + signal processor)
  - Resolution:
    - Keep logging in signal_processor.py only
    - Comment out duplicate in confluence.py

### Rollback Procedures

**Configuration Rollbacks:**
- Feature flags for new scoring modes (use `UnifiedScoringFramework` modes)
- Revert thresholds via config and reload
- Disable quality adjustment by setting `QUALITY_THRESHOLD_CONFIDENCE = 1.0` (makes all signals dampen)

**Quality System Rollback:**
If quality adjustment causing issues, can temporarily revert to base scores:
```python
# Emergency: Use base score without quality adjustment
adjusted_score = base_score  # Bypass quality adjustment
```
Note: This is emergency-only; prefer threshold tuning over disabling

### Monitoring Commands

**Check quality metrics:**
```bash
# View recent quality logs
tail -f logs/quality_metrics/quality_metrics_$(date +%Y%m%d).jsonl

# Check amplification frequency
grep "amplified" logs/quality_metrics/*.jsonl | wc -l

# Check dampening frequency
grep "dampened" logs/quality_metrics/*.jsonl | wc -l
```

**Check production logs for quality issues:**
```bash
# Find low-quality signals
ssh vps "grep 'confidence.*0\.[0-2]' /var/log/virtuoso-trading/monitoring.log"

# Find heavily dampened signals
ssh vps "grep 'Quality Impact.*+[1-9][0-9]' /var/log/virtuoso-trading/monitoring.log"

# Check for quality system errors
ssh vps "grep -i 'quality.*error' /var/log/virtuoso-trading/*.log"
```

---

## 14) Governance

- All changes to scoring weights, thresholds, or risk multipliers require PR with:
  - Backtest diff by regime
  - Live shadow metrics for 48h
  - Dashboard/alert parity verification

---

## 15) Appendix: Code Pointers

- Aggregation: `src/core/analysis/integrated_analysis.py`
- **Quality Adjustment (Hybrid Formula)**: `src/core/analysis/confluence.py` (lines 1900-1932, 3090-3122)
- **Quality Metrics Tracking**: `src/monitoring/quality_metrics_tracker.py`
- **Quality Display Formatting**: `src/core/formatting/formatter.py` (lines 2327-2351)
- Signal gen: `src/signal_generation/signal_generator.py`
- Signal processing: `src/monitoring/signal_processor.py` (lines 206-219)
- Scoring framework: `src/core/scoring/unified_scoring_framework.py`
- Indicators base utils: `src/indicators/base_indicator.py`, `src/utils/indicators.py`
- Strategy/Executor: `src/trade_execution/confluence_trading_strategy.py`, `src/trade_execution/trade_executor.py`
- Risk: `src/risk/risk_manager.py`, `src/core/risk/stop_loss_calculator.py`
- Realtime: `src/core/streaming/realtime_pipeline.py`, `src/enhanced_real_data_server.py`
- API/Dashboard: `src/api/routes/dashboard.py`, `src/api/routes/dashboard_unified.py`, `src/real_data_web_server.py`

---

Risk disclaimer: Past performance does not guarantee future results. This system is for research and systematic execution; ensure compliance with applicable regulations and exchange terms.



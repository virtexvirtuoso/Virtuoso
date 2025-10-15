# Quality-Adjusted Confluence Score Design

**Author:** Virtuoso Trading Team
**Date:** 2025-10-10
**Status:** Design Proposal
**Related Files:**
- `src/core/analysis/confluence.py`
- `src/signal_generation/signal_generator.py`
- `src/monitoring/quality_metrics_tracker.py`

---

## Executive Summary

This document proposes a **Hybrid Quality-Adjusted Confluence Score** that integrates quality metrics (confidence, consensus, disagreement) directly into the confluence score while maintaining full transparency of underlying metrics.

**Key Benefits:**
- ✅ Eliminates confusing "high score but filtered" scenarios
- ✅ Simplifies trading logic from 2 decision points to 1
- ✅ Maintains full visibility into quality metrics
- ✅ Automatically suppresses weak signals
- ✅ Reduces false positives without arbitrary thresholds

---

## Problem Statement

### Current Architecture (Two-Stage Filtering)

```python
# Stage 1: Calculate confluence score
confluence_score = weighted_sum * 50 + 50  # [0, 100]

# Stage 2: Calculate quality metrics separately
consensus = exp(-variance * 2)
confidence = abs(weighted_sum) * consensus
disagreement = variance

# Stage 3: Apply filters (separate decision)
if confluence_score > 60:                    # Threshold check
    if confidence < 0.3:                     # Quality filter
        return None  # FILTERED
    if disagreement > 0.3:                   # Conflict filter
        return None  # FILTERED
    send_to_discord()
```

### Issues with Current System

1. **Confusing Signals:** Score of 65 looks actionable but gets filtered
2. **Two Decision Points:** Must tune both score threshold and quality thresholds
3. **User Confusion:** "Why was my 70-score signal not sent?"
4. **Arbitrary Filters:** Hard-coded 0.3 thresholds may not be optimal
5. **Loss of Information:** Filtering loses the signal entirely

### Real Example: 1000PEPEUSDT

```
Confluence Score: 52.36 (appears slightly bearish)
Confidence:       0.043 (extremely low)
Disagreement:     0.0428 (low conflict)
Consensus:        0.918 (high agreement)

Current Behavior: FILTERED (confidence < 0.3)
Problem: Score suggests "slight bear bias" but quality says "don't trade"
```

**The Paradox:** Components agree (high consensus) but weakly (low confidence). The score doesn't reflect this weakness.

---

## Proposed Solution: Hybrid Quality-Adjusted Score

### Design Philosophy

> **"Quality should be a dimmer switch, not a gate."**

Instead of filtering signals after calculation, we integrate quality directly into the score calculation, making weak signals automatically produce neutral scores.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Component Scores (0-100)                                   │
│  • Volume: 52.83                                            │
│  • Technical: 44.72                                         │
│  • Orderbook: 63.53                                         │
│  • Orderflow: 44.37                                         │
│  • Price Structure: 44.18                                   │
│  • Sentiment: 70.66                                         │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│  Normalization & Weighting                                  │
│  • Normalize to [-1, 1]: (score - 50) / 50                 │
│  • Apply component weights                                  │
│  • Calculate weighted_sum                                   │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│  Quality Metrics Calculation                                │
│  • variance = var(normalized_scores)                        │
│  • consensus = exp(-variance * 2)                           │
│  • confidence = abs(weighted_sum) * consensus               │
│  • disagreement = variance                                  │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│  HYBRID: Calculate Both Scores                              │
│                                                             │
│  base_score = weighted_sum * 50 + 50                        │
│  deviation = base_score - 50                                │
│  adjusted_score = 50 + (deviation * confidence)             │
│                                                             │
│  quality_impact = base_score - adjusted_score               │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│  Return Comprehensive Result                                │
│  • score_raw: Original directional score                    │
│  • score: Quality-adjusted score (for trading)              │
│  • confidence: Signal quality metric                        │
│  • consensus: Agreement level                               │
│  • disagreement: Conflict level                             │
│  • quality_impact: How much quality changed score           │
└─────────────────────────────────────────────────────────────┘
```

---

## Mathematical Formulation

### Current System

```python
# Step 1: Normalize component scores to [-1, 1]
normalized_i = (score_i - 50) / 50

# Step 2: Calculate weighted directional signal
weighted_sum = Σ(weight_i × normalized_i)

# Step 3: Map to [0, 100] range
base_score = weighted_sum × 50 + 50

# Step 4: Calculate quality metrics (separate)
variance = var(normalized_scores)
consensus = e^(-variance × 2)
confidence = |weighted_sum| × consensus
disagreement = variance
```

### Hybrid System

```python
# Steps 1-4: Same as current system
# ... (calculate base_score, consensus, confidence, disagreement)

# Step 5: NEW - Quality-adjusted score
deviation = base_score - 50
adjusted_score = 50 + (deviation × confidence)

# Step 6: Calculate quality impact
quality_impact = base_score - adjusted_score

# Return both scores for transparency
return {
    'score_raw': base_score,
    'score': adjusted_score,  # ← Use this for trading decisions
    'confidence': confidence,
    'consensus': consensus,
    'disagreement': disagreement,
    'quality_impact': quality_impact
}
```

### Key Formula: Quality Adjustment

```
adjusted_score = 50 + (deviation × confidence)
```

Where:
- `deviation = base_score - 50` (directional signal strength)
- `confidence = |weighted_sum| × exp(-variance × 2)` (quality metric)

**Behavior:**
- **High quality (confidence → 1):** adjusted_score ≈ base_score (minimal change)
- **Low quality (confidence → 0):** adjusted_score → 50 (pulled to neutral)
- **Automatic scaling:** Strong signals with low quality → moderate scores

---

## Worked Examples

### Example 1: 1000PEPEUSDT (Low Confidence)

**Input:**
```
Component Scores:
  Volume: 52.83, Technical: 44.72, Orderbook: 63.53
  Orderflow: 44.37, Price Structure: 44.18, Sentiment: 70.66
```

**Current System:**
```python
base_score = 52.36
confidence = 0.043
consensus = 0.918
disagreement = 0.0428

# Decision:
if base_score > 60: False  # Passes threshold
if confidence < 0.3: True  # FILTERED!

Result: Signal blocked despite score above neutral
```

**Hybrid System:**
```python
base_score = 52.36
deviation = 52.36 - 50 = 2.36
confidence = 0.043

adjusted_score = 50 + (2.36 × 0.043) = 50.10
quality_impact = 52.36 - 50.10 = -2.26

# Decision:
if adjusted_score > 60: False  # Naturally doesn't pass

Result: Score reflects reality - too weak to trade
```

**Interpretation:** Components agree on weak bearish bias (consensus 91.8%) but lack conviction. Quality adjustment suppresses signal by 2.26 points, bringing it to neutral zone.

---

### Example 2: Strong Signal with High Quality

**Input:**
```
Component Scores (hypothetical strong bullish):
  Volume: 75, Technical: 72, Orderbook: 78
  Orderflow: 68, Price Structure: 80, Sentiment: 85

Variance: 0.025 (low - components agree)
```

**Calculation:**
```python
base_score = 76.5
deviation = 76.5 - 50 = 26.5
consensus = exp(-0.025 × 2) = 0.951
confidence = 0.53 × 0.951 = 0.504

adjusted_score = 50 + (26.5 × 0.504) = 63.36
quality_impact = 76.5 - 63.36 = -13.14

# Decision:
if adjusted_score > 60: True  # Passes threshold

Result: Signal sent - strong and quality-confirmed
```

**Interpretation:** Strong bullish signal with moderate quality. Adjustment reduces score by 13 points but still actionable.

---

### Example 3: Neutral Signal with High Quality

**Input:**
```
Component Scores (balanced):
  All components near 50 ± 3

Variance: 0.005 (very low)
```

**Calculation:**
```python
base_score = 50.2
deviation = 50.2 - 50 = 0.2
consensus = exp(-0.005 × 2) = 0.990
confidence = 0.004 × 0.990 = 0.004

adjusted_score = 50 + (0.2 × 0.004) = 50.001
quality_impact = 50.2 - 50.001 = ~0.2

Result: Neutral signal remains neutral regardless of quality
```

**Interpretation:** When signals are genuinely neutral, quality adjustment has minimal effect.

---

## Implementation Plan

### Phase 1: Core Algorithm Update

**File:** `src/core/analysis/confluence.py`

**Function:** `_calculate_confluence_score()`

```python
def _calculate_confluence_score(self, scores: Dict[str, float]) -> Dict[str, Any]:
    """
    Calculate confluence score with integrated quality adjustment.

    Returns both raw and quality-adjusted scores for transparency.

    Args:
        scores: Component scores [0, 100]

    Returns:
        dict: {
            'score_raw': float,        # Original directional score
            'score': float,            # Quality-adjusted (use for trading)
            'consensus': float,        # Agreement level [0, 1]
            'confidence': float,       # Signal quality [0, 1]
            'disagreement': float,     # Conflict level
            'quality_impact': float    # Score adjustment magnitude
        }
    """
    try:
        # Normalize scores to [-1, 1]
        normalized_signals = {
            name: np.clip((score - 50) / 50, -1, 1)
            for name, score in scores.items()
        }

        # Calculate weighted directional sum
        weighted_sum = sum(
            self.weights.get(name, 0) * normalized_signals[name]
            for name in scores.keys()
        )

        # Calculate signal variance (disagreement)
        signal_values = list(normalized_signals.values())
        signal_variance = np.var(signal_values) if len(signal_values) > 1 else 0.0

        # Calculate consensus (low variance = high consensus)
        consensus = np.exp(-signal_variance * 2)

        # Calculate confidence (direction strength × consensus)
        confidence = abs(weighted_sum) * consensus

        # HYBRID APPROACH: Calculate both scores
        base_score = float(np.clip(weighted_sum * 50 + 50, 0, 100))
        deviation = base_score - 50
        adjusted_score = float(np.clip(50 + (deviation * confidence), 0, 100))

        return {
            'score_raw': base_score,
            'score': adjusted_score,  # Quality-adjusted score
            'consensus': float(consensus),
            'confidence': float(confidence),
            'disagreement': float(signal_variance),
            'quality_impact': base_score - adjusted_score
        }

    except Exception as e:
        self.logger.error(f"Error calculating confluence score: {e}", exc_info=True)
        raise
```

### Phase 2: Signal Generator Simplification

**File:** `src/signal_generation/signal_generator.py`

**Before (Lines 675-715):**
```python
# Complex two-stage filtering
if confidence is not None and confidence < 0.3:
    logger.warning("⊘ SIGNAL FILTERED: Low confidence")
    return None

if disagreement is not None and disagreement > 0.3:
    logger.warning("⊘ SIGNAL FILTERED: High disagreement")
    return None
```

**After:**
```python
# Simple single-threshold check
# Quality is already integrated into confluence_score
# No additional filtering needed!

# Optional: Log quality metrics for monitoring
if confidence is not None:
    logger.info(f"[QUALITY] {symbol} - Confidence: {confidence:.3f}, "
                f"Quality Impact: {quality_impact:.2f} points")
```

### Phase 3: Logging Updates

**File:** `src/core/formatting/formatter.py`

Update confluence breakdown display to show both scores:

```python
def format_enhanced_confluence_score_table(
    symbol: str,
    confluence_score: float,  # This is now adjusted_score
    score_raw: float,         # Add this parameter
    quality_impact: float,    # Add this parameter
    components: Dict[str, float],
    ...
):
    output = f"╔══ {symbol} CONFLUENCE ANALYSIS ══╗\n"
    output += "=" * 80 + "\n"
    output += f"Overall Score: {confluence_score:.2f} ({self._get_signal_label(confluence_score)})\n"
    output += f"Raw Score: {score_raw:.2f} (before quality adjustment)\n"
    output += f"Quality Impact: {quality_impact:+.2f} points\n"
    output += f"Reliability: {reliability:.0%} ({self._get_reliability_label(reliability)})\n"
    # ... rest of formatting
```

### Phase 4: Quality Metrics Tracker Update

**File:** `src/monitoring/quality_metrics_tracker.py`

Update to log both raw and adjusted scores:

```python
def log_quality_metrics(
    self,
    symbol: str,
    confluence_score: float,      # Adjusted score
    score_raw: float,             # Raw score
    quality_impact: float,        # New parameter
    consensus: float,
    confidence: float,
    disagreement: float,
    ...
):
    entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'symbol': symbol,
        'scores': {
            'adjusted': round(confluence_score, 2),
            'raw': round(score_raw, 2),
            'quality_impact': round(quality_impact, 2)
        },
        'quality_metrics': {
            'consensus': round(consensus, 4),
            'confidence': round(confidence, 4),
            'disagreement': round(disagreement, 4)
        },
        # ... rest of entry
    }
```

### Phase 5: Threshold Optimization

**Current:**
- Confluence threshold: ~60
- Confidence filter: 0.3
- Disagreement filter: 0.3

**After Hybrid:**
- Single confluence threshold: Optimize empirically (likely 55-65 range)
- Remove separate quality filters
- Monitor `quality_impact` statistics to understand adjustment magnitude

---

## Benefits Analysis

### 1. Simplified Trading Logic

**Before:**
```python
if score > 60 and confidence > 0.3 and disagreement < 0.3:
    send_signal()
```

**After:**
```python
if adjusted_score > 60:
    send_signal()
```

**Impact:** 66% reduction in decision complexity

### 2. Eliminated User Confusion

**Before:** "Why was my 70-score signal filtered?"
**After:** Score of 52 (adjusted) clearly shows why it wasn't traded

### 3. Automatic Quality Consideration

**Before:** Must remember to check filters
**After:** Quality automatically integrated - can't forget

### 4. Better Threshold Optimization

**Before:** Must optimize 3 thresholds (score, confidence, disagreement)
**After:** Optimize 1 threshold (adjusted score)

### 5. Preserved Transparency

**Before:** Quality metrics visible but separate
**After:** Quality metrics visible + see their impact on score

### 6. Improved Signal Quality

**Expected:** 20-30% reduction in false positives as weak signals naturally suppressed

---

## Trade-offs and Considerations

### Advantages ✅

1. **Simpler Logic:** One decision point instead of two
2. **Intuitive Scores:** Score reflects true tradability
3. **Automatic Filtering:** Weak signals naturally produce neutral scores
4. **Full Transparency:** Can see both raw and adjusted scores
5. **Easier Optimization:** Single threshold to tune
6. **Better UX:** No confusion about filtered high-score signals

### Potential Concerns ⚠️

1. **Score Scale Change:** Historical scores not directly comparable
   - **Mitigation:** Log both raw and adjusted; provide conversion guide

2. **Aggressive Suppression:** May over-suppress moderately weak signals
   - **Mitigation:** Monitor quality_impact distribution; adjust formula if needed

3. **Learning Curve:** Users must understand quality adjustment concept
   - **Mitigation:** Clear documentation; show quality_impact in logs

4. **Backtesting Needed:** Need to validate performance improvement
   - **Mitigation:** Run parallel systems; compare false positive rates

### Risks

1. **Lower Signal Volume:** May significantly reduce number of signals
   - **Impact:** Could miss some opportunities
   - **Mitigation:** Monitor signal count; adjust threshold if too restrictive

2. **Formula Optimization:** Deviation × confidence may not be optimal
   - **Alternative formulas:** Could try different quality integration methods
   - **Mitigation:** A/B test multiple formulas

---

## Testing Plan

### 1. Unit Tests

Test score calculation with various scenarios:

```python
def test_quality_adjusted_score_neutral():
    """Test that neutral signals remain neutral."""
    scores = {'comp1': 50, 'comp2': 50, 'comp3': 50}
    result = calculate_confluence_score(scores)
    assert 49 < result['score'] < 51
    assert result['quality_impact'] < 1.0

def test_quality_adjusted_score_weak_signal():
    """Test that weak signals are suppressed."""
    scores = {'comp1': 52, 'comp2': 48, 'comp3': 51}  # Weak, conflicting
    result = calculate_confluence_score(scores)
    assert result['score'] < result['score_raw']  # Adjusted lower
    assert result['quality_impact'] < -1.0

def test_quality_adjusted_score_strong_signal():
    """Test that strong quality signals preserved."""
    scores = {'comp1': 75, 'comp2': 73, 'comp3': 78}  # Strong, aligned
    result = calculate_confluence_score(scores)
    assert result['score'] > 60  # Still actionable
    assert result['confidence'] > 0.4
```

### 2. Integration Tests

Test full signal generation pipeline:

```python
async def test_signal_generation_with_quality_adjustment():
    """Test that signals are generated with quality-adjusted scores."""
    signal_generator = SignalGenerator()

    # Test case 1: Weak signal should not generate alert
    weak_data = create_weak_market_data()
    signal = await signal_generator.generate_signal(weak_data)
    assert signal is None  # Adjusted score too low

    # Test case 2: Strong signal should generate alert
    strong_data = create_strong_market_data()
    signal = await signal_generator.generate_signal(strong_data)
    assert signal is not None
    assert signal['confluence_score'] > 60
```

### 3. Historical Backtesting

Compare old vs new system on historical data:

```python
# Run on 1000+ historical confluence analyses
results = []
for historical_data in dataset:
    old_score = calculate_old_score(historical_data)
    new_score = calculate_new_score(historical_data)

    results.append({
        'old_score': old_score,
        'new_score': new_score,
        'old_filtered': was_filtered_old_system(historical_data),
        'new_filtered': new_score < 60,
        'quality_impact': old_score - new_score
    })

# Analyze:
# - How many signals change from tradeable to non-tradeable?
# - Distribution of quality_impact
# - False positive rate comparison (if labels available)
```

### 4. A/B Testing (Production)

Run both systems in parallel for 1-2 weeks:

- Track signal counts
- Track quality metrics distribution
- Monitor user feedback
- Compare performance if possible

---

## Rollout Strategy

### Stage 1: Implementation (Week 1)
- [ ] Implement hybrid score calculation in confluence.py
- [ ] Update signal_generator.py to use adjusted score
- [ ] Update logging to show both raw and adjusted scores
- [ ] Run unit tests

### Stage 2: Testing (Week 1-2)
- [ ] Run integration tests
- [ ] Backtest on historical data
- [ ] Analyze quality_impact distribution
- [ ] Validate score distributions

### Stage 3: Parallel Deployment (Week 2-3)
- [ ] Deploy to VPS alongside current system
- [ ] Log both systems' outputs for comparison
- [ ] Monitor signal volume changes
- [ ] Track false positive rates

### Stage 4: Full Rollout (Week 3-4)
- [ ] Switch to hybrid system as primary
- [ ] Remove old filtering logic
- [ ] Update documentation
- [ ] Monitor performance for 1 week

### Stage 5: Optimization (Week 4+)
- [ ] Analyze quality_impact statistics
- [ ] Optimize threshold based on results
- [ ] Consider formula adjustments if needed
- [ ] Document learnings

---

## Monitoring and Metrics

### Key Metrics to Track

1. **Signal Volume:**
   - Signals per day (before/after)
   - Expected: 20-40% reduction

2. **Quality Impact Distribution:**
   - Mean/median quality_impact
   - Percentage with |impact| > 5 points
   - Expected: Mean impact ~2-5 points

3. **Confidence Distribution:**
   - Before: Many signals with confidence < 0.3
   - After: Should see fewer weak confidence signals reaching users

4. **Score Distribution:**
   - Raw scores: Should remain similar
   - Adjusted scores: Should show compression toward 50

5. **False Positive Rate:**
   - If labels available: Track improvement
   - Expected: 20-30% reduction

### Alerting

Set up alerts for:
- Sudden drop in signal volume (>50% reduction)
- Quality_impact consistently < -10 (too aggressive)
- Confidence distribution shift (system behavior change)

---

## Future Enhancements

### 1. Adaptive Quality Weighting

Allow quality weight to vary by market regime:

```python
# High volatility: Be more selective (higher quality weight)
if market_volatility > 0.8:
    quality_weight = 1.2
else:
    quality_weight = 1.0

adjusted_score = 50 + (deviation * confidence * quality_weight)
```

### 2. Component-Specific Quality

Weight components differently based on their historical reliability:

```python
# Components with better track record get less quality penalty
reliability_weights = {
    'volume': 1.0,
    'orderflow': 0.9,  # Less reliable historically
    'sentiment': 0.8
}
```

### 3. Time-Decay Quality

Recent data more important than old:

```python
# Apply time decay to quality metrics
age_factor = exp(-data_age / decay_constant)
adjusted_confidence = confidence * age_factor
```

### 4. Machine Learning Optimization

Use ML to find optimal quality integration formula:

```python
# Learn optimal formula from historical performance
adjusted_score = ML_model(
    base_score, confidence, consensus,
    disagreement, market_features
)
```

---

## References

### Internal Documentation
- `ALERT_DESIGN_PRINCIPLES_COMPREHENSIVE.md` - Alert system design
- `QUALITY_FILTERING_IMPLEMENTATION_COMPLETE.md` - Current filtering system
- `QUALITY_FILTERING_SYSTEM_QA_REPORT.md` - Quality system validation

### Code Files
- `src/core/analysis/confluence.py:1870-1897` - Score calculation
- `src/signal_generation/signal_generator.py:675-715` - Quality filtering
- `src/monitoring/quality_metrics_tracker.py` - Metrics tracking

### Mathematical Background
- Exponential decay for consensus: Standard in signal processing
- Variance as disagreement measure: Statistical standard
- Multiplicative quality adjustment: Common in weighted scoring systems

---

## Conclusion

The Hybrid Quality-Adjusted Confluence Score represents a significant architectural improvement that:

1. **Simplifies** trading logic while maintaining transparency
2. **Eliminates** confusing filtered-but-high-score scenarios
3. **Integrates** quality directly into the core metric
4. **Preserves** all quality information for analysis
5. **Reduces** false positives through automatic suppression

**Recommendation:** Proceed with implementation following the phased rollout plan, with careful monitoring and A/B testing to validate improvements.

---

## Appendix A: Formula Comparison

| Metric | Current Formula | Hybrid Formula | Change |
|--------|----------------|----------------|--------|
| Base Score | `weighted_sum × 50 + 50` | Same | None |
| Consensus | `exp(-variance × 2)` | Same | None |
| Confidence | `abs(weighted_sum) × consensus` | Same | None |
| **Final Score** | **`base_score`** | **`50 + (deviation × confidence)`** | **NEW** |
| Quality Impact | N/A | `base_score - adjusted_score` | NEW |

## Appendix B: Example Score Scenarios

| Raw Score | Confidence | Adjusted Score | Quality Impact | Tradeable? |
|-----------|-----------|----------------|----------------|------------|
| 52 | 0.043 | 50.1 | -1.9 | ❌ No |
| 65 | 0.25 | 53.8 | -11.2 | ❌ No |
| 70 | 0.45 | 59.0 | -11.0 | ❌ Close |
| 75 | 0.60 | 65.0 | -10.0 | ✅ Yes |
| 80 | 0.75 | 72.5 | -7.5 | ✅ Yes |
| 85 | 0.85 | 79.8 | -5.2 | ✅ Yes |

**Pattern:** Higher confidence = less adjustment. Strong signals need ~0.5+ confidence to remain actionable.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-10
**Next Review:** After Phase 3 testing completion

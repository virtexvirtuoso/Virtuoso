-- ============================================================================
-- Orderflow Fix Validation Queries
-- Date: 2025-12-11
-- Purpose: Analyze SHORT signal performance before/after orderflow multiplier fix
-- ============================================================================

-- Context:
-- - OLD multipliers: buyer_aggression=35, seller_aggression=30
-- - NEW multipliers: buyer_aggression=50, seller_aggression=45
-- - Fix deployed: 2025-12-09
-- - Hypothesis: SHORT signals should show improved win rate

-- ============================================================================
-- 1. OVERALL SHORT SIGNAL PERFORMANCE
-- ============================================================================

-- Compare SHORT vs LONG win rates
SELECT
    signal_type,
    COUNT(*) as total_signals,
    COUNT(*) FILTER (WHERE outcome = 'win') as wins,
    COUNT(*) FILTER (WHERE outcome = 'loss') as losses,
    COUNT(*) FILTER (WHERE outcome = 'stopped_out') as stopped_out,
    ROUND(COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*), 2) as win_rate_pct,
    ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
    ROUND(AVG(CASE WHEN outcome = 'win' THEN pnl_pct END), 2) as avg_win_pct,
    ROUND(AVG(CASE WHEN outcome = 'loss' THEN pnl_pct END), 2) as avg_loss_pct,
    ROUND(AVG(r_multiple), 2) as avg_r_multiple
FROM trading_signals
WHERE status = 'closed'
AND outcome IN ('win', 'loss', 'stopped_out')
GROUP BY signal_type
ORDER BY signal_type;

-- ============================================================================
-- 2. PRE-FIX vs POST-FIX COMPARISON (VALIDATION COHORT)
-- ============================================================================

-- SHORT signals before and after fix
SELECT
    CASE
        WHEN is_validation_cohort = 1 THEN 'POST-FIX (New: 50/45)'
        ELSE 'PRE-FIX (Old: 35/30)'
    END as cohort,
    orderflow_config,
    COUNT(*) as total_signals,
    COUNT(*) FILTER (WHERE outcome = 'win') as wins,
    COUNT(*) FILTER (WHERE outcome = 'loss') as losses,
    ROUND(COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*), 2) as win_rate_pct,
    ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
    ROUND(AVG(CASE WHEN outcome = 'win' THEN pnl_pct END), 2) as avg_win_pct,
    ROUND(AVG(CASE WHEN outcome = 'loss' THEN pnl_pct END), 2) as avg_loss_pct,
    ROUND(AVG(r_multiple), 2) as avg_r_multiple,
    ROUND(AVG(duration_hours), 1) as avg_duration_hours
FROM trading_signals
WHERE signal_type = 'SHORT'
AND status = 'closed'
AND outcome IN ('win', 'loss', 'stopped_out')
GROUP BY is_validation_cohort, orderflow_config
ORDER BY is_validation_cohort;

-- ============================================================================
-- 3. DIVERGENCE PATTERN ANALYSIS
-- ============================================================================

-- SHORT signals by pattern type (divergence vs confirmation)
SELECT
    signal_pattern,
    divergence_type,
    COUNT(*) as total_signals,
    COUNT(*) FILTER (WHERE outcome = 'win') as wins,
    ROUND(COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*), 2) as win_rate_pct,
    ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
    ROUND(AVG(r_multiple), 2) as avg_r_multiple
FROM trading_signals
WHERE signal_type = 'SHORT'
AND status = 'closed'
AND outcome IN ('win', 'loss', 'stopped_out')
AND signal_pattern IS NOT NULL
GROUP BY signal_pattern, divergence_type
ORDER BY win_rate_pct DESC;

-- ============================================================================
-- 4. DAILY TREND ANALYSIS
-- ============================================================================

-- SHORT signal performance by day
SELECT
    DATE(created_at) as date,
    COUNT(*) as signals,
    COUNT(*) FILTER (WHERE outcome = 'win') as wins,
    ROUND(COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*), 2) as win_rate_pct,
    ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
    ROUND(AVG(confluence_score), 1) as avg_confluence_score,
    MAX(CASE WHEN is_validation_cohort = 1 THEN '✓' ELSE '' END) as post_fix
FROM trading_signals
WHERE signal_type = 'SHORT'
AND status = 'closed'
AND outcome IN ('win', 'loss', 'stopped_out')
AND created_at >= DATE('now', '-30 days')
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- ============================================================================
-- 5. ORDERFLOW TAG ANALYSIS
-- ============================================================================

-- Performance by orderflow characteristics
SELECT
    CASE
        WHEN orderflow_tags LIKE '%high_seller_aggression%' THEN 'High Seller Aggression'
        WHEN orderflow_tags LIKE '%high_buyer_aggression%' THEN 'High Buyer Aggression'
        WHEN orderflow_tags LIKE '%absorption%' THEN 'Absorption Detected'
        WHEN orderflow_tags LIKE '%large_orders%' THEN 'Large Orders'
        ELSE 'No Special Tags'
    END as orderflow_characteristic,
    COUNT(*) as signals,
    ROUND(COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*), 2) as win_rate_pct,
    ROUND(AVG(pnl_pct), 2) as avg_pnl_pct
FROM trading_signals
WHERE signal_type = 'SHORT'
AND status = 'closed'
AND outcome IN ('win', 'loss', 'stopped_out')
GROUP BY orderflow_characteristic
HAVING COUNT(*) >= 3  -- At least 3 samples
ORDER BY win_rate_pct DESC;

-- ============================================================================
-- 6. EXCURSION ANALYSIS (How far signals moved favorably/adversely)
-- ============================================================================

-- Compare MFE/MAE for winning vs losing SHORT signals
SELECT
    outcome,
    COUNT(*) as signals,
    ROUND(AVG(mfe_pct), 2) as avg_mfe_pct,
    ROUND(AVG(mae_pct), 2) as avg_mae_pct,
    ROUND(AVG(mfe_pct - mae_pct), 2) as avg_excursion_range,
    ROUND(AVG(pnl_pct / NULLIF(mfe_pct, 0) * 100), 2) as pnl_to_mfe_ratio
FROM trading_signals
WHERE signal_type = 'SHORT'
AND status = 'closed'
AND outcome IN ('win', 'loss')
AND mfe_pct IS NOT NULL
AND mae_pct IS NOT NULL
GROUP BY outcome;

-- ============================================================================
-- 7. CONFLUENCE SCORE CORRELATION
-- ============================================================================

-- Win rate by confluence score bucket (SHORT signals)
SELECT
    CASE
        WHEN confluence_score >= 80 THEN '80-100 (Extreme)'
        WHEN confluence_score >= 70 THEN '70-79 (Strong)'
        WHEN confluence_score >= 60 THEN '60-69 (Moderate)'
        WHEN confluence_score >= 50 THEN '50-59 (Weak)'
        ELSE 'Below 50'
    END as score_bucket,
    COUNT(*) as signals,
    ROUND(COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*), 2) as win_rate_pct,
    ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
    ROUND(AVG(r_multiple), 2) as avg_r_multiple
FROM trading_signals
WHERE signal_type = 'SHORT'
AND status = 'closed'
AND outcome IN ('win', 'loss', 'stopped_out')
GROUP BY score_bucket
ORDER BY MIN(confluence_score) DESC;

-- ============================================================================
-- 8. SYMBOL-SPECIFIC ANALYSIS
-- ============================================================================

-- Which symbols produce best SHORT signals?
SELECT
    symbol,
    COUNT(*) as signals,
    ROUND(COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*), 2) as win_rate_pct,
    ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
    ROUND(AVG(confluence_score), 1) as avg_confluence
FROM trading_signals
WHERE signal_type = 'SHORT'
AND status = 'closed'
AND outcome IN ('win', 'loss', 'stopped_out')
GROUP BY symbol
HAVING COUNT(*) >= 5  -- At least 5 signals
ORDER BY win_rate_pct DESC
LIMIT 10;

-- ============================================================================
-- 9. EXIT REASON DISTRIBUTION
-- ============================================================================

-- How are SHORT signals exiting?
SELECT
    exit_reason,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM trading_signals WHERE signal_type = 'SHORT' AND status = 'closed'), 2) as pct_of_total,
    ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
    ROUND(AVG(duration_hours), 1) as avg_duration_hours
FROM trading_signals
WHERE signal_type = 'SHORT'
AND status = 'closed'
AND exit_reason IS NOT NULL
GROUP BY exit_reason
ORDER BY count DESC;

-- ============================================================================
-- 10. VALIDATION SUMMARY REPORT
-- ============================================================================

-- Key metrics for validation report
SELECT
    '=== ORDERFLOW FIX VALIDATION SUMMARY ===' as report;

SELECT
    'Metric' as metric,
    'Pre-Fix (35/30)' as pre_fix,
    'Post-Fix (50/45)' as post_fix,
    'Delta' as delta
UNION ALL
SELECT
    'Total SHORT Signals',
    CAST((SELECT COUNT(*) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 0 AND status = 'closed') AS TEXT),
    CAST((SELECT COUNT(*) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 1 AND status = 'closed') AS TEXT),
    CAST((SELECT COUNT(*) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 1 AND status = 'closed') -
         (SELECT COUNT(*) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 0 AND status = 'closed') AS TEXT)
UNION ALL
SELECT
    'Win Rate %',
    CAST(ROUND((SELECT COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 0 AND status = 'closed'), 2) AS TEXT),
    CAST(ROUND((SELECT COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 1 AND status = 'closed'), 2) AS TEXT),
    CAST(ROUND((SELECT COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 1 AND status = 'closed') -
         (SELECT COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 0 AND status = 'closed'), 2) AS TEXT) || ' pp'
UNION ALL
SELECT
    'Avg P&L %',
    CAST(ROUND((SELECT AVG(pnl_pct) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 0 AND status = 'closed'), 2) AS TEXT),
    CAST(ROUND((SELECT AVG(pnl_pct) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 1 AND status = 'closed'), 2) AS TEXT),
    CAST(ROUND((SELECT AVG(pnl_pct) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 1 AND status = 'closed') -
         (SELECT AVG(pnl_pct) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 0 AND status = 'closed'), 2) AS TEXT)
UNION ALL
SELECT
    'Avg R-Multiple',
    CAST(ROUND((SELECT AVG(r_multiple) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 0 AND status = 'closed'), 2) AS TEXT),
    CAST(ROUND((SELECT AVG(r_multiple) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 1 AND status = 'closed'), 2) AS TEXT),
    CAST(ROUND((SELECT AVG(r_multiple) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 1 AND status = 'closed') -
         (SELECT AVG(r_multiple) FROM trading_signals WHERE signal_type = 'SHORT' AND is_validation_cohort = 0 AND status = 'closed'), 2) AS TEXT);

-- ============================================================================
-- 11. ACTIVE SIGNALS MONITORING
-- ============================================================================

-- Currently active SHORT signals (for live tracking)
SELECT
    signal_id,
    symbol,
    confluence_score,
    entry_price,
    current_price,
    signal_pattern,
    ROUND((julianday('now') - julianday(opened_at)) * 24, 1) as hours_active,
    ROUND(mfe_pct, 2) as mfe_pct,
    ROUND(mae_pct, 2) as mae_pct,
    is_validation_cohort,
    orderflow_config
FROM trading_signals
WHERE signal_type = 'SHORT'
AND status = 'active'
ORDER BY opened_at DESC;

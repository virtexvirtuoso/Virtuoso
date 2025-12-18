-- ============================================================================
-- Validation Queries for Performance Tracking Migration
-- Date: 2025-12-11
-- Purpose: Verify migration completed successfully
-- ============================================================================

-- ============================================================================
-- 1. VERIFY ALL COLUMNS EXIST
-- ============================================================================

SELECT
    'Column Check' as test_name,
    COUNT(*) as new_columns_added,
    CASE
        WHEN COUNT(*) = 24 THEN 'PASS'
        ELSE 'FAIL - Expected 24 columns'
    END as status
FROM pragma_table_info('trading_signals')
WHERE name IN (
    'outcome', 'status', 'pnl_pct', 'pnl_absolute', 'r_multiple',
    'exit_price', 'confirmed_price', 'opened_at', 'closed_at', 'duration_hours',
    'signal_pattern', 'divergence_type', 'orderflow_tags',
    'mfe_pct', 'mae_pct', 'mfe_price', 'mae_price', 'mfe_at', 'mae_at',
    'is_validation_cohort', 'orderflow_config', 'trigger_component',
    'exit_reason', 'performance_notes'
);

-- ============================================================================
-- 2. VERIFY COLUMN TYPES
-- ============================================================================

SELECT
    name as column_name,
    type as data_type,
    [notnull] as not_null,
    dflt_value as default_value
FROM pragma_table_info('trading_signals')
WHERE name IN (
    'outcome', 'status', 'pnl_pct', 'exit_price', 'opened_at',
    'signal_pattern', 'is_validation_cohort'
)
ORDER BY name;

-- ============================================================================
-- 3. VERIFY INDEXES CREATED
-- ============================================================================

SELECT
    'Index Check' as test_name,
    COUNT(*) as performance_indexes,
    CASE
        WHEN COUNT(*) >= 8 THEN 'PASS'
        ELSE 'FAIL - Expected at least 8 performance indexes'
    END as status
FROM sqlite_master
WHERE type = 'index'
AND tbl_name = 'trading_signals'
AND name LIKE 'idx_signals_%';

-- List all performance indexes
SELECT name as index_name, sql as index_definition
FROM sqlite_master
WHERE type = 'index'
AND tbl_name = 'trading_signals'
AND name LIKE 'idx_signals_%'
ORDER BY name;

-- ============================================================================
-- 4. VERIFY EXISTING DATA INTEGRITY
-- ============================================================================

-- Check that existing signals weren't corrupted
SELECT
    'Data Integrity Check' as test_name,
    COUNT(*) as total_signals,
    COUNT(DISTINCT signal_id) as unique_signals,
    CASE
        WHEN COUNT(*) = COUNT(DISTINCT signal_id) THEN 'PASS'
        ELSE 'FAIL - Duplicate signal_ids found'
    END as status
FROM trading_signals;

-- ============================================================================
-- 5. VERIFY DEFAULT VALUES
-- ============================================================================

-- Check that new columns have appropriate defaults for existing data
SELECT
    'Default Values Check' as test_name,
    COUNT(*) as signals_with_pending_outcome,
    COUNT(*) FILTER (WHERE status = 'active') as signals_with_active_status,
    COUNT(*) FILTER (WHERE is_validation_cohort = 0) as signals_not_in_cohort,
    CASE
        WHEN COUNT(*) = COUNT(*) FILTER (WHERE outcome = 'pending' OR outcome IS NULL)
        THEN 'PASS'
        ELSE 'FAIL - Unexpected outcome values'
    END as status
FROM trading_signals;

-- ============================================================================
-- 6. TEST QUERY PERFORMANCE WITH NEW INDEXES
-- ============================================================================

-- Test 1: Query by outcome and status (should use idx_signals_outcome)
EXPLAIN QUERY PLAN
SELECT signal_id, symbol, signal_type, pnl_pct
FROM trading_signals
WHERE outcome = 'win' AND status = 'closed';

-- Test 2: Query by direction and outcome (should use idx_signals_type_outcome)
EXPLAIN QUERY PLAN
SELECT signal_type, COUNT(*) as count, AVG(pnl_pct) as avg_pnl
FROM trading_signals
WHERE signal_type = 'SHORT' AND outcome IN ('win', 'loss') AND status = 'closed'
GROUP BY signal_type;

-- Test 3: Query by date range (should use idx_signals_daily_performance)
EXPLAIN QUERY PLAN
SELECT DATE(created_at) as date, signal_type, outcome, COUNT(*) as count
FROM trading_signals
WHERE created_at > datetime('now', '-7 days')
GROUP BY DATE(created_at), signal_type, outcome;

-- Test 4: Validation cohort query (should use idx_signals_validation)
EXPLAIN QUERY PLAN
SELECT orderflow_config, signal_type, outcome, COUNT(*) as count, AVG(pnl_pct) as avg_pnl
FROM trading_signals
WHERE is_validation_cohort = 1
GROUP BY orderflow_config, signal_type, outcome;

-- Test 5: Pattern analysis (should use idx_signals_pattern)
EXPLAIN QUERY PLAN
SELECT signal_pattern, signal_type, outcome, COUNT(*) as count
FROM trading_signals
WHERE signal_pattern = 'divergence'
GROUP BY signal_pattern, signal_type, outcome;

-- ============================================================================
-- 7. VERIFY CHECK CONSTRAINTS
-- ============================================================================

-- Attempt to insert invalid outcome (should fail)
-- Uncomment to test:
-- INSERT INTO trading_signals (signal_id, symbol, signal_type, confluence_score, timestamp, outcome)
-- VALUES ('test_invalid', 'BTCUSDT', 'LONG', 50.0, strftime('%s', 'now') * 1000, 'invalid_outcome');
-- Expected: CHECK constraint failed

-- Attempt to insert invalid status (should fail)
-- Uncomment to test:
-- INSERT INTO trading_signals (signal_id, symbol, signal_type, confluence_score, timestamp, status)
-- VALUES ('test_invalid', 'BTCUSDT', 'LONG', 50.0, strftime('%s', 'now') * 1000, 'invalid_status');
-- Expected: CHECK constraint failed

-- ============================================================================
-- 8. SUMMARY REPORT
-- ============================================================================

SELECT
    '=== MIGRATION VALIDATION SUMMARY ===' as summary;

SELECT
    'Total Columns' as metric,
    (SELECT COUNT(*) FROM pragma_table_info('trading_signals')) as value,
    '44 expected (20 original + 24 new)' as expected;

SELECT
    'Total Indexes' as metric,
    COUNT(*) as value,
    '14+ expected (6 original + 8+ new)' as expected
FROM sqlite_master
WHERE type = 'index'
AND tbl_name = 'trading_signals';

SELECT
    'Total Signals' as metric,
    COUNT(*) as value,
    'Should match pre-migration count' as expected
FROM trading_signals;

SELECT
    'Signals with Default Values' as metric,
    COUNT(*) as value,
    'All existing signals should have defaults' as expected
FROM trading_signals
WHERE outcome = 'pending' OR outcome IS NULL;

-- ============================================================================
-- 9. SAMPLE DATA INSPECTION
-- ============================================================================

-- Show structure of a few signals with new columns
SELECT
    signal_id,
    symbol,
    signal_type,
    outcome,
    status,
    pnl_pct,
    signal_pattern,
    is_validation_cohort,
    orderflow_config,
    created_at
FROM trading_signals
ORDER BY created_at DESC
LIMIT 5;

-- ============================================================================
-- Migration: Add Performance Tracking to trading_signals
-- Date: 2025-12-11
-- Purpose: Track signal outcomes, P&L, and execution metrics for validation
-- ============================================================================

-- Add performance tracking columns
-- All columns are nullable to handle historical data that won't have these values

-- ============================================================================
-- OUTCOME TRACKING
-- ============================================================================

-- Signal outcome: 'pending', 'win', 'loss', 'stopped_out', 'expired'
ALTER TABLE trading_signals
ADD COLUMN outcome TEXT DEFAULT 'pending'
CHECK (outcome IN ('pending', 'win', 'loss', 'stopped_out', 'expired'));

-- Signal status: 'active', 'closed', 'cancelled'
ALTER TABLE trading_signals
ADD COLUMN status TEXT DEFAULT 'active'
CHECK (status IN ('active', 'closed', 'cancelled'));

-- ============================================================================
-- P&L METRICS
-- ============================================================================

-- Percentage gain/loss from entry to exit (e.g., 2.5 for +2.5%, -1.3 for -1.3%)
ALTER TABLE trading_signals
ADD COLUMN pnl_pct REAL;

-- Absolute P&L in quote currency (if position size known)
ALTER TABLE trading_signals
ADD COLUMN pnl_absolute REAL;

-- R-multiple (P&L as multiple of initial risk)
ALTER TABLE trading_signals
ADD COLUMN r_multiple REAL;

-- ============================================================================
-- EXECUTION PRICES
-- ============================================================================

-- Actual exit price when signal closed
ALTER TABLE trading_signals
ADD COLUMN exit_price REAL;

-- Price when signal was validated/confirmed (may differ from entry_price)
ALTER TABLE trading_signals
ADD COLUMN confirmed_price REAL;

-- ============================================================================
-- TIMESTAMPS
-- ============================================================================

-- When signal was opened/entered
ALTER TABLE trading_signals
ADD COLUMN opened_at DATETIME;

-- When signal was closed/exited
ALTER TABLE trading_signals
ADD COLUMN closed_at DATETIME;

-- Duration in hours that signal was active
ALTER TABLE trading_signals
ADD COLUMN duration_hours REAL;

-- ============================================================================
-- PATTERN CLASSIFICATION
-- ============================================================================

-- Signal pattern type: 'divergence', 'confirmation', 'momentum', 'reversal', 'continuation'
ALTER TABLE trading_signals
ADD COLUMN signal_pattern TEXT
CHECK (signal_pattern IN ('divergence', 'confirmation', 'momentum', 'reversal', 'continuation', 'other'));

-- Specific divergence type if applicable: 'bullish_divergence', 'bearish_divergence', 'hidden_divergence'
ALTER TABLE trading_signals
ADD COLUMN divergence_type TEXT;

-- Orderflow pattern tags (JSON array): e.g., ["large_buyer_aggression", "absorption"]
ALTER TABLE trading_signals
ADD COLUMN orderflow_tags TEXT;

-- ============================================================================
-- EXCURSION METRICS
-- ============================================================================

-- Maximum favorable excursion (MFE) - best price reached in % from entry
ALTER TABLE trading_signals
ADD COLUMN mfe_pct REAL;

-- Maximum adverse excursion (MAE) - worst price reached in % from entry
ALTER TABLE trading_signals
ADD COLUMN mae_pct REAL;

-- Price at which MFE occurred
ALTER TABLE trading_signals
ADD COLUMN mfe_price REAL;

-- Price at which MAE occurred
ALTER TABLE trading_signals
ADD COLUMN mae_price REAL;

-- Timestamp when MFE occurred
ALTER TABLE trading_signals
ADD COLUMN mfe_at DATETIME;

-- Timestamp when MAE occurred
ALTER TABLE trading_signals
ADD COLUMN mae_at DATETIME;

-- ============================================================================
-- VALIDATION METRICS
-- ============================================================================

-- Whether this signal is part of the orderflow fix validation cohort
ALTER TABLE trading_signals
ADD COLUMN is_validation_cohort BOOLEAN DEFAULT 0;

-- Orderflow multiplier configuration at signal generation (e.g., '50_45' for new, '35_30' for old)
ALTER TABLE trading_signals
ADD COLUMN orderflow_config TEXT;

-- Component that triggered the signal ('orderflow_divergence', 'orderflow_confirmation', etc.)
ALTER TABLE trading_signals
ADD COLUMN trigger_component TEXT;

-- ============================================================================
-- ADDITIONAL METADATA
-- ============================================================================

-- Exit reason: 'target_hit', 'stop_loss', 'manual_close', 'time_exit', 'reversal_signal'
ALTER TABLE trading_signals
ADD COLUMN exit_reason TEXT;

-- Notes/comments about signal performance
ALTER TABLE trading_signals
ADD COLUMN performance_notes TEXT;

-- ============================================================================
-- CREATE PERFORMANCE INDEXES
-- ============================================================================

-- Index for outcome queries (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_signals_outcome
ON trading_signals(outcome, status);

-- Index for direction + outcome analysis
CREATE INDEX IF NOT EXISTS idx_signals_type_outcome
ON trading_signals(signal_type, outcome)
WHERE status = 'closed';

-- Index for pattern analysis
CREATE INDEX IF NOT EXISTS idx_signals_pattern
ON trading_signals(signal_pattern, signal_type, outcome);

-- Index for time-based performance queries
CREATE INDEX IF NOT EXISTS idx_signals_closed_at
ON trading_signals(closed_at DESC)
WHERE closed_at IS NOT NULL;

-- Index for validation cohort queries
CREATE INDEX IF NOT EXISTS idx_signals_validation
ON trading_signals(is_validation_cohort, orderflow_config, signal_type, outcome)
WHERE is_validation_cohort = 1;

-- Composite index for daily aggregations
CREATE INDEX IF NOT EXISTS idx_signals_daily_performance
ON trading_signals(DATE(created_at), signal_type, outcome, status);

-- Index for divergence pattern queries
CREATE INDEX IF NOT EXISTS idx_signals_divergence
ON trading_signals(divergence_type, signal_type, outcome)
WHERE divergence_type IS NOT NULL;

-- Index for P&L analysis
CREATE INDEX IF NOT EXISTS idx_signals_pnl
ON trading_signals(pnl_pct, signal_type, created_at)
WHERE pnl_pct IS NOT NULL;

-- ============================================================================
-- VERIFY MIGRATION
-- ============================================================================

-- This will be run separately but documenting expected column count
-- SELECT COUNT(*) as new_columns FROM pragma_table_info('trading_signals')
-- WHERE name IN (
--   'outcome', 'status', 'pnl_pct', 'pnl_absolute', 'r_multiple',
--   'exit_price', 'confirmed_price', 'opened_at', 'closed_at', 'duration_hours',
--   'signal_pattern', 'divergence_type', 'orderflow_tags',
--   'mfe_pct', 'mae_pct', 'mfe_price', 'mae_price', 'mfe_at', 'mae_at',
--   'is_validation_cohort', 'orderflow_config', 'trigger_component',
--   'exit_reason', 'performance_notes'
-- );
-- Expected: 24 new columns

-- ============================================================================
-- NOTES FOR APPLICATION CODE
-- ============================================================================

-- 1. UPDATING OUTCOME:
--    - Update when signal reaches target or stop loss
--    - Calculate duration_hours: (closed_at - opened_at) in hours
--    - Set status = 'closed'
--
-- 2. CALCULATING PNL:
--    For LONG: pnl_pct = ((exit_price - entry_price) / entry_price) * 100
--    For SHORT: pnl_pct = ((entry_price - exit_price) / entry_price) * 100
--    r_multiple = pnl_pct / risk_pct (where risk_pct is distance to stop loss)
--
-- 3. TAGGING PATTERN:
--    - Check orderflow component scores for divergence patterns
--    - Check if orderflow score contradicts price action (divergence)
--    - Check if orderflow confirms price action (confirmation)
--
-- 4. TRACKING EXCURSIONS:
--    - Update MFE/MAE continuously while signal is active
--    - For LONG: mfe_pct = max((high - entry) / entry * 100)
--    - For LONG: mae_pct = min((low - entry) / entry * 100)
--    - For SHORT: swap the logic
--
-- 5. VALIDATION COHORT:
--    - Set is_validation_cohort = 1 for signals after 2025-12-09
--    - Set orderflow_config = '50_45' for new config
--    - Tag historical signals with orderflow_config = '35_30' if needed

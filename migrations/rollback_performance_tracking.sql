-- ============================================================================
-- Rollback: Remove Performance Tracking from trading_signals
-- Date: 2025-12-11
-- Purpose: Rollback migration if issues occur
-- WARNING: This will permanently delete performance data
-- ============================================================================

-- ============================================================================
-- DROP INDEXES FIRST
-- ============================================================================

DROP INDEX IF EXISTS idx_signals_outcome;
DROP INDEX IF EXISTS idx_signals_type_outcome;
DROP INDEX IF EXISTS idx_signals_pattern;
DROP INDEX IF EXISTS idx_signals_closed_at;
DROP INDEX IF EXISTS idx_signals_validation;
DROP INDEX IF EXISTS idx_signals_daily_performance;
DROP INDEX IF EXISTS idx_signals_divergence;
DROP INDEX IF EXISTS idx_signals_pnl;

-- ============================================================================
-- REMOVE COLUMNS
-- ============================================================================

-- SQLite doesn't support DROP COLUMN directly in older versions
-- We need to recreate the table without the new columns

-- Create backup of original data
CREATE TABLE trading_signals_backup AS
SELECT
    id,
    signal_id,
    symbol,
    signal_type,
    confluence_score,
    reliability,
    entry_price,
    stop_loss,
    current_price,
    timestamp,
    created_at,
    targets,
    components,
    interpretations,
    insights,
    influential_components,
    trade_params,
    sent_to_discord,
    json_path,
    pdf_path
FROM trading_signals;

-- Drop original table
DROP TABLE trading_signals;

-- Recreate original table structure
CREATE TABLE trading_signals (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Signal identification
    signal_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,  -- 'LONG' or 'SHORT'

    -- Scores and metrics
    confluence_score REAL NOT NULL,
    reliability REAL,  -- Overall signal reliability (0-1)

    -- Price and trade parameters
    entry_price REAL,
    stop_loss REAL,
    current_price REAL,

    -- Timestamp (milliseconds since epoch)
    timestamp INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- JSON fields for detailed data
    targets TEXT,  -- JSON array of target objects
    components TEXT,  -- JSON object with component scores
    interpretations TEXT,  -- JSON array of interpretations
    insights TEXT,  -- JSON array of actionable insights
    influential_components TEXT,  -- JSON array of influential component data
    trade_params TEXT,  -- JSON object with full trade parameters

    -- Metadata
    sent_to_discord BOOLEAN DEFAULT 0,
    json_path TEXT,
    pdf_path TEXT
);

-- Restore data
INSERT INTO trading_signals
SELECT * FROM trading_signals_backup;

-- Drop backup
DROP TABLE trading_signals_backup;

-- ============================================================================
-- RECREATE ORIGINAL INDEXES
-- ============================================================================

CREATE INDEX idx_trading_signals_symbol ON trading_signals(symbol);
CREATE INDEX idx_trading_signals_type ON trading_signals(signal_type);
CREATE INDEX idx_trading_signals_timestamp ON trading_signals(timestamp DESC);
CREATE INDEX idx_trading_signals_score ON trading_signals(confluence_score);
CREATE INDEX idx_trading_signals_created_at ON trading_signals(created_at DESC);
CREATE INDEX idx_trading_signals_analytics
    ON trading_signals(timestamp DESC, signal_type, confluence_score);

-- ============================================================================
-- VERIFY ROLLBACK
-- ============================================================================

-- Check that new columns are gone
SELECT COUNT(*) as remaining_columns FROM pragma_table_info('trading_signals');
-- Expected: 20 columns (original schema)
